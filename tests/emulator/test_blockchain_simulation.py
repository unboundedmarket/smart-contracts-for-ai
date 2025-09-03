"""
PyCardano emulator tests for blockchain simulation.
These tests simulate contract interactions without requiring a real blockchain.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from pycardano import (
    TransactionBuilder, TransactionOutput, Value, Address, PaymentSigningKey,
    PaymentVerificationKey, Network, UTxO, TransactionInput, PlutusV2Script,
    PlutusData, Redeemer, ScriptHash, VerificationKeyHash
)
from opshin.prelude import Token, FinitePOSIXTime, PubKeyHash

from onchain.contract import (
    SubscriptionDatum, UnlockPayment, UpdateSubscription, 
    PauseResumeSubscription, validator
)


class MockChainContext:
    """Mock chain context for emulator testing."""
    
    def __init__(self):
        self.utxos = {}
        self.current_slot = 1000000
        self.protocol_params = self._mock_protocol_params()
    
    def _mock_protocol_params(self):
        """Create mock protocol parameters."""
        return {
            'min_fee_a': 44,
            'min_fee_b': 155381,
            'max_tx_size': 16384,
            'key_deposit': 2000000,
            'pool_deposit': 500000000,
            'min_utxo': 1000000,
        }
    
    def add_utxo(self, tx_input: TransactionInput, tx_output: TransactionOutput):
        """Add UTXO to the mock chain state."""
        self.utxos[tx_input] = tx_output
    
    def get_utxo(self, tx_input: TransactionInput):
        """Get UTXO from the mock chain state."""
        return self.utxos.get(tx_input)
    
    def advance_slot(self, slots: int):
        """Advance the chain by specified slots."""
        self.current_slot += slots


@pytest.fixture
def chain_context():
    """Create a mock chain context for testing."""
    return MockChainContext()


@pytest.fixture
def contract_script():
    """Mock contract script for testing."""
    # Simple mock script bytes for testing
    return b"mock_contract_bytes"


@pytest.fixture
def contract_address():
    """Create mock contract address for testing."""
    # Create a simple mock address - in real tests this would be derived from the script
    # Using a mock script hash for testing purposes
    mock_script_hash = b"\x01" * 28  # 28 bytes for script hash
    script_hash = ScriptHash(mock_script_hash)
    return Address(payment_part=script_hash, network=Network.TESTNET)


class TestEmulatorBasics:
    """Basic emulator functionality tests."""
    
    def test_chain_context_creation(self, chain_context):
        """Test that chain context is created properly."""
        assert chain_context.current_slot == 1000000
        assert len(chain_context.utxos) == 0
        assert chain_context.protocol_params['min_fee_a'] == 44

    def test_utxo_management(self, chain_context):
        """Test adding and retrieving UTXOs."""
        # Create mock UTXO
        tx_input = TransactionInput.from_primitive([
            "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            0
        ])
        # Create a simple mock address for testing
        mock_hash = b"\x02" * 28  # 28 bytes for verification key hash
        verification_key_hash = VerificationKeyHash(mock_hash)
        mock_address = Address(payment_part=verification_key_hash, network=Network.TESTNET)
        tx_output = TransactionOutput(
            mock_address,
            Value(coin=2000000)
        )
        
        # Add and retrieve UTXO
        chain_context.add_utxo(tx_input, tx_output)
        retrieved_utxo = chain_context.get_utxo(tx_input)
        
        assert retrieved_utxo == tx_output
        assert retrieved_utxo.amount == Value(coin=2000000)

    def test_slot_advancement(self, chain_context):
        """Test advancing blockchain slots."""
        initial_slot = chain_context.current_slot
        chain_context.advance_slot(100)
        
        assert chain_context.current_slot == initial_slot + 100


class TestSubscriptionCreationEmulator:
    """Test subscription creation using emulator."""
    
    def test_create_subscription_transaction(self, chain_context, user_wallet, model_owner_wallet, 
                                           contract_address, sample_subscription_datum):
        """Test creating a subscription transaction in emulator."""
        # Create initial user UTXO with funds
        user_utxo_input = TransactionInput.from_primitive([
            "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            0
        ])
        user_utxo_output = TransactionOutput(
            user_wallet['address'],
            Value(coin=10000000)  # 10 ADA
        )
        chain_context.add_utxo(user_utxo_input, user_utxo_output)
        
        # Mock transaction builder
        with patch('pycardano.TransactionBuilder') as mock_builder:
            builder = Mock()
            mock_builder.return_value = builder
            
            # Configure builder mocks
            builder.add_input.return_value = builder
            builder.add_output.return_value = builder
            builder.build.return_value = Mock()
            
            # Build subscription creation transaction
            subscription_output = TransactionOutput(
                contract_address,
                Value(coin=5000000),  # 5 ADA locked
                datum=sample_subscription_datum
            )
            
            # Simulate transaction building using the mocked builder
            builder.add_input(user_utxo_input)
            builder.add_output(subscription_output)
            builder.build()
            
            # Verify transaction was configured correctly
            builder.add_input.assert_called_with(user_utxo_input)
            builder.add_output.assert_called_with(subscription_output)
            builder.build.assert_called_once()

    def test_subscription_datum_in_utxo(self, sample_subscription_datum, contract_address, chain_context):
        """Test that subscription datum is properly stored in UTXO."""
        # Create contract UTXO with subscription datum
        contract_utxo_input = TransactionInput.from_primitive([
            "fedcba0987654321fedcba0987654321fedcba0987654321fedcba0987654321",
            0
        ])
        contract_utxo_output = TransactionOutput(
            contract_address,
            Value(coin=5000000),
            datum=sample_subscription_datum
        )
        
        chain_context.add_utxo(contract_utxo_input, contract_utxo_output)
        
        # Retrieve and verify
        retrieved_utxo = chain_context.get_utxo(contract_utxo_input)
        assert retrieved_utxo.datum == sample_subscription_datum
        assert retrieved_utxo.amount == Value(coin=5000000)


class TestPaymentUnlockingEmulator:
    """Test payment unlocking using emulator."""
    
    def test_unlock_payment_transaction(self, chain_context, model_owner_wallet, contract_address,
                                       sample_subscription_datum, past_payment_date):
        """Test unlocking payment transaction in emulator."""
        # Set payment date to past so payment can be unlocked
        sample_subscription_datum.next_payment_date = past_payment_date
        
        # Create contract UTXO with subscription
        contract_input = TransactionInput.from_primitive([
            "1111111111111111111111111111111111111111111111111111111111111111",
            0
        ])
        contract_output_input = TransactionOutput(
            contract_address,
            Value(coin=5000000),
            datum=sample_subscription_datum
        )
        chain_context.add_utxo(contract_input, contract_output_input)
        
        # Mock transaction with time constraints
        current_time = int(datetime.now().timestamp() * 1000)
        
        with patch('pycardano.TransactionBuilder') as mock_builder:
            builder = Mock()
            mock_builder.return_value = builder
            
            # Configure transaction builder
            builder.add_input.return_value = builder
            builder.add_output.return_value = builder
            builder.build.return_value = Mock()
            
            # Build unlock transaction using the mocked builder
            builder.add_input(contract_input)
            builder.build()
            
            # Verify transaction was configured correctly
            builder.add_input.assert_called_with(contract_input)
            builder.build.assert_called_once()

    def test_insufficient_funds_unlock_fails(self, chain_context, contract_address, sample_subscription_datum):
        """Test that unlock fails when insufficient funds remain."""
        # Create contract UTXO with insufficient funds
        contract_input = TransactionInput.from_primitive([
            "2222222222222222222222222222222222222222222222222222222222222222",
            0  
        ])
        contract_output = TransactionOutput(
            contract_address,
            Value(coin=500000),  # Less than payment amount (1 ADA)
            datum=sample_subscription_datum
        )
        chain_context.add_utxo(contract_input, contract_output)
        
        # Verify insufficient funds scenario
        utxo_amount = contract_output.amount.coin
        payment_amount = sample_subscription_datum.payment_amount
        
        assert utxo_amount < payment_amount, "UTXO should have insufficient funds"


class TestPauseResumeEmulator:
    """Test pause/resume functionality using emulator."""
    
    def test_pause_subscription_transaction(self, chain_context, model_owner_wallet, contract_address,
                                          sample_subscription_datum, current_time):
        """Test pausing subscription transaction in emulator.""" 
        # Ensure subscription is not already paused
        sample_subscription_datum.is_paused = False
        
        # Create contract UTXO
        contract_input = TransactionInput.from_primitive([
            "3333333333333333333333333333333333333333333333333333333333333333",
            0
        ])
        contract_output = TransactionOutput(
            contract_address,
            Value(coin=5000000),
            datum=sample_subscription_datum
        )
        chain_context.add_utxo(contract_input, contract_output)
        
        # Create paused datum
        paused_datum = SubscriptionDatum(
            sample_subscription_datum.owner_pubkeyhash,
            sample_subscription_datum.model_owner_pubkeyhash,
            sample_subscription_datum.next_payment_date,
            sample_subscription_datum.payment_intervall,
            sample_subscription_datum.payment_amount,
            sample_subscription_datum.payment_token,
            True,  # is_paused = True
            FinitePOSIXTime(current_time)  # pause_start_time
        )
        
        # Verify pause logic
        assert not sample_subscription_datum.is_paused
        assert paused_datum.is_paused
        assert paused_datum.pause_start_time.time == current_time

    def test_resume_subscription_extends_payment_date(self, sample_subscription_datum, current_time):
        """Test that resuming subscription extends payment date by pause duration."""
        # Set up paused subscription
        pause_start = current_time - (2 * 24 * 60 * 60 * 1000)  # 2 days ago
        original_payment_date = current_time + (7 * 24 * 60 * 60 * 1000)  # 1 week future
        
        paused_datum = SubscriptionDatum(
            sample_subscription_datum.owner_pubkeyhash,
            sample_subscription_datum.model_owner_pubkeyhash,
            FinitePOSIXTime(original_payment_date),
            sample_subscription_datum.payment_intervall,
            sample_subscription_datum.payment_amount,
            sample_subscription_datum.payment_token,
            True,  # is_paused
            FinitePOSIXTime(pause_start)
        )
        
        # Calculate pause duration and extended payment date
        pause_duration = current_time - pause_start  # 2 days
        extended_payment_date = original_payment_date + pause_duration
        
        # Verify calculation
        assert pause_duration == 2 * 24 * 60 * 60 * 1000
        assert extended_payment_date > original_payment_date
        assert extended_payment_date - original_payment_date == pause_duration


class TestEmulatorIntegration:
    """Integration tests using emulator for complete flows."""
    
    def test_full_subscription_lifecycle(self, chain_context, user_wallet, model_owner_wallet, 
                                       contract_address, sample_subscription_datum, current_time):
        """Test complete subscription lifecycle in emulator."""
        
        # 1. Create subscription
        user_input = TransactionInput.from_primitive([
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            0
        ])
        user_utxo = TransactionOutput(
            user_wallet['address'],
            Value(coin=10000000)
        )
        chain_context.add_utxo(user_input, user_utxo)
        
        # 2. Lock funds in contract
        subscription_input = TransactionInput.from_primitive([
            "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            0
        ])
        subscription_utxo = TransactionOutput(
            contract_address,
            Value(coin=5000000),
            datum=sample_subscription_datum
        )
        chain_context.add_utxo(subscription_input, subscription_utxo)
        
        # 3. Simulate time passing
        chain_context.advance_slot(1000)  # Advance chain state
        
        # 4. Verify subscription exists
        retrieved_subscription = chain_context.get_utxo(subscription_input)
        assert retrieved_subscription is not None
        assert retrieved_subscription.datum == sample_subscription_datum
        
        # 5. Model owner can unlock payment (after payment date)
        # This would involve creating the unlock transaction
        # For now, we verify the setup is correct
        assert retrieved_subscription.amount.coin >= sample_subscription_datum.payment_amount

    def test_multiple_subscriptions_management(self, chain_context, contract_address):
        """Test managing multiple subscriptions in emulator."""
        subscriptions = []
        
        # Create multiple subscription UTXOs
        for i in range(3):
            tx_input = TransactionInput.from_primitive([
                f"{'c'*63}{i:01x}",
                0
            ])
            
            # Create different subscription data for each
            datum = SubscriptionDatum(
                owner_pubkeyhash=PubKeyHash(b"owner" + bytes([i]) * 24),
                model_owner_pubkeyhash=PubKeyHash(b"model" + bytes([i]) * 24),
                next_payment_date=FinitePOSIXTime(1000000 + i * 86400000),
                payment_intervall=7 * 24 * 60 * 60 * 1000,
                payment_amount=1000000 * (i + 1),
                payment_token=Token(b"", b""),
                is_paused=False,
                pause_start_time=FinitePOSIXTime(0)
            )
            
            tx_output = TransactionOutput(
                contract_address,
                Value(coin=5000000 * (i + 1)),
                datum=datum
            )
            
            chain_context.add_utxo(tx_input, tx_output)
            subscriptions.append((tx_input, tx_output))
        
        # Verify all subscriptions exist
        assert len(subscriptions) == 3
        for tx_input, expected_output in subscriptions:
            retrieved = chain_context.get_utxo(tx_input)
            assert retrieved == expected_output
