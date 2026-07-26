from abc import ABC, abstractmethod
from typing import TypedDict


class VaultData(TypedDict):
    """Data structure for storing sensitive information in the vault."""

    placeholders_map: dict[str, str]
    """Placeholders map for the data stored in the vault.

    The keys are the placeholders and the values are the actual data.
    """


class Vault(ABC):
    """Abstract base class for a vault that stores sensitive data."""

    @abstractmethod
    def store(self, key: str, data: VaultData) -> None:
        """Store data in the vault with the given key."""

    @abstractmethod
    def retrieve(self, key: str) -> VaultData | None:
        """Retrieve data from the vault with the given key.

        Returns None if the key does not exist.
        """

    @abstractmethod
    def clear(self, key: str) -> None:
        """Clear the data associated with the given key."""

    @abstractmethod
    def clear_all(self) -> None:
        """Clear all data in the vault."""


class MemoryVault(Vault):
    """In-memory implementation of the Vault interface.

    Attributes:
        _vault: A dictionary that stores the vault data in memory.
    """

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
