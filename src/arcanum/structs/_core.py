import ipaddress
import os
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar, Final, Literal, Self, Unpack, cast

from dotenv import dotenv_values, find_dotenv
from msgspec import Struct, StructMeta, json, toml, yaml
from msgspec.structs import asdict, fields

from ._types import StructKwargs, StructT
from ._utils import is_msgspec_decodable, is_msgspec_encodable

if TYPE_CHECKING:
    from onepassword import Client as Client

try:
    from structlog import get_logger

    logger = get_logger(__name__)
except ImportError:
    from logging import getLogger

    logger = getLogger(__name__)


class _BaseStructMeta(StructMeta):
    def __new__(
        cls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **struct_config: Unpack[StructKwargs],
    ) -> '_BaseStructMeta':
        for attr in ('kw_only', 'omit_defaults', 'repr_omit_defaults'):
            struct_config.setdefault(attr, True)
        return super().__new__(cls, name, bases, namespace, **struct_config)


class BaseStruct(Struct, metaclass=_BaseStructMeta):
    """Custom `msgspec.Struct` class.

    The following parameters are set to `True` by default:

    - `kw_only`: All fields will be treated as keyword-only arguments in the generated `__init__` method for this type.
    - `omit_defaults`: Fields having default values will be omitted from encoding for this type.
    - `repr_omit_defaults`: Fields having default values will be omitted from the generated `__repr__` for this type.
    """


class _PerfStructMeta(StructMeta):
    def __new__(
        cls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **struct_config: Unpack[StructKwargs],
    ) -> '_PerfStructMeta':
        for kw in ('array_like', 'cache_hash', 'eq', 'frozen', 'omit_defaults', 'order', 'repr_omit_defaults'):
            struct_config.setdefault(kw, True)
        return super().__new__(cls, name, bases, namespace, **struct_config)


class PerfStruct(Struct, metaclass=_PerfStructMeta):
    """Custom `msgspec.Struct` class which sets default parameters optimized for performance.

    The following parameters are set to `True` by default:

    - `eq`: An `__eq__` method will be generated for this type.
    - `order`: Methods  `__lt__`, `__le__`, `__gt__`, and `__ge__` will be generated for this type.
    - `frozen`: Instances of this type are pseudo-immutable (attribute assignment is disabled) and hashable.
    - `cache_hash`: The hash of an instance of this type will be computed at most once and then cached for reuse.
    - `omit_defaults`: Fields having default values will be omitted from encoding for this type.
    - `repr_omit_defaults`: Fields having default values will be omitted from the generated `__repr__` for this type.
    - `array_like`: When serializing, this type will be treated as an array-like type, rather than a `dict`-like type.
    """


class _KwargsStructMeta(StructMeta):
    def __new__(
        cls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **struct_config: Unpack[StructKwargs],
    ) -> '_KwargsStructMeta':
        for kw in ('kw_only', 'frozen', 'cache_hash', 'dict'):
            struct_config.setdefault(kw, True)
        return super().__new__(cls, name, bases, namespace, **struct_config)


