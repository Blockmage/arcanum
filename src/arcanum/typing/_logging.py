from types import TracebackType
from typing import Any, Protocol

# ruff: noqa: N815,N802

type ExcInfoT = (
    bool
    | tuple[type[BaseException], BaseException, TracebackType | None]
    | tuple[None, None, None]
    | BaseException
    | None
)


class LogRecordT(Protocol):
    args: Any
    asctime: str
    created: float
    exc_info: ExcInfoT | None
    filename: str
    funcName: str
    levelname: str
    levelno: int
    lineno: int | None
    message: str
    module: str
    msecs: int
    msg: Any | None
    name: str
    pathname: str | None
    process: int | None
    processName: str | None
    relativeCreated: int
    stack_info: Any | None
    thread: int | None
    threadName: str | None
    taskName: str | None

    def getMessage(self) -> str: ...
