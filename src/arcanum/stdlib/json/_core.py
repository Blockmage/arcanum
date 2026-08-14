import json as _std_json
import os
import tempfile
from typing import IO, Any, Literal, Unpack, overload

from msgspec import json, to_builtins, toml, yaml
from typed_sentinels import Sentinel

from arcanum.stdlib.path import Path

from ._types import DecCacheKey, DecKw, DumpsKw, EncCacheKey, EncHook, EncKw

_SNTL = Sentinel()

_DEFAULT_ENCODER: json.Encoder = json.Encoder()
_DEFAULT_DECODER: json.Decoder[Any] = json.Decoder()

_DEFAULT_ENC_CACHE_KEY: EncCacheKey = (_SNTL, 'string', 'canonical', None)
_DEFAULT_DEC_CACHE_KEY: DecCacheKey[Any] = (_SNTL, True, None, None)

_enc_cache: dict[EncCacheKey, json.Encoder] = {_DEFAULT_ENC_CACHE_KEY: _DEFAULT_ENCODER}
_dec_cache: dict[DecCacheKey, json.Decoder[Any]] = {_DEFAULT_DEC_CACHE_KEY: _DEFAULT_DECODER}


def _filter_dumps_kw(opt: Literal['std', 'msg'], /, **kwargs: Unpack[DumpsKw]) -> dict[str, Any]:
    """Filter a `DumpsKw` `TypedDict` of `kwargs` to split its key:value pairs.

    Splits into either of two sets:
    - Those pertaining to `msgspec.to_builtins()`, or
    - Those pertaining to the standard library's `json.dumps()` function.

    Parameters
    ----------
    opt : Literal['std', 'msg']
        Which set of key:value pairs from the input `kwargs` dictionary is to be returned, either `std` (the standard
        library's `json.dumps()` function) or `msg` (`msgspec.to_builtins()`).

    Returns
    -------
    dict[str, Any]
        A dictionary mapping keywords to their respective values for the corresponding function's parameters.
    """
    if opt == 'msg':
        return {k: v for k, v in kwargs.items() if k in ('order', 'enc_hook', 'builtin_types', 'str_keys')}
    return {k: v for k, v in kwargs.items() if k not in ('order', 'enc_hook', 'builtin_types', 'str_keys')}


def _build_dec_key[T: type](typ: T, **kwargs: Unpack[DecKw]) -> DecCacheKey[T]:
    """Return a `DecCacheKey` from input `typ` and `DecKw` keyword arguments."""
    return (
        typ,
        kwargs.get('strict', True),
        kwargs.get('dec_hook'),
        kwargs.get('float_hook'),
    )


def _build_enc_key[T: EncHook](hook: T, **kwargs: Unpack[EncKw]) -> EncCacheKey[T]:
    """Return an `EncCacheKey` from input `hook` and `EncKw` keyword arguments."""
    return (
        hook,
        kwargs.get('decimal_format', 'string'),
        kwargs.get('uuid_format', 'canonical'),
        kwargs.get('order'),
    )


def get_decoder[T: type](typ: T = _SNTL, **kwargs: Unpack[DecKw]) -> json.Decoder[T] | json.Decoder[Any]:
    """Get or create an instance of `msgspec.json.Decoder` instantiated with the provided arguments.

    For each new combination of `typ` and `kwargs`, a new instance is created, cached, and returned.
    Subsequent calls made with these same arguments return the cached instance. When called without
    arguments, a pre-cached, default instance is returned.

    Parameters
    ----------
    typ : type, optional
        Optional type to be used to instantiate the decoder.
        If provided, the returned decoder will decode JSON data into Python objects of this type.
    **kwargs : DecKw, optional
        Optional keyword arguments to be passed to the constructor of the decoder.

    Returns
    -------
    json.Decoder[T] | json.Decoder[Any]
        An instance of `msgspec.json.Decoder`.
    """
    if typ is _SNTL and not kwargs:
        return _DEFAULT_DECODER
    if (key := _build_dec_key(typ, **kwargs)) == _DEFAULT_DEC_CACHE_KEY:
        return _DEFAULT_DECODER
    if key in _dec_cache:
        return _dec_cache[key]
    dec = json.Decoder(type=typ, **kwargs) if typ is not _SNTL else json.Decoder(**kwargs)
    _dec_cache[key] = dec
    return dec


