# Open-Source Smart Contracts for AI: Facilitating Model Inference Payments on Cardano

## Introduction

Welcome to the development setup for our project, "Open-Source Smart Contracts for AI: Facilitating Model Inference Payments on Cardano". Our goal is to leverage Cardano's blockchain technology to facilitate payments for AI model inferences using smart contracts. This setup will help us achieve this by integrating AI inference with blockchain payments.

This project is submitted under [Project Catalyst Fund 11](https://projectcatalyst.io/funds/11/cardano-use-cases-concept/open-source-smart-contracts-for-ai-facilitating-model-inference-payments-on-cardano).

## Project Overview

Our project aims to create an open-source framework that integrates AI model inference with Cardano smart contracts. This will allow developers to set up smart contracts that handle payments for AI inference services. The project includes:

1. **Opshin Code**: For writing and deploying smart contracts on Cardano.
2. **AI Model Inference**: Using pre-trained models from Hugging Face for inference.
3. **Off-Chain Code**: Utilizing PyCardano and Python for handling interactions between the Cardano blockchain and the AI inference service.

## Development Setup

### Requirements

To set up the development environment, ensure you have the following prerequisites:

- Python 3.8 or higher
- pip (Python package installer)

### Installing Packages

The required packages for this setup are listed in `requirements.txt`. To install these packages, follow the steps below:

1. Clone the repository:

    ```bash
    git clone [https://github.com/your-repo/ai-cardano-smart-contracts.git](https://github.com/unboundedmarket/Smart-Contracts-for-AI.git)
    cd ai-cardano-smart-contracts
    ```

2. Install the required packages:

    ```bash
    pip install -r requirements.txt
    ```

### Opshin Code

Opshin is a Python-based smart contract language for Cardano. It allows developers to write smart contracts in a more familiar language, enhancing development speed and security. In this project, we use Opshin to write the smart contracts that handle payments for AI inferences.

### AI Model Inference

We utilize Hugging Face's Transformers library to perform AI model inference. The process involves loading a pre-trained model, tokenizing the input, performing inference, and interpreting the results.

### PyCardano for Off-Chain Code

PyCardano is a Python library for off-chain code interaction with the Cardano blockchain. It helps in building transactions, signing them, and submitting them to the network. We use PyCardano to handle the off-chain interactions required for our smart contract operations.

## Directory Structure

```
.
├── on-chain               # Directory containing Opshin smart contract code
├── model-inference        # Directory containing AI inference scripts
├── off-chain              # Directory containing PyCardano scripts
├── requirements.txt       # List of required Python packages
└── README.md              # This readme file
```

## Choices Behind the Development Setup

1. **Opshin**: Chosen for its Python-based approach, making it accessible for Python developers and ensuring a safer smart contract development environment.
2. **Hugging Face Transformers**: Provides a robust library for loading and using pre-trained AI models, simplifying the AI inference process.
3. **PyCardano**: Facilitates the creation and management of off-chain interactions, essential for integrating Cardano blockchain with our AI inference service.

## How to Use the Setup

1. **Setting up Opshin Smart Contracts**:
   - Write your smart contract in the `on-chain` directory.
   - Deploy the contract using Opshin tools.

2. **Performing AI Model Inference**:
   - Use the scripts in the `model-inference` directory to load a model and perform inference.
   - Ensure the model is downloaded and the inference script is correctly set up.

3. **Handling Off-Chain Code**:
   - Utilize PyCardano scripts in the `off-chain` directory to manage interactions with the Cardano blockchain.
   - These scripts will help in building, signing, and submitting transactions.
