import logging
import sys
from functools import wraps
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, TextIO

import structlog
from asgi_correlation_id import correlation_id
from fastapi import FastAPI
from pythonjsonlogger.json import JsonFormatter


class StreamHandler(logging.StreamHandler):
    def __init__(
        self,
        stream: TextIO = sys.stdout,
        formatter: logging.Formatter | None = None,
    ) -> None:
        super().__init__(stream)
        if formatter:
            self.setFormatter(formatter)


_default_json_formatter = JsonFormatter(
    '%(timestamp)s %(logger)s %(level)s %(module)s %(lineno)d %(message)s'
)
_default_stream_handler = StreamHandler(formatter=_default_json_formatter)


def add_correlation_id(
    _logger: structlog.stdlib.BoundLogger,
    _method_name: str,
    event_dict: structlog.typing.EventDict,
) -> structlog.typing.EventDict:
    if request_id := correlation_id.get():
        event_dict['request_id'] = request_id
    return event_dict


_processors = [
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
    processors=_processors,
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)


def get_logger(
    name: str,
    level: int = logging.INFO,
    handlers: list[logging.Handler] | None = None,
) -> structlog.stdlib.BoundLogger:
    logger = structlog.get_logger(name)
    logger.setLevel(level)
    logger.handlers.clear()

    if handlers:
        for handler in handlers:
            logger.addHandler(handler)
    else:
        logger.addHandler(_default_stream_handler)

    return logger


_default_app_logger = get_logger(name='app', level=logging.INFO)


def setup_log_rotation(
    loggers: list[structlog.stdlib.BoundLogger | logging.Logger | str],
    filepath: str,
    max_bytes: int = 1024 * 1024 * 10,
    backup_count: int = 5,
    formatter: logging.Formatter | None = None,
) -> None:
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


def get_app_logger(suffix: str | None = None) -> structlog.stdlib.BoundLogger:
    if not suffix:
        return _default_app_logger

    return structlog.stdlib.BoundLogger(
        logger=_default_app_logger.getChild(suffix),
        processors=_processors,
        context=structlog.get_context(_default_app_logger),
    )


def setup_app_logger(
    app: FastAPI,
    filepath: str | None = None,
    max_bytes: int = 1024 * 1024 * 10,
    backup_count: int = 5,
) -> None:
    app.state.logger = _default_app_logger
    app.state.get_child_logger = get_app_logger

    if filepath:
        setup_log_rotation(
            loggers=[_default_app_logger],
            filepath=filepath,
            max_bytes=max_bytes,
            backup_count=backup_count,
            formatter=_default_json_formatter,
        )


def log_decorator(  # noqa: ANN201
    logger: structlog.stdlib.BoundLogger = _default_app_logger,
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
    logger: structlog.stdlib.BoundLogger = _default_app_logger,
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
