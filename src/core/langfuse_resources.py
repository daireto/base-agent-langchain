import logging

from langfuse import Langfuse, get_client
from langfuse.langchain import CallbackHandler

from core.config import settings
from core.logger import get_logger

get_logger('langfuse', level=logging.ERROR)
_logger = get_logger('app.langfuse', level=logging.WARNING)


def get_langfuse_client() -> Langfuse | None:
    if not settings.langfuse.enabled:
        _logger.info('Langfuse is disabled in settings. Client initialization skipped.')
        return None

    try:
        client = get_client()
        if not client.auth_check():
            _logger.warning(
                'Langfuse is enabled in settings, but the authentication check failed.'
                ' Please check your Langfuse API key and ensure it is valid.'
            )
            settings.langfuse.enabled = False
            return None
    except Exception:
        _logger.exception('Failed to initialize Langfuse client')
        settings.langfuse.enabled = False
        return None

    _logger.info('Langfuse client initialized successfully.')
    return client


langfuse = get_langfuse_client()


def get_langfuse_callback_handler() -> CallbackHandler | None:
    if langfuse:
        return CallbackHandler()

    _logger.warning(
        'Langfuse client is not initialized. CallbackHandler will not be available.'
    )
    return None


langfuse_handler = get_langfuse_callback_handler()
