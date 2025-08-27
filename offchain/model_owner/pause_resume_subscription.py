"""
Pause or resume subscription to temporarily halt payments
Allows model owners to suspend service during maintenance or upgrades
"""

import click
from datetime import datetime
from typing import Optional
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
)
from onchain import contract


def find_subscription_for_model_owner(model_owner_address, utxo_id: Optional[str] = None) -> Optional[dict]:
    """Find subscription(s) belonging to a model owner"""
    script, _, script_address = get_contract("contract")
    model_owner_pkh = to_address(model_owner_address).payment_credential.credential_hash
    
    subscriptions = []
    
    for utxo in context.utxos(script_address):
        try:
            datum = contract.SubscriptionDatum.from_cbor(utxo.output.datum.cbor)
            
            # Check if this subscription belongs to the model owner
            if datum.model_owner_pubkeyhash.payload == model_owner_pkh.payload:
                subscription_info = {
                    "utxo": utxo,
                    "datum": datum,
                    "utxo_id": f"{utxo.input.transaction_id}#{utxo.input.index}",
                    "is_paused": getattr(datum, 'is_paused', False),
                    "pause_start_time": getattr(datum, 'pause_start_time', None),
                    "owner_pubkeyhash": datum.owner_pubkeyhash.payload.hex()
                }
                
                # If specific UTXO ID requested, return only that one
                if utxo_id and subscription_info["utxo_id"] == utxo_id:
                    return subscription_info
                
                subscriptions.append(subscription_info)
                
        except Exception as e:
            print(f"Error parsing UTXO {utxo.input}: {e}")
            continue
    
    if utxo_id:
        return None  # Specific UTXO not found
    
    return subscriptions


