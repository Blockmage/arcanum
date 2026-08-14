import logging
import logging.config
import os
import sys
import traceback
from collections.abc import Callable, Iterator
from io import TextIOWrapper
from logging.handlers import RotatingFileHandler as _RotatingFileHandler
from traceback import FrameSummary, format_exception
from types import FrameType
from typing import Any

import anyio
import structlog
from structlog.dev import RichTracebackFormatter
from structlog.stdlib import get_logger
from structlog.typing import EventDict, Processor

from arcanum.stdlib.path import Path

_here: Path = Path(__file__).resolve().parent

_logger_name: str = 'Arcanum'

if (_log_dir_from_env := os.getenv('LOG_DIR', '')).strip():
    _log_dir: Path = Path(_log_dir_from_env)
elif _log_dir_from_env := os.getenv('WORKSPACE_ROOT', '').strip():
    _log_dir: Path = Path(_log_dir_from_env) / '_meta' / 'log'
else:
    _log_dir: Path = _here.parent.parent / '_meta' / 'log'


class RotatingFileHandler(_RotatingFileHandler):
    def _open(self) -> TextIOWrapper:
        _path = Path(self.baseFilename).resolve().parent
        _path.mkdir(exist_ok=True, parents=True)
        return super()._open()


def _is_same_frame(frame: FrameType, target: FrameSummary) -> bool:
    return frame.f_code.co_filename == target.filename and frame.f_code.co_name == target.name


def _walk_frames(
    predicate: Callable[[FrameType, FrameSummary], bool],
    target: FrameSummary,
    *,
    start_frame: FrameType | None = None,
) -> Iterator[FrameType]:
    try:
        current_frame = start_frame if start_frame is not None else sys._getframe(1)
        while current_frame is not None:
            if not predicate(current_frame, target):
                yield current_frame
            current_frame = current_frame.f_back
    except Exception:
        return


def _get_frame_locals(target_frame: FrameSummary) -> dict[str, Any]:
    result = {}
    try:
        if matching_frame := next(
            (frame for frame in _walk_frames(lambda f, t: not _is_same_frame(f, t), target_frame)),
            None,
        ):
            result = matching_frame.f_locals
    except Exception:
        return result
    else:
        return result


def _format_exception_chain(exc: BaseException | None) -> dict[str, Any]:
    return (
        {
            'message': str(exc),
            'exc_args': exc.args,
            'exc_type': type(exc).__name__,
            'stack_trace': [
                line.strip().replace('\n', ' ')
                for line in (format_exception(exc.__class__, exc, exc.__traceback__))
                if line and line.strip()
            ],
        }
        if exc is not None
        else {}
    )


def _add_exception_chain(_: Any, __: Any, event_dict: EventDict) -> EventDict:
    if exc_info := event_dict.get('exc_info'):
        if isinstance(exc_info, BaseException):
            exc = exc_info
        elif isinstance(exc_info, tuple) and len(exc_info) == 3 and exc_info[1]:
            exc = exc_info[1]
        else:
            exc = None
        if not any('exception' in str(k) for k in event_dict):
            event_dict['exception_chain'] = _format_exception_chain(exc)
    return event_dict


def _extract_from_record(_: Any, __: Any, event_dict: EventDict) -> EventDict:
    record = event_dict['_record']
    event_dict['thread_name'] = record.threadName
    event_dict['process_name'] = record.processName
    return event_dict


def _get_pre_chain(time_fmt_str: str = '%Y-%m-%d %H:%M:%S') -> list[Processor]:
    return [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.ExtraAdder(),
        structlog.processors.TimeStamper(fmt=time_fmt_str),
    ]


def _configure_stdlib_logging(time_fmt_str: str = '%Y-%m-%d %H:%M:%S') -> None:
    logging.config.dictConfig(
        {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'plain': {
                    '()': structlog.stdlib.ProcessorFormatter,
                    'foreign_pre_chain': _get_pre_chain(),
                    'processors': [
                        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                        structlog.dev.ConsoleRenderer(colors=False),
                    ],
                },
                'colored': {
                    '()': structlog.stdlib.ProcessorFormatter,
                    'foreign_pre_chain': _get_pre_chain(),
                    'processors': [
                        _extract_from_record,
                        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                        structlog.contextvars.merge_contextvars,
                        structlog.processors.add_log_level,
                        structlog.processors.TimeStamper(fmt=time_fmt_str),
                        structlog.dev.ConsoleRenderer(
                            colors=True,
                            exception_formatter=RichTracebackFormatter(
                                show_locals=False,
                                max_frames=3,
                                width=120,
                            ),
                        ),
                    ],
                },
                'json': {
                    '()': structlog.stdlib.ProcessorFormatter,
                    'foreign_pre_chain': _get_pre_chain(),
                    'processors': [
                        _extract_from_record,
                        _add_exception_chain,
                        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                        structlog.contextvars.merge_contextvars,
                        structlog.processors.add_log_level,
                        structlog.processors.TimeStamper(fmt=time_fmt_str),
                        structlog.processors.JSONRenderer(),
                    ],
                },
            },
            'handlers': {
                'default': {
                    'level': logging.INFO,
                    'class': 'logging.StreamHandler',
                    'formatter': 'colored',
                },
                'file': {
                    'level': logging.INFO,
                    'class': RotatingFileHandler,
                    'filename': _log_dir / 'arcanum.log',
                    'formatter': 'json',
                },
            },
            'loggers': {
                '': {
                    'handlers': ['default', 'file'],
                    'level': logging.INFO,
                    'propagate': True,
                },
            },
        }
    )


