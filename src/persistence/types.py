from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.dialects.postgresql import UUID as POSTGRES_UUID
from sqlalchemy.types import CHAR, TypeDecorator
from uuid_utils.compat import UUID


class GUID(TypeDecorator[UUID]):
    """Platform-independent GUID type.

    PostgreSQL -> UUID
    SQL Server -> UNIQUEIDENTIFIER
    Others     -> CHAR(36)
    """

    impl = CHAR
    cache_ok = True

    _default_type = CHAR(36)

    def load_dialect_impl(self, dialect):  # noqa: ANN001, ANN201
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(POSTGRES_UUID())

        if dialect.name == 'mssql':
            return dialect.type_descriptor(UNIQUEIDENTIFIER())

        return dialect.type_descriptor(self._default_type)

    def process_bind_param(self, value, dialect):  # noqa: ANN001, ANN201
        if value is None or dialect.name in ('postgresql', 'mssql'):
            return value

        if not isinstance(value, UUID):
            value = UUID(value)

        return str(value)

    def process_result_value(self, value, dialect):  # noqa: ANN001, ANN201, ARG002
        if value is None:
            return None

        if not isinstance(value, UUID):
            value = UUID(value)

        return value
