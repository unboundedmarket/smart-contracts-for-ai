"""
Track payment history for subscriptions
Shows transaction history, payment patterns, and revenue analytics
"""

import click
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pycardano import Network
from collections import defaultdict

from offchain.utils import (
    get_signing_info,
    get_contract,
    context,
    to_address,
)
from onchain import contract


def get_transaction_history(script_address, lookback_days: int = 30) -> List[dict]:
    """Get transaction history for the contract address"""
    # Note: This is a simplified version. In a real implementation, you would
    # need to use blockchain indexing services like Blockfrost, Koios, or Ogmios
    # to get comprehensive transaction history.
    
    transactions = []
    
    try:
        # Get current UTXOs (active subscriptions)
        current_utxos = context.utxos(script_address)
        
        for utxo in current_utxos:
            try:
                datum = contract.SubscriptionDatum.from_cbor(utxo.output.datum.cbor)
                
                # Estimate transaction info from current state
                # In a real implementation, you'd query historical data
                transaction_info = {
                    "tx_id": str(utxo.input.transaction_id),
                    "type": "create_subscription",  # This is current state, so it was created
                    "timestamp": datetime.utcnow(),  # Placeholder - would be actual tx timestamp
                    "amount_ada": utxo.output.amount.coin / 1_000_000,
                    "owner_pubkeyhash": datum.owner_pubkeyhash.payload.hex(),
                    "model_owner_pubkeyhash": datum.model_owner_pubkeyhash.payload.hex(),
                    "payment_amount_ada": datum.payment_amount / 1_000_000,
                    "next_payment_date": datetime.fromtimestamp(datum.next_payment_date.time / 1000),
                    "status": "active"
                }
                transactions.append(transaction_info)
                
            except Exception as e:
                print(f"Error parsing UTXO {utxo.input}: {e}")
                continue
    
    except Exception as e:
        print(f"Error fetching transaction history: {e}")
    
    return transactions


def get_payment_history_for_user(wallet_name: str, network: Network, lookback_days: int = 30) -> List[dict]:
    """Get payment history for a specific user"""
    try:
        _, _, user_address = get_signing_info(wallet_name, network=network)
        script, _, script_address = get_contract("contract")
        user_pkh = to_address(user_address).payment_credential.credential_hash
        
        all_transactions = get_transaction_history(script_address, lookback_days)
        
        # Filter transactions for this user
        user_transactions = [
            tx for tx in all_transactions 
            if tx['owner_pubkeyhash'] == user_pkh.payload.hex()
        ]
        
        return user_transactions
        
    except Exception as e:
        print(f"Error getting payment history for {wallet_name}: {e}")
        return []


def get_payment_history_for_model_owner(wallet_name: str, network: Network, lookback_days: int = 30) -> List[dict]:
    """Get payment history for a specific model owner"""
    try:
        _, _, model_owner_address = get_signing_info(wallet_name, network=network)
        script, _, script_address = get_contract("contract")
        model_owner_pkh = to_address(model_owner_address).payment_credential.credential_hash
        
        all_transactions = get_transaction_history(script_address, lookback_days)
        
        # Filter transactions for this model owner
        model_owner_transactions = [
            tx for tx in all_transactions 
            if tx['model_owner_pubkeyhash'] == model_owner_pkh.payload.hex()
        ]
        
        return model_owner_transactions
        
    except Exception as e:
        print(f"Error getting payment history for {wallet_name}: {e}")
        return []


def analyze_payment_patterns(transactions: List[dict]) -> dict:
    """Analyze payment patterns and generate statistics"""
    if not transactions:
        return {
            "total_transactions": 0,
            "total_volume_ada": 0,
            "avg_payment_ada": 0,
            "unique_users": 0,
            "unique_model_owners": 0,
            "transactions_by_type": {},
            "daily_volume": {},
            "payment_frequency": {}
        }
    
    # Basic statistics
    total_transactions = len(transactions)
    total_volume = sum(tx['amount_ada'] for tx in transactions)
    avg_payment = total_volume / total_transactions if total_transactions > 0 else 0
    
    # Unique participants
    unique_users = len(set(tx['owner_pubkeyhash'] for tx in transactions))
    unique_model_owners = len(set(tx['model_owner_pubkeyhash'] for tx in transactions))
    
    # Transactions by type
    transactions_by_type = defaultdict(int)
    for tx in transactions:
        transactions_by_type[tx['type']] += 1
    
    # Daily volume (simplified - would need actual timestamps)
    daily_volume = defaultdict(float)
    for tx in transactions:
        date_key = tx['timestamp'].strftime('%Y-%m-%d')
        daily_volume[date_key] += tx['amount_ada']
    
    # Payment frequency analysis
    payment_amounts = [tx['payment_amount_ada'] for tx in transactions if 'payment_amount_ada' in tx]
    payment_frequency = defaultdict(int)
    for amount in payment_amounts:
        # Round to nearest 0.1 ADA for frequency analysis
        rounded_amount = round(amount, 1)
        payment_frequency[f"{rounded_amount} ADA"] += 1
    
    return {
        "total_transactions": total_transactions,
        "total_volume_ada": total_volume,
        "avg_payment_ada": avg_payment,
        "unique_users": unique_users,
        "unique_model_owners": unique_model_owners,
        "transactions_by_type": dict(transactions_by_type),
        "daily_volume": dict(daily_volume),
        "payment_frequency": dict(payment_frequency)
    }


