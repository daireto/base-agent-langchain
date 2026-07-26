from functools import lru_cache


class ServerHealth:
    """Handles the health status of the server."""

    def __init__(self) -> None:
        self.reset()

    @property
    def is_healthy(self) -> bool:
        """Whether the server is currently healthy."""
        return self._is_healthy

    @is_healthy.setter
    def is_healthy(self, value: bool) -> None:
        """Set the health status of the server."""
        self._is_healthy = value

    def reset(self) -> None:
        """Reset the health status to healthy and clear any unhealthy reason."""
        self._is_healthy = True
        self._unhealthy_reason = ''

    def set_unhealthy(self, reason: str) -> None:
        """Set the server's health status to unhealthy with a reason."""
        self._is_healthy = False
        self._unhealthy_reason = reason

    def get_unhealthy_reason(self) -> str:
        """Return the reason for the server being unhealthy."""
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
    """Return a singleton instance of ServerHealth."""
    return ServerHealth()


server_health = ServerHealth()
