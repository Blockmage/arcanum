import re
from collections.abc import Sequence
from types import GenericAlias
from typing import Any, Literal, NamedTuple, TypeGuard

import sniffio
from typing_extensions import _AnnotatedAlias

VENV_PATH_RX: re.Pattern[str] = re.compile(
    r'(^|[\\/])(\.?virtualenv|\.?venv|\.?env|lib[\\/python[0-9]+\.[0-9]+]'
    r'[\\/site-packages])([\\/]|$)'
)


def is_venv(obj: Any, /) -> bool:
    return VENV_PATH_RX.search(str(obj)) is not None


def is_sequence(obj: Any, /) -> TypeGuard[Sequence[Any]]:
    return isinstance(obj, Sequence) and not isinstance(obj, str | bytes | bytearray | memoryview)


def is_annotated(obj: Any, /) -> bool:
    return isinstance(obj, _AnnotatedAlias) and getattr(obj, '__args__', None) is not None


def is_truthy(val: str | int | Literal[True]) -> bool:
    if val is True:
        return val
    if (vl := str(val).lower().strip()) in ('1', 't', 'y', 'true', 'yes', 'on'):
        return True
    return bool(vl.startswith(('enable', 'activ')))


def is_falsy(val: str | int | Literal[False]) -> bool:
    if val is False:
        return True
    if (vl := str(val).lower().strip()) in ('0', 'f', 'false', 'n', 'no', 'off'):
        return True
    return bool(vl.startswith(('disable', 'deactivate')))


def is_async_ctx() -> bool:
    try:
        sniffio.current_async_library()
    except sniffio.AsyncLibraryNotFoundError:
        return False
    else:
        return True


def is_namedtuple_instance(obj: Any) -> TypeGuard[NamedTuple]:
    return (
        all(hasattr(obj, attr) for attr in ('_field_defaults', '_fields', '_asdict'))
        and callable(obj._asdict)
        and isinstance(obj, tuple)
    )


def is_namedtuple_type(obj: Any) -> TypeGuard[type[NamedTuple]]:
    return (
        isinstance(obj, (type, GenericAlias))
        and hasattr(obj, '_fields')
        and hasattr(obj, '_field_defaults')
        and hasattr(obj, '_make')
        and callable(getattr(obj, '_make', None))
    )
