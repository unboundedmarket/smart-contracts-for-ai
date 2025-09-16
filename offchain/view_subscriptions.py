"""
View all subscriptions for a user or model owner
Shows active subscriptions with their current status and details
"""

import click
import json
from datetime import datetime
from typing import List, Optional
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


def format_subscription_info(datum: contract.SubscriptionDatum, utxo, current_balance: int) -> dict:
    """Format subscription data for display"""
    next_payment = datetime.fromtimestamp(datum.next_payment_date.time / 1000)
    interval_days = datum.payment_intervall / (1000 * 60 * 60 * 24)  # Convert ms to days
    payment_ada = datum.payment_amount / 1_000_000  # Convert lovelace to ADA
    balance_ada = current_balance / 1_000_000
    
    # Safely handle token information
    token_policy = datum.payment_token.policy_id.payload.hex() if datum.payment_token.policy_id.payload else "ADA"
    token_name = safe_decode_token_name(datum.payment_token.token_name)
    token_display_name = format_token_display_name(token_name, token_policy)
    
    # Handle pause status
    is_paused = getattr(datum, 'is_paused', False)  # Default to False for backwards compatibility
    pause_start_time = getattr(datum, 'pause_start_time', None)
    
    # Calculate pause duration if paused
    pause_duration_days = 0
    if is_paused and pause_start_time:
        pause_duration = (datetime.utcnow().timestamp() * 1000) - pause_start_time.time
        pause_duration_days = pause_duration / (1000 * 60 * 60 * 24)
    
    return {
        "utxo_id": f"{utxo.input.transaction_id}#{utxo.input.index}",
        "owner_pubkeyhash": datum.owner_pubkeyhash.payload.hex(),
        "model_owner_pubkeyhash": datum.model_owner_pubkeyhash.payload.hex(),
        "next_payment_date": next_payment.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "payment_interval_days": interval_days,
        "payment_amount_ada": payment_ada,
        "current_balance_ada": balance_ada,
        "payments_remaining": int(balance_ada / payment_ada) if payment_ada > 0 else 0,
        "is_payment_due": datetime.utcnow() >= next_payment and not is_paused,
        "token_policy": token_policy,
        "token_name": token_name,
        "token_display_name": token_display_name,
        "is_paused": is_paused,
        "pause_duration_days": pause_duration_days,
        "pause_start_time": datetime.fromtimestamp(pause_start_time.time / 1000).strftime("%Y-%m-%d %H:%M:%S UTC") if is_paused and pause_start_time else None
    }


def get_subscriptions_for_user(user_address, quiet: bool = False) -> List[dict]:
    """Get all subscriptions where user is the owner"""
    script, _, script_address = get_contract("contract")
    user_pkh = to_address(user_address).payment_credential.credential_hash
    
    subscriptions = []
    
    for utxo in context.utxos(script_address):
        try:
            datum = contract.SubscriptionDatum.from_cbor(utxo.output.datum.cbor)
            if datum.owner_pubkeyhash.payload == user_pkh.payload:
                current_balance = utxo.output.amount.coin
                sub_info = format_subscription_info(datum, utxo, current_balance)
                subscriptions.append(sub_info)
        except Exception as e:
            if not quiet:
                print(f"Error parsing UTXO {utxo.input}: {e}")
            continue
    
    return subscriptions


def get_subscriptions_for_model_owner(model_owner_address, quiet: bool = False) -> List[dict]:
    """Get all subscriptions where user is the model owner"""
    script, _, script_address = get_contract("contract")
    model_owner_pkh = to_address(model_owner_address).payment_credential.credential_hash
    
    subscriptions = []
    
    for utxo in context.utxos(script_address):
        try:
            datum = contract.SubscriptionDatum.from_cbor(utxo.output.datum.cbor)
            if datum.model_owner_pubkeyhash.payload == model_owner_pkh.payload:
                current_balance = utxo.output.amount.coin
                sub_info = format_subscription_info(datum, utxo, current_balance)
                subscriptions.append(sub_info)
        except Exception as e:
            if not quiet:
                print(f"Error parsing UTXO {utxo.input}: {e}")
            continue
    
    return subscriptions


def get_all_subscriptions(quiet: bool = False) -> List[dict]:
    """Get all active subscriptions in the system"""
    script, _, script_address = get_contract("contract")
    
    subscriptions = []
    
    for utxo in context.utxos(script_address):
        try:
            datum = contract.SubscriptionDatum.from_cbor(utxo.output.datum.cbor)
            current_balance = utxo.output.amount.coin
            sub_info = format_subscription_info(datum, utxo, current_balance)
            subscriptions.append(sub_info)
        except Exception as e:
            if not quiet:
                print(f"Error parsing UTXO {utxo.input}: {e}")
            continue
    
    return subscriptions


