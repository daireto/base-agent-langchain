from agents.uefa_agent.store import close_qdrant_client
from core.config import settings
from presentation.rest.app import create_default_app

if settings.presentation_mode == 'rest':
    app = create_default_app()

if __name__ == '__main__':
    if settings.presentation_mode == 'ui':
        import sys

        try:
            from streamlit.web import cli as st_cli
        except ImportError:
            print('Streamlit no está instalado.')
            sys.exit(1)

        try:
            sys.argv = ['streamlit', 'run', 'src/presentation/ui/app.py']
            sys.exit(st_cli.main())
        finally:
            close_qdrant_client()

    elif settings.presentation_mode == 'rest':
        import uvicorn

        uvicorn.run(
            'main:app',
            host='0.0.0.0',
            port=settings.rest_server.port,
            log_config=None,
            # reload=settings.rest_server.is_dev,
            forwarded_allow_ips='*' if settings.rest_server.behind_proxy else None,
        )
