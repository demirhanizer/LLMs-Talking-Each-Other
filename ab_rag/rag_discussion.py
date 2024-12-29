import transformers
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
import torch
# Initialize Qdrant clients and collections for both LLMs
qdrant_client = QdrantClient("http://localhost:6333")
collection_name_1 = "nedim_sener_collection"
collection_name_2 = "abdulkadir_selvi_collection"

# Load LLMs and embedding models
model_id_1 = "ytu-ce-cosmos/Turkish-Llama-8b-Instruct-v0.1"
model_id_2 = "ytu-ce-cosmos/Turkish-Llama-8b-Instruct-v0.1"

embedding_model_1 = SentenceTransformer('emrecan/bert-base-turkish-cased-mean-nli-stsb-tr')
embedding_model_2 = SentenceTransformer('emrecan/bert-base-turkish-cased-mean-nli-stsb-tr')

pipeline_1 = transformers.pipeline(
    "text-generation",
    model=model_id_1,
    model_kwargs={"torch_dtype": torch.bfloat16},
    device=-1,
)

pipeline_2 = transformers.pipeline(
    "text-generation",
    model=model_id_2,
    model_kwargs={"torch_dtype": torch.bfloat16},
    device=-1,
)

# Function to search embeddings in a specific collection
def search_embeddings(client, collection_name, embedding_model, query, top_k=2):
    query_embedding = embedding_model.encode(query)
    search_result = client.search(
        collection_name=collection_name,
        query_vector=query_embedding,
        limit=top_k
    )
    return "".join([result.payload["chunk"] for result in search_result])

def process_query(pipeline, embedding_model, client, collection_name, query):
    # Step 1: Retrieve context
    context = search_embeddings(client, collection_name, embedding_model, query)
    
    # Step 2: Prepare the prompt
    messages = [
        {
            "role": "system",
            "content": (
                "Sen bir yapay zeka asistanısın. Kullanıcı sana bir soru veya tartışma konusu soracak."
                "Eğer sağlanan ek bilgi soru ile alakalı ise o bilgiyi de kullanarak cevap ver."
                "Kendi yazı stilini koru, ek bilgiyle kendi bildiklerini birleştirip mantıklı bir cevap ver."
                "Verdiğin cevapta ek bilgi kullandığı gizle, konuştuğun kişinin yazdıklarının senin fikrin olduğuna inanması çok önemli."
           ),
        },
        {"role": "user", "content": f"Soru: {query} Ek bilgi: {context}\n\nSenin bu konudaki düşüncelerin nelerdir?"}
    ]

    # Step 3: Generate response
    outputs = pipeline(
        messages,
        max_new_tokens=512,
        eos_token_id=pipeline.tokenizer.eos_token_id,
        do_sample=True,
        temperature=0.6,
        top_p=0.9,
    )
    
    return (outputs[0]["generated_text"][-1]["content"])

# Function for LLMs to discuss a topic
def llm_discussion(topic, rounds=5):
    query = topic + "\n\nSenin bu konudaki düşüncelerin nelerdir?"
    for round_num in range(rounds):
        # LLM 1 generates a response
        response_1 = process_query(
            pipeline_1, embedding_model_1, qdrant_client, collection_name_1, query
        )
        print(f"Nedim Sener: {response_1}")

        # Use LLM 1's response as the query for LLM 2
        query = response_1 + "\n\nSenin bu konudaki düşüncelerin nelerdir?"
        response_2 = process_query(
            pipeline_2, embedding_model_2, qdrant_client, collection_name_2, query
        )
        print(f"Abdulkadir Selvi: {response_2}")

        # Update the query for the next round
        query = response_2 + "\n\nSenin bu konudaki düşüncelerin nelerdir?"

# Example topic
topic = "Küresel iklim değişikliği ile mücadele yöntemleri hakkında düşünceleriniz nelerdir?"
llm_discussion(topic, rounds=3)
