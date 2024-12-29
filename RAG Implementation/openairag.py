
import json
import matplotlib.pyplot as plt
from evaluate import load
from sentence_transformers import SentenceTransformer, util
import seaborn as sns
import openai
from transformers import AutoModelForCausalLM, AutoTokenizer

openai.api_key = ""

model_name = "ytu-ce-cosmos/Turkish-Llama-8b-Instruct-v0.1"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name, device_map="auto")

predicted_file = "/cta/users/elalem2/ab/processed_responses.jsonl"
reference_file = "/cta/users/elalem2/ab/merged_400.json"
output_scores_file = "/cta/users/elalem2/ab/bert_scores_with_llm_and_base_modelaaaaaa.json"
output_plot_dir = "/cta/users/elalem2/ab/"  

def load_jsonl(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return [json.loads(line) for line in file]

def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)

predicted_data = load_jsonl(predicted_file)
reference_data = load_json(reference_file)

predicted_answers = [item["answer"] for item in predicted_data[:100]]
reference_answers = [item["answer"] for item in reference_data[:100]]
instructions = [item["instruction"] for item in predicted_data[:100]]

bert_score_metric = load("bertscore")

semantic_model = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")

def get_base_model_response(instruction):
    """Base modelden cevap alır."""
    input_ids = tokenizer.encode(instruction, return_tensors="pt").to("cuda")
    outputs = model.generate(input_ids, max_length=150, temperature=0.7, pad_token_id=tokenizer.eos_token_id)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

def calculate_metrics(predictions, references):
    """BERT F1 ve semantik benzerlik skorlarını hesaplar."""
    # BERT F1
    bert_results = bert_score_metric.compute(
        predictions=predictions,
        references=references,
        lang="tr",  
        model_type="dbmdz/bert-base-turkish-cased"
    )
    bert_f1_scores = bert_results["f1"]

    semantic_similarities = []
    for pred, ref in zip(predictions, references):
        pred_embedding = semantic_model.encode(pred, convert_to_tensor=True)
        ref_embedding = semantic_model.encode(ref, convert_to_tensor=True)
        similarity = util.cos_sim(pred_embedding, ref_embedding).item()
        semantic_similarities.append(similarity)

    return bert_f1_scores, semantic_similarities

def evaluate_with_llm(question, reference_answer, predicted_answer):
    """LLM ile değerlendirme yapar ve tek bir skor döndürür."""
    messages = [
        {"role": "system", "content": "Bir değerlendirme yargıcı olarak cevapları analiz et."},
        {"role": "user", "content": f"""
        Aşağıdaki iki cevabı karşılaştır ve bir skor ver:

        Soru: {question}
        Referans Yanıt: {reference_answer}
        Modelin Tahmini Yanıtı: {predicted_answer}

        Değerlendirme Kriterleri:
        - Doğruluk, bağlama uygunluk ve dil-stil uyumu gibi faktörleri göz önünde bulundur.
        - Ancak yalnızca 0 ile 1 arasında bir sayı döndür. Açıklama yapma. Sadece sayı yaz.
        """}
    ]

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            max_tokens=10,  
            temperature=0.0  
        )
        return float(response['choices'][0]['message']['content'].strip())
    except openai.error.OpenAIError as e:
        print(f"OpenAI API hatası: {e}")
        return None

base_model_answers = [get_base_model_response(instr) for instr in instructions]

predicted_bert_f1, predicted_semantic_similarity = calculate_metrics(predicted_answers, reference_answers)
base_model_bert_f1, base_model_semantic_similarity = calculate_metrics(base_model_answers, reference_answers)

predicted_llm_scores = [evaluate_with_llm(instr, ref, pred) for instr, ref, pred in zip(instructions, reference_answers, predicted_answers)]
base_model_llm_scores = [evaluate_with_llm(instr, ref, base) for instr, ref, base in zip(instructions, reference_answers, base_model_answers)]

score_data = []
for i, instruction in enumerate(instructions):
    score_data.append({
        "instruction": instruction,
        "predicted_answer": predicted_answers[i],
        "base_model_answer": base_model_answers[i],
        "reference_answer": reference_answers[i],
        "predicted_bert_f1": predicted_bert_f1[i],
        "base_model_bert_f1": base_model_bert_f1[i],
        "predicted_semantic_similarity": predicted_semantic_similarity[i],
        "base_model_semantic_similarity": base_model_semantic_similarity[i],
        "predicted_llm_score": predicted_llm_scores[i],
        "base_model_llm_score": base_model_llm_scores[i],
    })

with open(output_scores_file, "w", encoding="utf-8") as file:
    json.dump(score_data, file, ensure_ascii=False, indent=4)

print(f"Scores saved to {output_scores_file}")

metrics = [
    ("BERT F1", predicted_bert_f1, base_model_bert_f1),
    ("Semantic Similarity", predicted_semantic_similarity, base_model_semantic_similarity),
    ("LLM Score", predicted_llm_scores, base_model_llm_scores),
]

for metric_name, predicted_values, base_values in metrics:
    plt.figure(figsize=(10, 6))
    sns.histplot(predicted_values, bins=20, kde=True, color="blue", label="Predicted", stat="count")
    sns.histplot(base_values, bins=20, kde=True, color="orange", label="Base Model", stat="count")
    plt.title(f"{metric_name} Distribution")
    plt.xlabel("Score")
    plt.ylabel("Frequency")
    plt.legend()
    plt.grid(axis="y", linestyle="--", alpha=0.7)
    plt.savefig(f"{output_plot_dir}{metric_name.replace(' ', '_').lower()}_distributionaaaa.png")
    plt.close()

print("All histograms saved successfully!")
