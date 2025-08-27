# Import necessary modules from OpShin
from opshin.prelude import *
from opshin.std.builtins import *

from onchain.utils import *


@dataclass
class UnlockPayment(PlutusData):
    """
    Redeemer for the model owner to unlock part of the subscription payment
    """

    CONSTR_ID = 0
    # input contract utxo index
    input_index: int
    # output contract utxo index
    output_index: int


@dataclass
class UpdateSubscription(PlutusData):
    """
    Redeemer to update subscription (e.g. increase subscription payment, cancel subscription, add funds, etc)
    """

    CONSTR_ID = 1


@dataclass
class PauseResumeSubscription(PlutusData):
    """
    Redeemer to pause or resume subscription by model owner
    """

    CONSTR_ID = 2
    pause: bool  # True to pause, False to resume


PaymentRedeemer = Union[UnlockPayment, UpdateSubscription, PauseResumeSubscription]


@dataclass()
class SubscriptionDatum(PlutusData):
    owner_pubkeyhash: PubKeyHash
    model_owner_pubkeyhash: PubKeyHash
    next_payment_date: FinitePOSIXTime
    payment_intervall: int
    payment_amount: int
    payment_token: Token
    is_paused: bool  # New field to track pause status
    pause_start_time: FinitePOSIXTime  # When the pause started (0 if not paused)


def amount_of_token_in_output(token: Token, output: TxOut) -> int:
    return output.value.get(token.policy_id, {b"": 0}).get(token.token_name, 0)

def validator(
    datum: SubscriptionDatum, redeemer: PaymentRedeemer, context: ScriptContext
) -> None:

    tx_info = context.tx_info
    purpose = context.purpose

    # Check that we are indeed spending a UTxO
    assert isinstance(purpose, Spending), "Wrong type of script invocation"

    if isinstance(redeemer, UpdateSubscription):

        # check signature of subscription owner
        owner_is_updating = datum.owner_pubkeyhash in context.tx_info.signatories

        assert owner_is_updating, "Required Subscription Owner Signature missing"

    elif isinstance(redeemer, UnlockPayment):

        # get input and output utxo
        own_input = tx_info.inputs[redeemer.input_index]
        own_output = tx_info.outputs[redeemer.output_index]

        # (1) check signature of model owner present
        model_owner_is_signing = (
            datum.model_owner_pubkeyhash in context.tx_info.signatories
        )
        assert model_owner_is_signing, "Required Model Owner Signature missing"
        
        # (1.5) check that subscription is not paused
        assert not datum.is_paused, "Cannot unlock payment while subscription is paused"
 
        # (2) check that next payment is in the past (i.e. owner is allowed to withdraw)
        payment_time = datum.next_payment_date
        assert after_ext(tx_info.valid_range, payment_time)
        
        # (3) check that model owner is leaving enough funds at address (withdraw <= max amount allowed to withdraw)
        input_amount = amount_of_token_in_output(
            datum.payment_token, own_input.resolved
        )
        output_amount = amount_of_token_in_output(datum.payment_token, own_output)
        min_amount = input_amount - datum.payment_amount
        assert output_amount > min_amount, "Not enough funds returned to contract"

        # (4) compute the new payment data and check in (5) that its correct in datum
        new_payment_date = FinitePOSIXTime(payment_time.time + datum.payment_intervall)

        # (5) check that model owner is locking funds with wellformed datum
        new_subscription_datum = SubscriptionDatum(
            datum.owner_pubkeyhash,
            datum.model_owner_pubkeyhash,
            new_payment_date,
            datum.payment_intervall,
            datum.payment_amount,
            datum.payment_token,
            datum.is_paused,
            datum.pause_start_time,
        )
        output_datum = resolve_datum_unsafe(own_output, tx_info)
        
    elif isinstance(redeemer, PauseResumeSubscription):

        # check signature of model owner present (only model owner can pause/resume)
        model_owner_is_signing = (
            datum.model_owner_pubkeyhash in context.tx_info.signatories
        )
        assert model_owner_is_signing, "Required Model Owner Signature missing for pause/resume"

        # get input and output utxo
        own_input = tx_info.inputs[0]  # Assuming single script input for pause/resume
        own_output = tx_info.outputs[0]  # Assuming single script output

        # Validate pause/resume logic
        current_time = tx_info.valid_range.valid_range.lower_bound.time
        
        if redeemer.pause:
            # Pausing subscription
            assert not datum.is_paused, "Subscription is already paused"
            
            new_subscription_datum = SubscriptionDatum(
                datum.owner_pubkeyhash,
                datum.model_owner_pubkeyhash,
                datum.next_payment_date,
                datum.payment_intervall,
                datum.payment_amount,
                datum.payment_token,
                True,  # is_paused = True
                FinitePOSIXTime(current_time),  # pause_start_time = current time
            )
        else:
            # Resuming subscription
            assert datum.is_paused, "Subscription is not paused"
            
            # Calculate how long the subscription was paused
            pause_duration = current_time - datum.pause_start_time.time
            
            # Extend the next payment date by the pause duration
            extended_payment_date = FinitePOSIXTime(datum.next_payment_date.time + pause_duration)
            
            new_subscription_datum = SubscriptionDatum(
                datum.owner_pubkeyhash,
                datum.model_owner_pubkeyhash,
                extended_payment_date,
                datum.payment_intervall,
                datum.payment_amount,
                datum.payment_token,
                False,  # is_paused = False
                FinitePOSIXTime(0),  # pause_start_time = 0 (reset)
            )

        # Verify the output datum matches our expected new datum
        output_datum = resolve_datum_unsafe(own_output, tx_info)
        assert output_datum == new_subscription_datum, "Output datum does not match expected pause/resume datum"

        # Verify that the same amount of funds are returned to the contract
        input_amount = amount_of_token_in_output(datum.payment_token, own_input.resolved)
        output_amount = amount_of_token_in_output(datum.payment_token, own_output)
        assert input_amount == output_amount, "Funds must remain the same during pause/resume"
    

    else:
        assert False, "Invalid Redeemer"