def print_subscriptions(subscriptions: List[dict], title: str, output_format: str = "text", quiet: bool = False):
    """Pretty print subscription information or output as JSON"""
    if output_format == "json":
        # Prepare JSON output
        json_data = {
            "title": title,
            "subscriptions": subscriptions,
            "summary": {
                "total_subscriptions": len(subscriptions),
                "overdue_payments": sum(1 for sub in subscriptions if sub['is_payment_due']),
                "total_locked_ada": sum(sub['current_balance_ada'] for sub in subscriptions),
                "paused_subscriptions": sum(1 for sub in subscriptions if sub['is_paused'])
            }
        }
        print(json.dumps(json_data, indent=2, default=str))
        return
    
    if quiet:
        # Quiet mode: minimal output
        if not subscriptions:
            print("0")
            return
        print(f"{len(subscriptions)}")
        for sub in subscriptions:
            status = "PAUSED" if sub['is_paused'] else "OVERDUE" if sub['is_payment_due'] else "ACTIVE"
            print(f"{sub['utxo_id']},{status},{sub['current_balance_ada']},{sub['payment_amount_ada']}")
        return
    
    # Original text output
    print(f"\n{title}")
    print("=" * len(title))
    
    if not subscriptions:
        print("No subscriptions found.")
        return
    
    for i, sub in enumerate(subscriptions, 1):
        # Determine status display
        if sub['is_paused']:
            status = f"PAUSED (for {sub['pause_duration_days']:.1f} days)"
        elif sub['is_payment_due']:
            status = "OVERDUE"
        else:
            status = "ACTIVE"
        
        print(f"\n{i}. Subscription {sub['utxo_id'][:16]}...")
        print(f"   Status: {status}")
        print(f"   Next Payment: {sub['next_payment_date']}")
        print(f"   Payment Amount: {sub['payment_amount_ada']} ADA every {sub['payment_interval_days']} days")
        print(f"   Current Balance: {sub['current_balance_ada']} ADA")
        print(f"   Payments Remaining: {sub['payments_remaining']}")
        
        if sub['is_paused']:
            print(f"   Paused Since: {sub['pause_start_time']}")
        
        print(f"   Owner: {sub['owner_pubkeyhash'][:16]}...")
        print(f"   Model Owner: {sub['model_owner_pubkeyhash'][:16]}...")
        if sub['token_policy'] != "ADA":
            print(f"   Payment Token: {sub['token_display_name']} ({sub['token_policy'][:16]}...)")


@click.command()
@click.option('--wallet', '-w', default=None, help='Wallet name to check subscriptions for (user1, owner1, etc.)')
@click.option('--role', '-r', type=click.Choice(['user', 'owner', 'all']), default='all', 
              help='Role: user (subscriber), owner (model owner), or all subscriptions')
@click.option('--network', '-n', type=click.Choice(['testnet', 'mainnet']), default='testnet',
              help='Network to use')
@click.option('--format', '-f', type=click.Choice(['text', 'json']), default='text',
              help='Output format: text (human-readable) or json (machine-readable)')
@click.option('--quiet', '-q', is_flag=True, help='Quiet mode: minimal output suitable for scripts')
def main(wallet: Optional[str], role: str, network: str, format: str, quiet: bool):
    """View subscriptions based on wallet and role"""
    
    network_enum = Network.TESTNET if network == 'testnet' else Network.MAINNET
    
    if wallet and role in ['user', 'owner']:
        try:
            _, _, address = get_signing_info(wallet, network=network_enum)
            
            if role == 'user':
                subscriptions = get_subscriptions_for_user(address, quiet)
                print_subscriptions(subscriptions, f"Subscriptions owned by {wallet}", format, quiet)
            else:  # role == 'owner'
                subscriptions = get_subscriptions_for_model_owner(address, quiet)
                print_subscriptions(subscriptions, f"Subscriptions managed by {wallet}", format, quiet)
                
        except Exception as e:
            if not quiet:
                print(f"Error loading wallet {wallet}: {e}")
            return
    
    else:
        # Show all subscriptions
        subscriptions = get_all_subscriptions(quiet)
        print_subscriptions(subscriptions, "All Active Subscriptions", format, quiet)
        
        # Summary statistics (only show in text format and non-quiet mode)
        if format == "text" and not quiet:
            total_subs = len(subscriptions)
            overdue_subs = sum(1 for sub in subscriptions if sub['is_payment_due'])
            total_locked_ada = sum(sub['current_balance_ada'] for sub in subscriptions)
            
            print(f"\n📊 Summary:")
            print(f"   Total Subscriptions: {total_subs}")
            print(f"   Overdue Payments: {overdue_subs}")
            print(f"   Total Locked ADA: {total_locked_ada:.2f}")


if __name__ == "__main__":
    main()
