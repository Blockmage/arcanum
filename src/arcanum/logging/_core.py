import logging
import logging.config
import os
import sys
from io import TextIOWrapper
from logging.handlers import RotatingFileHandler as _RotatingFileHandler
from pathlib import Path
from traceback import format_exception
from typing import Any

import structlog
from structlog import is_configured
from structlog.dev import RichTracebackFormatter
from structlog.stdlib import BoundLogger
from structlog.stdlib import get_logger as _get_logger
from structlog.typing import EventDict, Processor

_here = Path(__file__).resolve().parent

_wsp_root_fallback = _here.parents[2]
if _wsp_root_env := os.getenv('WORKSPACE_ROOT', '').strip():
    try:
        _wsp_root = Path(_wsp_root_env).resolve(strict=True)
    except Exception:
        _wsp_root = _wsp_root_fallback
else:
    _wsp_root = _wsp_root_fallback


# --- Defaults
_LOG_DIR: Path = _wsp_root / '_meta' / 'log'
_LOG_LEVEL: int = logging.INFO
_LOGGER_NAME: str = 'arcanum'


class RotatingFileHandler(_RotatingFileHandler):
    def _open(self) -> TextIOWrapper:
        _path = Path(self.baseFilename).resolve().parent
        _path.mkdir(exist_ok=True, parents=True)
        return super()._open()


class LoggingMixin:
    def __init__(self, logger_name: str = '', *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        if not logger_name.strip():
            logger_name = _get_cfg_logger_name()
        if logger_name is _LOGGER_NAME:
            self._logger_name = f'{logger_name}.{self.__class__.__name__}'
        else:
            self._logger_name = logger_name

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


def _get_cfg_logger_name(*, default: str = _LOGGER_NAME) -> str:
    if env_name := os.getenv('LOGGER_NAME', '').strip():
        return env_name
    return default


def _get_cfg_log_level(*, default: int = _LOG_LEVEL) -> int:
    if env_lvl := os.getenv('LOG_LEVEL', '').strip():
        env_lvl = env_lvl.upper()
        if mapped := {
            'CRITICAL': logging.CRITICAL,
            'CRIT': logging.CRITICAL,
            'FATAL': logging.CRITICAL,
            'ERROR': logging.ERROR,
            'ERR': logging.ERROR,
            'WARNING': logging.WARNING,
            'WARN': logging.WARNING,
            'INFO': logging.INFO,
            'DEBUG': logging.DEBUG,
        }.get(env_lvl):
            return mapped
    return default


def _get_cfg_log_dir(*, default: Path = _LOG_DIR) -> Path:
    if env_dir := os.getenv('LOG_DIR', '').strip():
        try:
            env_path = Path(env_dir).resolve()
            env_path.mkdir(parents=True, exist_ok=True)
        except Exception:
            return _LOG_DIR
        else:
            return env_path
    return default


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
                    'level': _get_cfg_log_level(),
                    'class': 'logging.StreamHandler',
                    'formatter': 'colored',
                },
                'file': {
                    'level': _get_cfg_log_level(),
                    'class': RotatingFileHandler,
                    'filename': _get_cfg_log_dir() / f'{_get_cfg_logger_name()}.log.jsonl',
                    'formatter': 'json',
                },
            },
            'loggers': {
                '': {
                    'handlers': ['default', 'file'],
                    'level': _get_cfg_log_level(),
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


def get_logger(name: str = '') -> BoundLogger:
    if not is_configured():
        configure_logging()
    return _get_logger(name)
