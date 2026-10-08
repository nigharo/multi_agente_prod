from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from multi_agent.common.config import get_settings
from multi_agent.common.llm import get_embeddings


def get_client() -> QdrantClient:
    s = get_settings()
    return QdrantClient(url=s.qdrant_url, api_key=s.qdrant_api_key)


def ensure_collection(client: QdrantClient) -> None:
    s = get_settings()
    if not client.collection_exists(s.qdrant_collection):
        client.create_collection(
            s.qdrant_collection,
            vectors_config=VectorParams(size=s.embedding_dimensions, distance=Distance.COSINE),
        )


def get_vectorstore() -> QdrantVectorStore:
    client = get_client()
    ensure_collection(client)
    return QdrantVectorStore(
        client=client,
        collection_name=get_settings().qdrant_collection,
        embedding=get_embeddings(),
    )
