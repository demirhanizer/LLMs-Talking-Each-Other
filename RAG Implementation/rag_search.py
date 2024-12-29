# Search function
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams
from transformers import AutoTokenizer, AutoModel
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import torch
import numpy as np
import json

qdrant_client = QdrantClient("http://localhost:6333")  # Adjust as needed
collection_name = "abdulkadir_selvi_collection"
#collection_name = "nedim_sener_collection"

# Load Turkish embedding model
print("Downloading embedding model..")
embedding_model = SentenceTransformer('emrecan/bert-base-turkish-cased-mean-nli-stsb-tr')
print("Download completed")


def search(query, top_k=2):
    #query_embedding = embed_text(query)
    query_embedding = embedding_model.encode(query)  
    search_result = qdrant_client.search(
        collection_name=collection_name,
        query_vector=query_embedding,
        limit=top_k
    )
    return [
        {
            "score": result.score,
            "document_id": result.payload["document_id"],
            "chunk": result.payload["chunk"]
        }
        for result in search_result
    ]

# Example usage for search
query= "Türkiyede gerçekleşen 15 Temmuz darbe girişimleri demokrasiye büyük bir darbe vurma çalışması olarak değerlendirilmiştir, sizce bu konudaki fikiler ne kadar doğru?"
results = search(query)
print("Search Results:")
for result in results:
    print(f"Score: {result['score']}, Document ID: {result['document_id']}, Chunk: {result['chunk']}")
