import transformers
import torch
from transformers import AutoTokenizer, AutoModel
from qdrant_client import QdrantClient

qdrant_client = QdrantClient("http://localhost:6333")  # Adjust as needed
collection_name = "trial_collection_baris_terkoglu_unique"

# Load the model and tokenizer
model_id = "ytu-ce-cosmos/Turkish-Llama-8b-Instruct-v0.1"
pipeline = transformers.pipeline(
    "text-generation",
    model=model_id,
    model_kwargs={"torch_dtype": torch.bfloat16},
    device_map="auto",
)

embedding_model_name = "dbmdz/bert-base-turkish-cased"
tokenizer = AutoTokenizer.from_pretrained(embedding_model_name)
embedding_model = AutoModel.from_pretrained(embedding_model_name)

# Embedding function
def embed_query(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
    with torch.no_grad():
        outputs = embedding_model(**inputs)
    return outputs.last_hidden_state.mean(dim=1).squeeze().numpy()

# Search function
def search_embeddings(query, top_k=2):
    query_embedding = embed_query(query)
    search_result = qdrant_client.search(
        collection_name=collection_name,
        query_vector=query_embedding,
        limit=top_k
    )
    content = "".join([result.payload["chunk"] for result in search_result])
    return content

# Main processing
def process_query(query):
    # Step 1: Retrieve relevant content
    rag_content = search_embeddings(query)

    # Step 2: Prepare messages with a more humanistic and specialized system prompt
    messages = [
        {
            "role": "system",
            "content": (
                "Aşağıda nasıl cevap vermen gerektiğine dair bir örnek diyalog bulunmaktadır:"
                "\n\n"
                "Kullanıcı: 'Türkiye'deki sınır geçişleri son bir yılda ne kadar arttı?'"
                "\nAsistan: 'Geçtiğimiz yıl Türkiye sınırından geçen kişi sayısında belirgin bir artış gözlendi. Özellikle yaz aylarında... "
                "(örnek verileri kullanarak, insancıl ve gazeteci üslubu)'"
                "\n\n"
                "Bu örneği rehber al. Şimdi sen aynı üslupla cevap vereceksin. "
                "Gazeteci üslubunda, insancıl, anlaşılır ve ilgili ek bilgileri içeren bir cevap ver. "
                "Soru ile ilgili ek bilgileri kullan, ancak nereden aldığını asla belirtme."
            ),
        },
        {"role": "user", "content": f"Soru: {query}\nEk bilgi: {rag_content}"}
    ]

    # Termination tokens
    terminators = [
        pipeline.tokenizer.eos_token_id,
        pipeline.tokenizer.convert_tokens_to_ids("<|eot_id|>"),
    ]

    # Step 3: Generate a more humanistic response
    outputs = pipeline(
        messages,
        max_new_tokens=512,  # Allows a more elaborate response
        eos_token_id=terminators,
        do_sample=True,
        temperature=0.7,     # Slightly more creative, natural style
        top_p=0.95           # More flexibility in token selection
    )
    
    # Extract and return generated text
    return outputs[0]["generated_text"]


# Example usage
if __name__ == "__main__":
    query = "Ağustos 2024 tarihi itibarıyla sınırdan geçen Türk ailelerin sayısı nedir?"
    response = process_query(query)
    print("===================")
    print("LLM Response: ", response)