def pause_subscription(
    model_owner_wallet: str,
    utxo_id: Optional[str] = None,
    network: Network = Network.TESTNET,
    dry_run: bool = False
) -> Optional[str]:
    """Pause a subscription to temporarily halt payments"""
    
    # Get model owner signing info
    model_owner_vkey, model_owner_skey, model_owner_address = get_signing_info(
        model_owner_wallet, network=network
    )
    
    # Find subscription to pause
    if utxo_id:
        subscription = find_subscription_for_model_owner(model_owner_address, utxo_id)
        if not subscription:
            print(f"Subscription with UTXO ID {utxo_id} not found for {model_owner_wallet}")
            return None
    else:
        subscriptions = find_subscription_for_model_owner(model_owner_address)
        if not subscriptions:
            print(f"No subscriptions found for model owner {model_owner_wallet}")
            return None
        if len(subscriptions) > 1:
            print(f"Multiple subscriptions found. Please specify --utxo-id:")
            for sub in subscriptions:
                status = "PAUSED" if sub['is_paused'] else "ACTIVE"
                print(f"  {sub['utxo_id']} - {status}")
            return None
        subscription = subscriptions[0]
    
    # Check if already paused
    if subscription['is_paused']:
        print(f"Subscription {subscription['utxo_id']} is already paused")
        return None
    
    print(f"Pausing subscription {subscription['utxo_id'][:16]}...")
    print(f"Owner: {subscription['owner_pubkeyhash'][:16]}...")
    
    if dry_run:
        print("🔍 Dry run mode - transaction not submitted")
        return None
    
    try:
        # Get contract info
        script, _, script_address = get_contract("contract")
        
        # Get model owner's UTXOs for fees
        model_owner_utxos = context.utxos(model_owner_address)
        
        # Build the transaction
        builder = TransactionBuilder(context)
        builder.auxiliary_data = AuxiliaryData(
            data=AlonzoMetadata(
                metadata=Metadata({674: {"msg": ["Pause Subscription"]}})
            )
        )
        
        # Add model owner UTXOs as regular inputs
        for utxo in model_owner_utxos:
            builder.add_input(utxo)
        
        # Create pause redeemer
        pause_redeemer = Redeemer(contract.PauseResumeSubscription(pause=True))
        
        # Add subscription UTXO as script input
        builder.add_script_input(
            subscription['utxo'],
            script,
            None,
            pause_redeemer
        )
        
        # Create updated datum with pause information
        current_time_ms = int(datetime.utcnow().timestamp() * 1000)
        paused_datum = contract.SubscriptionDatum(
            subscription['datum'].owner_pubkeyhash,
            subscription['datum'].model_owner_pubkeyhash,
            subscription['datum'].next_payment_date,
            subscription['datum'].payment_intervall,
            subscription['datum'].payment_amount,
            subscription['datum'].payment_token,
            True,  # is_paused = True
            contract.FinitePOSIXTime(current_time_ms),  # pause_start_time = now
        )
        
        # Add output back to contract (same funds, updated datum)
        builder.add_output(
            TransactionOutput(
                address=script_address,
                amount=subscription['utxo'].output.amount,
                datum=paused_datum,
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
        print(f"\n✅ Subscription paused successfully!")
        print(f"Transaction ID: {tx_id}")
        print(f"Cardanoscan: https://preprod.cardanoscan.io/transaction/{tx_id}")
        
        return tx_id
        
    except Exception as e:
        print(f"\n❌ Error pausing subscription: {e}")
        return None


def resume_subscription(
    model_owner_wallet: str,
    utxo_id: Optional[str] = None,
    network: Network = Network.TESTNET,
    dry_run: bool = False
) -> Optional[str]:
    """Resume a paused subscription and extend payment date by pause duration"""
    
    # Get model owner signing info
    model_owner_vkey, model_owner_skey, model_owner_address = get_signing_info(
        model_owner_wallet, network=network
    )
    
    # Find subscription to resume
    if utxo_id:
        subscription = find_subscription_for_model_owner(model_owner_address, utxo_id)
        if not subscription:
            print(f"Subscription with UTXO ID {utxo_id} not found for {model_owner_wallet}")
            return None
    else:
        subscriptions = find_subscription_for_model_owner(model_owner_address)
        if not subscriptions:
            print(f"No subscriptions found for model owner {model_owner_wallet}")
            return None
        
        # Filter for paused subscriptions
        paused_subs = [sub for sub in subscriptions if sub['is_paused']]
        if not paused_subs:
            print(f"No paused subscriptions found for {model_owner_wallet}")
            return None
        
        if len(paused_subs) > 1:
            print(f"Multiple paused subscriptions found. Please specify --utxo-id:")
            for sub in paused_subs:
                pause_duration = (datetime.utcnow().timestamp() * 1000) - sub['pause_start_time'].time
                pause_days = pause_duration / (1000 * 60 * 60 * 24)
                print(f"  {sub['utxo_id']} - PAUSED for {pause_days:.1f} days")
            return None
        subscription = paused_subs[0]
    
    # Check if actually paused
    if not subscription['is_paused']:
        print(f"Subscription {subscription['utxo_id']} is not paused")
        return None
    
    # Calculate pause duration
    current_time_ms = datetime.utcnow().timestamp() * 1000
    pause_duration_ms = current_time_ms - subscription['pause_start_time'].time
    pause_duration_days = pause_duration_ms / (1000 * 60 * 60 * 24)
    
    print(f"Resuming subscription {subscription['utxo_id'][:16]}...")
    print(f"Owner: {subscription['owner_pubkeyhash'][:16]}...")
    print(f"Paused for: {pause_duration_days:.1f} days")
    print(f"Payment date will be extended by {pause_duration_days:.1f} days")
    
    if dry_run:
        print("🔍 Dry run mode - transaction not submitted")
        return None
    
    try:
        # Get contract info
        script, _, script_address = get_contract("contract")
        
        # Get model owner's UTXOs for fees
        model_owner_utxos = context.utxos(model_owner_address)
        
        # Build the transaction
        builder = TransactionBuilder(context)
        builder.auxiliary_data = AuxiliaryData(
            data=AlonzoMetadata(
                metadata=Metadata({674: {"msg": ["Resume Subscription"]}})
            )
        )
        
        # Add model owner UTXOs as regular inputs
        for utxo in model_owner_utxos:
            builder.add_input(utxo)
        
        # Create resume redeemer
        resume_redeemer = Redeemer(contract.PauseResumeSubscription(pause=False))
        
        # Add subscription UTXO as script input
        builder.add_script_input(
            subscription['utxo'],
            script,
            None,
            resume_redeemer
        )
        
        # Create updated datum with resume information
        # Extend next payment date by pause duration
        extended_payment_date = contract.FinitePOSIXTime(
            subscription['datum'].next_payment_date.time + int(pause_duration_ms)
        )
        
        resumed_datum = contract.SubscriptionDatum(
            subscription['datum'].owner_pubkeyhash,
            subscription['datum'].model_owner_pubkeyhash,
            extended_payment_date,
            subscription['datum'].payment_intervall,
            subscription['datum'].payment_amount,
            subscription['datum'].payment_token,
            False,  # is_paused = False
            contract.FinitePOSIXTime(0),  # pause_start_time = 0 (reset)
        )
        
        # Add output back to contract (same funds, updated datum)
        builder.add_output(
            TransactionOutput(
                address=script_address,
                amount=subscription['utxo'].output.amount,
                datum=resumed_datum,
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
        print(f"\n✅ Subscription resumed successfully!")
        print(f"Transaction ID: {tx_id}")
        print(f"Cardanoscan: https://preprod.cardanoscan.io/transaction/{tx_id}")
        
        return tx_id
        
    except Exception as e:
        print(f"\n❌ Error resuming subscription: {e}")
        return None


@click.command()
@click.option('--wallet', '-w', required=True, help='Model owner wallet name (owner1, etc.)')
@click.option('--action', '-a', type=click.Choice(['pause', 'resume']), required=True,
              help='Action to perform: pause or resume')
@click.option('--utxo-id', '-u', help='Specific subscription UTXO ID (format: transaction_id#index)')
@click.option('--dry-run', '-d', is_flag=True, help='Simulate transaction without submitting')
@click.option('--network', '-n', type=click.Choice(['testnet', 'mainnet']), default='testnet',
              help='Network to use')
def main(wallet: str, action: str, utxo_id: Optional[str], dry_run: bool, network: str):
    """Pause or resume subscription payments"""
    
    network_enum = Network.TESTNET if network == 'testnet' else Network.MAINNET
    
    print(f"\n🔧 Subscription {action.title()} Tool")
    print("=" * 40)
    
    if action == 'pause':
        if not dry_run:
            confirm = click.confirm(f"\nPause subscription for {wallet}? This will halt payments until resumed.")
            if not confirm:
                print("Pause operation cancelled.")
                return
        
        tx_id = pause_subscription(wallet, utxo_id, network_enum, dry_run)
        
    else:  # resume
        if not dry_run:
            confirm = click.confirm(f"\nResume subscription for {wallet}? Payment date will be extended by pause duration.")
            if not confirm:
                print("Resume operation cancelled.")
                return
        
        tx_id = resume_subscription(wallet, utxo_id, network_enum, dry_run)
    
    if tx_id and not dry_run:
        print(f"\n🎉 Subscription {action} completed successfully!")
        print(f"Monitor the transaction status on Cardanoscan.")


if __name__ == "__main__":
    main()
