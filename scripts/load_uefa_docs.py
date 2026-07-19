from pathlib import Path

from langchain_pymupdf4llm import PyMuPDF4LLMLoader

from agents.uefa_agent.store import qdrant_client, qdrant_vector_store
from core.definitions import QDRANT_UEFA_DOCS_COLLECTION


def load_uefa_docs() -> None:
    docs_count = qdrant_client.count(QDRANT_UEFA_DOCS_COLLECTION).count
    print(
        f'Cantidad de documentos en la colección {QDRANT_UEFA_DOCS_COLLECTION}: {docs_count}'
    )

    if not docs_count:
        documents_folder = Path(__file__).parent.parent / 'data' / 'uefa_docs'
        documents = []
        for file in documents_folder.glob('*.pdf'):
            loader = PyMuPDF4LLMLoader(file)
            d = loader.load()
            documents.extend(d)

        ids = qdrant_vector_store.add_documents(documents)
        print(f'Se cargaron {len(ids)} documentos.')


if __name__ == '__main__':
    load_uefa_docs()
