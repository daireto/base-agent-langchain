from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import FastEmbedSparse, QdrantVectorStore, RetrievalMode
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance, SparseVectorParams, VectorParams

from core.config import settings


class UEFAAgentStore:
    """Store for managing UEFA agent data and interactions with Qdrant.

    Attributes:
        _embeddings: An instance of OpenAIEmbeddings for dense vector embeddings.
        _sparse_embeddings: An instance of FastEmbedSparse for sparse vector embeddings.
        _qdrant_client: An instance of QdrantClient for interacting
            with the Qdrant database.
        _collection: The name of the Qdrant collection for storing UEFA documents.
        vector_store: An instance of QdrantVectorStore for managing vector data
            and retrieval operations.
    """

    def __init__(self) -> None:
        """Initialize the UEFA agent store."""
        self._embeddings = OpenAIEmbeddings(model=settings.uefa_rag.embeddings_model)
        self._sparse_embeddings = FastEmbedSparse(model_name='Qdrant/bm25')

        self._qdrant_client = self._get_client()

        self._collection = settings.uefa_rag.collection_name
        self._init_collection()

        self.vector_store = self._get_vector_store()

    def count_documents(self) -> int:
        """Count the number of documents in the Qdrant collection."""
        return self._qdrant_client.count(self._collection).count

    def close(self) -> None:
        """Close the Qdrant client connection."""
        self._qdrant_client.close()

    def _get_client(self) -> QdrantClient:
        """Get the Qdrant client based on the configuration settings."""
        if settings.qdrant.mode == 'server':
            return QdrantClient(
                url=settings.qdrant.url,
                timeout=settings.qdrant.timeout,
                api_key=settings.qdrant.api_key.get_secret_value(),
            )
        return QdrantClient(path=settings.qdrant.local_db_path)

    def _init_collection(self) -> None:
        """Initialize the Qdrant collection for UEFA documents if it doesn't exist."""
        if not self._qdrant_client.collection_exists(self._collection):
            self._qdrant_client.create_collection(
                collection_name=self._collection,
                vectors_config={
                    'dense': VectorParams(size=1536, distance=Distance.COSINE)
                },
                sparse_vectors_config={
                    'sparse': SparseVectorParams(
                        index=models.SparseIndexParams(on_disk=False)
                    )
                },
            )

    def _get_vector_store(self) -> QdrantVectorStore:
        """Get the Qdrant vector store for UEFA documents."""
        return QdrantVectorStore(
            client=self._qdrant_client,
            collection_name=self._collection,
            embedding=self._embeddings,
            sparse_embedding=self._sparse_embeddings,
            retrieval_mode=RetrievalMode.HYBRID,
            vector_name='dense',
            sparse_vector_name='sparse',
        )


uefa_store = UEFAAgentStore()
