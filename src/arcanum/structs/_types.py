from collections.abc import Callable
from typing import Any, Literal, Protocol, Self, TypedDict

from msgspec import Struct

type StructT[T: (Struct, type[Struct]) = Struct] = T
"""[TypeAliasType] Represents a `msgspec.Struct` class object or object instance."""


class StructKwargs(TypedDict, total=False):
    """`TypedDict` representing possible keyword arguments for configuring a `msgspec.Struct` class.

    Defaults
    --------
    ```
    frozen: bool = False
    order: bool = False
    eq: bool = True
    kw_only: bool = False
    omit_defaults: bool = False
    forbid_unknown_fields: bool = False
    tag: str | int | bool | Callable[[str], str | int] | None = None
    tag_field: str | None = None
    rename: Literal['lower', 'upper', 'camel', 'pascal', 'kebab'] | None = None
    repr_omit_defaults: bool = False
    array_like: bool = False
    gc: bool = True
    weakref: bool = False
    dict: bool = False
    cache_hash: bool = False
    ```
    """

    frozen: bool  # = False
    order: bool  # = False
    eq: bool  # = True
    kw_only: bool  # = False
    omit_defaults: bool  # = False
    forbid_unknown_fields: bool  # = False
    tag: str | int | bool | Callable[[str], str | int] | None  # = None
    tag_field: str | None  # = None
    rename: Literal['lower', 'upper', 'camel', 'pascal', 'kebab'] | None  # = None
    repr_omit_defaults: bool  # = False
    array_like: bool  # = False
    gc: bool  # = True
    weakref: bool  # = False
    dict: bool  # = False
    cache_hash: bool  # = False


class MsgspecEncodable(Protocol):
    """Protocol for objects that define their own `msgspec` encoding logic."""

    def __msgspec_encode__(self) -> Any: ...


class MsgspecDecodable(Protocol):
    """Protocol for objects that define their own `msgspec` decoding logic."""

    @classmethod
    def __msgspec_decode__(cls, obj: Any) -> Self: ...
