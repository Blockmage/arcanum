from collections.abc import Callable, Iterable
from typing import Any, Literal, TypedDict

type EncHook = Callable[[Any], Any] | None
type DecHook = Callable[[type, Any], Any] | None
type FloatHook = Callable[[str], Any] | None

type DecimalFormatT = Literal['string', 'number']
type UUIDFormatT = Literal['canonical', 'hex']
type OrderT = Literal['deterministic', 'sorted'] | None

type DecCacheKey[T: type = Any] = tuple[T, bool, DecHook, FloatHook]
"""A tuple of `type`, `bool`, `Callable[[type, Any], Any] | None`, and `Callable[[str], Any] | None`.

This is used as the key by which the `msgspec.json.Decoder` will be cached. The first argument, if provided, should be
the type (class) of Python object in to which the `Decoder` is meant to deserialize JSON data.
"""

type EncCacheKey[T: EncHook = Any] = tuple[T, DecimalFormatT, UUIDFormatT, OrderT]
"""A tuple of `Callable[[Any], Any] | None`, `Literal['string', 'number']`, `Literal['canonical', 'hex']`, and
`Literal['deterministic', 'sorted'] | None`.

This is used as the key by which the `msgspec.json.Encoder` will be cached. The first argument, if provided, should
be the function to be called to handle unsupported types when serializing Python data to JSON. It must take a single
argument - the object being serialized - and return it in a format that `msgspec` is able to serialize; otherwise, for
types not serializable, the function should raise `NotImplementedError`.
"""


class DecKw(TypedDict, total=False):
    strict: bool
    dec_hook: DecHook
    float_hook: FloatHook


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
    enc_hook: EncHook
    order: OrderT