def get_encoder(hook: EncHook = _SNTL, **kwargs: Unpack[EncKw]) -> json.Encoder:
    """Get or create an instance of `msgspec.json.Encoder` instantiated with the provided arguments.

    For each new combination of `hook` and `kwargs`, a new instance is created, cached, and returned.
    Subsequent calls made with these same arguments return the cached instance. When called without
    arguments, a pre-cached, default instance is returned.

    Parameters
    ----------
    hook : EncHook, optional
        Optional function to be called by the encoder to handle any unsupported types.
        If provided, this should be a function that takes a single object of type `Any` as input, and either returns a
        type serializable by the encoder, or raises a `NotImplementedError` for types that cannot be converted.
    **kwargs : EncKw, optional
        Optional keyword arguments to be passed to the constructor of the encoder.

    Returns
    -------
    json.Encoder
        An instance of `msgspec.json.Encoder`.
    """
    if hook is _SNTL and not kwargs:
        return _DEFAULT_ENCODER
    if (key := _build_enc_key(hook, **kwargs)) == _DEFAULT_ENC_CACHE_KEY:
        return _DEFAULT_ENCODER
    if key in _enc_cache:
        return _enc_cache[key]
    enc = json.Encoder(enc_hook=hook, **kwargs) if hook is not _SNTL else json.Encoder(**kwargs)
    _enc_cache[key] = enc
    return enc


@overload
def minify(data: bytes) -> bytes: ...
@overload
def minify(data: str) -> str: ...
def minify[T: (bytes, str)](data: T) -> T:
    """Minify `bytes` or `str` JSON `data`.

    Parameters
    ----------
    data : bytes | str
        JSON data.

    Returns
    -------
    bytes | str
        Minified JSON data.
    """
    return json.format(data, indent=-1)


@overload
def prettify(data: bytes, *, indent: int = 2) -> bytes: ...
@overload
def prettify(data: str, *, indent: int = 2) -> str: ...
def prettify[T: (bytes, str)](data: T, *, indent: int = 2) -> T:
    """Prettify `bytes` or `str` JSON `data`.

    Parameters
    ----------
    data : bytes | str
        JSON data.
    indent : int, optional
        Number of whitespace characters to be used for a single level of indentation.

    Returns
    -------
    bytes | str
        Prettified JSON data.

    Raises
    ------
    ValueError
        If provided a value for `indent` which is equal-to or less-than zero (use `minify()` instead).
    """
    if indent <= 0:
        msg = 'Use `minify()` instead'
        raise ValueError(msg)
    return json.format(data, indent=indent)


def _std_json_dumps(
    obj: Any,
    indent: int = _SNTL,
    encoding: str = 'utf-8',
    errors: str = 'strict',
    *,
    minified: bool = False,
    as_bytes: bool = False,
    **kwargs: Unpack[DumpsKw],
) -> str | bytes:
    """Return a JSON `bytes` or `str` object serialized using the standard library's `json.dumps()`.

    Data is first prepared with `msgspec.to_builtins()` for compatibility.
    """
    pretty = indent is not _SNTL
    msg_kw = _filter_dumps_kw('msg', **kwargs)
    std_kw = _filter_dumps_kw('std', **kwargs)
    result = _std_json.dumps(to_builtins(obj, **msg_kw), **std_kw)
    result = result.encode(encoding, errors) if as_bytes else result
    return minify(result) if minified else prettify(result, indent=indent) if pretty else result