def print_payment_history(transactions: List[dict], title: str):
    """Pretty print payment history"""
    print(f"\n{title}")
    print("=" * len(title))
    
    if not transactions:
        print("No payment history found.")
        return
    
    # Sort by timestamp (most recent first)
    sorted_transactions = sorted(transactions, key=lambda x: x['timestamp'], reverse=True)
    
    for i, tx in enumerate(sorted_transactions, 1):
        print(f"\n{i}. Transaction {tx['tx_id'][:16]}...")
        print(f"   Type: {tx['type'].replace('_', ' ').title()}")
        print(f"   Date: {tx['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"   Amount: {tx['amount_ada']:.6f} ADA")
        print(f"   Status: {tx['status'].upper()}")
        print(f"   Owner: {tx['owner_pubkeyhash'][:16]}...")
        print(f"   Model Owner: {tx['model_owner_pubkeyhash'][:16]}...")
        if 'payment_amount_ada' in tx:
            print(f"   Payment Amount: {tx['payment_amount_ada']:.6f} ADA")
        if 'next_payment_date' in tx:
            print(f"   Next Payment: {tx['next_payment_date'].strftime('%Y-%m-%d %H:%M:%S UTC')}")


def print_payment_analytics(analytics: dict):
    """Print payment analytics and statistics"""
    print(f"\n📊 Payment Analytics")
    print("=" * 30)
    
    print(f"\n💰 Volume Statistics:")
    print(f"   Total Transactions: {analytics['total_transactions']}")
    print(f"   Total Volume: {analytics['total_volume_ada']:.6f} ADA")
    print(f"   Average Payment: {analytics['avg_payment_ada']:.6f} ADA")
    
    print(f"\n👥 Participants:")
    print(f"   Unique Users: {analytics['unique_users']}")
    print(f"   Unique Model Owners: {analytics['unique_model_owners']}")
    
    if analytics['transactions_by_type']:
        print(f"\n📋 Transaction Types:")
        for tx_type, count in analytics['transactions_by_type'].items():
            print(f"   {tx_type.replace('_', ' ').title()}: {count}")
    
    if analytics['daily_volume']:
        print(f"\n📅 Daily Volume (Last 7 days):")
        sorted_days = sorted(analytics['daily_volume'].items(), reverse=True)[:7]
        for date, volume in sorted_days:
            print(f"   {date}: {volume:.6f} ADA")
    
    if analytics['payment_frequency']:
        print(f"\n💸 Common Payment Amounts:")
        sorted_amounts = sorted(analytics['payment_frequency'].items(), 
                              key=lambda x: x[1], reverse=True)[:5]
        for amount, count in sorted_amounts:
            print(f"   {amount}: {count} transactions")


@click.command()
@click.option('--wallet', '-w', help='Wallet name to check payment history for')
@click.option('--role', '-r', type=click.Choice(['user', 'owner', 'all']), default='all',
              help='Role: user (subscriber), owner (model owner), or all payments')
@click.option('--days', '-d', default=30, help='Number of days to look back (default: 30)')
@click.option('--analytics', '-a', is_flag=True, help='Show analytics and statistics')
@click.option('--network', '-n', type=click.Choice(['testnet', 'mainnet']), default='testnet',
              help='Network to use')
def main(wallet: Optional[str], role: str, days: int, analytics: bool, network: str):
    """Show payment history and analytics"""
    
    network_enum = Network.TESTNET if network == 'testnet' else Network.MAINNET
    
    if wallet and role in ['user', 'owner']:
        if role == 'user':
            transactions = get_payment_history_for_user(wallet, network_enum, days)
            title = f"Payment History for User {wallet}"
        else:  # role == 'owner'
            transactions = get_payment_history_for_model_owner(wallet, network_enum, days)
            title = f"Payment History for Model Owner {wallet}"
    else:
        # Show all payment history
        script, _, script_address = get_contract("contract")
        transactions = get_transaction_history(script_address, days)
        title = f"All Payment History (Last {days} days)"
    
    # Print transaction history
    print_payment_history(transactions, title)
    
    # Print analytics if requested
    if analytics:
        payment_analytics = analyze_payment_patterns(transactions)
        print_payment_analytics(payment_analytics)
    
    # Note about limitations
    print(f"\n📝 Note:")
    print(f"   This is a simplified implementation showing current subscription states.")
    print(f"   For complete transaction history, integrate with blockchain indexing services")
    print(f"   like Blockfrost, Koios, or Ogmios for historical transaction data.")


if __name__ == "__main__":
    main()
