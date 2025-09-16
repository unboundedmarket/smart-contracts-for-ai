"""
Process multiple subscription payments in batch operations
Allows model owners to redeem payments from multiple subscriptions efficiently
"""

import click
from datetime import datetime
from typing import List, Dict, Optional
from pycardano import (
    Network,
    TransactionBuilder,
    TransactionOutput,
    AuxiliaryData,
    AlonzoMetadata,
    Metadata,
    Value,
    Redeemer
)

from offchain.utils import (
    get_signing_info,
    get_contract,
    context,
    to_address,
    sorted_utxos,
)
from onchain import contract
from opshin.prelude import FinitePOSIXTime


vltdef find_redeemable_subscriptions(model_owner_address, quiet: bool = False) -> List[dict]:
    """Find all subscriptions where payments are due for a model owner"""
    script, _, script_address = get_contract("contract")
    model_owner_pkh = to_address(model_owner_address).payment_credential.credential_hash
    
    redeemable_subscriptions = []
    current_time = datetime.utcnow()
    
    for utxo in context.utxos(script_address):
        try:
            datum = contract.SubscriptionDatum.from_cbor(utxo.output.datum.cbor)
            
            # Check if this subscription belongs to the model owner
            if datum.model_owner_pubkeyhash.payload != model_owner_pkh.payload:
                continue
            
            # Check if subscription is paused
            is_paused = getattr(datum, 'is_paused', False)
            if is_paused:
                continue  # Skip paused subscriptions
            
            # Check if payment is due
            next_payment = datetime.fromtimestamp(datum.next_payment_date.time / 1000)
            if current_time >= next_payment:
                # Check if there are sufficient funds
                current_balance = utxo.output.amount.coin
                if current_balance >= datum.payment_amount:
                    subscription_info = {
                        "utxo": utxo,
                        "datum": datum,
                        "current_balance_ada": current_balance / 1_000_000,
                        "payment_amount_ada": datum.payment_amount / 1_000_000,
                        "next_payment_date": next_payment,
                        "days_overdue": (current_time - next_payment).days,
                        "owner_pubkeyhash": datum.owner_pubkeyhash.payload.hex(),
                        "is_paused": is_paused
                    }
                    redeemable_subscriptions.append(subscription_info)
        
        except Exception as e:
            if not quiet:
                print(f"Error parsing UTXO {utxo.input}: {e}")
            continue
    
    return redeemable_subscriptions


