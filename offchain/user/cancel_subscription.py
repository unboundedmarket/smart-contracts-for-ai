import datetime
from typing import Optional

import click
import fire
import pycardano
from pycardano import (
    TransactionBuilder,
    TransactionOutput,
    Asset,
    AuxiliaryData,
    AlonzoMetadata,
    Metadata,
    Network,
    ScriptHash,
)

from offchain.utils import (
    sorted_utxos,
    get_signing_info,
    get_contract,
    context,
    to_address,
)
from onchain import contract


@click.command()
def main():
    user_vkey, user_skey, user_address = get_signing_info("user1")

    script, _, script_address = get_contract("contract")

    # Find an open subscription belonging to user
    owner_order_utxo = None
    owner_order_datum = None
    for utxo in context.utxos(script_address):
        try:
            datum = contract.SubscriptionDatum.from_cbor(utxo.output.datum.cbor)
        except Exception as e:
            continue
        owner_pkh = datum.owner_pubkeyhash

        if owner_pkh != to_address(user_address).payment_credential.credential_hash:
            continue

        owner_order_datum = datum
        owner_order_utxo = utxo

    if owner_order_utxo is None:
        print("No orders found")
        return

    update_redeemer = pycardano.Redeemer(contract.UpdateSubscription())

    # Build the transaction
    builder = TransactionBuilder(context)
    builder.auxiliary_data = AuxiliaryData(
        data=AlonzoMetadata(metadata=Metadata({674: {"msg": ["Cancel User Subscription"]}}))
    )

    user_utxos = context.utxos(user_address)

    for u in user_utxos:
        builder.add_input(u)

    builder.add_script_input(
        owner_order_utxo,
        script,
        None,
        update_redeemer,
    )

    # Sign the transaction
    signed_tx = builder.build_and_sign(
        signing_keys=[user_skey],
        change_address=user_address,
        auto_ttl_offset=1000,
        auto_validity_start_offset=0,
    )

    # Submit the transaction
    context.submit_tx(signed_tx.to_cbor())

    print(f"transaction id: {signed_tx.id}")
    print(f"Cardanoscan: https://preprod.cardanoscan.io/transaction/{signed_tx.id}")


if __name__ == "__main__":
    main()
