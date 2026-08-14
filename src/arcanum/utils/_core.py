import copy
import os
import re
from collections.abc import Callable, Sequence
from copy import deepcopy
from typing import Any

from dotenv import dotenv_values, find_dotenv

from arcanum.predicates import is_sequence
from arcanum.stdlib.path import FsError, FsErrorCode, Path, PathLike

_CAMEL_TO_SNAKE_RE: re.Pattern[str] = re.compile(r'(?<=[a-z0-9])([A-Z])')


def camel_case(s: str, /) -> str:
    """Convert a string to camelCase."""
    s = s.replace('-', '_')
    parts = s.split('_')
    if len(parts) > 1:
        s = ''.join(part.title() for part in parts)
    return s[0].lower() + s[1:]


def snake_case(s: str, /) -> str:
    """Convert a string to snake_case."""
    s = s.replace('-', '_')
    s = re.sub(_CAMEL_TO_SNAKE_RE, r'_\1', s)
    return s.lower()


def pascal_case(s: str, /) -> str:
    """Convert a string to PascalCase."""
    camelcase_str = camel_case(s)
    return camelcase_str[0].upper() + camelcase_str[1:]


def kebab_case(s: str, /) -> str:
    """Convert a string to kebab-case."""
    s = s.replace('_', '-')
    s = re.sub(_CAMEL_TO_SNAKE_RE, r'-\1', s)
    return s.lower()


def normalize_str(s: list[str] | str, /) -> list[str] | str:
    """Normalize one or more string values (e.g., for use in comparisons).

    Normalizes strings by stripping them of whitespace, casefolding, deduplicating, and sorting them in ascending
    lexicographic order.

    Parameters
    ----------
    s : list[str] | str
        A string or list of strings to be normalized.

    Returns
    -------
    list[str] | str
        The normalized string(s). If given input of multiple strings and only a single string
        remains, it will be returned as a `str` rather than a `list[str]`.
    """

    s = [s] if isinstance(s, str) else s
    s = sorted({str(item).strip().casefold() for item in s})
    return next(iter(s)) if len(s) == 1 else s


def ensure_str_sequence(obj: object, /) -> Sequence[str]:
    """Return `obj` as a `Sequence[str]` by converting it into one if it is not already."""
    return [str(v).strip() for v in obj] if is_sequence(obj) else [str(obj).strip()]


def typed_getenv[T](var: str, *, cast_as: Callable[[Any], T] = str) -> T | None:
    """Return the value of a named variable `var` from the application environment.

    Returns
    -------
    T | None
        - If the named variable exists and is non-empty, this is the value of that variable, either
          as a `str`, or, if possible, as the provided `cast_as` type.
        - If the variable is unset, or any error is encountered when attempting to cast the value to
          the provided `cast_as` type, or for any errors otherwise, `None` is returned.
    """
    try:
        return cast_as(v) if ((v := os.getenv(var)) is not None) else None
    except Exception:
        return None


def compare_env(var: str, comparand: str | Sequence[str]) -> bool:
    comparand = ensure_str_sequence(comparand)
    return any(os.getenv(var, '').casefold() == _.casefold() for _ in comparand)


def env_exists(var: str | Sequence[str]) -> bool:
    var = ensure_str_sequence(var)
    return any(os.getenv(_) is not None for _ in var)


def load_env(
    prefix: str = '',
    dotenv_path: PathLike | None = None,
    dotenv_name: str = '.env',
    *,
    use_os_env: bool = True,
    **overrides: Any,
) -> dict[str, Any]:
    env_data = os.environ.copy() if use_os_env else {}
    if dotenv_path is None and (found_dotenv_path := find_dotenv(dotenv_name)) != '':
        dotenv_path = found_dotenv_path
    if dotenv_path is not None:
        env_data |= dotenv_values(resolve_path(dotenv_path))
    return filter_by_prefix(data=env_data, prefix=prefix) | overrides


