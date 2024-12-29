from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams
from transformers import AutoTokenizer, AutoModel
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import torch
import numpy as np
import json
from tqdm import tqdm
import re
import pandas as pd

# Initialize Qdrant client
qdrant_client = QdrantClient("http://localhost:6333")  # Adjust as needed
print("Connected to qdrant")
abdulkadir_selvi_collection = "abdulkadir_selvi_collection"
nedim_sener_collection = "nedim_sener_collection"

# Load Turkish embedding model
print("Downloading embedding model..")
embedding_model = SentenceTransformer('emrecan/bert-base-turkish-cased-mean-nli-stsb-tr')
print("Download completed")

# Ingest documents into Qdrant
def ingest_documents(documents, collection_name, chunk_size=800, chunk_overlap=80, batch_size=20):
    # Create collection if not exists
    collections_response = qdrant_client.get_collections()
    collections = collections_response.collections  # This is a list of CollectionDescription objects
    collection_names = [collection.name for collection in collections]
    print(f"Existing collections: {collection_names}")

    if collection_name in collection_names:
        print(f"Collection '{collection_name}' exists. Deleting it...")
        qdrant_client.delete_collection(collection_name=collection_name)

    # Recreate collection
    print(f"Recreating collection '{collection_name}'...")
    qdrant_client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=768, distance=Distance.COSINE)
    )
    print(f"Collection '{collection_name}' created.")
    
    # Split the text into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )

    points = []
    total_documents = len(documents)
    inserted_docs = 0

    # Iterate over documents with progress tracking
    chunk_no = 0
    for doc_id, doc in enumerate(documents):
        if doc_id%20 == 0:
            print(f"Processing document {doc_id + 1} of {total_documents}...")

        # Split the document into chunks
        chunks = text_splitter.split_text(doc)
        
        # Process each chunk
        for chunk in chunks:
            embedding = embedding_model.encode(chunk)
            points.append(PointStruct(
                id=chunk_no,
                vector=embedding,
                payload={"document_id": doc_id, "chunk": chunk}
            ))
            chunk_no+=1

        # After every `batch_size` documents, upsert to Qdrant
        if (doc_id + 1) % batch_size == 0 or (doc_id + 1) == total_documents:
            print(f"Inserting documents {inserted_docs + 1} to {doc_id + 1} into Qdrant...")
            qdrant_client.upsert(collection_name=collection_name, points=points)
            inserted_docs = doc_id + 1  # Update the number of inserted documents
            points = []  # Reset points for the next batch

    print(f"Document ingestion complete! {inserted_docs} documents inserted. Total number of chunks: {chunk_no}")

abdulkadir_selvi_data = pd.read_csv("ab/data/abdulkadir-selvi.csv")
nedim_sener_data = pd.read_csv("ab/data/nedim-sener.csv")

abdulkadir_selvi_texts = abdulkadir_selvi_data.iloc[:300]["Content"] # add first 300 articles
nedim_sener_texts = nedim_sener_data.iloc[:300]["Content"]


ingest_documents(abdulkadir_selvi_texts, abdulkadir_selvi_collection)
ingest_documents(nedim_sener_texts, nedim_sener_collection)



