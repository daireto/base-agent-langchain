"""Utility functions for generating UUIDs, including support for UUID version 7."""

import uuid_utils.compat as uuid


def uuid7() -> uuid.UUID:
    """Generate a UUID version 7 using ``uuid_utils.compat.uuid7``."""
    return uuid.uuid7()


def str_uuid7() -> str:
    """Generate a string representation of a UUID version 7.

    Uses ``uuid_utils.compat.uuid7`` to generate the UUID.
    """
    return str(uuid7())
