from pathlib import Path

from langchain_pymupdf4llm import PyMuPDF4LLMLoader

from agents.uefa_agent.store import UEFAAgentStore
from core.config import settings


def load_uefa_docs() -> None:
    store = UEFAAgentStore()
    collection = settings.uefa_rag.collection_name
    docs_count = store.count_documents()
    print(f'Cantidad de documentos en la colección {collection}: {docs_count}')

    if not docs_count:
        documents_folder = Path(__file__).parent.parent / 'data' / 'uefa_docs'
        documents = []
        for file in documents_folder.glob('*.pdf'):
            loader = PyMuPDF4LLMLoader(file)
            d = loader.load()
            documents.extend(d)

        ids = store.vector_store.add_documents(documents)
        print(f'Se cargaron {len(ids)} documentos.')
    store.close()


if __name__ == '__main__':
    load_uefa_docs()
