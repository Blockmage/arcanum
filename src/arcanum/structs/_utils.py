from typing import Any, TypeGuard

from ._types import MsgspecDecodable, MsgspecEncodable


def is_msgspec_encodable(obj: Any) -> TypeGuard[MsgspecEncodable]:
    """Return `True` if `obj` fulfills the protocol contract of `MsgspecEncodable`."""
    return hasattr(obj, '__msgspec_encode__') and callable(obj.__msgspec_encode__)


def is_msgspec_decodable(obj: Any) -> TypeGuard[MsgspecDecodable]:
    """Return `True` if `obj` fulfills the protocol contract of `MsgspecDecodable`."""
    return hasattr(obj, '__msgspec_decode__') and callable(obj.__msgspec_decode__)
