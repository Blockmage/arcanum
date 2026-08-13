import glob
import os
import os.path
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, Final, Literal, Self, TypeGuard

from ._exceptions import FsError

if TYPE_CHECKING:
    from _typeshed import ReadableBuffer
else:
    ReadableBuffer = object

# ruff: noqa: FBT001 (boolean-type-hint-positional-argument)
# ruff: noqa: FBT002 (boolean-default-value-positional-argument)

__all__ = (
    'BytesPath',
    'EncodingErrorPolicy',
    'LineEnding',
    'Path',
    'PathLike',
    'StrPath',
    'TextEncodingErrorPolicy',
)

_FILE_MODE: Final[int] = 0o600
_DIR_MODE: Final[int] = 0o700

# fmt: off
_WINDOWS_RESERVED_FS_NAMES: Final[frozenset[str]] = frozenset({
    *(f'COM{i}' for i in range(1, 10)),
    *(f'LPT{i}' for i in range(1, 10)),
    'CON', 'PRN', 'AUX', 'NUL',
})
# fmt: on

type StrPath = os.PathLike[str] | Path | str
type BytesPath = os.PathLike[bytes] | Path | bytes
type PathLike[T: (StrPath, BytesPath, Path) = StrPath] = T

LineEnding = Literal['', '\n', '\r', '\r\n']
EncodingErrorPolicy = Literal['strict', 'ignore', 'replace', 'backslashreplace', 'surrogateescape']
TextEncodingErrorPolicy = Literal[EncodingErrorPolicy, 'xmlcharrefreplace', 'namereplace']


def _is_pathlike(obj: object) -> TypeGuard[PathLike]:
    return isinstance(obj, str) or hasattr(obj, '__fspath__')


