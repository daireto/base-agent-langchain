import threading
from typing import TypeVar

T = TypeVar('T')


class SingletonMeta(type):
    _instances = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):  # noqa: ANN204
        return cls.get_instance(*args, **kwargs)

    def get_instance(cls: type[T], *args, **kwargs) -> T:
        if cls not in cls._instances:  # type: ignore
            with cls._lock:  # type: ignore
                if cls not in cls._instances:  # type: ignore
                    cls._instances[cls] = super().__call__(*args, **kwargs)  # type: ignore
        return cls._instances[cls]  # type: ignore
