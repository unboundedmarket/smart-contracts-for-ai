# User Guide: AI Smart Contracts on Cardano

## What Is This Project About?

This project creates a **decentralized ecosystem for AI services** using Cardano blockchain technology. In simple terms, it allows people to pay for AI services (like text analysis, sentiment analysis, etc.) using cryptocurrency, while ensuring both the user and AI service provider are protected through smart contracts.

Think of it like a subscription service (Netflix, Spotify) but for AI services, where:
- Users lock funds in a smart contract for regular payments
- AI service providers deliver services and get paid automatically
- Everything is transparent and secure on the blockchain

## The Big Picture: How It All Works

### Three Main Components

#### 1. **Smart Contracts** (The Blockchain Layer)
- **What it does**: Acts like a digital escrow service that holds money safely
- **Built with**: Opshin (a Python-like language for Cardano smart contracts)
- **Key features**: 
  - Time-locked payments (money can only be released on schedule)
  - Signature verification (only authorized people can access funds)
  - Pause/resume functionality (services can be temporarily stopped)

#### 2. **Off-Chain Scripts** (The User Interface)
- **What it does**: Handles all the complex blockchain interactions so users don't have to
- **Built with**: Python and PyCardano library
- **Key features**:
  - Easy subscription creation and management
  - Wallet management and transaction building
  - User-friendly command-line tools

#### 3. **AI Inference Engine** (The Service Provider)
- **What it does**: Provides actual AI services (currently sentiment analysis)
- **Built with**: Python and HuggingFace Transformers
- **Key features**:
  - Loads pre-trained AI models automatically
  - Processes text and returns predictions with confidence scores
  - Integrates seamlessly with payment verification

## Real-World Example: How a Transaction Works

Let's say Alice wants to use an AI sentiment analysis service provided by Bob:

### Step 1: Alice Creates a Subscription
```bash
# Alice runs this command to create a subscription
python offchain/user/create_subscription.py \
  --user-wallet alice \
  --model-owner-wallet bob \
  --payment-amount 1.0 \
  --payment-interval 3600 \
  --initial-balance 10.0
```

**What happens behind the scenes:**
1. Alice's wallet locks 10 ADA in the smart contract
2. The contract stores: "Alice pays Bob 1 ADA every hour for AI services"
3. The first payment becomes available in 1 hour
4. Transaction is recorded on Cardano blockchain

### Step 2: Bob Provides AI Service
```bash
# Alice requests sentiment analysis
python offchain/service_request.py \
  --input-text "I love this new AI service!" \
  --user-wallet alice \
  --model-owner bob
```

**What happens behind the scenes:**
1. System checks Alice has an active subscription with Bob
2. AI model analyzes the text: "POSITIVE sentiment, 99.8% confidence"
3. Result is returned to Alice
4. Usage is logged for billing

### Step 3: Bob Claims Payment
```bash
# Bob claims his payment (after the hour passes)
python offchain/model_owner/redeem_subscription.py
```

**What happens behind the scenes:**
1. Smart contract verifies it's time for payment (1 hour has passed)
2. Contract verifies Bob's signature
3. 1 ADA is transferred from contract to Bob's wallet
4. Next payment is scheduled for 1 hour later
5. Alice's remaining balance: 9 ADA

## Key Concepts Explained Simply

### Subscription Model
Instead of paying per AI request, users pre-fund a subscription. This is like:
- **Netflix**: You pay monthly, watch unlimited movies
- **Our system**: You lock funds, use AI services, provider gets paid on schedule

**Benefits:**
- Users don't need to approve every transaction
- Service providers get predictable income
- Lower transaction fees (bulk payments vs. micro-payments)

### Time-Locked Payments
Money in the contract can only be withdrawn on a schedule:
- **User perspective**: "I'm paying for a monthly service"
- **Provider perspective**: "I get paid monthly if I provide services"
- **Smart contract**: "I'll only release money on the agreed dates"

### Signature Verification
Every important action requires cryptographic proof:
- Only Alice can modify her subscription
- Only Bob can claim payments from Alice's subscription
- No one else can touch the money

### Pause/Resume Functionality
Service providers can temporarily stop services:
- Bob goes on vacation → pauses Alice's subscription
- Alice's payment schedule is extended by the pause duration
- Alice doesn't lose money for services not received

## Directory Structure Explained

```
contracts/
├── onchain/                    # Smart contract code (runs on blockchain)
│   ├── contract.py            # Main subscription logic and security rules
│   └── utils.py               # Helper functions for contracts
│
├── offchain/                   # User interface scripts (run on your computer)
│   ├── user/                  # Tools for subscription users
│   │   ├── create_subscription.py    # Start a new subscription
│   │   └── cancel_subscription.py    # End subscription and get refund
│   ├── model_owner/           # Tools for AI service providers
│   │   └── redeem_subscription.py    # Claim payments from subscriptions
│   ├── view_subscriptions.py  # See all active subscriptions
│   ├── subscription_status.py # Check detailed subscription info
│   ├── payment_history.py     # View payment analytics and history
│   ├── bulk_payment.py        # Process multiple payments efficiently
│   └── service_request.py     # Request AI service with payment verification
│
├── model-inference/           # AI service implementation
│   └── inference.py           # Loads AI models and processes requests
│
└── tests/                     # Testing and validation
    ├── unit/                  # Test individual components
    ├── integration/           # Test complete workflows
    ├── emulator/              # Test blockchain interactions safely
    └── validation/            # Performance and security validation
```

