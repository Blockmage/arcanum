import os
from collections.abc import AsyncIterator, Callable, Iterable, Iterator
from dataclasses import dataclass
from functools import partial
from os import PathLike
from typing import IO, TYPE_CHECKING, Any, Final, Self, TypeVar, overload

from anyio import to_thread
from anyio._core._synchronization import CapacityLimiter
from anyio.abc import AsyncResource

from . import _core

if TYPE_CHECKING:
    from _typeshed import OpenBinaryMode, OpenTextMode, ReadableBuffer, WriteableBuffer
else:
    ReadableBuffer = OpenBinaryMode = OpenTextMode = WriteableBuffer = object

# ruff: noqa: FBT001 (boolean-type-hint-positional-argument)
# ruff: noqa: FBT002 (boolean-default-value-positional-argument)

__all__ = (
    'AsyncFile',
    'AsyncPath',
    'aopen_file',
    'wrap_file',
)

T = TypeVar('T', bound='AsyncPath')


class AsyncFile[AnyStr: (bytes, str)](AsyncResource):
    """Asynchronous file object.

    This class wraps a standard file object and provides async friendly versions of the
    following blocking methods (where available on the original file object):

    - `read`
    - `read1`
    - `readline`
    - `readlines`
    - `readinto`
    - `readinto1`
    - `write`
    - `writelines`
    - `truncate`
    - `seek`
    - `tell`
    - `flush`

    All other methods are directly passed through.

    This class supports the asynchronous context manager protocol which closes the
    underlying file at the end of the context block.

    This class also supports asynchronous iteration:

    ```python
    async with await open_file(...) as f:
        async for line in f:
            print(line)
    ```
    """

    def __init__(self, fp: IO[AnyStr], *, limiter: CapacityLimiter | None = None) -> None:
        if limiter is not None and not isinstance(limiter, CapacityLimiter):
            msg = f'limiter must be a CapacityLimiter or None, not {limiter.__class__.__name__}'
            raise TypeError(msg)
        self._fp: Any = fp
        self._limiter = limiter

    def __getattr__(self, name: str) -> object:
        return getattr(self._fp, name)

    @property
    def limiter(self) -> CapacityLimiter | None:
        """The capacity limiter used by this file object, if not the global limiter."""
        return self._limiter

    @property
    def wrapped(self) -> IO[AnyStr]:
        """The wrapped file object."""
        return self._fp

    async def __aiter__(self) -> AsyncIterator[AnyStr]:
        while True:
            if line := await self.readline():
                yield line
            else:
                break

    async def aclose(self) -> None:
        return await to_thread.run_sync(self._fp.close, limiter=self._limiter)

    async def read(self, size: int = -1) -> AnyStr:
        return await to_thread.run_sync(self._fp.read, size, limiter=self._limiter)

    async def read1(self: 'AsyncFile[bytes]', size: int = -1) -> bytes:
        return await to_thread.run_sync(self._fp.read1, size, limiter=self._limiter)

    async def readline(self) -> AnyStr:
        return await to_thread.run_sync(self._fp.readline, limiter=self._limiter)

    async def readlines(self) -> list[AnyStr]:
        return await to_thread.run_sync(self._fp.readlines, limiter=self._limiter)

    async def readinto(self: 'AsyncFile[bytes]', b: WriteableBuffer) -> int:
        return await to_thread.run_sync(self._fp.readinto, b, limiter=self._limiter)

    async def readinto1(self: 'AsyncFile[bytes]', b: WriteableBuffer) -> int:
        return await to_thread.run_sync(self._fp.readinto1, b, limiter=self._limiter)

    @overload
    async def write(self: 'AsyncFile[bytes]', b: ReadableBuffer) -> int: ...
    @overload
    async def write(self: 'AsyncFile[str]', b: str) -> int: ...
    async def write(self, b: ReadableBuffer | str) -> int:
        return await to_thread.run_sync(self._fp.write, b, limiter=self._limiter)

    @overload
    async def writelines(self: 'AsyncFile[bytes]', lines: Iterable[ReadableBuffer]) -> None: ...
    @overload
    async def writelines(self: 'AsyncFile[str]', lines: Iterable[str]) -> None: ...
    async def writelines(self, lines: Iterable[ReadableBuffer] | Iterable[str]) -> None:
        return await to_thread.run_sync(self._fp.writelines, lines, limiter=self._limiter)

    async def truncate(self, size: int | None = None) -> int:
        return await to_thread.run_sync(self._fp.truncate, size, limiter=self._limiter)

    async def seek(self, offset: int, whence: int | None = os.SEEK_SET) -> int:
        return await to_thread.run_sync(self._fp.seek, offset, whence, limiter=self._limiter)

    async def tell(self) -> int:
        return await to_thread.run_sync(self._fp.tell, limiter=self._limiter)

    async def flush(self) -> None:
        return await to_thread.run_sync(self._fp.flush, limiter=self._limiter)


