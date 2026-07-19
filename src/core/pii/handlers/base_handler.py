from abc import ABC, abstractmethod


class BasePIIHandler(ABC):
    """Base class for PII handlers."""

    @abstractmethod
    def anonymize(self, text: str, vault_key: str) -> str:
        """Anonymize PII in the given text.

        Args:
            text: The text to anonymize.
            vault_key: The key to store the anonymized data in the vault.

        Returns:
            The anonymized text.
        """

    @abstractmethod
    def deanonymize(self, text: str, vault_key: str) -> str:
        """Deanonymize PII in the given text.

        Args:
            text: The text to deanonymize.
            vault_key: The key to retrieve the anonymized data from the vault.

        Returns:
            The deanonymized text.
        """

    @abstractmethod
    def clear_vault(self, vault_key: str) -> None:
        """Clear the vault data for the given key.

        Args:
            vault_key: The key to clear the vault data for.
        """