## Developer Setup Guide

### Prerequisites
You need these installed on your computer:
- **Python 3.8+**: The programming language everything is built with
- **pip**: Python's package installer (usually comes with Python)
- **git**: For downloading the code from GitHub

### Step-by-Step Setup

#### 1. Get the Code
```bash
git clone <repository-url>
cd contracts
```

#### 2. Create a Safe Working Environment
```bash
# Create a virtual environment (like a sandbox for this project)
python -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

#### 3. Install Required Packages
```bash
# Install main packages needed to run the system
pip install -r requirements.txt

# Install development tools for testing (optional but recommended)
pip install -r requirements-dev.txt
```

#### 4. Verify Installation
```bash
# Test that everything is working
python -c "import torch, transformers, pycardano; print('✅ All packages installed successfully!')"
```

If you see the success message, you're ready to go!

## How to Use the System

### For AI Service Users

#### Create a Subscription
```bash
cd offchain/user
python create_subscription.py \
  --user-wallet user1 \
  --model-owner-wallet owner1 \
  --payment-amount 2.0 \
  --payment-interval 3600 \
  --initial-balance 20.0
```

**Parameters explained:**
- `--user-wallet`: Your wallet name (must exist in `offchain/keys/`)
- `--model-owner-wallet`: AI service provider's wallet name
- `--payment-amount`: How much ADA to pay per interval
- `--payment-interval`: How often to pay (in seconds)
- `--initial-balance`: Total ADA to lock in the subscription

#### Use AI Services
```bash
python offchain/service_request.py \
  --input-text "This product is amazing!" \
  --user-wallet user1 \
  --model-owner owner1
```

**What you'll get:**
```
✅ AI Analysis Complete!
Input: "This product is amazing!"
Sentiment: POSITIVE
Confidence: 99.97%
Processing Time: 0.8 seconds
```

#### Check Your Subscription Status
```bash
python offchain/subscription_status.py --wallet user1
```

**Example output:**
```
📊 Subscription Status for user1:
Active Subscriptions: 1
Total Balance Locked: 20.0 ADA
Next Payment Due: 2024-01-15 14:30:00 UTC
Remaining Balance: 18.0 ADA
```

#### Cancel a Subscription
```bash
python cancel_subscription.py
```
This returns any remaining funds to your wallet.

### For AI Service Providers

#### Claim Payments
```bash
cd offchain/model_owner
python redeem_subscription.py
```

**What happens:**
- System finds all your subscriptions ready for payment
- Collects payments from eligible subscriptions
- Updates payment schedules for next cycle

#### View Your Subscriptions
```bash
python offchain/view_subscriptions.py --wallet owner1 --role owner
```

**Example output:**
```
📋 Subscriptions for owner1 (as service provider):
1. user1 → owner1: 2.0 ADA every hour (Balance: 18.0 ADA)
2. user2 → owner1: 1.0 ADA every day (Balance: 25.0 ADA)
Total Expected Revenue: 43.0 ADA
```

#### Process Multiple Payments at Once
```bash
python offchain/bulk_payment.py --wallet owner1 --limit 5
```
This is more efficient than claiming payments one by one.

#### Pause/Resume Services
```bash
python offchain/model_owner/pause_resume_subscription.py \
  --action pause \
  --utxo-id "transaction_id#0"
```

### Advanced Usage

#### Payment History and Analytics
```bash
# View payment history for the last 30 days
python offchain/payment_history.py --wallet user1 --role user --days 30

# View analytics as a service provider
python offchain/payment_history.py --wallet owner1 --role owner --analytics
```

#### Export Data as JSON
```bash
# Export subscription data for programmatic use
python offchain/view_subscriptions.py --role all --format json > subscriptions.json
```

## Testing the System

### Run All Tests
```bash
# Run the complete test suite
make test
```

### Run Specific Test Types
```bash
# Test smart contract logic
make test-unit

# Test complete user workflows
make test-integration

# Test blockchain interactions safely
make test-emulator

# Test with random inputs to find edge cases
make test-property

