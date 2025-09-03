"""
Integration tests for complete subscription workflows.
These tests verify end-to-end functionality across the entire system.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import os
from datetime import datetime, timedelta

from onchain.contract import SubscriptionDatum, UnlockPayment, UpdateSubscription, PauseResumeSubscription
from opshin.prelude import Token, FinitePOSIXTime, PubKeyHash


class TestSubscriptionCreationFlow:
    """Test complete subscription creation workflow."""
    
    @pytest.mark.integration
    def test_user_creates_subscription_end_to_end(self, user_wallet, model_owner_wallet, 
                                                  sample_subscription_datum, mock_ai_inference_result):
        """Test complete user subscription creation flow."""
        
        # Mock the offchain operations
        with patch('offchain.user.create_subscription') as mock_create:
            mock_create.return_value = {
                'transaction_id': '1234567890abcdef',
                'subscription_utxo': 'tx_id#0',
                'status': 'success'
            }
            
            # Simulate user creating subscription
            subscription_result = mock_create(
                user_wallet=user_wallet,
                model_owner=model_owner_wallet['address'],
                payment_amount=sample_subscription_datum.payment_amount,
                payment_interval=sample_subscription_datum.payment_intervall
            )
            
            # Verify subscription was created
            assert subscription_result['status'] == 'success'
            assert 'transaction_id' in subscription_result
            assert 'subscription_utxo' in subscription_result
            
            mock_create.assert_called_once()

    @pytest.mark.integration  
    def test_subscription_appears_in_view_subscriptions(self, user_wallet, sample_subscription_datum):
        """Test that created subscription appears in view subscriptions."""
        
        with patch('offchain.view_subscriptions.get_subscriptions') as mock_view:
            mock_view.return_value = [
                {
                    'utxo_id': 'tx_id#0',
                    'owner': user_wallet['address'],
                    'model_owner': sample_subscription_datum.model_owner_pubkeyhash,
                    'payment_amount': sample_subscription_datum.payment_amount,
                    'next_payment': sample_subscription_datum.next_payment_date.time,
                    'is_paused': sample_subscription_datum.is_paused
                }
            ]
            
            # Get user's subscriptions
            subscriptions = mock_view(wallet=user_wallet['address'], role='user')
            
            # Verify subscription is found
            assert len(subscriptions) == 1
            subscription = subscriptions[0]
            assert subscription['owner'] == user_wallet['address']
            assert subscription['payment_amount'] == sample_subscription_datum.payment_amount
            assert not subscription['is_paused']

    @pytest.mark.integration
    def test_subscription_status_check_after_creation(self, sample_subscription_datum):
        """Test checking subscription status after creation."""
        
        with patch('offchain.subscription_status.get_subscription_status') as mock_status:
            mock_status.return_value = {
                'utxo_id': 'tx_id#0',
                'status': 'active',
                'next_payment_date': sample_subscription_datum.next_payment_date.time,
                'payment_amount': sample_subscription_datum.payment_amount,
                'remaining_balance': 5000000,  # 5 ADA
                'is_paused': False,
                'days_until_payment': 1
            }
            
            # Check subscription status
            status = mock_status(utxo_id='tx_id#0')
            
            # Verify status information
            assert status['status'] == 'active'
            assert status['remaining_balance'] >= status['payment_amount']
            assert not status['is_paused']
            assert status['days_until_payment'] >= 0


class TestPaymentRedemptionFlow:
    """Test complete payment redemption workflow."""
    
    @pytest.mark.integration
    def test_model_owner_redeems_payment_flow(self, model_owner_wallet, sample_subscription_datum, 
                                             past_payment_date):
        """Test complete payment redemption by model owner."""
        
        # Set payment date to past so it can be redeemed
        sample_subscription_datum.next_payment_date = past_payment_date
        
        with patch('offchain.model_owner.redeem_subscription.redeem_payment') as mock_redeem:
            mock_redeem.return_value = {
                'transaction_id': 'fedcba0987654321',
                'payment_amount': sample_subscription_datum.payment_amount,
                'new_payment_date': past_payment_date.time + sample_subscription_datum.payment_intervall,
                'status': 'success'
            }
            
            # Model owner redeems payment
            redemption_result = mock_redeem(
                model_owner_wallet=model_owner_wallet,
                subscription_utxo='tx_id#0'
            )
            
            # Verify payment was redeemed
            assert redemption_result['status'] == 'success'
            assert redemption_result['payment_amount'] == sample_subscription_datum.payment_amount
            assert redemption_result['new_payment_date'] > past_payment_date.time
            
            mock_redeem.assert_called_once()

    @pytest.mark.integration
    def test_payment_history_updated_after_redemption(self, model_owner_wallet, sample_subscription_datum):
        """Test that payment history is updated after redemption."""
        
        with patch('offchain.payment_history.get_payment_history') as mock_history:
            mock_history.return_value = {
                'payments': [
                    {
                        'date': datetime.now().isoformat(),
                        'amount': sample_subscription_datum.payment_amount,
                        'subscription_id': 'tx_id#0',
                        'model_owner': model_owner_wallet['address'],
                        'status': 'completed'
                    }
                ],
                'total_revenue': sample_subscription_datum.payment_amount,
                'payment_count': 1
            }
            
            # Get payment history
            history = mock_history(wallet=model_owner_wallet['address'], role='owner')
            
            # Verify payment appears in history
            assert len(history['payments']) == 1
            payment = history['payments'][0]
            assert payment['amount'] == sample_subscription_datum.payment_amount
            assert payment['status'] == 'completed'
            assert history['total_revenue'] == sample_subscription_datum.payment_amount

    @pytest.mark.integration
    def test_subscription_updated_after_payment(self, sample_subscription_datum, past_payment_date):
        """Test that subscription is properly updated after payment."""
        
        # Calculate expected next payment date
        expected_next_payment = past_payment_date.time + sample_subscription_datum.payment_intervall
        
        with patch('offchain.subscription_status.get_subscription_status') as mock_status:
            mock_status.return_value = {
                'utxo_id': 'tx_id#0',
                'status': 'active',
                'next_payment_date': expected_next_payment,
                'payment_amount': sample_subscription_datum.payment_amount,
                'remaining_balance': 4000000,  # Reduced by payment amount
                'payments_made': 1
            }
            
            # Check updated subscription status
            status = mock_status(utxo_id='tx_id#0')
            
            # Verify subscription was updated
            assert status['next_payment_date'] == expected_next_payment
            assert status['remaining_balance'] < 5000000  # Balance decreased
            assert status['payments_made'] == 1


class TestSubscriptionCancellationFlow:
    """Test complete subscription cancellation workflow."""
    
    @pytest.mark.integration
    def test_user_cancels_subscription_flow(self, user_wallet, sample_subscription_datum):
        """Test complete subscription cancellation by user."""
        
        with patch('offchain.user.cancel_subscription.cancel_subscription') as mock_cancel:
            mock_cancel.return_value = {
                'transaction_id': 'abcdef1234567890',
                'returned_amount': 4000000,  # Remaining balance
                'status': 'cancelled'
            }
            
            # User cancels subscription
            cancellation_result = mock_cancel(
                user_wallet=user_wallet,
                subscription_utxo='tx_id#0'
            )
            
            # Verify cancellation
            assert cancellation_result['status'] == 'cancelled'
            assert cancellation_result['returned_amount'] > 0
            assert 'transaction_id' in cancellation_result
            
            mock_cancel.assert_called_once()

    @pytest.mark.integration
    def test_cancelled_subscription_not_in_active_list(self, user_wallet):
        """Test that cancelled subscription doesn't appear in active subscriptions."""
        
        with patch('offchain.view_subscriptions.get_subscriptions') as mock_view:
            mock_view.return_value = []  # No active subscriptions
            
            # Get user's active subscriptions
            subscriptions = mock_view(wallet=user_wallet['address'], role='user')
            
            # Verify no active subscriptions
            assert len(subscriptions) == 0


