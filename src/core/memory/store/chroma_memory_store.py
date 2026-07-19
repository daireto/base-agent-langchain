import asyncio
from typing import TypedDict
from uuid import uuid4

import chromadb

from core.definitions import CHROMA_DB_DIR
from core.memory.store.base_memory_store import BaseMemoryStore


class Memory(TypedDict):
    id: str
    content: str
    category: str


class ChromaMemoryStore(BaseMemoryStore):
    """A memory store that uses ChromaDB to store and retrieve memories."""

    def __init__(self) -> None:
        """Initialize the MemoryStore."""
        self.__client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
        self.__collection = self.__client.get_or_create_collection('memories')

    async def search(self, user_id: str, query: str, k: int = 5) -> list[str]:
        results = await asyncio.to_thread(
            self.__collection.query,
            query_texts=[query],
            where={'user_id': user_id},
            n_results=k,
        )
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

        await asyncio.to_thread(
            self.__collection.add,
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

    async def get_user_memories(self, user_id: str, k: int = 100) -> list[str]:
        results = await asyncio.to_thread(
            self.__collection.get,
            where={'user_id': user_id},
            limit=k,
        )
        return self._zip_records(results)

    def _zip_query_results(self, results: chromadb.QueryResult) -> list[str]:
        documents = results['documents'][0] if results['documents'] else []
        metadatas = results['metadatas'][0] if results['metadatas'] else []
        return self._zip(documents, metadatas)

    def _zip_records(self, results: chromadb.GetResult) -> list[str]:
        documents = results['documents'] or []
        metadatas = results['metadatas'] or []
        return self._zip(documents, metadatas)

    def _zip(
        self, documents: list[str], metadatas: list[chromadb.Metadata]
    ) -> list[str]:
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
