from transformers import AutoTokenizer, AutoModelForCausalLM
from bert_score import BERTScorer
import json
from typing import List, Dict
import numpy as np
import os
import torch
from accelerate import init_empty_weights, infer_auto_device_map, load_checkpoint_and_dispatch

def load_test_data(file_path: str) -> List[Dict]:
    """Load test data from a newline-delimited JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return [json.loads(line) for line in f]
    except FileNotFoundError:
        raise FileNotFoundError(f"Test data file not found at: {os.path.abspath(file_path)}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Error decoding JSON from file: {file_path}. Details: {e}")

def generate_responses(model, tokenizer, test_data: List[Dict]) -> List[Dict]:
    """
    Generate responses using the fine-tuned model for each question in the test data.
    """
    for idx, item in enumerate(test_data):
        print(f"Processing item {idx + 1}/{len(test_data)}")
        question = item['Question']
        print(f"Question: {question}")
        inputs = tokenizer(question, return_tensors="pt", padding=True, truncation=True, max_length=512)
        inputs = {key: value.to('cuda' if torch.cuda.is_available() else 'cpu') for key, value in inputs.items()}

        with torch.no_grad():
            outputs = model.generate(**inputs, max_length=100, num_return_sequences=1, pad_token_id=tokenizer.pad_token_id)
        predicted_response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(f"Predicted Response: {predicted_response}")

        item['Predicted_Response'] = predicted_response
    
    return test_data

def evaluate_responses(test_data: List[Dict]) -> Dict:
    """
    Evaluate model's responses using BERTScore
    """
    scorer = BERTScorer(
        model_type="dbmdz/bert-base-turkish-cased",
        num_layers=9,
        batch_size=32,
        lang="tr"
    )

    references = []
    predictions = []
    questions = []

    for item in test_data:
        if 'Predicted_Response' in item and item['Predicted_Response']:  
            references.append(item['Answer'])
            predictions.append(item['Predicted_Response'])
            questions.append(item['Question'])

    if not predictions:
        raise ValueError("No valid predictions found in the test data")

    print(f"Evaluating {len(predictions)} QA pairs...")

    # Calculate BERTScores
    P, R, F1 = scorer.score(predictions, references)

    # Convert to numpy for calculations
    P = P.numpy()
    R = R.numpy()
    F1 = F1.numpy()

    # Prepare detailed results
    detailed_results = []
    for i in range(len(questions)):
        detailed_results.append({
            'question': questions[i],
            'reference': references[i],
            'prediction': predictions[i],
            'precision': float(P[i]),
            'recall': float(R[i]),
            'f1': float(F1[i])
        })

    # Calculate average scores
    results = {
        'average_scores': {
            'precision': float(np.mean(P)),
            'recall': float(np.mean(R)),
            'f1': float(np.mean(F1))
        },
        'detailed_results': detailed_results
    }

    return results

def save_results(results: Dict, output_file: str):
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"Results saved to: {os.path.abspath(output_file)}")
    except Exception as e:
        raise Exception(f"Error saving results to {output_file}: {str(e)}")

def main():
    test_data_path = "/cta/users/elalem2/converted_file.jsonl"
    results_output_path = "/cta/users/elalem2/evaluation_results_bert.json"

    try:
        print(f"Loading test data from: {os.path.abspath(test_data_path)}")
        test_data = load_test_data(test_data_path)
        test_data = test_data[:5]

        print("Loading the fine-tuned model and tokenizer...")
        with init_empty_weights():
            model = AutoModelForCausalLM.from_pretrained(
                "",
                device_map="auto",
                offload_folder="offload",  
                offload_state_dict=True, 
            )

        tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-70B")
        tokenizer.pad_token = tokenizer.eos_token

        print("Generating model responses...")
        test_data = generate_responses(model, tokenizer, test_data)

        print("Running BERTScore evaluation...")
        results = evaluate_responses(test_data)

        print("\nEvaluation Summary:")
        print(f"Average F1: {results['average_scores']['f1']:.3f}")
        print(f"Average Precision: {results['average_scores']['precision']:.3f}")
        print(f"Average Recall: {results['average_scores']['recall']:.3f}")

        save_results(results, results_output_path)
    except Exception as e:
        print(f"Error during evaluation: {str(e)}")
        raise

if __name__ == "__main__":
    main()