def filter_by_keys(data: dict[str, Any], match_keys: Sequence[str], *, deepcopy: bool = False) -> dict[str, Any]:
    data = copy.deepcopy(data) if deepcopy else data
    return {k: v for k, v in data.items() if k in match_keys}


def filter_by_prefix(data: dict[str, Any], prefix: str) -> dict[str, Any]:
    try:
        return {k[len(prefix) :]: v for k, v in data.items() if k.casefold().startswith(prefix.casefold())}
    except AttributeError as exc:
        msg = "Keys in data must be of type 'str'"
        raise TypeError(msg) from exc


def filter_config_data(
    *,
    data: dict[str, Any],
    keys: Sequence[str],
    prefix: str = '',
    dotenv_name: str = '.env',
    dotenv_path: Path | str | None = None,
    use_dotenv: bool = True,
    use_os_env: bool = True,
    **overrides: Any,
) -> dict[str, Any]:
    data = deepcopy(data)
    overrides = overrides or {}
    env_data = os.environ.copy() if use_os_env else {}

    if use_dotenv:
        env_data.update(
            load_env(
                prefix=prefix,
                dotenv_path=dotenv_path,
                dotenv_name=dotenv_name,
                use_os_env=use_os_env,
            )
        )

    env_data = filter_by_prefix(data=env_data, prefix=prefix)
    data = filter_by_keys(data=(data | env_data), match_keys=keys)

    if overrides:
        for key in overrides:
            if key not in keys:
                msg = f'Invalid field for config class: {key}'
                raise ValueError(msg)

    return data | overrides


def resolve_path(path: PathLike, *, strict: bool = False) -> Path:
    try:
        _expanded = os.path.expandvars(str(path))
        _path = Path(_expanded).expanduser()
        return _path.resolve(strict=strict)
    except Exception as exc:
        raise FsError(path, FsErrorCode.LOOP) from exc


def create_file(path: PathLike, *, file_mode: int = 0o600, dir_mode: int = 0o700) -> Path:
    try:
        _path = resolve_path(path)
        _path.parent.mkdir(mode=dir_mode, parents=True, exist_ok=True)
        _path.touch(mode=file_mode, exist_ok=True)
    except PermissionError as exc:
        raise FsError(path, FsErrorCode.PERMISSION_DENIED) from exc
    except Exception as exc:
        raise FsError(path) from exc
    else:
        return _path


def create_dir(path: PathLike, *, dir_mode: int = 0o700) -> Path:
    try:
        _path = resolve_path(path)
        _path.mkdir(mode=dir_mode, parents=True, exist_ok=True)
    except PermissionError as exc:
        raise FsError(path, FsErrorCode.PERMISSION_DENIED) from exc
    except Exception as exc:
        raise FsError(path) from exc
    else:
        return _path


def dir_path_from_env(
    var: str,
    *,
    create: bool = False,
    dir_mode: int = 0o700,
) -> Path | None:
    if (_str_path := os.getenv(var)) is None:
        return None
    try:
        _path = resolve_path(_str_path)
        if create:
            _path.mkdir(mode=dir_mode, parents=True, exist_ok=True)
    except PermissionError as exc:
        raise FsError(_str_path, FsErrorCode.PERMISSION_DENIED) from exc
    except Exception as exc:
        raise FsError(_str_path) from exc
    else:
        return _path


def file_path_from_env(
    var: str,
    *,
    create: bool = False,
    file_mode: int = 0o600,
    dir_mode: int = 0o700,
) -> Path | None:
    if (_str_path := os.getenv(var)) is None:
        return None
    try:
        _path = resolve_path(_str_path)
        if create:
            _path.parent.mkdir(mode=dir_mode, parents=True, exist_ok=True)
            _path.touch(mode=file_mode, exist_ok=True)
    except PermissionError as exc:
        raise FsError(_str_path, FsErrorCode.PERMISSION_DENIED) from exc
    except Exception as exc:
        raise FsError(_str_path) from exc
    else:
        return _path