@overload
async def aopen_file(
    file: _core.PathLike | int,
    mode: OpenBinaryMode,
    buffering: int = ...,
    encoding: str | None = ...,
    errors: str | None = ...,
    newline: str | None = ...,
    closefd: bool = ...,
    opener: Callable[[str, int], int] | None = ...,
    *,
    limiter: CapacityLimiter | None = ...,
) -> AsyncFile[bytes]: ...
@overload
async def aopen_file(
    file: _core.PathLike | int,
    mode: OpenTextMode = ...,
    buffering: int = ...,
    encoding: str | None = ...,
    errors: str | None = ...,
    newline: str | None = ...,
    closefd: bool = ...,
    opener: Callable[[str, int], int] | None = ...,
    *,
    limiter: CapacityLimiter | None = ...,
) -> AsyncFile[str]: ...
async def aopen_file(
    file: _core.PathLike | int,
    mode: str = 'r',
    buffering: int = -1,
    encoding: str | None = None,
    errors: str | None = None,
    newline: str | None = None,
    closefd: bool = True,
    opener: Callable[[str, int], int] | None = None,
    *,
    limiter: CapacityLimiter | None = None,
) -> AsyncFile[Any]:
    """Open a file asynchronously."""
    fp = await to_thread.run_sync(
        open, file, mode, buffering, encoding, errors, newline, closefd, opener, limiter=limiter
    )
    return AsyncFile(fp, limiter=limiter)


def wrap_file[AnyStr: (bytes, str)](file: IO[AnyStr], *, limiter: CapacityLimiter | None = None) -> AsyncFile[AnyStr]:
    """Wrap an existing file as an asynchronous file."""
    return AsyncFile(file, limiter=limiter)


@dataclass(eq=False)
class _PathIterator(AsyncIterator[T]):
    iterator: Iterator[_core.PathLike]
    limiter: CapacityLimiter | None
    path_cls: type[T]

    async def __anext__(self) -> T:
        nextval = await to_thread.run_sync(next, self.iterator, None, abandon_on_cancel=True, limiter=self.limiter)
        if nextval is None:
            raise StopAsyncIteration from None
        return self.path_cls(nextval, limiter=self.limiter)


