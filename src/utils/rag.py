"""Utility functions for RAG (Retrieval-Augmented Generation) operations."""

from pathlib import Path

from langchain_core.documents import Document


def format_docs(docs: list[Document]) -> str:
    """Formats a list of Document objects into a readable string representation.

    Args:
        docs: A list of Document objects to be formatted.

    Returns:
        A string representation of the documents, with each document's content
        preceded by a header indicating its index and any available metadata
        (source and page number).
    """
    formatted = []

    for i, doc in enumerate(docs, 1):
        header = f'[Fragmento {i}]'

        if doc.metadata:
            if source := doc.metadata.get('source', ''):
                source = Path(source).name
                header += f' - Fuente: {source}'
            if page := doc.metadata.get('page', ''):
                header += f' - Página: {page}'

        content = doc.page_content.strip()
        formatted.append(f'{header}\n{content}')

    return '\n\n'.join(formatted)
