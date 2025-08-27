import datetime
from typing import Optional

import click
import fire
import pycardano
from pycardano import (
    TransactionBuilder,
    TransactionOutput,
    AuxiliaryData,
    AlonzoMetadata,
    Metadata,
    Value
    )

from offchain.utils import (
    sorted_utxos,
    get_signing_info,
    get_contract,
    context,
    to_address,
)
from onchain import contract
from opshin.prelude import FinitePOSIXTime


@click.command()
def main():
    model_owner_vkey, model_owner_skey, model_owner_address = get_signing_info("owner1")

    script, _, script_address = get_contract("contract")

    # Find an open subscription belonging to that model owner
    owner_utxo = None
    owner_datum = None
    for utxo in context.utxos(script_address):
        try:
            datum = contract.SubscriptionDatum.from_cbor(utxo.output.datum.cbor)
        except Exception as e:
            continue
        owner_pkh = datum.model_owner_pubkeyhash

        if owner_pkh != to_address(model_owner_address).payment_credential.credential_hash:
            continue

        owner_datum = datum
        owner_utxo = utxo

    if owner_utxo is None:
        print("No open subscription for this model found")
        return
    
    print("open subscriptions found")
    payment_utxos = context.utxos(model_owner_address)

    all_inputs_sorted = sorted_utxos(payment_utxos + [owner_utxo])
    owner_input_index = all_inputs_sorted.index(owner_utxo)

    # Build the transaction
    builder = TransactionBuilder(context)
    builder.auxiliary_data = AuxiliaryData(
        data=AlonzoMetadata(metadata=Metadata({674: {"msg": ["Cancel User Subscription"]}}))
    )

    for u in payment_utxos:
        builder.add_input(u)

    unlock_redeemer = pycardano.Redeemer(contract.UnlockPayment(
        input_index=owner_input_index,
        output_index=0,
    ))

    builder.add_script_input(
        owner_utxo,
        script,
        None,
        unlock_redeemer
    )

    next_payment_date = FinitePOSIXTime(owner_datum.next_payment_date.time + owner_datum.payment_intervall)

    updated_datum = contract.SubscriptionDatum(
        owner_datum.owner_pubkeyhash,
        owner_datum.model_owner_pubkeyhash,
        owner_datum.next_payment_date,
        owner_datum.payment_intervall,
        owner_datum.payment_amount,
        owner_datum.payment_token
    )

    print(owner_datum.to_cbor_hex(), "\n\n", updated_datum.to_cbor_hex())


    builder.add_output(
        TransactionOutput(
            address=script_address,
            amount=Value(
                coin=int(4e6)
            ),
            datum=updated_datum,
        )
    )

    # Sign the transaction
    signed_tx = builder.build_and_sign(
        signing_keys=[model_owner_skey],
        change_address=model_owner_address,
        auto_ttl_offset=1000,
        auto_validity_start_offset=0,
    )

    # Submit the transaction
    context.submit_tx(signed_tx.to_cbor())

    print(f"transaction id: {signed_tx.id}")
    print(f"Cardanoscan: https://preprod.cardanoscan.io/transaction/{signed_tx.id}")


if __name__ == "__main__":
    main()
