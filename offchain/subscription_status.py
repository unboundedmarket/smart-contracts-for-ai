"""
Check detailed status of a specific subscription
Shows payment history, remaining balance, and next payment information
"""

import click
import json
from datetime import datetime, timedelta
from typing import Optional
from pycardano import Network

from offchain.utils import (
    get_signing_info,
    get_contract,
    context,
    to_address,
    safe_decode_token_name,
    format_token_display_name,
)
from onchain import contract


def get_subscription_by_utxo(utxo_id: str) -> Optional[dict]:
    """Get subscription details by UTXO ID"""
    script, _, script_address = get_contract("contract")
    
    # Parse UTXO ID format: "transaction_id#index"
    try:
        tx_id, index = utxo_id.split('#')
        index = int(index)
    except ValueError:
        # Return None silently on format error in quiet mode
        return None
    
    for utxo in context.utxos(script_address):
        if (str(utxo.input.transaction_id) == tx_id and 
            utxo.input.index == index):
            try:
                datum = contract.SubscriptionDatum.from_cbor(utxo.output.datum.cbor)
                return analyze_subscription_status(datum, utxo)
            except Exception as e:
                # Error handling can be quiet for automation
                return None
    
    # Return None silently if not found
    return None


def get_user_subscription(wallet_name: str, network: Network) -> Optional[dict]:
    """Get subscription for a specific user wallet"""
    try:
        _, _, user_address = get_signing_info(wallet_name, network=network)
        script, _, script_address = get_contract("contract")
        user_pkh = to_address(user_address).payment_credential.credential_hash
        
        for utxo in context.utxos(script_address):
            try:
                datum = contract.SubscriptionDatum.from_cbor(utxo.output.datum.cbor)
                if datum.owner_pubkeyhash.payload == user_pkh.payload:
                    return analyze_subscription_status(datum, utxo)
            except Exception as e:
                continue
        
        # Return None silently if no subscription found
        return None
        
    except Exception as e:
        # Return None silently on error
        return None


def analyze_subscription_status(datum: contract.SubscriptionDatum, utxo) -> dict:
    """Analyze subscription and return detailed status information"""
    current_time = datetime.utcnow()
    next_payment = datetime.fromtimestamp(datum.next_payment_date.time / 1000)
    
    # Convert values
    payment_interval_ms = datum.payment_intervall
    payment_interval_days = payment_interval_ms / (1000 * 60 * 60 * 24)
    payment_amount_ada = datum.payment_amount / 1_000_000
    current_balance_ada = utxo.output.amount.coin / 1_000_000
    
    # Calculate payment cycles
    payments_remaining = int(current_balance_ada / payment_amount_ada) if payment_amount_ada > 0 else 0
    days_until_next_payment = (next_payment - current_time).days
    is_overdue = current_time >= next_payment
    
    # Estimate subscription end date
    if payments_remaining > 0:
        total_days_remaining = payments_remaining * payment_interval_days
        estimated_end_date = next_payment + timedelta(days=total_days_remaining)
    else:
        estimated_end_date = next_payment
    
    # Payment token info
    token_policy = datum.payment_token.policy_id.payload.hex() if datum.payment_token.policy_id.payload else ""
    token_name = safe_decode_token_name(datum.payment_token.token_name)
    
    token_info = {
        "policy_id": token_policy,
        "token_name": token_name,
        "display_name": format_token_display_name(token_name, token_policy),
        "is_ada": not datum.payment_token.policy_id.payload and not datum.payment_token.token_name
    }
    
    return {
        "utxo_id": f"{utxo.input.transaction_id}#{utxo.input.index}",
        "subscription_address": str(utxo.output.address),
        "owner_pubkeyhash": datum.owner_pubkeyhash.payload.hex(),
        "model_owner_pubkeyhash": datum.model_owner_pubkeyhash.payload.hex(),
        
        # Payment details
        "payment_amount_ada": payment_amount_ada,
        "payment_interval_days": payment_interval_days,
        "current_balance_ada": current_balance_ada,
        "payments_remaining": payments_remaining,
        
        # Timing information
        "next_payment_date": next_payment,
        "days_until_next_payment": days_until_next_payment,
        "is_payment_overdue": is_overdue,
        "estimated_end_date": estimated_end_date,
        
        # Token information
        "payment_token": token_info,
        
        # Status
        "status": "OVERDUE" if is_overdue else "ACTIVE" if payments_remaining > 0 else "INSUFFICIENT_FUNDS",
        "can_make_payment": is_overdue and payments_remaining > 0,
        
        # Raw data for advanced users
        "raw_datum": {
            "next_payment_timestamp": datum.next_payment_date.time,
            "payment_interval_ms": payment_interval_ms,
            "payment_amount_lovelace": datum.payment_amount,
            "current_balance_lovelace": utxo.output.amount.coin
        }
    }


