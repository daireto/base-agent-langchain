import uuid_utils.compat as uuid


def uuid7() -> uuid.UUID:
    return uuid.uuid7()


def str_uuid7() -> str:
    return str(uuid7())
