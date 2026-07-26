from langchain.tools import tool
from langchain_core.documents import Document

from agents.uefa_agent.store import uefa_store
from utils.rag import format_docs


@tool(response_format='content_and_artifact')
async def uefa_docs_retriever(query: str) -> tuple[str, list[Document]]:
    """Retrieve relevant documents from the UEFA knowledge base.

    Args:
        query: The query to search for
    """
    documents = await uefa_store.vector_store.asimilarity_search(query, k=3)
    return format_docs(documents), documents
