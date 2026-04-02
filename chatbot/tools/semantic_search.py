from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient


def vectorstore_search(collection_name:str, query:str, encoder, client):
    hits = client.query_points(
        collection_name=collection_name,
        query=encoder.encode(query).tolist(),
        limit=20
    ).points

    return hits

if __name__ == "__main__":
    collection_name = "Recurso_metadados"
    query = "infecção"
    hits = vectorstore_search(query=query, collection_name=collection_name)
    print(hits)