class KwargsStruct(Struct, metaclass=_KwargsStructMeta):
    """Custom `msgspec.Struct` class ideal for creating typed keyword argument objects.

    The following parameters are set to `True` by default:

    - `kw_only`: All fields will be treated as keyword-only arguments in the generated `__init__` method for this type.
    - `frozen`: Instances of this type are pseudo-immutable (attribute assignment is disabled) and hashable.
    - `cache_hash`: The hash of an instance of this type will be computed at most once and then cached for reuse.
    - `dict`: Instances of this type will include a `__dict__`.
    """

    @classmethod
    def _filter_data(cls, *, data: dict[str, Any], prefix: str = '') -> dict[str, Any]:
        """Filter data by case-insensitively matching prefixed keys to class attributes."""
        filtered = {}

        pre_len = len(prefix)
        pre_folded = prefix.casefold()
        field_mapping = {field.casefold(): field for field in cls.__struct_fields__}

        for key, val in data.items():
            if not (folded := key.casefold()).startswith(pre_folded):
                continue

            field_folded = folded[pre_len:]
            if original_field := field_mapping.get(field_folded):
                filtered[original_field] = val

        return filtered

    @classmethod
    def from_kwargs(cls, *, prefix: str = '', **kwargs: Any) -> Self:
        """Return a new instance from `kwargs` filtered by matching keys prefixed by `prefix` to class attributes.

        Parameters
        ----------
        prefix : str, optional
            Prefix by which to case-insensitively filter keys (i.e., attribute names).
        **kwargs: Any
            Dictionary of keyword arguments with which to instantiate the class object.

        Returns
        -------
        Self
            A new instance of the class instantiated with the input dictionary.
        """
        return cls(**cls._filter_data(data=kwargs, prefix=prefix))

    @classmethod
    def from_env(
        cls,
        *,
        prefix: str = '',
        dotenv_path: str | None = None,
        dotenv_filename: str = '.env',
        **kwargs: Any,
    ) -> Self:
        """Create an instance of the class from environment variables.

        This method loads environment variables from a specified dotenv file or the file path returned by `find_dotenv`
        using `dotenv_filename`. It filters the loaded environment variables based on the provided `prefix` and
        initializes an instance of the class with the filtered data.

        Parameters
        ----------
        prefix : str, optional
            A prefix by which to filter the environment variable keys, by default `''`.
        dotenv_path : Path | str | None, optional
            The path to the dotenv file, by default `None`. If `None` or if the file cannot be found, the path returned
            by `find_dotenv` using `dotenv_filename` will be used.
        dotenv_filename : str, optional
            The name of the dotenv file for which to search, by default `'.env'`.
        **kwargs: Any
            Additional keyword arguments to be merged with the dotenv data.

        Returns
        -------
        Self
            An instance of the class initialized with the filtered environment variables.
        """
        env_data = (
            dotenv_values(path)
            if ((path := dotenv_path) and (path := os.path.normpath(os.path.expanduser(os.path.expandvars(path)))))
            else dotenv_values(find_dotenv(dotenv_filename))
        ) | kwargs
        return cls(**cls._filter_data(data=env_data, prefix=prefix))

    def to_kwargs(self, *, omit_none: bool = True, **kwargs: Any) -> dict[str, Any]:
        """Convert object attributes to a dictionary of keyword arguments.

        Excludes `None` values and updates any values for keys in `kwargs` if present and valid as attribute names.

        Parameters
        ----------
        omit_none : bool, optional
            Whether to remove all attributes (keys in the resulting dictionary) whose values are `None`.

        Returns
        -------
        dict[str, Any]
            A dictionary representation of this class object's attributes, updated with the
            key:value pairs in `kwargs` for any keys matched to attribute names.
        """
        kwargs_dict = asdict(self) | {key: val for key, val in kwargs.items() if key in asdict(self)}
        return {key: val for key, val in kwargs_dict.items() if val is not None} if omit_none else kwargs_dict


class DataStructConfig(Struct, kw_only=True):
    json_encoder_decimal_format: Literal['string', 'number'] = 'string'
    json_encoder_uuid_format: Literal['canonical', 'hex'] = 'canonical'
    json_encoder_order: Literal['deterministic', 'sorted'] | None = None

    json_decoder_float_hook: Callable[[str], Any] = float


class _DataStructMeta(StructMeta):
    def __new__(
        mcls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **struct_config: Unpack[StructKwargs],
    ) -> '_DataStructMeta':
        struct_config.setdefault('kw_only', True)
        inst = super().__new__(mcls, name, bases, namespace, **struct_config)

        cfg_dict = {}

        # TODO: Figure this out, because it doesn't appear to be working.
        # It hasn't been tested thoroughly though, so try it first.
        for base in reversed(bases):
            if hasattr(base, '__datastruct_config__'):
                if isinstance(base.__datastruct_config__, DataStructConfig):
                    cfg_dict.update(
                        {
                            f: getattr(base.__datastruct_config__, f)
                            for f in base.__datastruct_config__.__struct_fields__
                        }
                    )
                else:
                    msg = "'__datastruct_config__' must be an instance of DataStructConfig, "
                    msg += f'not {type(base.__datastruct_config__)!r}'
                    raise TypeError(msg)

        super().__setattr__(inst, '__datastruct_config__', DataStructConfig(**cfg_dict))
        return inst


