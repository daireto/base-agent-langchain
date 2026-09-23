import logging
import sys
from functools import wraps
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, TextIO

import structlog
from asgi_correlation_id import correlation_id
from pythonjsonlogger.json import JsonFormatter
from starlette.applications import Starlette


class StreamHandler(logging.StreamHandler):
    """Custom stream handler that allows for a custom formatter.

    Inherits from logging.StreamHandler and allows for a custom formatter
    to be set during initialization. If no formatter is provided,
    the default formatter will be used.
    """

    def __init__(
        self,
        stream: TextIO = sys.stdout,
        formatter: logging.Formatter | None = None,
    ) -> None:
        super().__init__(stream)
        if formatter:
            self.setFormatter(formatter)


default_json_formatter = JsonFormatter(
    '%(timestamp)s %(logger)s %(level)s %(module)s %(lineno)d %(message)s'
)
default_stream_handler = StreamHandler(formatter=default_json_formatter)


def add_correlation_id(
    _logger: structlog.stdlib.BoundLogger,
    _method_name: str,
    event_dict: structlog.typing.EventDict,
) -> structlog.typing.EventDict:
    """Processor to add the correlation ID to the log event dictionary."""
    if request_id := correlation_id.get():
        event_dict['request_id'] = request_id
    return event_dict


processors = [
    structlog.stdlib.filter_by_level,
    structlog.stdlib.add_logger_name,
    structlog.stdlib.add_log_level,
    add_correlation_id,
    structlog.processors.TimeStamper(fmt='iso', utc=False),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
    structlog.processors.UnicodeDecoder(),
    structlog.stdlib.render_to_log_kwargs,
]

structlog.configure(
    processors=processors,
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)


def get_logger(
    name: str,
    level: int = logging.INFO,
    handlers: list[logging.Handler] | None = None,
) -> structlog.stdlib.BoundLogger:
    """Get a logger instance with the specified name, level, and handlers.

    Args:
        name: The name of the logger.
        level: The level of the logger. Defaults to logging.INFO.
        handlers: The handlers to add to the logger. Defaults to None.

    Returns:
        The logger instance.
    """
    logger = structlog.get_logger(name)
    logger.setLevel(level)
    logger.handlers.clear()

    if handlers:
        for handler in handlers:
            logger.addHandler(handler)
    else:
        logger.addHandler(default_stream_handler)

    return logger


default_app_logger = get_logger(name='app', level=logging.INFO)


def get_app_logger(suffix: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a child logger for the application with an optional suffix.

    Args:
        suffix: The suffix to append to the logger name. Defaults to None.

    Returns:
        The child logger instance.
    """
    if not suffix:
        return default_app_logger

    return structlog.stdlib.BoundLogger(
        logger=default_app_logger.getChild(suffix),
        processors=processors,
        context=structlog.get_context(default_app_logger),
    )


DEFAULT_MAX_BYTES = 1024 * 1024 * 10  # 10 MB
DEFAULT_BACKUP_COUNT = 5  # Number of backup files to keep


def setup_log_rotation(
    loggers: list[structlog.stdlib.BoundLogger | logging.Logger | str],
    filepath: str,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
    formatter: logging.Formatter | None = None,
) -> None:
    """Set up log rotation for the specified loggers.

    Args:
        loggers: A list of loggers to set up log rotation for. Can be logger instances or logger names.
        filepath: The path to the log file.
        max_bytes: The maximum size of the log file before it is rotated.
        backup_count: The number of backup files to keep.
        formatter: The formatter to use for the log file. Defaults to None.
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        filepath,
        maxBytes=max_bytes,
        backupCount=backup_count,
    )

    if formatter:
        file_handler.setFormatter(formatter)

    for logger in loggers:
        if isinstance(logger, str):
            get_logger(logger).addHandler(file_handler)
        else:
            logger.addHandler(file_handler)


def setup_app_logger(
    app: Starlette,
    filepath: str | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
) -> None:
    """Set up the application logger in the Starlette application state.

    Args:
        app: The Starlette application instance.
        filepath: The path to the log file. Defaults to None.
        max_bytes: The maximum size of the log file before it is rotated.
        backup_count: The number of backup files to keep.
    """
    app.state.logger = default_app_logger
    app.state.get_child_logger = get_app_logger

    if filepath:
        setup_log_rotation(
            loggers=[default_app_logger],
            filepath=filepath,
            max_bytes=max_bytes,
            backup_count=backup_count,
            formatter=default_json_formatter,
        )


def log_decorator(  # noqa: ANN201
    logger: structlog.stdlib.BoundLogger = default_app_logger,
    on_start_msg: str = '',
    on_end_msg: str = '',
    on_error_msg: str = '',
):
    def decorator(func):  # noqa: ANN001, ANN202
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if on_start_msg:
                logger.info(on_start_msg)

            try:
                result = func(*args, **kwargs)
                if on_end_msg:
                    logger.info(on_end_msg)
            except Exception as e:
                if on_error_msg:
                    logger.exception(on_error_msg, exc_info=e)
                raise

            return result

        return wrapper

    return decorator


def async_log_decorator(  # noqa: ANN201
    logger: structlog.stdlib.BoundLogger = default_app_logger,
    on_start_msg: str = '',
    on_end_msg: str = '',
    on_error_msg: str = '',
):
    def decorator(func):  # noqa: ANN001, ANN202
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            if on_start_msg:
                logger.info(on_start_msg)

            try:
                result = await func(*args, **kwargs)
                if on_end_msg:
                    logger.info(on_end_msg)
            except Exception as e:
                if on_error_msg:
                    logger.exception(on_error_msg, exc_info=e)
                raise

            return result

        return wrapper

    return decorator
