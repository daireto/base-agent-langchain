from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import FastEmbedSparse, QdrantVectorStore, RetrievalMode
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance, SparseVectorParams, VectorParams

from core.config import settings
from core.definitions import QDRANT_DB_DIR, QDRANT_UEFA_DOCS_COLLECTION

_embeddings = OpenAIEmbeddings(model=settings.uefa_docs_embeddings_model)
_sparse_embeddings = FastEmbedSparse(model_name='Qdrant/bm25')

qdrant_client = QdrantClient(path=QDRANT_DB_DIR)

if not qdrant_client.collection_exists(QDRANT_UEFA_DOCS_COLLECTION):
    qdrant_client.create_collection(
        collection_name=QDRANT_UEFA_DOCS_COLLECTION,
        vectors_config={'dense': VectorParams(size=1536, distance=Distance.COSINE)},
        sparse_vectors_config={
            'sparse': SparseVectorParams(index=models.SparseIndexParams(on_disk=False))
        },
    )

qdrant_vector_store = QdrantVectorStore(
    client=qdrant_client,
    collection_name=QDRANT_UEFA_DOCS_COLLECTION,
    embedding=_embeddings,
    sparse_embedding=_sparse_embeddings,
    retrieval_mode=RetrievalMode.HYBRID,
    vector_name='dense',
    sparse_vector_name='sparse',
)


def close_qdrant_client() -> None:
    qdrant_client.close()
