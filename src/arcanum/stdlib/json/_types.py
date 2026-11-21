from collections.abc import Callable, Iterable
from typing import Any, Literal, Protocol, TypedDict, TypeVar

__all__ = (
    'DecCacheKeyT',
    'DecHookT',
    'DecKw',
    'DecimalFormatT',
    'DumpsKw',
    'EncCacheKeyT',
    'EncHookT',
    'EncKw',
    'FloatHookT',
    'OrderT',
    'UUIDFormatT',
    '_CacheT',
)

_K_contra = TypeVar('_K_contra', contravariant=True)
_V = TypeVar('_V')

type EncHookT = Callable[[Any], Any] | None
type DecHookT = Callable[[type, Any], Any] | None
type FloatHookT = Callable[[str], Any] | None

type DecimalFormatT = Literal['string', 'number']
type UUIDFormatT = Literal['canonical', 'hex']
type OrderT = Literal['deterministic', 'sorted'] | None

type DecCacheKeyT[T: type = Any] = tuple[T, bool, DecHookT, FloatHookT]
"""Used as the key by which the `msgspec.json.Decoder` will be cached.

The first argument, if provided, should be the type (class) of Python object in to which the `Decoder` is meant to
deserialize JSON data.
"""

type EncCacheKeyT[T: EncHookT = Any] = tuple[T, DecimalFormatT, UUIDFormatT, OrderT]
"""Used as the key by which the `msgspec.json.Encoder` will be cached.

The first argument, if provided, should be the function to be called to handle unsupported types when serializing Python
data to JSON. It must take a single argument - the object being serialized - and return it in a format that `msgspec` is
able to serialize; otherwise, for types not serializable, the function should raise `NotImplementedError`.
"""


class DecKw(TypedDict, total=False):
    strict: bool
    dec_hook: DecHookT
    float_hook: FloatHookT


class EncKw(TypedDict, total=False):
    decimal_format: DecimalFormatT
    uuid_format: UUIDFormatT
    order: OrderT


class DumpsKw(TypedDict, total=False):
    skipkeys: bool
    ensure_ascii: bool
    check_circular: bool
    allow_nan: bool
    separators: tuple[str, str] | None
    sort_keys: bool
    str_keys: bool
    builtin_types: Iterable[type]
    enc_hook: EncHookT
    order: OrderT


class _CacheT(Protocol[_K_contra, _V]):
    def __getitem__(self, key: _K_contra, /) -> _V: ...
    def __setitem__(self, key: _K_contra, value: _V, /) -> None: ...
    def __contains__(self, key: object, /) -> bool: ...
