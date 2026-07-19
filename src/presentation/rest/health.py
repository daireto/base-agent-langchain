from functools import lru_cache


class ServerHealth:
    def __init__(self) -> None:
        self.reset()

    @property
    def is_healthy(self) -> bool:
        return self._is_healthy

    @is_healthy.setter
    def is_healthy(self, value: bool) -> None:
        self._is_healthy = value

    def reset(self) -> None:
        self._is_healthy = True
        self._unhealthy_reason = ''

    def set_unhealthy(self, reason: str) -> None:
        self._is_healthy = False
        self._unhealthy_reason = reason

    def get_unhealthy_reason(self) -> str:
        return self._unhealthy_reason

    def __str__(self) -> str:
        return (
            'healthy'
            if self.is_healthy
            else f'unhealthy, reason={self.get_unhealthy_reason()}'
        )

    def __bool__(self) -> bool:
        return self.is_healthy


@lru_cache
def get_server_health() -> ServerHealth:
    return ServerHealth()


server_health = ServerHealth()
