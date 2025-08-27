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


def main(wallet_user: str = "user1", wallet_model_owner: str = "owner1"):

    (
        script,
        script_policy_id,
        script_address,
    ) = get_contract(module_name(contract))

    user_vkey, user_skey, user_address = get_signing_info(
        wallet_user, network=Network.TESTNET
    )

    model_owner_vkey, model_owner_skey, model_owner_address = get_signing_info(
        wallet_model_owner, network=Network.TESTNET
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
            int((datetime.utcnow() + timedelta(seconds=10)).timestamp() * 1000)
        ),
        int(10 * 1000),
        int(1e6),
        Token(b"", b""),
        False,  # is_paused = False (new subscriptions start unpaused)
        FinitePOSIXTime(0),  # pause_start_time = 0 (not paused)
    )

    builder.add_output(
        TransactionOutput(
            address=script_address,
            amount=Value(
                coin=int(4e6),
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

    print(f"transaction id: {signed_tx.id}")
    print(f"Cardanoscan: https://preprod.cardanoscan.io/transaction/{signed_tx.id}")


if __name__ == "__main__":
    main()
