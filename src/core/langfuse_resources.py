import warnings

from langfuse import Langfuse, get_client
from langfuse.langchain import CallbackHandler

from core.config import settings


def get_langfuse_client() -> Langfuse | None:
    if not settings.langfuse_enabled:
        return None

    client = get_client()
    if not client.auth_check():
        warnings.warn(
            'Langfuse is enabled in settings, but the authentication check failed.'
            ' Please check your Langfuse API key and ensure it is valid.',
            stacklevel=2,
        )
        settings.langfuse_enabled = False
        return None

    return client


langfuse = get_langfuse_client()
langfuse_handler = CallbackHandler()
