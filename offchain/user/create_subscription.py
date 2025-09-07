import click
from pycardano import (
    Network,
    TransactionBuilder,
    AuxiliaryData,
    AlonzoMetadata,
    Metadata,
    TransactionOutput,
    Value,
)

from opshin.prelude import Token
from opshin.ledger.api_v2 import FinitePOSIXTime

from offchain.utils import get_contract, module_name, get_signing_info
from onchain import contract
from offchain.utils import context
from datetime import datetime, timedelta


@click.command()
@click.option('--user-wallet', '-u', default='user1', help='User wallet name (default: user1)')
@click.option('--model-owner-wallet', '-m', default='owner1', help='Model owner wallet name (default: owner1)')
@click.option('--payment-amount', '-p', default=1.0, type=float, help='Payment amount in ADA (default: 1.0)')
@click.option('--payment-interval', '-i', default=10, type=int, help='Payment interval in seconds (default: 10)')
@click.option('--initial-balance', '-b', default=4.0, type=float, help='Initial subscription balance in ADA (default: 4.0)')
@click.option('--network', '-n', type=click.Choice(['testnet', 'mainnet']), default='testnet', help='Network to use (default: testnet)')
def main(user_wallet: str, model_owner_wallet: str, payment_amount: float, payment_interval: int, initial_balance: float, network: str):
    """Create a new subscription with the specified parameters"""
    
    network_enum = Network.TESTNET if network == 'testnet' else Network.MAINNET
    
    # Convert ADA to lovelace
    payment_amount_lovelace = int(payment_amount * 1e6)
    initial_balance_lovelace = int(initial_balance * 1e6)
    
    # Validate inputs
    if payment_amount <= 0:
        click.echo("Error: Payment amount must be positive", err=True)
        return
    
    if payment_interval <= 0:
        click.echo("Error: Payment interval must be positive", err=True)
        return
        
    if initial_balance < payment_amount:
        click.echo("Error: Initial balance must be at least equal to payment amount", err=True)
        return

    (
        script,
        script_policy_id,
        script_address,
    ) = get_contract(module_name(contract))

    user_vkey, user_skey, user_address = get_signing_info(
        user_wallet, network=network_enum
    )

    model_owner_vkey, model_owner_skey, model_owner_address = get_signing_info(
        model_owner_wallet, network=network_enum
    )

    # Build the transaction
    builder = TransactionBuilder(context)
    builder.add_input_address(user_address)
    builder.auxiliary_data = AuxiliaryData(
        data=AlonzoMetadata(
            metadata=Metadata({674: {"msg": ["Create SmartContract Subscription"]}})
        )
    )

    # Build Subscription Datum
    datum = contract.SubscriptionDatum(
        user_address.payment_part.payload,
        model_owner_address.payment_part.payload,
        FinitePOSIXTime(
            int((datetime.utcnow() + timedelta(seconds=payment_interval)).timestamp() * 1000)
        ),
        int(payment_interval * 1000),  # Convert to milliseconds
        payment_amount_lovelace,
        Token(b"", b""),
        False,  # is_paused = False (new subscriptions start unpaused)
        FinitePOSIXTime(0),  # pause_start_time = 0 (not paused)
    )

    builder.add_output(
        TransactionOutput(
            address=script_address,
            amount=Value(
                coin=initial_balance_lovelace,
            ),
            datum=datum,
        )
    )

    # Sign the transaction
    signed_tx = builder.build_and_sign(
        signing_keys=[user_skey],
        change_address=user_address,
    )

    # Submit the transaction
    context.submit_tx(signed_tx.to_cbor())

    click.echo("\n✅ Subscription created successfully!")
    click.echo(f"User: {user_wallet}")
    click.echo(f"Model Owner: {model_owner_wallet}")
    click.echo(f"Payment Amount: {payment_amount} ADA")
    click.echo(f"Payment Interval: {payment_interval} seconds")
    click.echo(f"Initial Balance: {initial_balance} ADA")
    click.echo(f"Transaction ID: {signed_tx.id}")
    click.echo(f"Cardanoscan: https://preprod.cardanoscan.io/transaction/{signed_tx.id}")


if __name__ == "__main__":
    main()
