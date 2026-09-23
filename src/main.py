from agents.uefa_agent.store import uefa_store
from core.config import settings
from core.logger import get_logger
from presentation.api.app import create_default_app

_logger = get_logger('main')

if settings.presentation_mode == 'api':
    app = create_default_app()

if __name__ == '__main__':
    if settings.presentation_mode == 'ui':
        import sys

        try:
            from streamlit.web import cli as st_cli
        except ImportError:
            _logger.exception('Streamlit no está instalado.')
            sys.exit(1)

        try:
            sys.argv = ['streamlit', 'run', 'src/presentation/ui/app.py']
            sys.exit(st_cli.main())
        finally:
            uefa_store.close()

    elif settings.presentation_mode == 'api':
        import uvicorn

        reload_ = settings.rest_server.is_dev
        if settings.qdrant.mode == 'local':
            # Disable auto-reload when using a local Qdrant database
            # to avoid issues related to qdrant folder being accessed
            # by multiple instances in different threads.
            reload_ = False

        uvicorn.run(
            'main:app',
            host='0.0.0.0',
            port=settings.rest_server.port,
            log_config=None,
            reload=reload_,
            forwarded_allow_ips='*' if settings.rest_server.behind_proxy else None,
        )