# Generate performance and security reports
make test-validation
```

### Manual Testing

#### Test AI Inference
```bash
cd model-inference
python inference.py
```

#### Test Subscription Creation
```bash
cd offchain/user
python create_subscription.py
```

## Understanding the Smart Contract

### What the Smart Contract Does

The smart contract is like a **digital escrow service** with built-in rules. Here are the key rules it enforces:

#### Rule 1: Only Authorized People Can Act
```python
# In the smart contract code
assert owner_is_updating, "Required Subscription Owner Signature missing"
assert model_owner_is_signing, "Required Model Owner Signature missing"
```
**Translation**: Only Alice can modify Alice's subscription. Only Bob can claim payments from Alice's subscription.

#### Rule 2: Payments Are Time-Locked
```python
# In the smart contract code
assert after_ext(tx_info.valid_range, payment_time)
```
**Translation**: Bob can only claim payment after the scheduled payment time has passed.

#### Rule 3: Sufficient Funds Must Remain
```python
# In the smart contract code
assert output_amount > min_amount, "Not enough funds returned to contract"
```
**Translation**: Bob can't withdraw more than the agreed payment amount. Remaining funds stay locked for future payments.

#### Rule 4: Pause Extends Payment Schedule
```python
# When resuming a paused subscription
pause_duration = current_time - datum.pause_start_time.time
extended_payment_date = FinitePOSIXTime(datum.next_payment_date.time + pause_duration)
```
**Translation**: If Bob pauses services for 1 week, Alice's next payment is delayed by 1 week.

### Data Structure
The smart contract stores this information for each subscription:
- `owner_pubkeyhash`: Alice's wallet identifier
- `model_owner_pubkeyhash`: Bob's wallet identifier  
- `next_payment_date`: When the next payment is due
- `payment_interval`: How often to pay (e.g., every hour)
- `payment_amount`: How much to pay each time
- `payment_token`: What cryptocurrency to use (currently ADA)
- `is_paused`: Whether the subscription is paused
- `pause_start_time`: When the pause started (for calculating extensions)

## Understanding the AI System

### How the AI Model Works

The system uses **DistilBERT**, a state-of-the-art AI model for text analysis:

#### Model Loading
```python
# From inference.py
self.tokenizer = AutoTokenizer.from_pretrained(model_name)
self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
```
**What happens**: Downloads and loads a pre-trained AI model from Hugging Face.

#### Text Processing
```python
# From inference.py
inputs = self.tokenizer(input_text, return_tensors='pt')
```
**What happens**: Converts human text into numbers the AI model can understand.

#### Prediction
```python
# From inference.py
outputs = self.model(**inputs)
predictions = torch.nn.functional.softmax(logits, dim=-1)
```
**What happens**: AI model analyzes the text and provides predictions with confidence scores.

### Current AI Capabilities
- **Text Classification**: Currently supports sentiment analysis (positive/negative)
- **High Accuracy**: Model achieves 99%+ confidence on clear examples
- **Fast Processing**: Results typically return in under 1 second
- **Extensible**: Easy to add support for other AI models and tasks

## Security Considerations

### Smart Contract Security
- **Signature Verification**: All critical operations require cryptographic proof of authorization
- **Time Locks**: Payments cannot be withdrawn before scheduled dates
- **Fund Protection**: Contract ensures sufficient collateral remains after withdrawals
- **Access Control**: Only authorized parties can modify their own subscriptions

### Off-Chain Security
- **Key Management**: Private keys are stored securely and never transmitted
- **Transaction Validation**: All transactions are validated before submission
- **Error Handling**: Robust error checking prevents invalid transactions

### AI Service Security
- **Subscription Verification**: AI services only process requests from verified subscribers
- **Usage Logging**: All AI requests are logged for audit trails
- **Rate Limiting**: Prevents abuse of AI services

## Common Troubleshooting

### Installation Issues
```bash
# If packages fail to install
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### Transaction Failures
- **Insufficient Balance**: Make sure your wallet has enough ADA for transactions
- **Wrong Network**: Ensure you're using the same network (testnet/mainnet) consistently
- **Key Issues**: Verify wallet files exist in `offchain/keys/`

### AI Model Issues
```bash
# If AI model fails to load
python -c "import torch; print(torch.cuda.is_available())"  # Check if GPU is available
pip install --upgrade transformers  # Update transformers library
```

### Blockchain Connection Issues
- **Network Problems**: Check your internet connection
- **Node Synchronization**: Blockchain nodes may take time to sync
- **Rate Limits**: Wait a few minutes between transactions

## Performance and Costs

### Transaction Costs
- **Subscription Creation**: ~0.2-0.3 ADA
- **Payment Redemption**: ~0.2-0.3 ADA  
- **Bulk Payments**: More efficient for multiple subscriptions

### AI Processing Performance
- **Sentiment Analysis**: 0.5-1.0 seconds per request
- **Memory Usage**: ~1-2GB RAM for model loading
- **CPU vs GPU**: GPU provides 5-10x speed improvement

### Scalability
- **Concurrent Users**: System can handle multiple simultaneous users
- **Subscription Limits**: No hard limits on number of subscriptions
- **Blockchain Throughput**: Limited by Cardano network capacity (~250 TPS)

## Contributing to the Project

### Development Workflow
```bash
# Make changes to code
# Run tests to ensure nothing breaks
make test

# Check code quality
make check

# Run full development pipeline
make ci
```

### Adding New AI Models
1. Create new model handler in `model-inference/`
2. Update service request handler to support new model types
3. Add corresponding tests
4. Update documentation

### Adding New Smart Contract Features
1. Modify `onchain/contract.py` with new logic
2. Add corresponding off-chain scripts
3. Write comprehensive tests
4. Validate security implications