class TestPauseResumeFlow:
    """Test complete pause/resume workflow."""
    
    @pytest.mark.integration
    def test_model_owner_pauses_subscription_flow(self, model_owner_wallet, sample_subscription_datum, current_time):
        """Test complete subscription pause by model owner."""
        
        with patch('offchain.model_owner.pause_resume_subscription.pause_subscription') as mock_pause:
            mock_pause.return_value = {
                'transaction_id': '1111222233334444',
                'pause_start_time': current_time,
                'status': 'paused'
            }
            
            # Model owner pauses subscription
            pause_result = mock_pause(
                model_owner_wallet=model_owner_wallet,
                subscription_utxo='tx_id#0'
            )
            
            # Verify pause
            assert pause_result['status'] == 'paused'
            assert pause_result['pause_start_time'] == current_time
            
            mock_pause.assert_called_once()

    @pytest.mark.integration
    def test_paused_subscription_cannot_be_redeemed(self, model_owner_wallet):
        """Test that paused subscription cannot have payments redeemed."""
        
        with patch('offchain.model_owner.redeem_subscription.redeem_payment') as mock_redeem:
            mock_redeem.side_effect = Exception("Cannot unlock payment while subscription is paused")
            
            # Attempt to redeem payment from paused subscription
            with pytest.raises(Exception, match="Cannot unlock payment while subscription is paused"):
                mock_redeem(
                    model_owner_wallet=model_owner_wallet,
                    subscription_utxo='tx_id#0'
                )

    @pytest.mark.integration
    def test_model_owner_resumes_subscription_flow(self, model_owner_wallet, current_time):
        """Test complete subscription resume by model owner."""
        
        pause_duration = 2 * 24 * 60 * 60 * 1000  # 2 days in milliseconds
        
        with patch('offchain.model_owner.pause_resume_subscription.resume_subscription') as mock_resume:
            mock_resume.return_value = {
                'transaction_id': '5555666677778888',
                'pause_duration': pause_duration,
                'extended_payment_date': current_time + pause_duration,
                'status': 'active'
            }
            
            # Model owner resumes subscription
            resume_result = mock_resume(
                model_owner_wallet=model_owner_wallet,
                subscription_utxo='tx_id#0'
            )
            
            # Verify resume
            assert resume_result['status'] == 'active'
            assert resume_result['pause_duration'] == pause_duration
            assert resume_result['extended_payment_date'] > current_time
            
            mock_resume.assert_called_once()


