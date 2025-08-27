"""
Submit AI inference requests with payment verification
Integrates subscription payments with AI model inference services
"""

import click
import json
from datetime import datetime
from typing import Optional, Dict, Any
from pycardano import Network

from offchain.utils import (
    get_signing_info,
    get_contract,
    context,
    to_address,
)
from onchain import contract

# Import AI inference functionality
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from model_inference.inference import ModelHandler


def verify_subscription_status(user_wallet: str, model_owner_wallet: str, network: Network) -> Optional[dict]:
    """Verify that user has an active subscription with the model owner"""
    try:
        # Get wallet addresses
        _, _, user_address = get_signing_info(user_wallet, network=network)
        _, _, model_owner_address = get_signing_info(model_owner_wallet, network=network)
        
        user_pkh = to_address(user_address).payment_credential.credential_hash
        model_owner_pkh = to_address(model_owner_address).payment_credential.credential_hash
        
        # Get contract info
        script, _, script_address = get_contract("contract")
        
        # Find matching subscription
        for utxo in context.utxos(script_address):
            try:
                datum = contract.SubscriptionDatum.from_cbor(utxo.output.datum.cbor)
                
                # Check if this subscription matches user and model owner
                if (datum.owner_pubkeyhash.payload == user_pkh.payload and 
                    datum.model_owner_pubkeyhash.payload == model_owner_pkh.payload):
                    
                    # Check subscription status
                    current_time = datetime.utcnow()
                    next_payment = datetime.fromtimestamp(datum.next_payment_date.time / 1000)
                    current_balance = utxo.output.amount.coin
                    payment_amount = datum.payment_amount
                    is_paused = getattr(datum, 'is_paused', False)
                    
                    subscription_info = {
                        "utxo_id": f"{utxo.input.transaction_id}#{utxo.input.index}",
                        "is_active": current_balance >= payment_amount and not is_paused,
                        "balance_ada": current_balance / 1_000_000,
                        "payment_amount_ada": payment_amount / 1_000_000,
                        "next_payment_date": next_payment,
                        "is_payment_overdue": current_time >= next_payment,
                        "payments_remaining": int(current_balance / payment_amount) if payment_amount > 0 else 0,
                        "is_paused": is_paused,
                        "can_use_service": current_balance >= payment_amount and current_time < next_payment and not is_paused
                    }
                    
                    return subscription_info
                    
            except Exception as e:
                continue
        
        return None
        
    except Exception as e:
        print(f"Error verifying subscription: {e}")
        return None


def process_ai_inference_request(
    input_text: str, 
    model_name: str = "distilbert-base-uncased-finetuned-sst-2-english",
    subscription_info: Optional[dict] = None
) -> Dict[str, Any]:
    """Process AI inference request with subscription verification"""
    
    request_timestamp = datetime.utcnow()
    
    # Check subscription authorization
    if subscription_info and not subscription_info.get('can_use_service', False):
        return {
            "success": False,
            "error": "Subscription not active or payment overdue",
            "timestamp": request_timestamp.isoformat(),
            "subscription_status": subscription_info
        }
    
    try:
        # Initialize model handler
        print(f"🤖 Loading AI model: {model_name}")
        model_handler = ModelHandler(model_name)
        model_handler.load_model()
        
        # Process the inference request
        print(f"🔍 Processing inference request...")
        inputs = model_handler.preprocess_input(input_text)
        logits = model_handler.predict(inputs)
        predicted_class, confidence = model_handler.interpret_logits(logits)
        
        # Prepare response
        response = {
            "success": True,
            "timestamp": request_timestamp.isoformat(),
            "request": {
                "input_text": input_text,
                "model_name": model_name
            },
            "result": {
                "predicted_class": predicted_class,
                "confidence": float(confidence),
                "interpretation": "POSITIVE" if predicted_class == 1 else "NEGATIVE"
            },
            "subscription_info": subscription_info,
            "service_metadata": {
                "processing_time_ms": 0,  # Would be calculated in real implementation
                "model_version": "1.0",
                "service_provider": "AI Smart Contract Service"
            }
        }
        
        print(f"✅ Inference completed successfully")
        print(f"   Input: {input_text}")
        print(f"   Result: {response['result']['interpretation']} (confidence: {confidence:.2%})")
        
        return response
        
    except Exception as e:
        return {
            "success": False,
            "error": f"AI inference failed: {str(e)}",
            "timestamp": request_timestamp.isoformat(),
            "subscription_info": subscription_info
        }


def log_service_usage(response: Dict[str, Any], user_wallet: str, model_owner_wallet: str):
    """Log service usage for analytics and billing"""
    
    # In a real implementation, this would write to a database or blockchain
    log_entry = {
        "timestamp": response["timestamp"],
        "user_wallet": user_wallet,
        "model_owner_wallet": model_owner_wallet,
        "success": response["success"],
        "input_length": len(response.get("request", {}).get("input_text", "")),
        "model_name": response.get("request", {}).get("model_name", ""),
        "subscription_utxo": response.get("subscription_info", {}).get("utxo_id", ""),
        "error": response.get("error")
    }
    
    # For demo purposes, save to local file
    log_file = Path(__file__).parent / "service_usage.log"
    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    print(f"📝 Service usage logged to {log_file}")


