import os
import os.path
from collections.abc import Generator, Iterator, Sequence
from typing import IO, TYPE_CHECKING, Any, Final, Literal, Self, TypeGuard, overload

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


class _PathParents(Sequence['Path']):
    __slots__ = ('_cls', '_path')

    def __init__(self, path: str, cls: type['Path']) -> None:
        self._path = path
        self._cls = cls

    def __len__(self) -> int:
        count = 0
        curr = self._path
        while True:
            parent = os.path.dirname(curr)
            if parent == curr or not parent:
                break
            count += 1
            curr = parent
        return count

    @overload
    def __getitem__(self, index: int) -> 'Path': ...
    @overload
    def __getitem__(self, index: slice) -> Sequence['Path']: ...
    def __getitem__(self, index: int | slice) -> 'Path | Sequence[Path]':
        if isinstance(index, slice):
            # Convert to list to satisfy the Sequence[Path] return type for slices
            return [self[i] for i in range(*index.indices(len(self)))]

        if not isinstance(index, int):
            msg = f'Path.parents indices must be integers or slices, not {type(index).__name__}'
            raise TypeError(msg)

        curr = self._path
        if index < 0:
            index += len(self)

        if index < 0:
            msg = 'Index out of range'
            raise IndexError(msg)

        for _ in range(index + 1):
            parent = os.path.dirname(curr)
            if parent == curr or not parent:
                msg = 'Index out of range'
                raise IndexError(msg)
            curr = parent
        return self._cls(curr)


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

    def mkdir(self, mode: int = 0o700, parents: bool = False, exist_ok: bool = False) -> None:
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
        import glob

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
        import glob

        for path in glob.glob(os.path.join(self._path, '**', pattern), recursive=True):
            yield self.__class__(path)

    def touch(self, mode: int = 0o600, exist_ok: bool = True) -> None:
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

    # --- 2026-09-20

    @property
    def parts(self) -> tuple[str, ...]:
        """Tuple providing access to the path's components."""
        # This is slightly expensive, but necessary for parity
        res = []
        path = self._path
        while True:
            path, last = os.path.split(path)
            if last:
                res.append(last)
            else:
                if path:
                    res.append(path)
                break
        return tuple(reversed(res))

    @property
    def suffixes(self) -> list[str]:
        """List of the path's file extensions."""
        if len(parts := self.name.split('.')) == 1:
            return []
        return [f'.{x}' for x in parts[1:]]

    def with_stem(self, stem: str) -> Self:
        """Return a new path with the stem changed."""
        return self.with_name(f'{stem}{self.suffix}')

    def readlink(self) -> Self:
        """Return the path to which the symbolic link points."""
        return self.__class__(os.readlink(self._path))

    # File type checks using stat to avoid multiple syscalls
    def _get_mode(self) -> int:
        try:
            return self.stat(follow_symlinks=False).st_mode
        except OSError:
            return 0

    def is_mount(self) -> bool:
        return os.path.ismount(self._path)

    def is_socket(self) -> bool:
        import stat

        return stat.S_ISSOCK(self._get_mode())

    def is_fifo(self) -> bool:
        import stat

        return stat.S_ISFIFO(self._get_mode())

    @property
    def parents(self) -> Sequence['Path']:
        """The logical ancestors of the path."""
        return _PathParents(self._path, self.__class__)

    @property
    def root(self) -> str:
        """The root of the path, if any."""
        return os.path.splitdrive(self._path)[1][0] if self.is_absolute() else ''

    def is_relative_to(self, other: PathLike) -> bool:
        """Return `True` if the path is relative to `other`."""
        try:
            self.relative_to(other)
        except FsError:
            return False
        else:
            return True

    def match(self, pattern: str) -> bool:
        """Return `True` if the path matches the given glob-style pattern."""
        import fnmatch

        # If the pattern is absolute, match the whole path
        if pattern.startswith(('/', '\\')) or (len(pattern) > 1 and pattern[1] == ':'):
            return fnmatch.fnmatch(self._path, pattern)

        # Otherwise, match against the name or the end of the path
        # This mirrors pathlib's behavior of matching the tail
        return fnmatch.fnmatch(self.name, pattern) or fnmatch.fnmatch(self._path, f'*/{pattern}'.replace('//', '/'))

    def open(self, mode: str = 'r', buffering: int = -1, **kwargs: Any) -> IO[Any]:
        """Open the file pointed to by the path."""
        return open(self._path, mode, buffering, **kwargs)

    def lstat(self) -> os.stat_result:
        """Like `stat()`, but if the path is a symlink, return the symlink's status."""
        return self.stat(follow_symlinks=False)

    def lchmod(self, mode: int) -> None:
        """Like `chmod()`, but if the path is a symlink, change the symlink's mode."""
        os.chmod(self._path, mode, follow_symlinks=False)

    def owner(self) -> str:
        """Return the name of the user owning the file."""
        import pwd

        return pwd.getpwuid(self.stat().st_uid).pw_name

    def group(self) -> str:
        """Return the name of the group owning the file."""
        import grp

        return grp.getgrgid(self.stat().st_gid).gr_name

    def symlink_to(self, target: PathLike, target_is_directory: bool = False) -> None:
        """Make this path a symlink to the given target."""
        os.symlink(os.fspath(target), self._path, target_is_directory)

    def hardlink_to(self, target: PathLike) -> None:
        """Make this path a hard link to the same file as target."""
        os.link(os.fspath(target), self._path)

    def is_block_device(self) -> bool:
        import stat

        return stat.S_ISBLK(self._get_mode())

    def is_char_device(self) -> bool:
        import stat

        return stat.S_ISCHR(self._get_mode())

    def walk(
        self, topdown: bool = True, on_error: Any = None, follow_symlinks: bool = False
    ) -> Generator[tuple['Path', list[str], list[str]], Any]:
        """Directory tree generator."""
        for root, dirs, files in os.walk(self._path, topdown, on_error, follow_symlinks):
            yield self.__class__(root), dirs, files

    def copy(self, target: PathLike, follow_symlinks: bool = True) -> Self:
        """Copy the file to a new location (using `shutil.copy2`)."""
        import shutil

        dst = os.fspath(target)
        shutil.copy2(self._path, dst, follow_symlinks=follow_symlinks)
        return self.__class__(dst)

    def copy_into(self, target_dir: PathLike, follow_symlinks: bool = True) -> Self:
        """Copy this file into the specified directory."""
        dst = self.__class__(target_dir).joinpath(self.name)
        return self.copy(dst, follow_symlinks=follow_symlinks)

    def move(self, target: PathLike) -> Self:
        """Move the file or directory to a new location."""
        import shutil

        dst = os.fspath(target)
        shutil.move(self._path, dst)
        return self.__class__(dst)

    def move_into(self, target_dir: PathLike) -> Self:
        """Move this file into the specified directory."""
        dst = self.__class__(target_dir).joinpath(self.name)
        return self.move(dst)

    def with_segments(self, *segments: PathLike) -> Self:
        """Create a new path from the given segments, using the same flavor."""
        # For our implementation, this is essentially a join on the root or current class
        return self.__class__(os.path.join(*(os.fspath(s) for s in segments)))

    def is_junction(self) -> bool:
        """Return True if the path is a Windows junction."""
        try:
            st = self.lstat()
            # Junctions are directories with a reparse point attribute
            import stat

            return stat.S_ISDIR(st.st_mode) and hasattr(st, 'st_reparse_tag')
        except (OSError, AttributeError):
            return False

    def info(self) -> dict[str, Any]:
        """Return a dictionary of file metadata."""
        st = self.stat()
        return {
            'size': st.st_size,
            'mtime': st.st_mtime,
            'ctime': st.st_ctime,
            'isdir': self.is_dir(),
            'islink': self.is_symlink(),
        }

    @property
    def parser(self) -> Any:
        """Return the underlying path module (os.path)."""
        return os.path

    def as_posix(self) -> str:
        """Return the string representation with forward slashes."""
        return self._path.replace('\\', '/')


os.PathLike.register(Path)


if __name__ == '__main__':
    import pathlib

    def get_public_api(obj: Any) -> set[str]:
        return {name for name in dir(obj) if not name.startswith('_')}

    pathlib_api = get_public_api(pathlib.Path('.'))
    custom_api = get_public_api(Path('.'))

    missing = sorted(pathlib_api - custom_api)
    extra = sorted(custom_api - pathlib_api)

    msg = 'Missing from Custom Path:'
    print(msg)
    print('-' * (len(msg) + 1))
    for item in missing:
        print(item)

    msg = 'Extra in Custom Path:'
    print(f'\n{msg}')
    print('-' * (len(msg) + 1))
    for item in extra:
        print(item)