class DataStruct(Struct, metaclass=_DataStructMeta):
    """Custom `msgspec.Struct` type with with cached, class-level encoder/decoder and extensible serialization hooks."""

    __datastruct_config__: ClassVar[DataStructConfig] = DataStructConfig()

    _json_encoders: ClassVar[dict[type, json.Encoder]] = {}
    _json_decoders: ClassVar[dict[type, json.Decoder[StructT[Self]]]] = {}

    _enc_handlers: ClassVar[dict[type, Callable[[Any], Any]]] = {}
    _dec_handlers: ClassVar[dict[type, Callable[[type, Any], Any]]] = {}

    @classmethod
    def register_encoding_handler(cls, obj_type: Any, handler: Callable[[Any], Any]) -> None:
        """Register custom encoder for a specific type."""
        cls._enc_handlers[obj_type] = handler

    @classmethod
    def register_decoding_handler(cls, obj_type: Any, handler: Callable[[type, Any], Any]) -> None:
        """Register custom decoder for a specific type."""
        cls._dec_handlers[obj_type] = handler

    @classmethod
    def _float_dec_hook(cls, val: str) -> Any:
        """Decode untyped float literals (may be overridden in subclasses - defaults to `float()`)."""
        return float(val)

    @classmethod
    def _enc_hook(cls, obj: Any) -> Any:
        """Convert object of unsupported type to a type supported for encoding."""
        if is_msgspec_encodable(obj):
            return obj.__msgspec_encode__()
        for obj_type, enc_handler in cls._enc_handlers.items():
            if isinstance(obj, obj_type):
                return enc_handler(obj)
        msg = f'No handler registered for encoding objects of type {type(obj).__name__}'
        raise NotImplementedError(msg)

    @classmethod
    def _dec_hook(cls, obj_type: type, obj: Any) -> Any:
        """Convert object of unsupported type to a type supported for decoding."""
        if is_msgspec_decodable(obj):
            return obj.__msgspec_decode__(obj)
        if obj_type in cls._dec_handlers:
            return cls._dec_handlers[obj_type](obj_type, obj)
        msg = f'No handler registered for decoding objects of type {obj_type.__name__}'
        raise NotImplementedError(msg)

    @classmethod
    def _get_json_encoder(cls) -> json.Encoder:
        """Retrieve or create cached encoder for this class.

        Notes
        -----
        Registers a `msgspec.json.Encoder` instance on the class directly, making it available to across all instances.
        This `Encoder` instance is stored in `cls._json_encoders`, which is a `dict[type, Encoder]` where each key is a
        `cls` object mapped to the `Encoder` instance for that class.

        Each `Encoder` instance is instantiated as:

        ```python
        encoder = Encoder(
            enc_hook=cls._enc_hook,
            decimal_format=cls.__datastruct_config__.json_encoder_decimal_format,
            uuid_format=cls.__datastruct_config__.json_encoder_uuid_format,
            order=cls.__datastruct_config__.json_encoder_order,
        )
        ```

        This results in a single `Encoder` instance per class definition, which is shared across all instances of the
        `DataStruct` class object. We instantiate each `Encoder` with a reference to `cls._enc_hook`, which is a
        `classmethod` that takes an object of `Any` type and iterates over the functions registered in
        `cls._enc_handlers`. If the object's type exists in the mapping of `type: Callable[[]]
        """
        if cls not in cls._json_encoders:
            cls._json_encoders[cls] = json.Encoder(
                enc_hook=cls._enc_hook,
                decimal_format=cls.__datastruct_config__.json_encoder_decimal_format,
                uuid_format=cls.__datastruct_config__.json_encoder_uuid_format,
                order=cls.__datastruct_config__.json_encoder_order,
            )
        return cls._json_encoders[cls]

    @classmethod
    def _get_json_decoder(cls) -> json.Decoder[Self]:
        """Retrieve or create cached decoder for this class."""
        if cls not in cls._json_decoders:
            cls._json_decoders[cls] = json.Decoder(cls, dec_hook=cls._dec_hook, float_hook=cls._float_dec_hook)
        return cls._json_decoders[cls]

    @classmethod
    def from_file(cls, path: str, /) -> Self:
        """Create an instance of the class from a JSON, TOML, or YAML file."""
        if not os.path.isfile(path):
            msg = f'File not found or not a regular file: {path}'
            raise FileNotFoundError(msg)

        _, ext = os.path.splitext(path)
        if (ext := ext.lower().removeprefix('.')) not in {'json', 'yaml', 'yml', 'toml'}:
            msg = f"Unsupported file extension - must be 'json', 'yaml', 'yml', or 'toml' - received: {ext}"
            raise ValueError(msg)

        with open(path) as file:
            data = file.read()

        if ext == 'json':
            return cls.from_json(data)

        if ext == 'toml':
            return cls.from_toml(data)

        return cls.from_yaml(data)

    @classmethod
    def from_json(cls, data: bytes | str, /) -> Self:
        """Create an instance of the class from `bytes` or `str` JSON data."""
        return cls._get_json_decoder().decode(data)

    @classmethod
    def from_yaml(cls, data: bytes | str) -> Self:
        """Create an instance of the class from `bytes` or `str` YAML data."""
        return yaml.decode(data, type=cls, dec_hook=cls._dec_hook)

    @classmethod
    def from_toml(cls, data: bytes | str) -> Self:
        """Create an instance of the class from `bytes` or `str` TOML data."""
        return toml.decode(data, type=cls, dec_hook=cls._dec_hook)

    def to_file(
        self,
        path: str,
        *,
        json_indent: int = 0,
        overwrite: bool = False,
        file_type: Literal['json', 'yaml', 'yml', 'toml'] | None = None,
    ) -> str:
        """Serialize an instance of the class and write the data to file.

        Supports writing JSON, YAML, and TOML data.

        Parameters
        ----------
        path : str
            File path to which to write serialized data.
        json_indent : int, optional
            Amount of JSON indentation (default: `0`).
        overwrite : bool, optional
            Whether to overwrite an existing file if one exists at the given path (default: `False`).
        file_type : Literal['json', 'yaml', 'yml', 'toml'] | None, optional
            Format of the serialized data.
            By default, the format is inferred from the file extension and handled accordingly.

        Returns
        -------
        str
            Path of the written file.

        Raises
        ------
        FileExistsError
            If a file exists at `path` and `overwrite` is `False`.
        OSError
            If `path` exists but is not a regular file.
        ValueError
            If the provided file type (or inferred type based on the file extension) is unsupported.
        """
        if os.path.exists(path):
            if overwrite is not True:
                msg = f'File exists - pass `overwrite=True` to overwrite existing file: {path}'
                raise FileExistsError(msg)
            if not os.path.isfile(path):
                msg = f'Unable to overwrite file (not a regular file): {path}'
                raise OSError(msg)

        if file_type is None:
            _, ext = os.path.splitext(path)
            if (ext := ext.lower().removeprefix('.')) not in {'json', 'yaml', 'yml', 'toml'}:
                msg = f"Unsupported file extension - must be 'json', 'yaml', 'yml', or 'toml' - received: {ext}"
                if not ext.strip():
                    msg = f'Unable to infer file type from extension and `file_type` was not provided: {path}'
                raise ValueError(msg)
            file_type = cast("Literal['json', 'yaml', 'yml', 'toml']", ext)

        data = (
            self.to_json(indent=json_indent)
            if file_type == 'json'
            else self.to_toml()
            if file_type == 'toml'
            else self.to_yaml()
        )

        with open(path, 'wb') as file:
            file.write(data)

        return path

    def to_json(self, *, indent: int = 0) -> bytes:
        """Serialize an instance of the class into JSON bytes data."""
        return json.format(self._get_json_encoder().encode(self), indent=indent)

    def to_yaml(self, *, order: Literal['deterministic', 'sorted'] | None = None) -> bytes:
        """Serialize an instance of the class into YAML bytes data."""
        return yaml.encode(self, enc_hook=self._enc_hook, order=order)

    def to_toml(self, *, order: Literal['deterministic', 'sorted'] | None = None) -> bytes:
        """Serialize an instance of the class into TOML bytes data."""
        return toml.encode(self, enc_hook=self._enc_hook, order=order)


