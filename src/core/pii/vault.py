from abc import ABC, abstractmethod
from typing import TypedDict


class VaultData(TypedDict):
    placeholders_map: dict[str, str]


class Vault(ABC):
    @abstractmethod
    def store(self, key: str, data: VaultData) -> None:
        raise NotImplementedError

    @abstractmethod
    def retrieve(self, key: str) -> VaultData | None:
        raise NotImplementedError

    @abstractmethod
    def clear(self, key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def clear_all(self) -> None:
        raise NotImplementedError


class MemoryVault(Vault):
    def __init__(self) -> None:
        self._vault: dict[str, VaultData] = {}

    def store(self, key: str, data: VaultData) -> None:
        self._vault[key] = data

    def retrieve(self, key: str) -> VaultData | None:
        return self._vault.get(key)

    def clear(self, key: str) -> None:
        self._vault.pop(key, None)

    def clear_all(self) -> None:
        self._vault.clear()