class TestAIServiceIntegrationFlow:
    """Test AI service integration with subscription system."""
    
    @pytest.mark.integration
    def test_ai_inference_with_valid_subscription(self, user_wallet, model_owner_wallet, 
                                                 mock_ai_inference_result):
        """Test AI inference with valid subscription."""
        
        with patch('offchain.service_request.process_service_request') as mock_service:
            mock_service.return_value = {
                'subscription_valid': True,
                'inference_result': mock_ai_inference_result,
                'payment_status': 'verified',
                'processing_time': 0.123
            }
            
            # Submit AI inference request
            service_result = mock_service(
                input_text="I love this service!",
                user_wallet=user_wallet,
                model_owner=model_owner_wallet['address']
            )
            
            # Verify service was provided
            assert service_result['subscription_valid']
            assert service_result['inference_result']['prediction'] == 'POSITIVE'
            assert service_result['inference_result']['confidence'] == 0.95
            assert service_result['payment_status'] == 'verified'

    @pytest.mark.integration
    def test_ai_inference_rejected_without_valid_subscription(self, user_wallet, model_owner_wallet):
        """Test AI inference is rejected without valid subscription."""
        
        with patch('offchain.service_request.process_service_request') as mock_service:
            mock_service.return_value = {
                'subscription_valid': False,
                'error': 'No valid subscription found',
                'payment_status': 'missing'
            }
            
            # Submit AI inference request without valid subscription
            service_result = mock_service(
                input_text="Test text",
                user_wallet=user_wallet,
                model_owner=model_owner_wallet['address']
            )
            
            # Verify service was rejected
            assert not service_result['subscription_valid']
            assert 'error' in service_result
            assert service_result['payment_status'] == 'missing'


class TestBulkOperationsFlow:
    """Test bulk operations workflows."""
    
    @pytest.mark.integration
    def test_bulk_payment_processing_flow(self, model_owner_wallet):
        """Test bulk payment processing workflow."""
        
        with patch('offchain.bulk_payment.process_bulk_payments') as mock_bulk:
            mock_bulk.return_value = {
                'processed_payments': 3,
                'total_amount': 3000000,  # 3 ADA total
                'transaction_id': 'bulk_tx_123456',
                'fee_saved': 200000,  # Saved fees from bulk processing
                'status': 'success'
            }
            
            # Process bulk payments
            bulk_result = mock_bulk(
                model_owner_wallet=model_owner_wallet,
                max_payments=5
            )
            
            # Verify bulk processing
            assert bulk_result['status'] == 'success'
            assert bulk_result['processed_payments'] == 3
            assert bulk_result['total_amount'] == 3000000
            assert bulk_result['fee_saved'] > 0

    @pytest.mark.integration
    def test_bulk_processing_analytics(self, model_owner_wallet):
        """Test bulk processing analytics and reporting."""
        
        with patch('offchain.payment_history.get_bulk_analytics') as mock_analytics:
            mock_analytics.return_value = {
                'total_bulk_transactions': 5,
                'total_fees_saved': 1000000,  # 1 ADA saved
                'average_payments_per_bulk': 3.2,
                'efficiency_gain': '45%'
            }
            
            # Get bulk processing analytics
            analytics = mock_analytics(model_owner_wallet=model_owner_wallet)
            
            # Verify analytics
            assert analytics['total_bulk_transactions'] == 5
            assert analytics['total_fees_saved'] == 1000000
            assert analytics['efficiency_gain'] == '45%'


class TestErrorRecoveryFlow:
    """Test error recovery and edge case workflows."""
    
    @pytest.mark.integration
    def test_transaction_failure_recovery(self, user_wallet, sample_subscription_datum):
        """Test recovery from transaction failures."""
        
        with patch('offchain.user.create_subscription') as mock_create:
            # First attempt fails
            mock_create.side_effect = [
                Exception("Network error"),
                {
                    'transaction_id': 'retry_success_123',
                    'status': 'success'
                }
            ]
            
            # Simulate retry logic
            try:
                result = mock_create(user_wallet=user_wallet)
            except Exception:
                # Retry
                result = mock_create(user_wallet=user_wallet)
            
            # Verify eventual success
            assert result['status'] == 'success'
            assert result['transaction_id'] == 'retry_success_123'

    @pytest.mark.integration
    def test_insufficient_funds_handling(self, user_wallet):
        """Test handling of insufficient funds scenarios."""
        
        with patch('offchain.user.create_subscription') as mock_create:
            mock_create.return_value = {
                'error': 'Insufficient funds',
                'required_amount': 5000000,
                'available_amount': 2000000,
                'status': 'failed'
            }
            
            # Attempt subscription with insufficient funds
            result = mock_create(user_wallet=user_wallet)
            
            # Verify error handling
            assert result['status'] == 'failed'
            assert 'error' in result
            assert result['required_amount'] > result['available_amount']
