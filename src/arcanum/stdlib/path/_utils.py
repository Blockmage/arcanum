import os
from datetime import datetime

from ._bytesize import ByteSize
from ._core import PathLike
from ._exceptions import FsError

__all__ = (
    'assert_dir_exists',
    'assert_exists',
    'assert_file_exists',
    'assert_not_dir',
    'assert_not_exists',
    'assert_not_file',
    'dt_atime',
    'dt_ctime',
    'dt_mtime',
    'exists',
    'get_file_size',
    'get_file_size_strfmt',
    'get_mode',
    'is_absolute',
    'is_dir',
    'is_empty',
    'is_empty_dir',
    'is_empty_file',
    'is_file',
    'is_link',
    'is_relative',
    'set_mode',
    'str_atime',
    'str_ctime',
    'str_mtime',
)


def assert_exists(path: PathLike) -> None:
    """Raise `FsError` if `path` does not exist."""
    if not os.path.exists(path):
        raise FsError(path, error='NOT_FOUND')


def assert_dir_exists(path: PathLike) -> None:
    """Raise `FsError` if `path` does not exist or is not a directory."""
    if not os.path.isdir(path):
        error = 'NOT_A_DIRECTORY'
        if not os.path.exists(path):
            error = 'NOT_FOUND'
        raise FsError(path, error=error)


def assert_file_exists(path: PathLike) -> None:
    """Raise `FsError` if `path` does not exist or is not a file."""
    if not os.path.isfile(path):
        if not os.path.exists(path):
            raise FsError(path, error='NOT_FOUND')
        raise FsError(path, msg='Not a regular file')


def assert_not_exists(path: PathLike) -> None:
    """Raise `FsError` if `path` exists."""
    if os.path.exists(path):
        raise FsError(path, error='EXISTS')


def assert_not_dir(path: PathLike) -> None:
    """Raise `FsError` if `path` is an existing directory."""
    if os.path.isdir(path):
        raise FsError(path, 'IS_A_DIRECTORY')


def assert_not_file(path: PathLike) -> None:
    """Raise `FsError` if `path` is an existing file."""
    if os.path.isfile(path):
        raise FsError(path, 'EXISTS')


def is_empty(path: PathLike, /, *, raising: bool = False) -> bool:
    """Return `True` if the path exists and is either an empty file or an empty directory."""
    return (is_empty_dir(path, raising=raising) is True) or (is_empty_file(path, raising=raising) is True)


def is_empty_dir(path: PathLike, /, *, raising: bool = False) -> bool:
    """Return `True` if directory is effectively empty, ignoring `.DS_Store` files.

    Directory is considered empty if it:
    - Contains no files except `.DS_Store`
    - Contains only empty subdirectories or subdirectories with only `.DS_Store` files

    Parameters
    ----------
    path : PathLike
        Directory path to check.
    raising : bool, default=False
        If `True`, raise `FsError` when path is invalid or doesn't exist.

    Returns
    -------
    bool
        `True` if directory is effectively empty, `False` otherwise.

    Raises
    ------
    FsError
        If `raising=True` and path is not a valid directory.
    """
    try:
        with os.scandir(path) as it:
            for entry in it:
                if entry.name == '.DS_Store':
                    continue
                if entry.is_file():
                    return False
                if entry.is_dir():
                    if not is_empty_dir(entry.path, raising=raising):
                        return False
            return True
    except (OSError, FsError) as exc:
        if raising:
            if isinstance(exc, FsError):
                raise FsError(path, error=exc.error_code) from exc
            raise FsError(path, error=(exc.errno if exc.errno is not None else 'UNKNOWN')) from exc
        return False


def is_empty_file(path: PathLike, /, *, raising: bool = False) -> bool:
    """Return `True` if the path exists, is a regular file, and has a total size of `0` bytes."""
    try:
        assert_file_exists(path)
    except Exception as exc:
        if raising:
            raise FsError(path, error='EXISTS') from exc
        return False
    return is_file(path) and os.path.getsize(path) == 0


def exists(path: PathLike) -> bool:
    """Return `True`if the path exists (can be a file, directory, or link)."""
    return os.path.exists(path)


def is_file(path: PathLike) -> bool:
    """Return `True` if the path exists and is a regular file (not a link)."""
    return os.path.isfile(path) and not os.path.islink(path)


def is_dir(path: PathLike) -> bool:
    """Return `True` if the path exists and is a regular directory (not a link)."""
    return os.path.isdir(path) and not os.path.islink(path)


def is_link(path: PathLike) -> bool:
    """Return `True` if the path exists and is a link."""
    return os.path.islink(path)


def is_absolute(path: PathLike) -> bool:
    """`Return `True` if the path is absolute."""
    return os.path.isabs(path)


def is_relative(path: PathLike) -> bool:
    """`Return `True` if the path is relative (i.e., not absolute)."""
    return not os.path.isabs(path)


def get_mode(path: PathLike) -> int:
    """Get the octal file or directory permissions."""
    return int(str(oct(os.stat(path).st_mode & 0o777))[2:])


def set_mode(path: PathLike, value: int) -> None:
    """Set the octal file or directory permissions."""
    os.chmod(path, (int(str(value), 8) & 0o777))


def get_file_size(path: PathLike) -> int:
    """Get the file size in bytes as an integer value."""
    return os.path.getsize(path)


def get_file_size_strfmt(path: PathLike) -> str:
    """Get the file size formatted as a human-readable string."""
    return ByteSize(os.path.getsize(path)).to_str()


def dt_atime(path: PathLike) -> datetime:
    """Get the last data access time (`atime`) for the file at `path` as a `datetime` object."""
    return datetime.fromtimestamp(os.stat(path).st_atime, datetime.now().astimezone().tzinfo)


def dt_ctime(path: PathLike) -> datetime:
    """Get the last metadata change time (`ctime`) for the file at `path` as a `datetime` object."""
    return datetime.fromtimestamp(os.stat(path).st_ctime, datetime.now().astimezone().tzinfo)


def dt_mtime(path: PathLike) -> datetime:
    """Get the last modification time (`mtime`) for the file at `path` as a `datetime` object."""
    return datetime.fromtimestamp(os.stat(path).st_mtime, datetime.now().astimezone().tzinfo)


def str_atime(path: PathLike, *, fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    """Get the last data access time (`atime`) for the path and return it as a formatted string."""
    return dt_atime(path).strftime(fmt)


def str_ctime(path: PathLike, *, fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    """Get the last metadata change time (`ctime`) for the path and return it as a formatted string."""
    return dt_ctime(path).strftime(fmt)


def str_mtime(path: PathLike, *, fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    """Get the last modification time (`mtime`) for the path and return it as a formatted string."""
    return dt_mtime(path).strftime(fmt)
