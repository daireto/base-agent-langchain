from pathlib import Path

from langchain_pymupdf4llm import PyMuPDF4LLMLoader

from agents.uefa_agent.store import UEFAAgentStore
from core.config import settings
from core.logger import get_logger

_logger = get_logger('load_uefa_docs')


def load_uefa_docs() -> None:
    store = UEFAAgentStore()
    collection = settings.uefa_rag.collection_name
    docs_count = store.count_documents()
    _logger.info(
        'Cantidad de documentos en la colección %s: %s', collection, docs_count
    )

    if not docs_count:
        documents_folder = Path(__file__).parent.parent / 'data' / 'uefa_docs'
        documents = []
        for file in documents_folder.glob('*.pdf'):
            loader = PyMuPDF4LLMLoader(file)
            d = loader.load()
            documents.extend(d)

        _logger.info('Cargando documentos...')
        ids = store.vector_store.add_documents(documents)
        _logger.info('Se cargaron %s documentos.', len(ids))
    store.close()


if __name__ == '__main__':
    load_uefa_docs()
