from __future__ import annotations

import errno
from enum import Enum
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from ._core import PathLike

__all__ = (
    'FsError',
    'FsErrorCode',
    'FsErrorCodeStr',
)

FsErrorCodeStr = Literal[
    'CUSTOM',
    'UNKNOWN',
    'PERMISSION_DENIED',
    'READ_ONLY',
    'NOT_FOUND',
    'EXISTS',
    'NOT_A_DIRECTORY',
    'IS_A_DIRECTORY',
    'DIR_NOT_EMPTY',
    'NOT_CONNECTED',
    'TIMED_OUT',
    'CONNECTION_REFUSED',
    'NETWORK_DOWN',
    'LOOP',
    'BUSY',
    'IO_ERROR',
    'FILENAME_TOO_LONG',
    'QUOTA_EXCEEDED',
    'NO_SPACE',
]


class FsErrorCode(Enum):
    """Enumeration of local and network filesystem error conditions."""

    CUSTOM = ''  # Placeholder for custom error messages
    UNKNOWN = 'Unknown error encountered'  # Generic/unknown (default)

    # fmt: off
    # Access and Permissions
    PERMISSION_DENIED = 'Permission denied'  # EACCES / EPERM
    READ_ONLY = 'Path is read-only'          # EROFS

    # Existence and State
    NOT_FOUND = 'Not found'                 # ENOENT
    EXISTS = 'Path exists'                  # EEXIST
    NOT_A_DIRECTORY = 'Not a directory'     # ENOTDIR
    IS_A_DIRECTORY = 'Path is a directory'  # EISDIR
    DIR_NOT_EMPTY = 'Directory not empty'   # ENOTEMPTY

    # Resource Constraints
    NO_SPACE = 'No space remaining'          # ENOSPC
    QUOTA_EXCEEDED = 'Quota exceeded'        # EDQUOT
    TOO_MANY_LINKS = 'Too many hard links'   # EMLINK
    FILENAME_TOO_LONG = 'Filename too long'  # ENAMETOOLONG

    # System and IO
    IO_ERROR = 'Input/output error'     # EIO
    BUSY = 'Resource busy'              # EBUSY
    STALE_HANDLE = 'Stale file handle'  # ESTALE (Common in NFS)
    LOOP = 'Symlink loop'               # ELOOP

    # Network / Distributed Specific
    NETWORK_DOWN = 'Network down'                   # ENETDOWN
    HOST_UNREACHABLE = 'Host unreachable'           # EHOSTUNREACH
    CONNECTION_REFUSED = 'Connection refused'       # ECONNREFUSED
    TIMED_OUT = 'Operation timed out'               # ETIMEDOUT
    LOCK_RECLAIM_FAILED = 'Failed to reclaim lock'  # ENOLCK (NFS locking issues)
    NOT_CONNECTED = 'Not connected'                 # ENOTCONN
    # fmt: on

    @classmethod
    def format_msg(cls, path: str, err: FsErrorCode | FsErrorCodeStr | int) -> str:
        """Create a formatted error message from a path and message type."""
        return (
            f'{cls.from_err_no(err)}: {path}'
            if isinstance(err, int)
            else f'{cls.from_err_str(err)}: {path}'
            if isinstance(err, str)
            else f'{err.value}: {path}'
            if isinstance(err, FsErrorCode)
            else f'{cls.UNKNOWN}: {path}'
        )

    @classmethod
    def from_err_str(cls, err: FsErrorCodeStr) -> FsErrorCode:
        """Get `FsErrorCode` from string error names."""
        return {
            'CUSTOM': cls.CUSTOM,
            'UNKNOWN': cls.UNKNOWN,
            'PERMISSION_DENIED': cls.PERMISSION_DENIED,
            'READ_ONLY': cls.READ_ONLY,
            'NOT_FOUND': cls.NOT_FOUND,
            'EXISTS': cls.EXISTS,
            'NOT_A_DIRECTORY': cls.NOT_A_DIRECTORY,
            'IS_A_DIRECTORY': cls.IS_A_DIRECTORY,
            'NOT_EMPTY': cls.DIR_NOT_EMPTY,
            'NO_SPACE': cls.NO_SPACE,
            'QUOTA_EXCEEDED': cls.QUOTA_EXCEEDED,
            'TOO_MANY_LINKS': cls.TOO_MANY_LINKS,
            'FILENAME_TOO_LONG': cls.FILENAME_TOO_LONG,
            'IO_ERROR': cls.IO_ERROR,
            'BUSY': cls.BUSY,
            'STALE_HANDLE': cls.STALE_HANDLE,
            'LOOP': cls.LOOP,
            'NETWORK_DOWN': cls.NETWORK_DOWN,
            'HOST_UNREACHABLE': cls.HOST_UNREACHABLE,
            'CONNECTION_REFUSED': cls.CONNECTION_REFUSED,
            'TIMED_OUT': cls.TIMED_OUT,
            'LOCK_RECLAIM_FAILED': cls.LOCK_RECLAIM_FAILED,
            'NOT_CONNECTED': cls.NOT_CONNECTED,
        }.get(err, cls.UNKNOWN)

    @classmethod
    def from_err_no(cls, err: int) -> FsErrorCode:
        """Get `FsErrorCode` from standard OS `errno`."""
        return {
            errno.EACCES: cls.PERMISSION_DENIED,
            errno.EPERM: cls.PERMISSION_DENIED,
            errno.EROFS: cls.READ_ONLY,
            errno.ENOENT: cls.NOT_FOUND,
            errno.EEXIST: cls.EXISTS,
            errno.ENOTDIR: cls.NOT_A_DIRECTORY,
            errno.EISDIR: cls.IS_A_DIRECTORY,
            errno.ENOTEMPTY: cls.DIR_NOT_EMPTY,
            errno.ENOSPC: cls.NO_SPACE,
            errno.EDQUOT: cls.QUOTA_EXCEEDED,
            errno.EMLINK: cls.TOO_MANY_LINKS,
            errno.ENAMETOOLONG: cls.FILENAME_TOO_LONG,
            errno.EIO: cls.IO_ERROR,
            errno.EBUSY: cls.BUSY,
            errno.ESTALE: cls.STALE_HANDLE,
            errno.ELOOP: cls.LOOP,
            errno.ENETDOWN: cls.NETWORK_DOWN,
            errno.EHOSTUNREACH: cls.HOST_UNREACHABLE,
            errno.ECONNREFUSED: cls.CONNECTION_REFUSED,
            errno.ETIMEDOUT: cls.TIMED_OUT,
            errno.ENOLCK: cls.LOCK_RECLAIM_FAILED,
            errno.ENOTCONN: cls.NOT_CONNECTED,
        }.get(err, cls.UNKNOWN)