def read_file(
    filename: os.PathLike[str],
    *,
    mode: str = 'r',
    encoding: str = 'utf-8',
    errors: str = 'strict',
) -> str:
    try:
        with open(filename, encoding=encoding, errors=errors, mode=mode) as f:
            return f.read()
    except (OSError, FileNotFoundError, PermissionError) as exc:
        msg = f"Failed to read file '{filename}': {exc!s}"
        raise type(exc)(msg) from exc


def write_file(
    filename: os.PathLike[str],
    data: bytes | str,
    *,
    encoding: str = 'utf-8',
    errors: str = 'strict',
    make_dirs: bool = False,
    atomic: bool = False,
) -> None:
    path = Path(filename)

    if make_dirs:
        path.parent.mkdir(parents=True, exist_ok=True)

    mode = 'wb' if isinstance(data, bytes) else 'w'

    try:
        if atomic:
            directory = str(path.parent)
            prefix = f'.{path.name}.'
            suffix = '.tmp'

            with tempfile.NamedTemporaryFile(
                mode=mode,
                encoding=None if mode == 'wb' else encoding,
                errors=None if mode == 'wb' else errors,
                delete=False,
                dir=directory,
                prefix=prefix,
                suffix=suffix,
            ) as tmp:
                tmp_name = tmp.name
                tmp.write(data)
            os.replace(tmp_name, path)
        else:
            with open(
                path,
                mode,
                encoding=None if mode == 'wb' else encoding,
                errors=None if mode == 'wb' else errors,
            ) as f:
                f.write(data)
    except (OSError, FileNotFoundError, PermissionError) as e:
        msg = f"Failed to write to file '{filename}': {e!s}"
        raise type(e)(msg) from e


@overload
def dumps(
    obj: Any,
    encoder: json.Encoder | None = None,
    indent: int = _SNTL,
    encoding: str = 'utf-8',
    errors: str = 'strict',
    *,
    minified: bool = False,
    **kwargs: Unpack[DumpsKw],
) -> str: ...
@overload
def dumps(
    obj: Any,
    encoder: json.Encoder | None = None,
    indent: int = _SNTL,
    encoding: str = 'utf-8',
    errors: str = 'strict',
    *,
    minified: bool = False,
    as_bytes: Literal[False],
    **kwargs: Unpack[DumpsKw],
) -> str: ...
@overload
def dumps(
    obj: Any,
    encoder: json.Encoder | None = None,
    indent: int = _SNTL,
    encoding: str = 'utf-8',
    errors: str = 'strict',
    *,
    minified: bool = False,
    as_bytes: Literal[True],
    **kwargs: Unpack[DumpsKw],
) -> bytes: ...
def dumps(
    obj: Any,
    encoder: json.Encoder | None = None,
    indent: int = _SNTL,
    encoding: str = 'utf-8',
    errors: str = 'strict',
    *,
    minified: bool = False,
    as_bytes: bool = False,
    **kwargs: Unpack[DumpsKw],
) -> str | bytes:
    """Serialize `obj` as JSON `str` or `bytes` data, optionally prettifying or minifying.

    Parameters
    ----------
    obj : Any
        Arbitrary Python object to be encoded as JSON.
    encoder : json.Encoder | None, optional
        Optional `msgspec.json.Encoder` instance with which to encode `obj`.
        Mutually exclusive with `kwargs`.
    indent : int, optional
        Number of whitespace characters to be used for a single level of indentation.
        Mutually exclusive with `minified`.
    encoding : str, optional
        Optional encoding to be used when decoding bytes data.
        Applicable only when `as_bytes` is `False` (passed to `bytes.decode()`).
    errors : str, optional
        Error handling policy for any errors encountered while decoding.
        Applicable only when `as_bytes` is `False` (passed to `bytes.decode()`).
    minified : bool, optional
        Whether to return minified JSON.
        Mutually exclusive with `indent`.
    as_bytes : bool, optional
        Whether to return `bytes` JSON data instead of `str`.
        Default is `False`, i.e., JSON `str` is returned.
    **kwargs : DumpsKw
        Optional keyword arguments to be passed to `msgspec.to_builtins()` and `json.dumps()`.
        Note that if any of these are present, serialization is likely to be far less performant, because we are only
        passing `obj` first to `msgspec` for preparation, before using the standard library's `json.dumps()` to handle
        the actual serialization. It is recommended to avoid this where possible. Additionally, it is an error to
        provide any of these keyword arguments alongside an argument for `encoder`.

    Returns
    -------
    str | bytes
        The input `obj` encoded as either `str` or `bytes` JSON data.

    Raises
    ------
    ValueError
        If any mutually-exclusive arguments are provided together.
    """
    if (pretty := indent is not _SNTL) and minified:
        msg = 'Arguments are mutually-exclusive - '
        msg += f'Pick one: `minified` (minified={minified}) or `indent` (indent={indent})'
        raise ValueError(msg)

    if kwargs and encoder:
        msg = 'Arguments are mutually-exclusive - '
        msg += 'Pick one: `encoder` or keyword arguments (`DumpsKw`)\n'
        msg += f'Received: encoder={encoder}; kwargs={list(kwargs)}'
        raise ValueError(msg)

    if kwargs:
        return _std_json_dumps(
            obj=obj,
            indent=indent,
            encoding=encoding,
            errors=errors,
            minified=minified,
            as_bytes=as_bytes,
            **kwargs,
        )

    encoder = encoder or _DEFAULT_ENCODER
    result = encoder.encode(obj)
    if as_bytes is False:
        result = result.decode(encoding, errors)
    return minify(result) if minified else prettify(result, indent=indent) if pretty else result