def create_bulk_payment_transaction(
    model_owner_wallet: str, 
    subscription_limit: int = 5,
    network: Network = Network.TESTNET,
    dry_run: bool = False,
    quiet: bool = False
) -> Optional[str]:
    """Create a transaction to redeem payments from multiple subscriptions"""
    
    # Get model owner signing info
    model_owner_vkey, model_owner_skey, model_owner_address = get_signing_info(
        model_owner_wallet, network=network
    )
    
    # Get contract info
    script, _, script_address = get_contract("contract")
    
    # Find redeemable subscriptions
    redeemable_subs = find_redeemable_subscriptions(model_owner_address, quiet)
    
    if not redeemable_subs:
        if not quiet:
            print("No subscriptions with due payments found.")
        return None
    
    # Limit the number of subscriptions to process
    subs_to_process = redeemable_subs[:subscription_limit]
    
    if not quiet:
        print(f"\nProcessing {len(subs_to_process)} subscriptions:")
        total_payment_ada = 0
        
        for i, sub in enumerate(subs_to_process, 1):
            print(f"  {i}. {sub['payment_amount_ada']:.6f} ADA from {sub['owner_pubkeyhash'][:16]}... "
                  f"(overdue by {sub['days_overdue']} days)")
            total_payment_ada += sub['payment_amount_ada']
        
        print(f"\nTotal payment to redeem: {total_payment_ada:.6f} ADA")
    
    if dry_run:
        if not quiet:
            print("\n🔍 Dry run mode - transaction not submitted")
        return None
    
    try:
        # Get model owner's UTXOs for fees
        model_owner_utxos = context.utxos(model_owner_address)
        
        # Get all UTXOs that will be inputs (model owner + subscription UTXOs)
        all_subscription_utxos = [sub['utxo'] for sub in subs_to_process]
        all_input_utxos = model_owner_utxos + all_subscription_utxos
        all_inputs_sorted = sorted_utxos(all_input_utxos)
        
        # Build the transaction
        builder = TransactionBuilder(context)
        builder.auxiliary_data = AuxiliaryData(
            data=AlonzoMetadata(
                metadata=Metadata({674: {"msg": [f"Bulk payment redemption - {len(subs_to_process)} subscriptions"]}})
            )
        )
        
        # Add model owner UTXOs as regular inputs
        for utxo in model_owner_utxos:
            builder.add_input(utxo)
        
        # Add subscription UTXOs as script inputs with redeemers
        for sub in subs_to_process:
            utxo = sub['utxo']
            datum = sub['datum']
            
            # Find the index of this UTXO in the sorted list
            input_index = all_inputs_sorted.index(utxo)
            
            # Create unlock redeemer
            unlock_redeemer = Redeemer(contract.UnlockPayment(
                input_index=input_index,
                output_index=len(subs_to_process) - 1 - subs_to_process.index(sub),  # Output index for this subscription
            ))
            
            builder.add_script_input(
                utxo,
                script,
                None,
                unlock_redeemer
            )
        
        # Add outputs for each subscription (returning remaining funds)
        for i, sub in enumerate(subs_to_process):
            datum = sub['datum']
            utxo = sub['utxo']
            
            # Calculate new payment date
            new_payment_date = FinitePOSIXTime(
                datum.next_payment_date.time + datum.payment_intervall
            )
            
            # Create updated datum
            updated_datum = contract.SubscriptionDatum(
                datum.owner_pubkeyhash,
                datum.model_owner_pubkeyhash,
                new_payment_date,
                datum.payment_intervall,
                datum.payment_amount,
                datum.payment_token,
                getattr(datum, 'is_paused', False),
                getattr(datum, 'pause_start_time', contract.FinitePOSIXTime(0))
            )
            
            # Calculate remaining balance after payment
            remaining_balance = utxo.output.amount.coin - datum.payment_amount
            
            # Add output back to contract
            builder.add_output(
                TransactionOutput(
                    address=script_address,
                    amount=Value(coin=remaining_balance),
                    datum=updated_datum,
                )
            )
        
        # Sign and submit the transaction
        signed_tx = builder.build_and_sign(
            signing_keys=[model_owner_skey],
            change_address=model_owner_address,
            auto_ttl_offset=1000,
            auto_validity_start_offset=0,
        )
        
        # Submit the transaction
        context.submit_tx(signed_tx.to_cbor())
        
        tx_id = str(signed_tx.id)
        if not quiet:
            print(f"\n✅ Bulk payment transaction submitted!")
            print(f"Transaction ID: {tx_id}")
            print(f"Cardanoscan: https://preprod.cardanoscan.io/transaction/{tx_id}")
        else:
            print(tx_id)  # Just print the transaction ID in quiet mode
        
        return tx_id
        
    except Exception as e:
        if not quiet:
            print(f"\n❌ Error creating bulk payment transaction: {e}")
        return None