def print_subscription_status(status: dict, output_format: str = "text", quiet: bool = False):
    """Pretty print subscription status or output as JSON"""
    if output_format == "json":
        # Convert datetime objects to strings for JSON serialization
        json_status = status.copy()
        json_status['next_payment_date'] = status['next_payment_date'].strftime('%Y-%m-%d %H:%M:%S UTC')
        json_status['estimated_end_date'] = status['estimated_end_date'].strftime('%Y-%m-%d %H:%M:%S UTC')
        print(json.dumps(json_status, indent=2, default=str))
        return
    
    if quiet:
        # Quiet mode: CSV output for automation
        print(f"{status['utxo_id']},{status['status']},{status['payment_amount_ada']},{status['current_balance_ada']},{status['payments_remaining']},{status['days_until_next_payment']}")
        return
    
    # Original text output
    print(f"\n🔍 Subscription Status Report")
    print("=" * 50)
    
    print(f"\n📋 Basic Information:")
    print(f"   UTXO ID: {status['utxo_id']}")
    print(f"   Status: {status['status']}")
    print(f"   Contract Address: {status['subscription_address']}")
    
    print(f"\n👥 Participants:")
    print(f"   Owner (User): {status['owner_pubkeyhash'][:32]}...")
    print(f"   Model Owner: {status['model_owner_pubkeyhash'][:32]}...")
    
    print(f"\n💰 Payment Details:")
    token_display = status['payment_token']['display_name']
    print(f"   Payment Amount: {status['payment_amount_ada']} {token_display}")
    print(f"   Payment Interval: {status['payment_interval_days']} days")
    print(f"   Current Balance: {status['current_balance_ada']} {token_display}")
    print(f"   Payments Remaining: {status['payments_remaining']}")
    
    print(f"\n⏰ Timing Information:")
    print(f"   Next Payment: {status['next_payment_date'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    if status['is_payment_overdue']:
        print(f"   ⚠️  Payment is OVERDUE by {abs(status['days_until_next_payment'])} days")
    else:
        print(f"   ⏳ Payment due in {status['days_until_next_payment']} days")
    
    print(f"   Estimated End: {status['estimated_end_date'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    print(f"\n🚀 Actions Available:")
    if status['can_make_payment']:
        print("   ✅ Model owner can redeem payment")
    else:
        print("   ❌ Payment not yet due")
    
    if status['payments_remaining'] == 0:
        print("   ⚠️  Insufficient funds - subscription will end after next payment")
    
    if not status['payment_token']['is_ada']:
        print(f"\n🪙 Token Information:")
        print(f"   Policy ID: {status['payment_token']['policy_id']}")
        print(f"   Token Name: {status['payment_token']['token_name']}")
    
    print(f"\n🔧 Raw Data (for developers):")
    print(f"   Next Payment Timestamp: {status['raw_datum']['next_payment_timestamp']}")
    print(f"   Payment Interval (ms): {status['raw_datum']['payment_interval_ms']}")
    print(f"   Payment Amount (lovelace): {status['raw_datum']['payment_amount_lovelace']}")
    print(f"   Current Balance (lovelace): {status['raw_datum']['current_balance_lovelace']}")


@click.command()
@click.option('--utxo-id', '-u', help='Specific UTXO ID to check (format: transaction_id#index)')
@click.option('--wallet', '-w', help='Wallet name to check subscription for (user1, owner1, etc.)')
@click.option('--network', '-n', type=click.Choice(['testnet', 'mainnet']), default='testnet',
              help='Network to use')
@click.option('--format', '-f', type=click.Choice(['text', 'json']), default='text',
              help='Output format: text (human-readable) or json (machine-readable)')
@click.option('--quiet', '-q', is_flag=True, help='Quiet mode: minimal output suitable for scripts')
def main(utxo_id: Optional[str], wallet: Optional[str], network: str, format: str, quiet: bool):
    """Check detailed status of a subscription"""
    
    network_enum = Network.TESTNET if network == 'testnet' else Network.MAINNET
    
    if utxo_id:
        status = get_subscription_by_utxo(utxo_id)
    elif wallet:
        status = get_user_subscription(wallet, network_enum)
    else:
        if not quiet:
            print("Please provide either --utxo-id or --wallet parameter")
        return
    
    if status:
        print_subscription_status(status, format, quiet)
    else:
        if not quiet:
            print("Subscription not found or error occurred")


if __name__ == "__main__":
    main()