def loads[T](s: str | bytes | bytearray, *, decoder: json.Decoder[Any] | None = None, typ: type[T] = _SNTL) -> Any:
    if decoder is not None:
        return decoder.decode(s)
    return get_decoder(typ).decode(s)


def dump(obj: Any, fp: IO[str], *, indent: int | None = None) -> None:
    """Serialize `obj` as JSON and write to file object `fp`.

    If `indent` is not `None`, pretty-print output.
    """
    if indent is not None:
        encoded = _DEFAULT_ENCODER.encode(obj)
        formatted = json.format(encoded, indent=indent)
        fp.write(formatted.decode('utf-8'))
    else:
        fp.write(_DEFAULT_ENCODER.encode(obj).decode('utf-8'))


def dump_file(obj: Any, filename: os.PathLike[str], *, indent: int | None = None) -> None:
    """Serialize `obj` as JSON and write to file `filename`.

    If `indent` is not `None`, pretty-print output.
    """
    data = dumps(obj, indent=indent) if indent is not None else dumps(obj)
    write_file(filename, data)


def load[T](fp: IO[str], *, typ: type[T] | None = None) -> Any:
    """Deserialize JSON content from file object `fp` to a Python object.

    If provided an argument for `typ`, get or create a new cached `Decoder` instance corresponding to that type.
    """
    s = fp.read()
    if typ is not None:
        return get_decoder(typ).decode(s)
    return _DEFAULT_DECODER.decode(s)


def load_file[T](filename: os.PathLike[str], *, typ: type[T] | None = None) -> Any:
    """Deserialize JSON content from file `filename` to a Python object.

    If provided an argument for `typ`, get or create a new cached `Decoder` instance corresponding to that type.
    """
    s = read_file(filename)
    if typ is not None:
        return get_decoder(typ).decode(s)
    return _DEFAULT_DECODER.decode(s)


@overload
def dumps_toml(obj: Any, *, encoding: str = 'utf-8', errors: str = 'strict') -> str: ...
@overload
def dumps_toml(obj: Any, *, encoding: str = 'utf-8', errors: str = 'strict', as_bytes: Literal[False]) -> str: ...
@overload
def dumps_toml(obj: Any, *, encoding: str = 'utf-8', errors: str = 'strict', as_bytes: Literal[True]) -> bytes: ...
def dumps_toml(obj: Any, *, encoding: str = 'utf-8', errors: str = 'strict', as_bytes: bool = False) -> bytes | str:
    result = toml.encode(obj)
    if as_bytes:
        return result
    return result.decode(encoding, errors)


