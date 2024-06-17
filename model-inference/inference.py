import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

class ModelHandler:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.tokenizer = None
        self.model = None

    def load_model(self):
        """Load the model and tokenizer from Hugging Face"""
        print(f"Loading model {self.model_name}...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
        print("Model loaded successfully.")

    def preprocess_input(self, input_text: str):
        """Tokenize the input text"""
        print(f"Tokenizing input: {input_text}")
        inputs = self.tokenizer(input_text, return_tensors='pt')
        print(f"Tokenized input: {inputs}")
        return inputs

    def predict(self, inputs):
        """Perform inference on the input text"""
        print("Performing inference...")
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
        print(f"Logits: {logits}")
        return logits

    def interpret_logits(self, logits):
        """Convert logits to human-readable output"""
        predictions = torch.nn.functional.softmax(logits, dim=-1)
        predicted_class = torch.argmax(predictions, dim=-1).item()
        confidence = torch.max(predictions).item()
        print(f"Predicted class: {predicted_class}, Confidence: {confidence}")
        return predicted_class, confidence

def hard_coded_inference(model_handler: ModelHandler):
    """Perform inference on a hard-coded input"""
    input_text = "I love using Hugging Face models!"
    inputs = model_handler.preprocess_input(input_text)
    logits = model_handler.predict(inputs)
    predicted_class, confidence = model_handler.interpret_logits(logits)
    return predicted_class, confidence

def test_model_loading():
    """Test if the model and tokenizer are loaded correctly"""
    model_name = "distilbert-base-uncased-finetuned-sst-2-english"
    model_handler = ModelHandler(model_name)
    model_handler.load_model()
    assert model_handler.tokenizer is not None, "Tokenizer loading failed!"
    assert model_handler.model is not None, "Model loading failed!"
    print("Model loading test passed.")

def test_preprocessing():
    """Test the preprocessing of input text"""
    model_name = "distilbert-base-uncased-finetuned-sst-2-english"
    model_handler = ModelHandler(model_name)
    model_handler.load_model()
    input_text = "This is a test."
    inputs = model_handler.preprocess_input(input_text)
    assert 'input_ids' in inputs, "Tokenization failed!"
    assert 'attention_mask' in inputs, "Tokenization failed!"
    print("Preprocessing test passed.")

def test_inference():
    """Test the inference on a hard-coded input"""
    model_name = "distilbert-base-uncased-finetuned-sst-2-english"
    model_handler = ModelHandler(model_name)
    model_handler.load_model()
    predicted_class, confidence = hard_coded_inference(model_handler)
    assert predicted_class is not None, "Inference failed!"
    assert confidence is not None, "Confidence score missing!"
    print("Inference test passed.")

if __name__ == "__main__":
    print("Testing model loading...")
    test_model_loading()
    
    print("\nTesting preprocessing...")
    test_preprocessing()
    
    print("\nTesting inference...")
    test_inference()
    
    print("\nAll tests passed.")
