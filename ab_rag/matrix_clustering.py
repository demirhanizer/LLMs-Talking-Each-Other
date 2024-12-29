import transformers
import torch
import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import matplotlib.pyplot as plt
import seaborn as sns
from transformers import AutoTokenizer, AutoModel

# Load embedding model
embedding_model_name = "dbmdz/bert-base-turkish-cased"
tokenizer = AutoTokenizer.from_pretrained(embedding_model_name)
embedding_model = AutoModel.from_pretrained(embedding_model_name)

# Function to embed text
def embed_text(text):
    if not isinstance(text, str):
        text = str(text)  # Convert input to string if not already
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
    with torch.no_grad():
        outputs = embedding_model(**inputs)
    return outputs.last_hidden_state.mean(dim=1).squeeze().numpy()

# Load the generated responses and reference answers
generated_responses_file = "/cta/users/elalem2/ab/generated_responses_0_50.json"
reference_answers_file = "/cta/users/elalem2/ab/merged_400.json"

def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)

# Load data
generated_responses_data = load_json(generated_responses_file)

# Debug the structure of generated_responses_data
print("Inspecting structure of generated_responses_data...")
print(type(generated_responses_data))  # Should be a list
print(generated_responses_data[:1])   # Print the first entry for debugging

# Extract generated responses
generated_responses = []
for response_list in generated_responses_data:
    # Find the assistant's content within the nested structure
    assistant_response = next(
        (item["content"] for item in response_list if item["role"] == "assistant"), None
    )
    if assistant_response:
        generated_responses.append(assistant_response)

print(f"Extracted {len(generated_responses)} generated responses.")

# Load reference answers
reference_data = load_json(reference_answers_file)
reference_answers = [item["answer"] for item in reference_data[:50]]

# Compute similarity matrix
def compute_similarity_matrix(generated, reference):
    print("Computing similarity matrix...")
    generated_embeddings = [embed_text(text) for text in generated]
    reference_embeddings = [embed_text(text) for text in reference]
    similarity_matrix = cosine_similarity(generated_embeddings, reference_embeddings)
    return similarity_matrix

similarity_matrix = compute_similarity_matrix(generated_responses, reference_answers)

# Plot similarity matrix
def plot_similarity_matrix(matrix, output_file, title="Similarity Matrix"):
    print(f"Plotting similarity matrix: {title}")
    plt.figure(figsize=(12, 8))
    sns.heatmap(matrix, annot=False, cmap="viridis", cbar=True)
    plt.title(title)
    plt.xlabel("Reference Answers")
    plt.ylabel("Generated Responses")
    plt.tight_layout()
    plt.savefig(output_file)
    plt.close()
    print(f"Similarity matrix saved to {output_file}")

similarity_matrix_output = f"/cta/users/elalem2/ab/similarity_matrix_0_50.png"
plot_similarity_matrix(similarity_matrix, similarity_matrix_output)

# Find least similar rows
def find_least_similar_rows(matrix, num_rows=5):
    row_sums = np.mean(matrix, axis=1)
    least_similar_indices = np.argsort(row_sums)[:num_rows]
    return least_similar_indices, row_sums[least_similar_indices]

least_similar_indices, least_similar_scores = find_least_similar_rows(similarity_matrix)

# Save least similar rows
least_similar_data = [
    {
        "index": int(idx),
        "generated_response": generated_responses[idx],
        "reference_answer": reference_answers[idx],
        "similarity_score": float(least_similar_scores[i]),
    }
    for i, idx in enumerate(least_similar_indices)
]

least_similar_file = f"/cta/users/elalem2/ab/least_similar_responses_0_50.json"
with open(least_similar_file, "w", encoding="utf-8") as file:
    json.dump(least_similar_data, file, ensure_ascii=False, indent=4)
print(f"Least similar rows saved to {least_similar_file}")

print("All tasks completed successfully!")