def simulate_bulk_payment_savings(model_owner_wallet: str, network: Network = Network.TESTNET, quiet: bool = False):
    """Simulate potential savings from bulk payment processing"""
    model_owner_vkey, model_owner_skey, model_owner_address = get_signing_info(
        model_owner_wallet, network=network
    )
    
    redeemable_subs = find_redeemable_subscriptions(model_owner_address, quiet)
    
    if not redeemable_subs:
        if not quiet:
            print("No redeemable subscriptions found.")
        return
    
    # Estimate transaction fees (simplified)
    base_fee_ada = 0.17  # Base transaction fee
    script_fee_per_input_ada = 0.05  # Additional fee per script input
    
    individual_tx_fees = len(redeemable_subs) * (base_fee_ada + script_fee_per_input_ada)
    bulk_tx_fee = base_fee_ada + (len(redeemable_subs) * script_fee_per_input_ada)
    
    savings_ada = individual_tx_fees - bulk_tx_fee
    savings_percent = (savings_ada / individual_tx_fees) * 100 if individual_tx_fees > 0 else 0
    
    total_payment_ada = sum(sub['payment_amount_ada'] for sub in redeemable_subs)
    
    if quiet:
        # Quiet mode: CSV output for automation
        print(f"{len(redeemable_subs)},{total_payment_ada:.6f},{savings_ada:.6f},{savings_percent:.1f}")
    else:
        print(f"\n💰 Bulk Payment Simulation")
        print("=" * 40)
        print(f"Redeemable Subscriptions: {len(redeemable_subs)}")
        print(f"Total Payment Value: {total_payment_ada:.6f} ADA")
        print(f"\n📊 Fee Comparison:")
        print(f"Individual Transactions: {individual_tx_fees:.6f} ADA")
        print(f"Bulk Transaction: {bulk_tx_fee:.6f} ADA")
        print(f"Estimated Savings: {savings_ada:.6f} ADA ({savings_percent:.1f}%)")
        
        if len(redeemable_subs) > 1:
            print(f"\n✅ Bulk processing recommended for {len(redeemable_subs)} subscriptions")
        else:
            print(f"\n💡 Single subscription - no bulk processing benefit")


@click.command()
@click.option('--wallet', '-w', required=True, help='Model owner wallet name (owner1, etc.)')
@click.option('--limit', '-l', default=5, help='Maximum number of subscriptions to process (default: 5)')
@click.option('--dry-run', '-d', is_flag=True, help='Simulate transaction without submitting')
@click.option('--simulate', '-s', is_flag=True, help='Show potential savings from bulk processing')
@click.option('--network', '-n', type=click.Choice(['testnet', 'mainnet']), default='testnet',
              help='Network to use')
@click.option('--quiet', '-q', is_flag=True, help='Quiet mode: minimal output suitable for scripts')
def main(wallet: str, limit: int, dry_run: bool, simulate: bool, network: str, quiet: bool):
    """Process multiple subscription payments in bulk"""
    
    network_enum = Network.TESTNET if network == 'testnet' else Network.MAINNET
    
    if simulate:
        simulate_bulk_payment_savings(wallet, network_enum, quiet)
        return
    
    # Find and display redeemable subscriptions
    model_owner_vkey, model_owner_skey, model_owner_address = get_signing_info(
        wallet, network=network_enum
    )
    
    redeemable_subs = find_redeemable_subscriptions(model_owner_address, quiet)
    
    if not redeemable_subs:
        if not quiet:
            print(f"No subscriptions with due payments found for {wallet}")
        return
    
    if not quiet:
        print(f"\n🔍 Found {len(redeemable_subs)} redeemable subscriptions for {wallet}")
    
    if not dry_run and not quiet:
        # Calculate total payment value for confirmation
        subs_to_process = redeemable_subs[:limit]
        total_payment_ada = sum(sub['payment_amount_ada'] for sub in subs_to_process)
        
        print(f"WARNING: This will process {len(subs_to_process)} subscription payments totaling {total_payment_ada:.6f} ADA")
        confirm = click.confirm(f"Are you sure you want to proceed with bulk payment redemption?", default=False)
        if not confirm:
            print("Bulk payment cancelled.")
            return
    
    # Process the bulk payment
    tx_id = create_bulk_payment_transaction(
        wallet, 
        subscription_limit=limit,
        network=network_enum,
        dry_run=dry_run,
        quiet=quiet
    )
    
    if tx_id and not dry_run and not quiet:
        print(f"\n🎉 Successfully processed bulk payment!")
        print(f"Monitor the transaction status on Cardanoscan.")


if __name__ == "__main__":
    main()
