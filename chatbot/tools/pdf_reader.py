from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient, models
from pathlib import Path
import uuid
import gc
import os
from chatbot.utils import debug
from config.paths import GOV_DATA

def embed_texts(texts, encoder, batch_size=5):
    vectors = []
    debug()(f"Tamanho do texto: {len(texts)}")
    for i in range(0, len(texts), batch_size):
        debug()(i)
        batch = texts[i:i + batch_size]
        emb = encoder.encode(batch, convert_to_numpy=True)
        vectors.extend(emb)
        del batch, emb
        gc.collect()
    return vectors

def external_doc(config, source):
    encoder = config['configurable']['encoder']
    client = config['configurable']['client']
    link = source['link']

    collection_name = Path(os.path.basename(link)).stem
    file_name = collection_name = Path(os.path.basename(link)).stem
    file_path = GOV_DATA/file_name/Path(os.path.basename(link))

    loader = PyPDFLoader(file_path)
    docs = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    chunks = text_splitter.split_documents(docs)
    texts = [chunk.page_content for chunk in chunks]

    vectors = embed_texts(texts, encoder, batch_size=5)

    if not client.collection_exists(collection_name=collection_name):
        client.create_collection(
            collection_name=collection_name, # nome da coleção
            vectors_config=models.VectorParams(
            size=encoder.get_sentence_embedding_dimension(),  # Vector size is defined by used model
            distance=models.Distance.COSINE, # Metrica de similaridade
        ),
)

    points = []
    for i, chunk in enumerate(chunks):
        points.append(
            models.PointStruct(
                id=str(uuid.uuid4()),
                vector=vectors[i].tolist(),
                payload={
                    "page_content": chunk.page_content,
                    "metadata": chunk.metadata,
                    "chunk_index": i
                }
            )
        )

    client.upsert(
        collection_name=collection_name,
        points=points
    )

def text_query(query:str, config:dict, source:dict)->list:

    encoder = config['configurable']['encoder']
    client = config['configurable']['client']
    link = source['link']
    
    collection_name = Path(os.path.basename(link)).stem

    external_doc(config=config, source=source)

    hits = client.query_points(
        collection_name=collection_name,
        query=encoder.encode(query).tolist(),
        limit=3
    ).points

    chunks = []

    for hit in hits:
        debug()(hit.payload['page_content'])
        chunks.append(hit.payload['page_content'])

    return chunks