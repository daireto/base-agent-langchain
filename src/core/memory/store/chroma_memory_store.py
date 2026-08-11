import asyncio
from typing import TypedDict
from uuid import uuid4

from chromadb import (
    AsyncClientAPI,
    AsyncHttpClient,
    ClientAPI,
    Collection,
    GetResult,
    Metadata,
    PersistentClient,
    QueryResult,
)
from chromadb.api.models.AsyncCollection import AsyncCollection

from core.config import settings
from core.memory.store.base_memory_store import BaseMemoryStore


class Memory(TypedDict):
    """Data structure representing a memory."""

    id: str
    """Unique identifier for the memory."""

    content: str
    """Content of the memory (e.g., 'User is named John Doe', 'Likes pizza')."""

    category: str
    """Category of the memory (e.g., 'name', 'preference')."""


class _ChromaCollectionMixin:
    """Mixin class providing methods to interact with a ChromaDB collection."""

    async def query(self, user_id: str, query: str, k: int) -> QueryResult:
        """Proxy for chromadb.Collection.query to support both sync and async clients."""
        collection = await self._get_collection()
        if isinstance(collection, AsyncCollection):
            return await collection.query(
                query_texts=[query],
                where={'user_id': user_id},
                n_results=k,
            )
        return await asyncio.to_thread(
            collection.query,
            query_texts=[query],
            where={'user_id': user_id},
            n_results=k,
        )

    async def add(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[Metadata],
    ) -> None:
        """Proxy for chromadb.Collection.add to support both sync and async clients."""
        collection = await self._get_collection()
        if isinstance(collection, AsyncCollection):
            return await collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
        return await asyncio.to_thread(
            collection.add,
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

    async def get(self, user_id: str, k: int) -> GetResult:
        """Proxy for chromadb.Collection.get to support both sync and async clients."""
        collection = await self._get_collection()
        if isinstance(collection, AsyncCollection):
            return await collection.get(
                where={'user_id': user_id},
                limit=k,
            )
        return await asyncio.to_thread(
            collection.get,
            where={'user_id': user_id},
            limit=k,
        )

    async def _get_collection(self) -> Collection | AsyncCollection:
        client = await self._get_client()
        if isinstance(client, AsyncClientAPI):
            return await client.get_or_create_collection(
                settings.memories.collection_name
            )
        return client.get_or_create_collection(settings.memories.collection_name)

    async def _get_client(self) -> ClientAPI | AsyncClientAPI:
        if settings.chroma.mode == 'server':
            return await AsyncHttpClient(
                host=settings.chroma.host,
                port=settings.chroma.port,
                ssl=settings.chroma.ssl,
                headers={
                    'Authorization': f'Bearer {settings.chroma.api_token.get_secret_value()}'
                },
            )
        return PersistentClient(path=settings.chroma.local_db_path)


class ChromaMemoryStore(BaseMemoryStore, _ChromaCollectionMixin):
    """A memory store that uses ChromaDB to store and retrieve memories."""

    async def search(self, user_id: str, query: str, k: int = 5) -> list[str]:
        results = await self.query(user_id=user_id, query=query, k=k)
        return self._zip_query_results(results)

    async def save(self, user_id: str, memories: list[str]) -> None:
        parsed_memories = self._parse_extracted_memories(memories)

        ids = []
        documents = []
        metadatas = []

        for memory in parsed_memories:
            ids.append(memory['id'])
            documents.append(memory['content'])
            metadatas.append(
                {
                    'category': memory['category'],
                    'user_id': user_id,
                }
            )

        await self.add(ids=ids, documents=documents, metadatas=metadatas)

    async def get_user_memories(self, user_id: str, k: int = 100) -> list[str]:
        results = await self.get(user_id=user_id, k=k)
        return self._zip_records(results)

    def _zip_query_results(self, results: QueryResult) -> list[str]:
        documents = results['documents'][0] if results['documents'] else []
        metadatas = results['metadatas'][0] if results['metadatas'] else []
        return self._zip(documents, metadatas)

    def _zip_records(self, results: GetResult) -> list[str]:
        documents = results['documents'] or []
        metadatas = results['metadatas'] or []
        return self._zip(documents, metadatas)

    def _zip(self, documents: list[str], metadatas: list[Metadata]) -> list[str]:
        zipped = []
        for doc, meta in zip(documents, metadatas, strict=False):
            zipped.append(f'{meta["category"]}: {doc}')
        return zipped

    def _parse_extracted_memories(self, memories: list[str]) -> list[Memory]:
        parsed = []
        for memory in memories:
            if ':' not in memory:
                continue

            category, content = memory.split(':', 1)
            parsed.append(
                Memory(
                    id=uuid4().hex,
                    content=content.strip(),
                    category=category.strip(),
                )
            )
        return parsed
