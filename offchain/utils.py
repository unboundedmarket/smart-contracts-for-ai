from pathlib import Path

from pycardano import Address, PlutusV2Script, plutus_script_hash, Network, UTxO

from pycardano import (
    PaymentSigningKey,
    PaymentVerificationKey,
    BlockFrostChainContext,
    VerificationKeyHash,
    ScriptHash,
    PointerAddress,
)
from blockfrost import ApiUrls
from typing import List
from opshin.prelude import *
import pycardano


build_dir = Path(__file__).parent.parent.joinpath("build")
keys_dir = Path(__file__).parent.joinpath("keys")

context = BlockFrostChainContext(
    "preprodjgdbXRrz6gH0hTST2Bx2C5bRqNKFq9ub", base_url=ApiUrls.preprod.value
)


def module_name(module):
    return Path(module.__file__).stem


def get_contract(name):
    with open(build_dir.joinpath(f"{name}/script.cbor")) as f:
        contract_cbor_hex = f.read().strip()
    contract_cbor = bytes.fromhex(contract_cbor_hex)

    contract_plutus_script = PlutusV2Script(contract_cbor)
    contract_script_hash = plutus_script_hash(contract_plutus_script)
    contract_script_address = pycardano.Address(
        contract_script_hash, network=Network.TESTNET
    )
    return contract_plutus_script, contract_script_hash, contract_script_address


def get_signing_info(name, network=Network.TESTNET):
    skey_path = str(keys_dir.joinpath(f"{name}.skey"))
    payment_skey = PaymentSigningKey.load(skey_path)
    payment_vkey = PaymentVerificationKey.from_signing_key(payment_skey)
    payment_address = pycardano.Address(payment_vkey.hash(), network=network)
    return payment_vkey, payment_skey, payment_address


def sorted_utxos(txs: List[UTxO]):
    return sorted(
        txs,
        key=lambda u: (u.input.transaction_id.payload, u.input.index),
    )


def to_payment_credential(c: Union[VerificationKeyHash, ScriptHash]):
    if isinstance(c, VerificationKeyHash):
        return PubKeyCredential(PubKeyHash(c.to_primitive()))
    if isinstance(c, ScriptHash):
        return ScriptCredential(ValidatorHash(c.to_primitive()))
    raise NotImplementedError(f"Unknown payment key type {type(c)}")


def to_staking_hash(sk: Union[VerificationKeyHash, ScriptHash, PointerAddress]):
    if isinstance(sk, PointerAddress):
        return StakingPtr(sk.slot, sk.tx_index, sk.cert_index)
    if isinstance(sk, VerificationKeyHash):
        return StakingHash(PubKeyCredential(sk.payload))
    if isinstance(sk, ScriptHash):
        return StakingHash(ScriptCredential(sk.payload))
    raise NotImplementedError(f"Unknown stake key type {type(sk)}")


def to_staking_credential(
    sk: Union[
        VerificationKeyHash,
        ScriptHash,
        PointerAddress,
        None,
    ]
):
    try:
        return SomeStakingCredential(to_staking_hash(sk))
    except NotImplementedError:
        return NoStakingCredential()


def to_address(a: Address):
    return Address(
        to_payment_credential(a.payment_part),
        to_staking_credential(a.staking_part),
    )


def safe_decode_token_name(token_name_bytes) -> str:
    """
    Safely decode token name, handling both UTF-8 and binary data.
    
    Args:
        token_name_bytes: Raw bytes of the token name
        
    Returns:
        str: UTF-8 decoded string if possible, otherwise hex representation with 0x prefix
    """
    if not token_name_bytes:
        return ""
    
    try:
        # Try UTF-8 decoding first
        return token_name_bytes.decode('utf-8')
    except UnicodeDecodeError:
        # If UTF-8 fails, return hex representation with prefix
        return f"0x{token_name_bytes.hex()}"


def format_token_display_name(token_name: str, policy_id: str = "") -> str:
    """
    Format token name for user-friendly display.
    
    Args:
        token_name: Token name (may be hex if binary)
        policy_id: Token policy ID (optional)
        
    Returns:
        str: Formatted display name
    """
    if not token_name:
        return "ADA"
    
    if token_name.startswith("0x"):
        # Binary token name - show as hex with indication
        return f"Token({token_name})"
    else:
        # UTF-8 token name - display as-is
        return token_name