# Register some common types that should really be handled
# out-of-the-box by `msgspec`, but somehow aren't...

_ip_type_map = {
    ipaddress.IPv4Address: ipaddress.IPv4Address,
    ipaddress.IPv6Address: ipaddress.IPv6Address,
    ipaddress.IPv4Network: ipaddress.IPv4Network,
    ipaddress.IPv6Network: ipaddress.IPv6Network,
    ipaddress.IPv4Interface: ipaddress.IPv4Interface,
    ipaddress.IPv6Interface: ipaddress.IPv6Interface,
}


def _decode_ip_type(typ: type, obj: Any) -> Any:
    if handler := _ip_type_map.get(typ):
        return handler(obj)
    raise NotImplementedError


for typ in _ip_type_map:
    DataStruct.register_decoding_handler(obj_type=typ, handler=_decode_ip_type)
    DataStruct.register_encoding_handler(obj_type=typ, handler=str)


class ConfigStruct(DataStruct):
    _op_client: ClassVar[Any | None] = None
    _op_raise_if_missing: ClassVar[bool] = False
    _op_integration_name: ClassVar[Final[str]] = 'ConfigStruct'
    _op_integration_version: ClassVar[Final[str]] = 'v1.0.0'

    @classmethod
    async def _get_op_client(cls) -> 'Client':
        if cls._op_client is None:
            try:
                from onepassword import Client, DesktopAuth
            except ImportError as err:
                msg = "Missing required dependency 'onepassword-sdk'"
                raise ImportError(msg) from err
            else:
                tkn, acc_name, client = '', '', None
                kwds = {
                    'integration_name': cls._op_integration_name,
                    'integration_version': cls._op_integration_version,
                }
                if acc_name := os.getenv('OP_ACCOUNT', '').strip():
                    client = await Client.authenticate(auth=DesktopAuth(account_name=acc_name), **kwds)
                if tkn := os.getenv('OP_SERVICE_ACCOUNT_TOKEN', '').strip():
                    client = await Client.authenticate(auth=tkn, **kwds)
                if (not tkn.strip() and not acc_name.strip()) or client is None:
                    msg = "If using 1Password, at least one of 'OP_ACCOUNT' or 'OP_SERVICE_ACCOUNT_NAME' "
                    msg += 'variables must be set and non-empty in the environment'
                    raise ValueError(msg)
                cls._op_client = client
                return cls._op_client
        else:
            return cls._op_client

    async def resolve_secret_fields(self) -> None:
        pending: list[tuple[Struct, str, str]] = []

        def _collect(obj: Struct) -> None:
            for fld in fields(obj):
                val = getattr(obj, fld.name)
                if fld.type is str and isinstance(val, str) and (stripped := val.strip()).startswith('op://'):
                    pending.append((obj, fld.name, stripped))
                elif isinstance(val, Struct):
                    _collect(val)

        _collect(self)

        if not pending:
            return

        client = await self._get_op_client()
        secrets = await client.secrets.resolve_all([ref for _, _, ref in pending])
        missing_refs: list[str] = []
        for instance, attr_name, op_ref in pending:
            if (resolved := secrets.individual_responses.get(op_ref)) is not None:
                if (res := resolved.content) is not None and res.secret:
                    setattr(instance, attr_name, str(res.secret))
                    continue
            missing_refs.append(op_ref)

        if self._op_raise_if_missing and missing_refs:
            unique_missing_refs = list(dict.fromkeys(missing_refs))
            for op_ref in unique_missing_refs:
                logger.error('Unable to resolve 1Password secret reference: %s', op_ref)
            missing_str = ', '.join(unique_missing_refs)
            msg = f'Unable to resolve one or more 1Password secret references: {missing_str}'
            raise ValueError(msg)