class AsyncPath:
    __slots__ = ('__weakref__', '_limiter', '_path')

    __weakref__: Any

    def __init__(self, *args: _core.PathLike, limiter: CapacityLimiter | None = None) -> None:
        if (limiter is not None) and (not isinstance(limiter, CapacityLimiter)):
            msg = f'limiter must be a CapacityLimiter or None, not {limiter.__class__.__name__}'
            raise TypeError(msg)
        self._path: Final[_core.Path] = _core.Path(*args)
        self._limiter = limiter

    def __fspath__(self) -> str:
        return self._path.__fspath__()

    def __str__(self) -> str:
        return self._path.__str__()

    # def __repr__(self) -> str:
    #    return f'{self.__class__.__name__}({self.as_posix()!r})'

    def __bytes__(self) -> bytes:
        return self._path.__bytes__()

    def __hash__(self) -> int:
        return self._path.__hash__()

    def __eq__(self, other: object) -> bool:
        target = other._path if isinstance(other, AsyncPath) else other
        return self._path.__eq__(target)

    def __lt__(self, other: _core.PathLike) -> bool:
        target = other._path if isinstance(other, AsyncPath) else other
        return self._path.__lt__(target)

    def __le__(self, other: _core.PathLike) -> bool:
        target = other._path if isinstance(other, AsyncPath) else other
        return self._path.__le__(target)

    def __gt__(self, other: _core.PathLike) -> bool:
        target = other._path if isinstance(other, AsyncPath) else other
        return self._path.__gt__(target)

    def __ge__(self, other: _core.PathLike) -> bool:
        target = other._path if isinstance(other, AsyncPath) else other
        return self._path.__ge__(target)

    def __truediv__(self, other: _core.PathLike) -> Self:
        return type(self)(self._path / other, limiter=self._limiter)

    def __rtruediv__(self, other: _core.PathLike) -> Self:
        return type(self)(other, limiter=self._limiter) / self

    @property
    def limiter(self) -> CapacityLimiter | None:
        """The capacity limiter used by this path, if not the global limiter."""
        return self._limiter

    @property
    def drive(self) -> str:
        return self._path.drive

    @property
    def anchor(self) -> str:
        return self._path.anchor

    @property
    def parent(self) -> Self:
        return type(self)(self._path.parent, limiter=self._limiter)

    @property
    def name(self) -> str:
        return self._path.name

    @property
    def suffix(self) -> str:
        return self._path.suffix

    @property
    def stem(self) -> str:
        return self._path.stem

    # @property
    # def parts(self) -> tuple[str, ...]:
    #    return self._path.parts

    # @property
    # def root(self) -> str:
    #    return self._path.root

    # @property
    # def parents(self) -> Sequence[Self]:
    #    return tuple(type(self)(p, limiter=self._limiter) for p in self._path.parents)

    # @property
    # def suffixes(self) -> list[str]:
    #    return self._path.suffixes

    # def with_stem(self, stem: str) -> Self:
    #    return type(self)(self._path.with_stem(stem), limiter=self._limiter)

    # async def owner(self) -> str:
    #    return await to_thread.run_sync(self._path.owner, abandon_on_cancel=True, limiter=self._limiter)

    # async def touch(self, mode: int = 0o666, exist_ok: bool = True) -> None:
    #    await to_thread.run_sync(self._path.touch, mode, exist_ok, limiter=self._limiter)

    # async def group(self) -> str:
    #    return await to_thread.run_sync(self._path.group, abandon_on_cancel=True, limiter=self._limiter)

    # async def is_block_device(self) -> bool:
    #    return await to_thread.run_sync(self._path.is_block_device, abandon_on_cancel=True, limiter=self._limiter)

    # async def is_char_device(self) -> bool:
    #    return await to_thread.run_sync(self._path.is_char_device, abandon_on_cancel=True, limiter=self._limiter)

    # async def is_fifo(self) -> bool:
    #    return await to_thread.run_sync(self._path.is_fifo, abandon_on_cancel=True, limiter=self._limiter)

    # async def is_socket(self) -> bool:
    #    return await to_thread.run_sync(self._path.is_socket, abandon_on_cancel=True, limiter=self._limiter)

    # async def lchmod(self, mode: int) -> None:
    #    await to_thread.run_sync(self._path.lchmod, mode, limiter=self._limiter)

    # async def lstat(self) -> os.stat_result:
    #    return await to_thread.run_sync(self._path.lstat, abandon_on_cancel=True, limiter=self._limiter)

    # @overload
    # async def open(
    #    self,
    #    mode: OpenBinaryMode,
    #    buffering: int = ...,
    #    encoding: str | None = ...,
    #    errors: str | None = ...,
    #    newline: str | None = ...,
    # ) -> AsyncFile[bytes]: ...
    # @overload
    # async def open(
    #    self,
    #    mode: OpenTextMode = ...,
    #    buffering: int = ...,
    #    encoding: str | None = ...,
    #    errors: str | None = ...,
    #    newline: str | None = ...,
    # ) -> AsyncFile[str]: ...
    # async def open(
    #    self,
    #    mode: str = 'r',
    #    buffering: int = -1,
    #    encoding: str | None = None,
    #    errors: str | None = None,
    #    newline: str | None = None,
    # ) -> AsyncFile[Any]:
    #    fp = await to_thread.run_sync(
    #        self._path.open,
    #        mode,
    #        buffering,
    #        encoding,
    #        errors,
    #        newline,
    #        limiter=self._limiter,
    #    )
    #    return AsyncFile(fp, limiter=self._limiter)

    # async def symlink_to(
    #    self,
    #    target: str | bytes | PathLike[str] | PathLike[bytes],
    #    target_is_directory: bool = False,
    # ) -> None:
    #    if isinstance(target, Path):
    #        target = target._path

    #    await to_thread.run_sync(self._path.symlink_to, target, target_is_directory, limiter=self._limiter)

    # async def walk(
    #    self,
    #    top_down: bool = True,
    #    on_error: Callable[[OSError], object] | None = None,
    #    follow_symlinks: bool = False,
    # ) -> AsyncIterator[tuple[Self, list[str], list[str]]]:
    #    def get_next_value() -> tuple[_core.Path, list[str], list[str]] | None:
    #        try:
    #            return next(gen)
    #        except StopIteration:
    #            return None

    #    gen = self._path.walk(top_down, on_error, follow_symlinks)
    #    while True:
    #        value = await to_thread.run_sync(get_next_value, limiter=self._limiter)
    #        if value is None:
    #            return

    #        root, dirs, paths = value
    #        yield type(self)(root, limiter=self._limiter), dirs, paths

    # async def unlink(self, missing_ok: bool = False) -> None:
    #    try:
    #        await to_thread.run_sync(self._path.unlink, limiter=self._limiter)
    #    except FileNotFoundError:
    #        if not missing_ok:
    #            raise

    @classmethod
    async def home(cls, *, limiter: CapacityLimiter | None = None) -> Self:
        home_path = await to_thread.run_sync(_core.Path.home, limiter=limiter)
        return cls(home_path, limiter=limiter)

    @classmethod
    async def cwd(cls, *, limiter: CapacityLimiter | None = None) -> Self:
        path = await to_thread.run_sync(_core.Path.cwd, limiter=limiter)
        return cls(path, limiter=limiter)

    def joinpath(self, *args: _core.PathLike) -> Self:
        return type(self)(self._path.joinpath(*args), limiter=self._limiter)

    def glob(self, pattern: str) -> AsyncIterator[Self]:
        gen = self._path.glob(pattern)
        return _PathIterator(gen, self._limiter, type(self))

    def relative_to(self, *other: _core.PathLike) -> Self:
        others = [_core.Path(other) for other in other]
        return type(self)(self._path.relative_to(*others), limiter=self._limiter)

    def is_absolute(self) -> bool:
        return self._path.is_absolute()

    def is_reserved(self) -> bool:
        return self._path.is_reserved()

    def rglob(self, pattern: str) -> AsyncIterator[Self]:
        gen = self._path.rglob(pattern)
        return _PathIterator(gen, self._limiter, type(self))

    def with_name(self, name: str) -> Self:
        return type(self)(self._path.with_name(name), limiter=self._limiter)

    def with_suffix(self, suffix: str) -> Self:
        return type(self)(self._path.with_suffix(suffix), limiter=self._limiter)

    def with_segments(self, *pathsegments: _core.PathLike) -> Self:
        return type(self)(*pathsegments, limiter=self._limiter)

    def is_relative_to(self, other: _core.PathLike) -> bool:
        try:
            self.relative_to(other)
        except ValueError:
            return False
        else:
            return True

    async def absolute(self) -> Self:
        path = await to_thread.run_sync(self._path.absolute, limiter=self._limiter)
        return type(self)(path, limiter=self._limiter)

    async def chmod(self, mode: int, *, follow_symlinks: bool = True) -> None:
        func = partial(os.chmod, follow_symlinks=follow_symlinks)
        return await to_thread.run_sync(func, self._path, mode, limiter=self._limiter)

    async def exists(self) -> bool:
        return await to_thread.run_sync(self._path.exists, abandon_on_cancel=True, limiter=self._limiter)

    async def expanduser(self) -> Self:
        return type(self)(
            await to_thread.run_sync(self._path.expanduser, abandon_on_cancel=True, limiter=self._limiter),
            limiter=self._limiter,
        )

    async def hardlink_to(self, target: str | bytes | PathLike[str] | PathLike[bytes]) -> None:
        if isinstance(target, AsyncPath):
            target = target._path
        await to_thread.run_sync(os.link, target, self, limiter=self._limiter)

    async def is_dir(self) -> bool:
        return await to_thread.run_sync(self._path.is_dir, abandon_on_cancel=True, limiter=self._limiter)

    async def is_file(self) -> bool:
        return await to_thread.run_sync(self._path.is_file, abandon_on_cancel=True, limiter=self._limiter)

    async def is_mount(self) -> bool:
        return await to_thread.run_sync(os.path.ismount, self._path, abandon_on_cancel=True, limiter=self._limiter)

    async def is_symlink(self) -> bool:
        return await to_thread.run_sync(self._path.is_symlink, abandon_on_cancel=True, limiter=self._limiter)

    async def iterdir(self) -> AsyncIterator[Self]:
        gen = await to_thread.run_sync(self._path.iterdir, abandon_on_cancel=True, limiter=self._limiter)
        async for path in _PathIterator(gen, self._limiter, type(self)):
            yield path

    async def mkdir(self, mode: int = 0o777, parents: bool = False, exist_ok: bool = False) -> None:
        await to_thread.run_sync(self._path.mkdir, mode, parents, exist_ok, limiter=self._limiter)

    async def read_bytes(self) -> bytes:
        return await to_thread.run_sync(self._path.read_bytes, limiter=self._limiter)

    async def read_text(
        self,
        encoding: str = 'utf-8',
        errors: _core.TextEncodingErrorPolicy = 'strict',
        newline: _core.LineEnding | None = None,
    ) -> str:
        return await to_thread.run_sync(self._path.read_text, encoding, errors, newline, limiter=self._limiter)

    async def readlink(self) -> Self:
        target = await to_thread.run_sync(os.readlink, self._path, limiter=self._limiter)
        return type(self)(target, limiter=self._limiter)

    async def rename(self, target: str | _core.PathLike) -> Self:
        if isinstance(target, AsyncPath):
            target = target._path
        await to_thread.run_sync(self._path.rename, target, limiter=self._limiter)
        return type(self)(target, limiter=self._limiter)

    async def replace(self, target: str | _core.PathLike) -> Self:
        if isinstance(target, AsyncPath):
            target = target._path
        await to_thread.run_sync(self._path.replace, target, limiter=self._limiter)
        return type(self)(target, limiter=self._limiter)

    async def resolve(self, strict: bool = False) -> Self:
        func = partial(self._path.resolve, strict=strict)
        return type(self)(
            await to_thread.run_sync(func, abandon_on_cancel=True, limiter=self._limiter),
            limiter=self._limiter,
        )

    async def rmdir(self) -> None:
        await to_thread.run_sync(self._path.rmdir, limiter=self._limiter)

    async def samefile(self, other_path: _core.PathLike) -> bool:
        if isinstance(other_path, AsyncPath):
            other_path = other_path._path
        return await to_thread.run_sync(self._path.samefile, other_path, abandon_on_cancel=True, limiter=self._limiter)

    async def stat(self, *, follow_symlinks: bool = True) -> os.stat_result:
        func = partial(os.stat, follow_symlinks=follow_symlinks)
        return await to_thread.run_sync(func, self._path, abandon_on_cancel=True, limiter=self._limiter)

    async def write_bytes(self, data: ReadableBuffer) -> int:
        return await to_thread.run_sync(self._path.write_bytes, data, limiter=self._limiter)

    async def write_text(
        self,
        data: str,
        encoding: str = 'utf-8',
        errors: _core.TextEncodingErrorPolicy = 'strict',
        newline: _core.LineEnding | None = None,
    ) -> int:
        return await to_thread.run_sync(self._path.write_text, data, encoding, errors, newline, limiter=self._limiter)


PathLike.register(AsyncPath)
