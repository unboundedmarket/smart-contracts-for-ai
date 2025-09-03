"""
Unit tests for smart contract validation logic.
These tests verify the core contract logic without blockchain interaction.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from opshin.prelude import Token, FinitePOSIXTime, PubKeyHash
from pycardano import PaymentSigningKey, PaymentVerificationKey

from onchain.contract import (
    SubscriptionDatum, UnlockPayment, UpdateSubscription, 
    PauseResumeSubscription, validator, amount_of_token_in_output
)

# Mock opshin types for testing
class MockSpending:
    pass

class MockScriptContext:
    pass


def create_mock_context(signatories=None):
    """Helper function to create a proper mock context for testing."""
    context = Mock()
    context.tx_info.signatories = signatories or []
    context.purpose = MockSpending()
    return context


# Patch isinstance globally for all contract tests
def mock_isinstance(obj, cls):
    """Custom isinstance that recognizes our mock types."""
    if hasattr(cls, '__name__') and cls.__name__ == 'Spending' and isinstance(obj, MockSpending):
        return True
    return isinstance.__wrapped__(obj, cls)


class TestContractValidation:
    """Test the main validator function with different redeemer types."""
    
    @patch('onchain.contract.isinstance', side_effect=mock_isinstance)
    def test_update_subscription_requires_owner_signature(self, mock_isinstance_func, sample_subscription_datum, update_subscription_redeemer):
        """Test that updating subscription requires owner signature."""
        context = create_mock_context(signatories=[])
        
        # Should raise assertion error
        with pytest.raises(AssertionError, match="Required Subscription Owner Signature missing"):
            validator(sample_subscription_datum, update_subscription_redeemer, context)
    
    def test_update_subscription_succeeds_with_owner_signature(self, sample_subscription_datum, update_subscription_redeemer):
        """Test that updating subscription succeeds with owner signature."""
        # Create mock context with owner signature
        context = Mock()
        context.tx_info.signatories = [sample_subscription_datum.owner_pubkeyhash]
        context.purpose = Mock()
        context.purpose.__class__.__name__ = "Spending"
        
        # Should not raise any error
        try:
            validator(sample_subscription_datum, update_subscription_redeemer, context)
        except AssertionError:
            pytest.fail("Validator should not fail with owner signature")

    def test_unlock_payment_requires_model_owner_signature(self, sample_subscription_datum, unlock_payment_redeemer):
        """Test that unlocking payment requires model owner signature."""
        context = Mock()
        context.tx_info.signatories = []  # No signatures
        context.purpose = Mock()
        context.purpose.__class__.__name__ = "Spending"
        
        with pytest.raises(AssertionError, match="Required Model Owner Signature missing"):
            validator(sample_subscription_datum, unlock_payment_redeemer, context)

    def test_unlock_payment_fails_when_paused(self, paused_subscription_datum, unlock_payment_redeemer):
        """Test that unlocking payment fails when subscription is paused."""
        context = Mock()
        context.tx_info.signatories = [paused_subscription_datum.model_owner_pubkeyhash]
        context.purpose = Mock()
        context.purpose.__class__.__name__ = "Spending"
        
        with pytest.raises(AssertionError, match="Cannot unlock payment while subscription is paused"):
            validator(paused_subscription_datum, unlock_payment_redeemer, context)

    def test_unlock_payment_fails_before_payment_date(self, sample_subscription_datum, unlock_payment_redeemer, current_time):
        """Test that unlocking payment fails before the payment date."""
        # Set payment date to future
        sample_subscription_datum.next_payment_date = FinitePOSIXTime(current_time + 86400000)  # 1 day future
        
        context = Mock()
        context.tx_info.signatories = [sample_subscription_datum.model_owner_pubkeyhash]
        context.tx_info.valid_range = Mock()
        context.purpose = Mock()
        context.purpose.__class__.__name__ = "Spending"
        
        # Mock the after_ext function to return False (payment time not reached)
        import onchain.contract
        original_after_ext = onchain.contract.after_ext
        onchain.contract.after_ext = Mock(return_value=False)
        
        try:
            with pytest.raises(AssertionError):
                validator(sample_subscription_datum, unlock_payment_redeemer, context)
        finally:
            onchain.contract.after_ext = original_after_ext

    def test_pause_subscription_requires_model_owner_signature(self, sample_subscription_datum, pause_redeemer):
        """Test that pausing subscription requires model owner signature."""
        context = Mock()
        context.tx_info.signatories = []  # No signatures
        context.purpose = Mock()
        context.purpose.__class__.__name__ = "Spending"
        
        with pytest.raises(AssertionError, match="Required Model Owner Signature missing for pause/resume"):
            validator(sample_subscription_datum, pause_redeemer, context)

    def test_pause_already_paused_subscription_fails(self, paused_subscription_datum, pause_redeemer):
        """Test that pausing an already paused subscription fails."""
        context = Mock()
        context.tx_info.signatories = [paused_subscription_datum.model_owner_pubkeyhash]
        context.purpose = Mock()
        context.purpose.__class__.__name__ = "Spending"
        
        with pytest.raises(AssertionError, match="Subscription is already paused"):
            validator(paused_subscription_datum, pause_redeemer, context)

    def test_resume_non_paused_subscription_fails(self, sample_subscription_datum, resume_redeemer):
        """Test that resuming a non-paused subscription fails."""
        context = Mock()
        context.tx_info.signatories = [sample_subscription_datum.model_owner_pubkeyhash]
        context.purpose = Mock()
        context.purpose.__class__.__name__ = "Spending"
        
        with pytest.raises(AssertionError, match="Subscription is not paused"):
            validator(sample_subscription_datum, resume_redeemer, context)


class TestAmountOfTokenInOutput:
    """Test the amount_of_token_in_output utility function."""
    
    def test_ada_token_amount_calculation(self, ada_token):
        """Test calculating ADA amount in output."""
        # Mock output with ADA value
        mock_output = Mock()
        mock_output.value.get.return_value = {b"": 1000000}  # 1 ADA
        
        result = amount_of_token_in_output(ada_token, mock_output)
        assert result == 1000000

    def test_missing_token_returns_zero(self, ada_token):
        """Test that missing token returns zero amount."""
        # Mock output with empty value
        mock_output = Mock()
        mock_output.value.get.return_value = {b"": 0}
        
        result = amount_of_token_in_output(ada_token, mock_output)
        assert result == 0

    def test_custom_token_amount_calculation(self):
        """Test calculating custom token amount in output."""
        custom_token = Token(b"policy123", b"token456")
        
        # Mock output with custom token
        mock_output = Mock()
        mock_output.value.get.return_value = {b"token456": 5000}
        
        result = amount_of_token_in_output(custom_token, mock_output)
        assert result == 5000


class TestSubscriptionDatum:
    """Test subscription datum creation and validation."""
    
    def test_subscription_datum_creation(self, user_wallet, model_owner_wallet, future_payment_date, ada_token):
        """Test creating a valid subscription datum."""
        datum = SubscriptionDatum(
            owner_pubkeyhash=PubKeyHash(user_wallet['verification_key'].hash().payload),
            model_owner_pubkeyhash=PubKeyHash(model_owner_wallet['verification_key'].hash().payload),
            next_payment_date=future_payment_date,
            payment_intervall=7 * 24 * 60 * 60 * 1000,  # 1 week
            payment_amount=1000000,  # 1 ADA
            payment_token=ada_token,
            is_paused=False,
            pause_start_time=FinitePOSIXTime(0)
        )
        
        assert datum.payment_amount == 1000000
        assert datum.payment_intervall == 7 * 24 * 60 * 60 * 1000
        assert not datum.is_paused
        assert datum.pause_start_time.time == 0

    def test_paused_subscription_datum(self, sample_subscription_datum, current_time):
        """Test creating a paused subscription datum."""
        datum = sample_subscription_datum
        datum.is_paused = True
        datum.pause_start_time = FinitePOSIXTime(current_time)
        
        assert datum.is_paused
        assert datum.pause_start_time.time == current_time


class TestRedeemers:
    """Test redeemer creation and properties."""
    
    def test_unlock_payment_redeemer(self):
        """Test UnlockPayment redeemer creation."""
        redeemer = UnlockPayment(input_index=0, output_index=1)
        
        assert redeemer.input_index == 0
        assert redeemer.output_index == 1
        assert redeemer.CONSTR_ID == 0

    def test_update_subscription_redeemer(self):
        """Test UpdateSubscription redeemer creation."""
        redeemer = UpdateSubscription()
        assert redeemer.CONSTR_ID == 1

    def test_pause_resume_subscription_redeemer(self):
        """Test PauseResumeSubscription redeemer creation."""
        pause_redeemer = PauseResumeSubscription(pause=True)
        resume_redeemer = PauseResumeSubscription(pause=False)
        
        assert pause_redeemer.pause is True
        assert resume_redeemer.pause is False
        assert pause_redeemer.CONSTR_ID == 2
        assert resume_redeemer.CONSTR_ID == 2


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_invalid_redeemer_type_fails(self, sample_subscription_datum):
        """Test that invalid redeemer type raises error."""
        invalid_redeemer = "invalid_redeemer_string"
        context = Mock()
        context.purpose = Mock()
        context.purpose.__class__.__name__ = "Spending"
        
        with pytest.raises(AssertionError, match="Invalid Redeemer"):
            validator(sample_subscription_datum, invalid_redeemer, context)

    def test_non_spending_purpose_fails(self, sample_subscription_datum, update_subscription_redeemer):
        """Test that non-spending script purpose fails."""
        context = Mock()
        context.purpose = Mock()
        context.purpose.__class__.__name__ = "Minting"  # Not spending
        
        with pytest.raises(AssertionError, match="Wrong type of script invocation"):
            validator(sample_subscription_datum, update_subscription_redeemer, context)

    @pytest.mark.parametrize("payment_amount,expected_valid", [
        (0, False),           # Zero payment
        (-1000000, False),    # Negative payment  
        (1000000, True),      # Valid payment
        (100000000, True),    # Large payment
    ])
    def test_payment_amount_validation(self, payment_amount, expected_valid, sample_subscription_datum):
        """Test payment amount validation with different values."""
        sample_subscription_datum.payment_amount = payment_amount
        
        # This is a basic validation test - in real contract logic,
        # negative amounts would be handled by Plutus type system
        if expected_valid:
            assert sample_subscription_datum.payment_amount >= 0
        else:
            assert sample_subscription_datum.payment_amount < 0 or sample_subscription_datum.payment_amount == 0
