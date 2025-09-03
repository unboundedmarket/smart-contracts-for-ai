import pytest
from datetime import datetime, timedelta
from pycardano import (
    Address, PaymentSigningKey, PaymentVerificationKey, StakeSigningKey, 
    StakeVerificationKey, Network, HDWallet, TransactionBuilder, 
    TransactionOutput, Value, PlutusV2Script, PlutusData, Redeemer,
    UTxO, TransactionInput
)
from pycardano.hash import SCRIPT_DATA_HASH_SIZE
from onchain.contract import SubscriptionDatum, UnlockPayment, UpdateSubscription, PauseResumeSubscription
from opshin.prelude import Token, FinitePOSIXTime, PubKeyHash


@pytest.fixture
def network():
    """Test network configuration."""
    return Network.TESTNET


@pytest.fixture
def user_wallet():
    """Create a test user wallet."""
    signing_key = PaymentSigningKey.generate()
    verification_key = PaymentVerificationKey.from_signing_key(signing_key)
    return {
        'signing_key': signing_key,
        'verification_key': verification_key,
        'address': Address(verification_key.hash(), network=Network.TESTNET)
    }


@pytest.fixture
def model_owner_wallet():
    """Create a test model owner wallet."""
    signing_key = PaymentSigningKey.generate()
    verification_key = PaymentVerificationKey.from_signing_key(signing_key)
    return {
        'signing_key': signing_key,
        'verification_key': verification_key,
        'address': Address(verification_key.hash(), network=Network.TESTNET)
    }


@pytest.fixture
def ada_token():
    """ADA token for payments."""
    return Token(b"", b"")


@pytest.fixture
def current_time():
    """Current time as POSIX timestamp."""
    return int(datetime.now().timestamp() * 1000)


@pytest.fixture
def future_payment_date(current_time):
    """Future payment date (1 day from now)."""
    future_time = current_time + (24 * 60 * 60 * 1000)  # 1 day in milliseconds
    return FinitePOSIXTime(future_time)


@pytest.fixture
def past_payment_date(current_time):
    """Past payment date (1 day ago)."""
    past_time = current_time - (24 * 60 * 60 * 1000)  # 1 day ago in milliseconds
    return FinitePOSIXTime(past_time)


@pytest.fixture
def sample_subscription_datum(user_wallet, model_owner_wallet, future_payment_date, ada_token):
    """Create a sample subscription datum for testing."""
    return SubscriptionDatum(
        owner_pubkeyhash=PubKeyHash(user_wallet['verification_key'].hash().payload),
        model_owner_pubkeyhash=PubKeyHash(model_owner_wallet['verification_key'].hash().payload),
        next_payment_date=future_payment_date,
        payment_intervall=7 * 24 * 60 * 60 * 1000,  # 1 week in milliseconds
        payment_amount=1000000,  # 1 ADA in lovelace
        payment_token=ada_token,
        is_paused=False,
        pause_start_time=FinitePOSIXTime(0)
    )


@pytest.fixture
def paused_subscription_datum(sample_subscription_datum, current_time):
    """Create a paused subscription datum for testing."""
    datum = sample_subscription_datum
    datum.is_paused = True
    datum.pause_start_time = FinitePOSIXTime(current_time)
    return datum


@pytest.fixture
def unlock_payment_redeemer():
    """Create UnlockPayment redeemer for testing."""
    return UnlockPayment(input_index=0, output_index=0)


@pytest.fixture
def update_subscription_redeemer():
    """Create UpdateSubscription redeemer for testing."""
    return UpdateSubscription()


@pytest.fixture
def pause_redeemer():
    """Create PauseResumeSubscription redeemer for pausing."""
    return PauseResumeSubscription(pause=True)


@pytest.fixture
def resume_redeemer():
    """Create PauseResumeSubscription redeemer for resuming."""
    return PauseResumeSubscription(pause=False)


@pytest.fixture
def sample_utxo_input():
    """Create a sample UTXO input for testing."""
    return TransactionInput.from_primitive([
        "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        0
    ])


@pytest.fixture
def mock_ai_inference_result():
    """Mock AI inference result for testing."""
    return {
        "prediction": "POSITIVE",
        "confidence": 0.95,
        "processing_time": 0.123,
        "model_version": "test-model-v1.0"
    }


@pytest.fixture
def contract_address():
    """Mock contract address for testing."""
    # This would be the actual contract address in a real test
    return Address.from_bech32("addr_test1qpw0djgj0x59ngrjvqthn7enhvruxnsavsw5th63la3mjel3tkc974sr23jmlzgq5zda4gtv8k9cy38756r9y3qgmkqqjz6aa7")


@pytest.fixture
def large_utxo_value():
    """Large UTXO value for testing sufficient funds."""
    return Value.from_primitive(10000000)  # 10 ADA


@pytest.fixture
def small_utxo_value():
    """Small UTXO value for testing insufficient funds."""
    return Value.from_primitive(500000)  # 0.5 ADA


@pytest.fixture
def payment_amounts():
    """Different payment amounts for testing."""
    return {
        "small": 100000,   # 0.1 ADA
        "medium": 1000000, # 1 ADA
        "large": 10000000  # 10 ADA
    }


@pytest.fixture
def time_intervals():
    """Different time intervals for testing."""
    return {
        "daily": 24 * 60 * 60 * 1000,       # 1 day
        "weekly": 7 * 24 * 60 * 60 * 1000,  # 1 week
        "monthly": 30 * 24 * 60 * 60 * 1000 # 30 days
    }


# Property-based testing helpers
@pytest.fixture
def valid_pubkey_hash():
    """Generate valid pubkey hash for property testing."""
    key = PaymentSigningKey.generate()
    return PubKeyHash(PaymentVerificationKey.from_signing_key(key).hash().payload)


@pytest.fixture
def emulator_context():
    """Create emulator context for blockchain simulation tests."""
    # This fixture will be expanded when we implement the emulator tests
    return {
        "chain_context": None,  # Will be initialized in emulator tests
        "protocol_params": None
    }
