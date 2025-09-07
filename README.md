# Open-Source Smart Contracts for AI: Facilitating Model Inference Payments on Cardano

To report an issue or place a feature request please either raise an issue on GitHub or submit a suggestion/bug on our feedback form https://forms.gle/TvXMytFCFJoCw3Hv8 and we will raise the GitHub issue for you.

## Introduction

Welcome to the development setup for our project, "Open-Source Smart Contracts for AI: Facilitating Model Inference Payments on Cardano". Our goal is to leverage Cardano's blockchain technology to facilitate payments for AI model inferences using smart contracts. This setup will help us achieve this by integrating AI inference with blockchain payments.

This project is submitted under [Project Catalyst Fund 11](https://projectcatalyst.io/funds/11/cardano-use-cases-concept/open-source-smart-contracts-for-ai-facilitating-model-inference-payments-on-cardano).

## Project Overview

Our project aims to create an open-source framework that integrates AI model inference with Cardano smart contracts. This will allow developers to set up smart contracts that handle payments for AI inference services. The project includes:

1. **Opshin Code**: For writing and deploying smart contracts on Cardano.
2. **AI Model Inference**: Using pre-trained models from Hugging Face for inference.
3. **Off-Chain Code**: Utilizing PyCardano and Python for handling interactions between the Cardano blockchain and the AI inference service.

## Smart Contract Features

The smart contract system provides a subscription-based payment model for AI services:

### Subscription Management
- **Create Subscription**: Users can create new subscriptions by locking funds in the smart contract
- **Payment Scheduling**: Automatic payment intervals with configurable amounts and timing
- **Subscription Updates**: Users can modify their subscription details or cancel subscriptions
- **Payment Unlocking**: Model owners can unlock payments after providing services

### Security Features
- **Signature Verification**: All transactions require proper user signatures
- **Time-based Controls**: Payments can only be unlocked after the scheduled payment date
- **Fund Protection**: Ensures sufficient funds remain in the contract after withdrawals

## AI Model Inference System

The AI inference system provides a complete pipeline for running machine learning models:

### Model Handler
- **Easy Model Loading**: Simple interface to load pre-trained models from Hugging Face
- **Text Processing**: Automatic tokenization and preprocessing of input text
- **Inference Pipeline**: Complete workflow from input to prediction results
- **Confidence Scoring**: Provides confidence levels for model predictions

### Supported Models
- **Text Classification**: Currently supports sentiment analysis models
- **Extensible**: Easy to add support for other model types
- **Testing Framework**: Built-in tests to verify model functionality

## Off-Chain Operations

The off-chain system handles all blockchain interactions:

### User Operations
- **Create Subscription**: Lock funds and set up payment schedule
- **Cancel Subscription**: Terminate subscription and recover remaining funds
- **Wallet Management**: Secure key handling for testnet operations

### Model Owner Operations
- **Redeem Payments**: Unlock subscription payments after providing services
- **Subscription Monitoring**: Track active subscriptions and payment schedules
- **Fund Management**: Handle incoming and outgoing payment flows

### Advanced Management Tools
- **View Subscriptions**: List and filter all active subscriptions by user or model owner
- **Subscription Status**: Check detailed status including payment timing and remaining balance
- **Payment History**: Track transaction history with analytics and revenue reports
- **Bulk Payment Processing**: Efficiently process multiple subscription payments in one transaction
- **AI Service Integration**: Submit AI inference requests with automatic payment verification
- **JSON Export**: Export subscription data in JSON format for programmatic access and integration

## Development Setup

### Requirements

To set up the development environment, ensure you have the following prerequisites:

- Python 3.8 or higher
- pip (Python package installer)
- git (for cloning the repository)

### Installing Packages

This project requires several Python packages to work properly. All the required packages are listed in the `requirements.txt` file, which makes installation easy and consistent. Follow these step-by-step instructions to get everything set up on your computer:

#### Step 1: Get the Code
First, you need to download the project code to your computer. This is called "cloning" the repository:

```bash
git clone <repository-url>  # Replace with actual repository URL
cd contracts
```

#### Step 2: Set Up a Safe Working Space
For this project its a good idea to create a virtual enviornment. 

With the following command you can create the enviornment: 
```bash
python -m venv venv
```

Now activate (turn on) this virtual environment:

```bash
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

#### Step 3: Install the Main Packages
Now install all the packages the project needs to run:

```bash
pip install -r requirements.txt
```

#### Step 4: Install Development Tools (Optional but Recommended)
If you want to run tests or contribute to the project, also install the development packages:

```bash
pip install -r requirements-dev.txt
```

#### Verification
To make sure everything installed correctly, you can run this simple test:

```bash
python -c "import torch, transformers, pycardano; print('All packages installed successfully!')"
```

If you see the success message, you're all set! If you get an error, double-check that you followed all the steps above.

### Key Dependencies
- **torch**: PyTorch for AI model inference
- **transformers**: Hugging Face library for pre-trained models
- **pycardano**: Python library for Cardano blockchain interaction
- **opshin**: Python-based smart contract language for Cardano
- **click**: Command-line interface framework

## Directory Structure

```
.
├── onchain/                    # Directory containing Opshin smart contract code
│   ├── contract.py            # Main smart contract with subscription logic
│   └── utils.py               # Contract utility functions
├── model-inference/           # Directory containing AI inference scripts
│   ├── inference.py           # AI model handler and inference pipeline
│   └── __init__.py            # Package initialization
├── offchain/                  # Directory containing PyCardano scripts
│   ├── keys/                  # Test wallet keys and addresses
│   ├── user/                  # User subscription operations
│   │   ├── create_subscription.py    # Create new subscription
│   │   └── cancel_subscription.py    # Cancel existing subscription
│   ├── model_owner/           # Model owner operations
│   │   └── redeem_subscription.py    # Redeem subscription payments
│   ├── view_subscriptions.py  # View and list active subscriptions
│   ├── subscription_status.py # Check detailed subscription status
│   ├── payment_history.py     # Track payment history and analytics
│   ├── bulk_payment.py        # Process multiple payments efficiently
│   ├── service_request.py     # AI inference with payment verification
│   ├── utils.py               # Off-chain utility functions
│   └── secret.py              # Configuration and secrets
├── tests/                      # Comprehensive test suite
│   ├── unit/                  # Unit tests for contract logic
│   │   ├── test_contract.py   # Smart contract validation tests
│   │   └── test_property_based.py # Property-based tests with hypothesis
│   ├── integration/           # End-to-end workflow tests
│   │   └── test_subscription_flows.py # Complete subscription lifecycle tests
│   ├── emulator/              # Blockchain simulation tests
│   │   └── test_blockchain_simulation.py # PyCardano emulator tests
│   ├── validation/            # Contract validation and reporting
│   │   └── test_contract_validation.py # Performance and security validation
│   └── conftest.py            # Shared test fixtures and configuration
├── requirements.txt            # List of required Python packages
├── requirements-dev.txt        # Development and testing dependencies
├── pytest.ini                 # Test configuration
├── Makefile                    # Test automation and development commands
└── README.md                  # This readme file
```

## How the System Works

### 1. Subscription Creation
1. User creates a subscription by locking funds in the smart contract
2. Contract stores subscription details: owner, model owner, payment schedule, and amounts
3. Funds are locked until the payment date arrives

### 2. AI Service Provision
1. Model owner provides AI inference services to the user
2. When payment is due, model owner can unlock the scheduled payment
3. Contract verifies the model owner's signature and payment timing

### 3. Payment Processing
1. Contract checks that payment date has passed
2. Verifies sufficient funds remain in the contract
3. Updates subscription data for the next payment cycle
4. Transfers payment to the model owner

### 4. Subscription Management
1. Users can update subscription details or cancel subscriptions
2. All changes require proper user signatures
3. Cancelled subscriptions return remaining funds to users

## Smart Contract Testing

Our project includes a complete test suite that validates smart contract logic, blockchain interactions, and system performance. We are trying to follow a best-practice approach for blockchain testing. 

### Test Types

**Unit Tests** - Test individual contract functions and validation logic
- Test signature verification for all operations
- Test time lock enforcement for payments  
- Test fund protection mechanisms
- Test pause/resume functionality

**Integration Tests** - Test complete workflows from start to finish
- Test full subscription creation process
- Test payment redemption cycles
- Test subscription cancellation flows
- Test AI service integration with payments

**Emulator Tests** - Test blockchain interactions without real network
- Simulate contract transactions
- Test UTXO management
- Test multiple subscription scenarios
- Validate transaction costs and timing

**Property-Based Tests** - Test contract with random inputs to find edge cases
- Generate random valid/invalid subscription data
- Test contract invariants (funds never disappear, signatures always required)

**Validation Tests** - Generate reports on contract performance and security
- Check contract size limits (must be under 16KB)
- Analyze transaction costs for each operation
- Validate security properties and access controls
- Generate performance metrics and efficiency reports

### Running Tests

Install test dependencies:
```bash
pip install -r requirements-dev.txt
```

Run all tests:
```bash
make test
```

Run specific test types:
```bash
# Unit tests only
make test-unit

# Integration tests only  
make test-integration

# Emulator tests only
make test-emulator

# Property-based tests only
make test-property

# Validation tests only
make test-validation
```

Generate test coverage report:
```bash
make coverage
```

This creates an HTML report in `htmlcov/` showing which code is tested. Current coverage: 40%.

### Test Results and Reports

Tests generate validation artifacts that can be used to test any changes and help guarantee security properties set in the contract. 


### Quick Development Workflow

```bash
# Check code quality and run fast tests
make check

# Full development pipeline (run before committing)
make ci
```

### Manual Testing and Development

### Running AI Inference Tests
```bash
cd model-inference
python inference.py
```

### Creating Test Subscriptions
```bash
cd offchain/user
python create_subscription.py
```

### Managing Subscriptions
```bash
# Cancel subscription as user
cd offchain/user
python cancel_subscription.py

# Redeem payment as model owner
cd offchain/model_owner
python redeem_subscription.py
```

### Advanced Off-Chain Operations

#### Viewing and Monitoring Subscriptions
```bash
# View all active subscriptions
python offchain/view_subscriptions.py --role all

# View subscriptions for a specific user
python offchain/view_subscriptions.py --wallet user1 --role user

# View subscriptions managed by a model owner
python offchain/view_subscriptions.py --wallet owner1 --role owner

# Export subscription data as JSON for programmatic access
python offchain/view_subscriptions.py --role all --format json
python offchain/view_subscriptions.py --wallet user1 --role user --format json
```

#### Checking Subscription Status
```bash
# Check status by wallet
python offchain/subscription_status.py --wallet user1

# Check status by specific UTXO ID
python offchain/subscription_status.py --utxo-id "transaction_id#index"

# Export detailed status as JSON
python offchain/subscription_status.py --wallet user1 --format json
python offchain/subscription_status.py --utxo-id "transaction_id#index" --format json
```

#### Payment History and Analytics
```bash
# View payment history for a user
python offchain/payment_history.py --wallet user1 --role user --days 30

# View payment analytics for a model owner
python offchain/payment_history.py --wallet owner1 --role owner --analytics

# View all payment history with analytics
python offchain/payment_history.py --role all --analytics --days 7
```

#### Bulk Payment Processing
```bash
# Simulate bulk payment savings
python offchain/bulk_payment.py --wallet owner1 --simulate

# Process bulk payments (dry run)
python offchain/bulk_payment.py --wallet owner1 --limit 5 --dry-run

# Execute bulk payment processing (includes safety confirmation prompt)
python offchain/bulk_payment.py --wallet owner1 --limit 3
```

#### AI Service Requests
```bash
# Submit AI inference request with payment verification
python offchain/service_request.py \
  --input-text "I love using this AI service!" \
  --user-wallet user1 \
  --model-owner owner1

# Test AI inference without subscription verification
python offchain/service_request.py \
  --input-text "This product is amazing!" \
  --user-wallet user1 \
  --model-owner owner1 \
  --skip-verification

# Save results to file
python offchain/service_request.py \
  --input-text "Great experience!" \
  --user-wallet user1 \
  --model-owner owner1 \
  --output-file results.json
```

## Choices Behind the Development Setup

1. **Opshin**: Chosen for its Python-based approach, making it accessible for Python developers and ensuring a safer smart contract development environment.
2. **Hugging Face Transformers**: Provides a robust library for loading and using pre-trained AI models, simplifying the AI inference process.
3. **PyCardano**: Facilitates the creation and management of off-chain interactions, essential for integrating Cardano blockchain with our AI inference service.
4. **Subscription Model**: Implements a recurring payment system that matches typical AI service usage patterns.
5. **Time-based Payments**: Ensures fair payment scheduling and prevents premature fund withdrawal.

## Security Considerations

- **Signature Verification**: All critical operations require proper cryptographic signatures
- **Time Locks**: Payments cannot be withdrawn before scheduled dates
- **Fund Protection**: Smart contract ensures sufficient collateral remains
- **Access Control**: Only authorized parties can modify their own subscriptions

## Contributing

We welcome contributions from the community! Please open an issue here on Github or contact us on our X page.   
