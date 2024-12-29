from qdrant_client import QdrantClient

# Connect to your Qdrant instance
client = QdrantClient(host="localhost", port=6333)

# Specify the collection name
collections_response = client.get_collections()
collections = collections_response.collections
collection_name = "trial_collection_baris_terkoglu_unique"
collection_names = [collection.name for collection in collections]
print(f"Existing collections: {collection_names}")
# Get collection info
collection_info = client.get_collection(collection_name)

# Print collection size
print(f"Collection Size: {collection_info}")
