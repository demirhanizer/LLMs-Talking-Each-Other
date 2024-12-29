import transformers
import torch
from transformers import AutoTokenizer, AutoModel
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer


print(torch.cuda.is_available())
qdrant_client = QdrantClient("http://localhost:6333")  # Adjust as needed
collection_name = "abdulkadir_selvi_collection"

# Load the model and tokenizer
model_id = "ytu-ce-cosmos/Turkish-Llama-8b-Instruct-v0.1"
embedding_model = SentenceTransformer('emrecan/bert-base-turkish-cased-mean-nli-stsb-tr')

pipeline = transformers.pipeline(
    "text-generation",
    model=model_id,
    model_kwargs={"torch_dtype": torch.bfloat16},
    device=-1,
)


#  Search function
def search_embeddings(embedded_query, top_k=2):
    
    query_embedding = embedding_model.encode(query)
    search_result = qdrant_client.search(
        collection_name=collection_name,
        query_vector=query_embedding,
        limit=top_k
    )
    content = "".join([result.payload["chunk"] for result in search_result])
    #print("Content : ", content)
    return content

# Main processing
def process_query(query):
    # Step 1: Embed the query
    embedded_query = embedding_model.encode(query)

    # Step 2: Search for relevant content
    rag_content = search_embeddings(embedded_query)

    # Step 3: Prepare the prompt for the Turkish LLM
    messages = [
        {
            "role": "system",
            "content": (
                "Sen bir yapay zeka asistanısın. Kullanıcı sana bir soru soracak."
                "Eğer sağlanan ek bilgi soru ile alakalı ise o bilgiyi de kullanarak cevap ver."
                "Kendi yazı stilini koru, ek bilgiyle kendi bildiklerini birleştirip mantıklı bir cevap ver."
                "Verdiğin cevapta ek bilgi kullandığı gizle, konuştuğun kişinin yazdıklarının senin fikrin olduğuna inanması çok önemli."
           ),
        },
        {"role": "user", "content": f"Soru: {query} Ek bilgi: {rag_content}"}
    ]

    # Termination tokens
    terminators = [
        pipeline.tokenizer.eos_token_id,
        pipeline.tokenizer.convert_tokens_to_ids("<|eot_id|>"),
    ]

    # Step 4: Generate output
    outputs = pipeline(
        messages,
        max_new_tokens=512,
        eos_token_id=terminators,
        do_sample=True,
        temperature=0.6,
        top_p=0.9,
    )
    
    # Extract and return generated text
    return (outputs[0]["generated_text"][-1])

# Example usage
#query= "Türkiyede gerçekleşen 15 Temmuz darbe girişimleri demokrasiye büyük bir darbe vurma çalışması olarak değerlendirilmiştir, sizce bu konudaki fikiler ne kadar doğru?"
query = "Amerikan başkanı Donald Trumpın yakın zamanda yaptıkları ve gerçekleştirdikleri görüşmeler hakkında yorumlarınız nelerdir?"
response = process_query(query)['content']
print("===================")
print("LLM Response: ", response)
