import openai
import json
import os
import time
from dotenv import load_dotenv
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.tokenize import word_tokenize
import nltk
from difflib import SequenceMatcher

nltk.download('punkt')

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

input_path = '/cta/users/elalem2/evaluation_results_bert.json'

def load_data(path):
    """JSON dosyasını yükler."""
    try:
        with open(path, 'r') as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        print(f"Hata: Dosya {path} bulunamadı.")
        return None
    except json.JSONDecodeError:
        print("Hata: JSON dosyası okunurken bir hata oluştu.")
        return None

def evaluate_with_llm(question, reference_answer, predicted_answer):
    """LLM ile değerlendirme yapar (chat modeli kullanarak)."""
    messages = [
        {"role": "system", "content": "Bir değerlendirme yargıcı olarak cevapları analiz et."},
        {"role": "user", "content": f"""
        Aşağıdaki iki cevabı karşılaştır ve belirtilen kriterlere göre değerlendir:

        Soru: {question}
        Referans Yanıt: {reference_answer}
        Modelin Tahmini Yanıtı: {predicted_answer}

        Değerlendirme Kriterleri:
        - Doğruluk (1-5 arasında puanlayın)
        - Bağlama Uygunluk (1-5 arasında puanlayın)
        - Dil ve Stil Uyumu (1-5 arasında puanlayın)
        Lütfen her kriter için puan verin ve bir açıklama ekleyin.
        """}
    ]

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini", 
            messages=messages,
            max_tokens=200,
            temperature=0.7
        )
        return response['choices'][0]['message']['content']
    except openai.error.OpenAIError as e:
        print(f"OpenAI API Error: {e}")
        return "X."

def calculate_cosine_similarity(reference_answer, predicted_answer):
    vectorizer = CountVectorizer().fit_transform([reference_answer, predicted_answer])
    vectors = vectorizer.toarray()
    cosine_sim = cosine_similarity(vectors)
    return cosine_sim[0, 1]

def calculate_sequence_similarity(reference_answer, predicted_answer):
    return SequenceMatcher(None, reference_answer, predicted_answer).ratio()

def calculate_word_overlap(reference_answer, predicted_answer):
    ref_tokens = set(word_tokenize(reference_answer.lower()))
    pred_tokens = set(word_tokenize(predicted_answer.lower()))
    overlap = ref_tokens.intersection(pred_tokens)
    return len(overlap) / len(ref_tokens) if ref_tokens else 0

data = load_data(input_path)

if data:
    for idx, item in enumerate(data.get('detailed_results', [])):
        question = item['question']
        reference_answer = item['reference']
        predicted_answer = item['prediction']
        
        
        print(f"({idx + 1}/{len(data['detailed_results'])}) Soru: {question}")
        llm_evaluation = evaluate_with_llm(question, reference_answer, predicted_answer)
        print(f"LLM Değerlendirmesi: {llm_evaluation}\n")
        
        cosine_score = calculate_cosine_similarity(reference_answer, predicted_answer)
        print(f"Cosine Benzerlik Skoru: {cosine_score:.2f}")
        
        sequence_score = calculate_sequence_similarity(reference_answer, predicted_answer)
        print(f"Dizisel Benzerlik Skoru: {sequence_score:.2f}")
        
        word_overlap_score = calculate_word_overlap(reference_answer, predicted_answer)
        print(f"Kelime Benzerlik Oranı: {word_overlap_score:.2f}\n")
        
        time.sleep(1)  