class FsError(OSError):
    """Exception raised for filesystem-related errors."""

    error_code: FsErrorCode

    @staticmethod
    def _decode_path(path: PathLike) -> str:
        try:
            if isinstance(path, bytes):
                path = path.decode(encoding='utf-8')
        except Exception:
            path = '__failed_to_decode__'
        return str(path)

    def __init__(
        self,
        path: PathLike,
        error: FsErrorCode | FsErrorCodeStr | int = FsErrorCode.UNKNOWN,
        *,
        msg: str | None = None,
    ) -> None:
        """Initialize `FsError`.

        Parameters
        ----------
        path : PathLike
            Path with which the error was encountered.
        error : FsErrorCode | FsErrorCodeStr | int, optional
            Error code number, error name string, or a member of the `FsErrorCode` enumeration.
        msg : str | None, optional
            If provided, `error` is ignored and `error_code` on the class is set to `FsErrorCode.CUSTOM`.
            The full error message will then be formatted as `{msg}: {path}`.
        """
        path_str = self._decode_path(path)
        if isinstance(error, int):
            self.error_code = FsErrorCode.from_err_no(error)
        elif isinstance(error, str):
            self.error_code = FsErrorCode.from_err_str(error)
        else:
            self.error_code = error
        if msg is not None:
            self.error_code = FsErrorCode.CUSTOM
            message = f'{msg}: {path_str}'
        else:
            message = FsErrorCode.format_msg(path_str, self.error_code)
        super().__init__(message)
