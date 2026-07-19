from collections.abc import Sequence

from fastapi import Response
from pydantic import BaseModel
from pydantic_core import ErrorDetails

from core.errors import Error


class ValidationErrorDetail(BaseModel):
    detail: str
    pointer: str


class RFC9457Error(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str | None
    code: str
    errors: list[ValidationErrorDetail] | None


def pydantic_loc_to_json_pointer(loc: tuple[int | str, ...]) -> str:
    return f'#/{"/".join(str(step) for step in loc)}'


def map_error_details(
    errors: Sequence[ValidationErrorDetail | ErrorDetails],
) -> list[ValidationErrorDetail]:
    members = []

    for err in errors:
        if isinstance(err, ValidationErrorDetail):
            members.append(err)
        else:
            pointer = pydantic_loc_to_json_pointer(err['loc'])
            members.append(ValidationErrorDetail(detail=err['msg'], pointer=pointer))

    return members


def build_rfc_9457_response(
    title: str,
    status: int,
    detail: str,
    code: str,
    instance: str | None = None,
    type_: str = 'about:blank',
    errors: Sequence[ValidationErrorDetail | ErrorDetails] | None = None,
    headers: dict[str, str] | None = None,
) -> Response:
    content = RFC9457Error(
        type=type_,
        title=title,
        status=status,
        detail=detail,
        instance=instance,
        code=code,
        errors=map_error_details(errors) if errors else None,
    ).model_dump_json()
    return Response(
        content=content,
        status_code=status,
        headers=headers,
        media_type='application/json',
    )


def error_to_rfc_9457_response(
    error: Error,
    instance: str | None = None,
    headers: dict[str, str] | None = None,
) -> Response:
    return build_rfc_9457_response(
        title=error.title,
        status=error.status,
        detail=error.detail,
        code=error.code,
        type_=error.type,
        instance=instance,
        headers=headers,
    )