def loads_toml[T](s: str | bytes | bytearray, *, typ: type[T] = dict[Any, Any], strict: bool = True) -> T:
    if isinstance(s, str):
        s = s.encode('utf-8')
    elif isinstance(s, bytearray):
        s = bytes(s)
    return toml.decode(s, type=typ, strict=strict)


def dump_toml(obj: Any, fp: IO[str]) -> None:
    data = dumps_toml(obj, as_bytes=False)
    fp.write(str(data))


def load_toml[T](
    fp: IO[str],
    *,
    typ: type[T] = dict[Any, Any],
    strict: bool = True,
) -> T:
    data = fp.read()
    return loads_toml(data, typ=typ, strict=strict)


def dump_toml_file(
    obj: Any,
    filename: os.PathLike[str],
    *,
    encoding: str = 'utf-8',
    errors: str = 'strict',
    make_dirs: bool = False,
    atomic: bool = False,
) -> None:
    data = dumps_toml(obj)
    write_file(filename, data, encoding=encoding, errors=errors, make_dirs=make_dirs, atomic=atomic)


def load_toml_file[T](
    filename: os.PathLike[str],
    *,
    typ: type[T] = dict[Any, Any],
    encoding: str = 'utf-8',
    errors: str = 'strict',
    strict: bool = True,
) -> T:
    data = read_file(filename, encoding=encoding, errors=errors)
    return loads_toml(data, typ=typ, strict=strict)


@overload
def dumps_yaml(obj: Any, *, encoding: str = 'utf-8', errors: str = 'strict') -> str: ...
@overload
def dumps_yaml(obj: Any, *, encoding: str = 'utf-8', errors: str = 'strict', as_bytes: Literal[False]) -> str: ...
@overload
def dumps_yaml(obj: Any, *, encoding: str = 'utf-8', errors: str = 'strict', as_bytes: Literal[True]) -> bytes: ...
def dumps_yaml(obj: Any, *, encoding: str = 'utf-8', errors: str = 'strict', as_bytes: bool = False) -> bytes | str:
    result = yaml.encode(obj)
    if as_bytes:
        return result
    return result.decode(encoding, errors)


def loads_yaml[T](s: str | bytes | bytearray, *, typ: type[T] = dict[Any, Any], strict: bool = True) -> T:
    if isinstance(s, str):
        s = s.encode('utf-8')
    elif isinstance(s, bytearray):
        s = bytes(s)
    return yaml.decode(s, type=typ, strict=strict)


def dump_yaml(obj: Any, fp: IO[str]) -> None:
    data = dumps_yaml(obj, as_bytes=False)
    fp.write(data)


def load_yaml[T](fp: IO[str], *, typ: type[T] = dict[Any, Any], strict: bool = True) -> T:
    data = fp.read()
    return loads_yaml(data, typ=typ, strict=strict)


def dump_yaml_file(
    obj: Any,
    filename: os.PathLike[str],
    *,
    encoding: str = 'utf-8',
    errors: str = 'strict',
    make_dirs: bool = False,
    atomic: bool = False,
) -> None:
    data = dumps_yaml(obj)
    write_file(filename, data, encoding=encoding, errors=errors, make_dirs=make_dirs, atomic=atomic)


def load_yaml_file[T](
    filename: os.PathLike[str],
    *,
    typ: type[T] = dict[Any, Any],
    encoding: str = 'utf-8',
    errors: str = 'strict',
    strict: bool = True,
) -> T:
    data = read_file(filename, encoding=encoding, errors=errors)
    return loads_yaml(data, typ=typ, strict=strict)