def create_service_request_with_verification(
    input_text: str,
    user_wallet: str,
    model_owner_wallet: str,
    model_name: str = "distilbert-base-uncased-finetuned-sst-2-english",
    network: Network = Network.TESTNET,
    skip_verification: bool = False
) -> Dict[str, Any]:
    """Create a complete service request with subscription verification"""
    
    print(f"🔍 Service Request Processing")
    print("=" * 40)
    print(f"User: {user_wallet}")
    print(f"Model Owner: {model_owner_wallet}")
    print(f"Model: {model_name}")
    print(f"Input: {input_text}")
    
    subscription_info = None
    
    if not skip_verification:
        print(f"\n🔐 Verifying subscription...")
        subscription_info = verify_subscription_status(user_wallet, model_owner_wallet, network)
        
        if not subscription_info:
            return {
                "success": False,
                "error": "No active subscription found between user and model owner",
                "timestamp": datetime.utcnow().isoformat(),
                "user_wallet": user_wallet,
                "model_owner_wallet": model_owner_wallet
            }
        
        print(f"✅ Subscription verified:")
        print(f"   Balance: {subscription_info['balance_ada']:.6f} ADA")
        print(f"   Can use service: {subscription_info['can_use_service']}")
        
        if not subscription_info['can_use_service']:
            if subscription_info['is_paused']:
                error_msg = "Service is temporarily paused by the model owner"
            elif subscription_info['is_payment_overdue']:
                error_msg = "Payment is overdue - please make payment to continue using service"
            else:
                error_msg = "Insufficient subscription balance"
            
            return {
                "success": False,
                "error": error_msg,
                "timestamp": datetime.utcnow().isoformat(),
                "subscription_info": subscription_info
            }
    
    # Process the AI inference
    print(f"\n🚀 Processing AI inference...")
    response = process_ai_inference_request(input_text, model_name, subscription_info)
    
    # Log usage
    log_service_usage(response, user_wallet, model_owner_wallet)
    
    return response


@click.command()
@click.option('--input-text', '-i', required=True, help='Text to analyze with AI model')
@click.option('--user-wallet', '-u', required=True, help='User wallet name (user1, etc.)')
@click.option('--model-owner', '-m', required=True, help='Model owner wallet name (owner1, etc.)')
@click.option('--model-name', default='distilbert-base-uncased-finetuned-sst-2-english',
              help='AI model to use for inference')
@click.option('--skip-verification', '-s', is_flag=True, 
              help='Skip subscription verification (for testing)')
@click.option('--network', '-n', type=click.Choice(['testnet', 'mainnet']), default='testnet',
              help='Network to use')
@click.option('--output-file', '-o', help='Save response to JSON file')
def main(input_text: str, user_wallet: str, model_owner: str, model_name: str, 
         skip_verification: bool, network: str, output_file: Optional[str]):
    """Submit AI inference request with subscription verification"""
    
    network_enum = Network.TESTNET if network == 'testnet' else Network.MAINNET
    
    # Process the service request
    response = create_service_request_with_verification(
        input_text=input_text,
        user_wallet=user_wallet,
        model_owner_wallet=model_owner,
        model_name=model_name,
        network=network_enum,
        skip_verification=skip_verification
    )
    
    # Display results
    print(f"\n📋 Service Response")
    print("=" * 30)
    
    if response["success"]:
        result = response["result"]
        print(f"✅ Success: {result['interpretation']}")
        print(f"🎯 Confidence: {result['confidence']:.2%}")
        print(f"📊 Predicted Class: {result['predicted_class']}")
        
        if response.get("subscription_info"):
            sub_info = response["subscription_info"]
            print(f"\n💳 Subscription Used:")
            print(f"   Remaining Balance: {sub_info['balance_ada']:.6f} ADA")
            print(f"   Payments Remaining: {sub_info['payments_remaining']}")
    else:
        print(f"❌ Error: {response['error']}")
        
        if response.get("subscription_info"):
            sub_info = response["subscription_info"]
            print(f"\n💳 Subscription Status:")
            print(f"   Active: {sub_info['is_active']}")
            print(f"   Balance: {sub_info['balance_ada']:.6f} ADA")
            print(f"   Payment Overdue: {sub_info['is_payment_overdue']}")
            if sub_info.get('is_paused'):
                print(f"   ⏸️  Service is PAUSED by model owner")
    
    # Save to file if requested
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(response, f, indent=2, default=str)
        print(f"\n💾 Response saved to {output_file}")


if __name__ == "__main__":
    main()