class Path:
    __slots__ = ('_path',)

    @classmethod
    def __msgspec_decode__(cls, obj: Any) -> Self:
        return cls(obj)

    def __msgspec_encode__(self) -> str:
        return self._path

    def __init__(self, path: PathLike, /) -> None:
        self._path = os.fspath(path)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self._path!s}')"

    def __str__(self) -> str:
        return self._path

    def __bytes__(self) -> bytes:
        return self._path.encode()

    def __hash__(self) -> int:
        return hash(self._path)

    def __fspath__(self) -> str:
        return self._path

    def __truediv__(self, other: PathLike) -> Self:
        return self.joinpath(other)

    def __eq__(self, other: object) -> bool:
        if not _is_pathlike(other):
            return NotImplemented
        try:
            result = os.path.normpath(self._path) == os.path.normpath(os.fspath(other))
        except Exception:
            return False
        else:
            return result

    def __lt__(self, other: object) -> bool:
        if not _is_pathlike(other):
            return NotImplemented
        try:
            return self._path < os.fspath(other)
        except Exception:
            return NotImplemented

    def __le__(self, other: object) -> bool:
        if not _is_pathlike(other):
            return NotImplemented
        try:
            return self._path <= os.fspath(other)
        except Exception:
            return NotImplemented

    def __gt__(self, other: object) -> bool:
        if not _is_pathlike(other):
            return NotImplemented
        try:
            return self._path > os.fspath(other)
        except Exception:
            return NotImplemented

    def __ge__(self, other: object) -> bool:
        if not _is_pathlike(other):
            return NotImplemented
        try:
            return self._path >= os.fspath(other)
        except Exception:
            return NotImplemented

    def _str_replace(self, old: str, new: str, count: int = -1) -> str:
        return self._path.replace(old, new, count)

    def exists(self) -> bool:
        """Return `True` if the path exists and is a file, directory, or symlink."""
        return os.path.exists(self._path)

    def is_file(self) -> bool:
        """Return `True` if the path exists and is a regular file (not a symlink)."""
        return (not os.path.islink(self._path)) and os.path.isfile(self._path)

    def is_dir(self) -> bool:
        """Return `True` if the path exists and is a regular directory (not a symlink)."""
        return (not os.path.islink(self._path)) and os.path.isdir(self._path)

    def is_symlink(self) -> bool:
        """Return `True` if the path exists and is a symlink."""
        return os.path.islink(self._path)

    def is_absolute(self) -> bool:
        """Return `True` if the path is absolute."""
        return os.path.isabs(self._path)

    def is_relative(self) -> bool:
        """Return `True` if the path is relative (i.e., not absolute)."""
        return not self.is_absolute()

    @classmethod
    def cwd(cls) -> Self:
        """Return a new `Path` object representing the current working directory."""
        return cls(os.getcwd())

    @classmethod
    def home(cls) -> Self:
        """Return a new `Path` object representing the `$HOME` directory for the current user."""
        return cls(os.path.expanduser('~'))

    @property
    def as_str(self) -> str:
        """Path as a string."""
        return self._path

    @property
    def parent(self) -> Self:
        """Parent directory of the path."""
        return self.__class__(os.path.dirname(self._path))

    @property
    def name(self) -> str:
        """Final component of the path."""
        return os.path.basename(self._path)

    @property
    def suffix(self) -> str:
        """File extension of the final component, including the leading dot (`'.'`)."""
        _, ext = os.path.splitext(self._path)
        return ext

    @property
    def stem(self) -> str:
        """Final path component, sans suffix."""
        if not (basename := self.name):
            return ''
        if 0 < (i := basename.rfind('.')) < len(basename) - 1:
            return basename[:i]
        return basename

    @property
    def drive(self) -> str:
        """The drive prefix, if any."""
        return os.path.splitdrive(self._path)[0]

    @property
    def anchor(self) -> str:
        """The concatenation of the drive and root, or `''` if the path is relative."""
        if not self.is_absolute():
            return ''
        drive, path = os.path.splitdrive(self._path)
        if path.startswith(os.sep):
            return drive + os.sep
        return drive

    def joinpath(self, *parts: str | PathLike | os.DirEntry[str]) -> Self:
        """Join the path with additional path components."""
        return self.__class__(os.path.join(self._path, *(os.fspath(p) for p in parts)))

    def with_name(self, name: str) -> Self:
        """Return a new version of the path with the name changed to `name`."""
        return self.parent.joinpath(name)

    def with_suffix(self, suffix: str) -> Self:
        """Return a new version of the path with the suffix changed to `suffix`."""
        return self.with_name(f'{os.path.splitext(self.name)[0]}{suffix}')

    def stat(self, *, follow_symlinks: bool = True) -> os.stat_result:
        """Perform a stat system call on the path."""
        return os.stat(self._path, follow_symlinks=follow_symlinks)

    def resolve(self, *, strict: bool = False) -> Self:
        """Return a new version of the path with all symlinks resolved."""
        return self.__class__(os.path.realpath(self._path, strict=strict))

    def absolute(self) -> Self:
        """Return a new version of the path made absolute."""
        return self.__class__(os.path.abspath(self._path))

    def expand(self) -> Self:
        """Return a new path with user tilde (`~`) and shell variables in the form of `$var` and `${var}` expanded."""
        return self.__class__(os.path.expandvars(os.path.expanduser(self._path)))

    def expandvars(self) -> Self:
        """Return a new path with shell variables in the form of `$var` and `${var}` expanded."""
        return self.__class__(os.path.expandvars(self._path))

    def expanduser(self) -> Self:
        """Return a new path with user tilde (`~`) expanded."""
        return self.__class__(os.path.expandvars(os.path.expanduser(self._path)))

    def read_text(
        self,
        encoding: str = 'utf-8',
        errors: TextEncodingErrorPolicy = 'strict',
        newline: LineEnding | None = None,
    ) -> str:
        """Return the contents of the file as a string.

        Parameters
        ----------
        encoding : str, optional
            Encoding (default: 'utf-8').
        errors : TextEncodingErrorPolicy, optional
            Error handling scheme (default: 'strict').
        newline : LineEnding | None, optional
            Character used to indicate line breaks in the file (default: `None` (universal newlines mode)).

        Returns
        -------
        str
            Contents of the file as a string.
        """
        with open(self._path, encoding=encoding, errors=errors, newline=newline) as f:
            return f.read()

    def read_bytes(self) -> bytes:
        """Read the contents of this file as bytes.

        Returns
        -------
        bytes
            Contents of the file as bytes.
        """
        with open(self._path, 'rb') as f:
            return f.read()

    def write_text(
        self,
        data: str,
        encoding: str = 'utf-8',
        errors: TextEncodingErrorPolicy = 'strict',
        newline: LineEnding | None = None,
    ) -> int:
        """Write text to the file.

        Parameters
        ----------
        data : str
            Data to be written to the file.
        encoding : str, optional
            Encoding (default: 'utf-8').
        errors : TextEncodingErrorPolicy, optional
            Error handling scheme (default: 'strict').
        newline : LineEnding | None, optional
            Character used to indicate line breaks in the data (default: `None` (universal newlines mode)).

        Returns
        -------
        int
            Number of characters written.
        """
        with open(self._path, 'w', encoding=encoding, errors=errors, newline=newline) as f:
            return f.write(data)

    def write_bytes(self, data: ReadableBuffer) -> int:
        """Write bytes to this file.

        Parameters
        ----------
        data : bytes
            Data to be written to the file.

        Returns
        -------
        int
            Number of bytes written.
        """
        with open(self._path, 'wb') as f:
            return f.write(data)

    def mkdir(self, mode: int = _DIR_MODE, parents: bool = False, exist_ok: bool = False) -> None:
        """Create a new directory at the path.

        Parameters
        ----------
        mode : int, optional
            Octal mode to be set on the newly-created directory (default: `0o700`).
        parents : bool, optional
            If `True`, create parent directories as needed.
            Note: `mode` is not set for parent directories.
        exist_ok : bool, optional
            If `False` and the directory already exists, raise `OSError`.
        """
        if parents:
            os.makedirs(self._path, mode=mode, exist_ok=exist_ok)
        else:
            os.mkdir(self._path, mode=mode)

    def rmdir(self) -> None:
        """Remove the directory (must be empty)."""
        os.rmdir(self._path)

    def unlink(self, *, missing_ok: bool = False) -> None:
        """Remove the file or symbolic link.

        Parameters
        ----------
        missing_ok : bool, optional
            If `False` and the file does not exist, raise `FsError`.
        """
        try:
            os.unlink(self._path)
        except OSError as exc:
            if not missing_ok:
                raise FsError(self._path, error='NOT_FOUND') from exc

    def rename(self, target: PathLike) -> Self:
        """Rename the file or directory to `target`.

        Parameters
        ----------
        target : str | PathLike
            New name for the target.

        Returns
        -------
        Path
            Path object of the renamed file or directory.
        """
        target_path = os.fspath(target)
        os.rename(self._path, target_path)
        return self.__class__(target_path)

    def replace(self, target: PathLike, *args: Any, **kwargs: Any) -> Self:
        """Rename this file or directory to the given target, replacing the target if it exists.

        Parameters
        ----------
        target : str | PathLike
            New name for the target.

        Returns
        -------
        Path
            Path object of the renamed file or directory.
        """
        target_path = os.fspath(target)
        os.replace(self._path, target_path)
        return self.__class__(target_path)

    def iterdir(self) -> Iterator[Self]:
        """Iterate the contents of the directory, yielding files and directories.

        Yields
        ------
        Path
            Path objects of the contents of the directory.
        """
        with os.scandir(self._path) as it:
            for name in it:
                yield self.joinpath(name)

    def glob(self, pattern: str) -> Iterator[Self]:
        """Iterate over paths in the directory, yielding paths matched to `pattern`.

        Parameters
        ----------
        pattern : str
            Glob pattern against which to match.

        Yields
        ------
        Path
            Each matching path.
        """
        for path in glob.glob(os.path.join(self._path, pattern)):
            yield self.__class__(path)

    def rglob(self, pattern: str) -> Iterator[Self]:
        """Recursively iterate over paths in the directory, yielding paths matched to `pattern`.

        Parameters
        ----------
        pattern : str
            Glob pattern against which to match.

        Yields
        ------
        Path
            Each matching path.
        """
        for path in glob.glob(os.path.join(self._path, '**', pattern), recursive=True):
            yield self.__class__(path)

    def touch(self, mode: int = _FILE_MODE, exist_ok: bool = True) -> None:
        """Create a file at the path.

        Parameters
        ----------
        mode : int, optional
            Octal mode to be set on the newly-created file (default: `0o600`).
        exist_ok : bool, optional
            If `False` and the file already exists, raise `FsPathExistsError`.
        """
        fd = None
        flags = os.O_CREAT | os.O_WRONLY
        if not exist_ok:
            flags |= os.O_EXCL
        try:
            fd = os.open(self._path, flags, mode)
        except FileExistsError as exc:
            if not exist_ok:
                raise FsError(self._path, error='EXISTS') from exc
        finally:
            if fd is not None:
                os.close(fd)

    def chmod(self, mode: int) -> None:
        """Change the octal mode (permissions) of the path."""
        os.chmod(self._path, mode)

    def samefile(self, other_path: PathLike) -> bool:
        """Return `True` if the path and `other_path` point to the same target."""
        return os.path.samefile(self._path, os.fspath(other_path))

    def relative_to(self, other: PathLike) -> Self:
        """Return a version of the path made relative to `other`.

        Parameters
        ----------
        other : PathLike
            Path to which the path should be made relative.

        Returns
        -------
        Path
            Path relative to `other`.

        Raises
        ------
        FsError
            If the path is not prefixed with `other`.
        """
        other_path = os.fspath(other)
        rel = os.path.relpath(self._path, other_path)
        if rel.startswith('..'):
            raise FsError(other_path, msg=f'Path cannot be made relative to {self._path}')
        return self.__class__(rel)

    def is_reserved(self) -> bool:
        """Return `True` if this path is a reserved path on Windows systems."""
        if '.' in (name := self.name.upper()):
            name = name.split('.', 1)[0]
        return name in _WINDOWS_RESERVED_FS_NAMES


os.PathLike.register(Path)
