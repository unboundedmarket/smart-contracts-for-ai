from pathlib import Path

import click
from pycardano import Address, Network, PaymentSigningKey, PaymentVerificationKey
import os


@click.command()
@click.argument("name")
def main(name):
    """
    Creates a testnet signing key, verification key, and address.
    """
    skey_path = f"{name}.skey"
    vkey_path = f"{name}.vkey"
    addr_path = f"{name}.addr"

    if os.path.exists(skey_path):
        raise FileExistsError(f"signing key file ${skey_path} already exists")
    if os.path.exists(vkey_path):
        raise FileExistsError(f"verification key file ${vkey_path} already exists")
    if os.path.exists(addr_path):
        raise FileExistsError(f"address file ${addr_path} already exists")

    signing_key = PaymentSigningKey.generate()
    signing_key.save(str(skey_path))

    verification_key = PaymentVerificationKey.from_signing_key(signing_key)
    verification_key.save(str(vkey_path))

    address = Address(payment_part=verification_key.hash(), network=Network.TESTNET)
    with open(addr_path, mode="w") as f:
        f.write(str(address))

    print(f"wrote signing key to: {skey_path}")
    print(f"wrote verification key to: {vkey_path}")
    print(f"wrote address to: {addr_path}")


if __name__ == "__main__":
    main()