def _configure_structlog(time_fmt_str: str = '%Y-%m-%d %H:%M:%S') -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt=time_fmt_str),
            structlog.processors.CallsiteParameterAdder(
                {
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                }
            ),
            _add_exception_chain,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def _handle_exception(exc_type: type[BaseException], exc_value: BaseException, exc_traceback: Any) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger = get_logger()
    exc_info = (exc_type, exc_value, exc_traceback)
    logger.exception('Uncaught exception', exc_info=exc_info)


sys.excepthook = _handle_exception


def configure_logging() -> None:
    _configure_stdlib_logging()
    _configure_structlog()


def _demo_exception_handling() -> None:
    def inner_function(x: Any, y: Any) -> Any:
        current_frame = sys._getframe()
        frame_summary = traceback.FrameSummary(
            current_frame.f_code.co_filename, current_frame.f_lineno, current_frame.f_code.co_name, line=None
        )

        print('=' * 80)
        print(f'         FRAME LOCALS : {current_frame.f_locals}')
        print(f'       FRAME FILENAME : {current_frame.f_code.co_filename}')
        print(f'         FRAME LINENO : {current_frame.f_lineno}')
        print(f'FRAMESUMMARY FILENAME : {frame_summary.filename}')
        print(f'  FRAMESUMMARY LINENO : {frame_summary.lineno}')
        print(f'        IS SAME FRAME : {_is_same_frame(current_frame, frame_summary)}')
        _get_frame_locals(frame_summary)
        print('=' * 80)

        return x / y

    def middle_function() -> Any:
        try:
            return inner_function(10, 0)
        except ZeroDivisionError as e:
            msg = 'Something went wrong in processing'
            raise ValueError(msg) from e

    def outer_function() -> Any:
        try:
            return middle_function()
        except ValueError as e:
            msg = 'Top level error occurred'
            raise RuntimeError(msg) from e

    try:
        outer_function()
    except Exception as e:
        if e.__cause__ and e.__cause__.__cause__:
            _format_exception_chain(e.__cause__.__cause__)
        tb = e.__traceback__
        while tb:
            frame_summary = traceback.extract_tb(tb)[0] if traceback.extract_tb(tb) else None
            if frame_summary:
                _get_frame_locals(frame_summary)

            tb = tb.tb_next

    inner_function(10, 0)


class LoggingMixin:
    def __init__(self, logger_name: str = _logger_name, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._logger_name = logger_name

        if logger_name is _logger_name:
            self._logger_name = f'{logger_name}.{self.__class__.__name__}'

        self._logger = get_logger(self._logger_name)

    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        return self._logger

    def log_step_start(self, step_name: str, **kwargs: Any) -> None:
        self._logger = self._logger.bind(**kwargs)
        self._logger.info('begin workflow step', step=step_name)

    def log_step_complete(self, step_name: str, **kwargs: Any) -> None:
        self._logger.info('complete workflow step', step=step_name, status='SUCCESS')
        self._logger = self._logger.try_unbind(*kwargs.keys())

    def log_step_error(self, step_name: str, exc: Exception, **kwargs: Any) -> None:
        self._logger.exception('failed workflow step', step=step_name, exc_info=exc, status='ERROR', **kwargs)

    def log_step_warning(self, step_name: str, msg: str, **kwargs: Any) -> None:
        self._logger.warning(msg, step=step_name, **kwargs)


async def _demo_async_logging() -> None:
    logger = get_logger(f'{_logger_name}.DemoAsyncLogger')

    await logger.ainfo('This in an async informational message', some_dict={'a': 'value'})
    await logger.awarning('This is an async warning message', some_list=[1, '2', 'three'])
    await logger.aerror('This is an async error message', some_tuple=(1, '2', 'three'))
    await logger.acritical('This is an async critical message', some_set=set({'a', 'b', 'c'}))

    try:
        msg = 'Exception occurred while trying to raise an exception asynchronously'
        raise Exception(msg)  # noqa: TRY002, TRY301
    except Exception as exc:
        await logger.aexception('Exception occurred asynchronously', exc_info=exc)


def _demo_sync_logging() -> None:
    logger = get_logger(f'{_logger_name}.DemoSyncLogger')

    logger.info('This in an informational message', some_dict={'a': 'value'})
    logger.warning('This is a warning message', some_list=[1, '2', 'three'])
    logger.error('This is an error message', some_tuple=(1, '2', 'three'))
    logger.critical('This is a critical message', some_set=set({'a', 'b', 'c'}))

    try:
        msg = 'Exception occurred while trying to raise an exception synchronously'
        raise Exception(msg)  # noqa: TRY002, TRY301
    except Exception as exc:
        logger.exception('Exception occurred', exc_info=exc)


if __name__ == '__main__':
    _demo_sync_logging()
    anyio.run(_demo_async_logging)
    _demo_exception_handling()
