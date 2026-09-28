from starlette.applications import Starlette

from core.logger import (
    DEFAULT_BACKUP_COUNT,
    DEFAULT_MAX_BYTES,
    default_app_logger,
    default_json_formatter,
    get_app_logger,
    setup_log_rotation,
)


def setup_app_logger(
    app: Starlette,
    dirpath: str | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
) -> None:
    """Set up the application logger in the Starlette application state.

    Args:
        app: The Starlette application instance.
        dirpath: The path to the log directory. Defaults to None.
        max_bytes: The maximum size of the log file before it is rotated.
        backup_count: The number of backup files to keep.
    """
    app.state.logger = default_app_logger
    app.state.get_child_logger = get_app_logger

    if dirpath:
        setup_log_rotation(
            loggers=[default_app_logger],
            dirpath=dirpath,
            max_bytes=max_bytes,
            backup_count=backup_count,
            formatter=default_json_formatter,
        )
