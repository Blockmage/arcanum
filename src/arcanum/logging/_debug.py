from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from structlog.stdlib import BoundLogger


def _get_logger(name: str, /) -> Any:
    import logging

    import structlog

    logging.basicConfig(level='DEBUG', force=True)
    return structlog.stdlib.get_logger(name)


def _format_duration(seconds: float) -> str:
    if seconds >= 1:
        return f'{seconds:.3f}s'
    if seconds >= 0.001:
        return f'{seconds * 1000:.3f}ms'
    if seconds >= 0.000001:
        return f'{seconds * 1000000:.3f}µs'
    return f'{seconds * 1000000000:.3f}ns'


def _collect_metadata(fn: Callable[..., Any]) -> dict[str, Any]:
    import inspect

    debug_info: dict[str, Any] = {'function': fn.__name__, 'qualname': fn.__qualname__}
    try:
        debug_info.update({'module': fn.__module__, 'annotations': fn.__annotations__})
        if (frame := inspect.currentframe()) and (back := frame.f_back) and (back2 := back.f_back):
            debug_info.update(
                {
                    'caller_name': back2.f_code.co_name,
                    'caller_file': back2.f_code.co_filename,
                    'caller_line': back2.f_lineno,
                }
            )
    except Exception as exc:
        debug_info['metadata_error'] = str(exc)
    return debug_info


def _collect_result_info(result: Any, fn: Callable[..., Any]) -> dict[str, Any]:
    from contextlib import suppress

    debug_info = {}
    with suppress(Exception):
        res_type, exp_type = type(result), fn.__annotations__.get('return')
        debug_info.update(
            {
                'result': result,
                'result_type': res_type.__name__,
                'expected_type': exp_type,
                'result_matches_expected': bool(exp_type in res_type.mro()),
                'result_type_mro': [t.__name__ for t in res_type.mro()],
            }
        )

    return debug_info


def _collect_error_info(exc: Exception) -> dict[str, Any]:
    import traceback

    return {'error': str(exc), 'error_type': type(exc).__name__, 'traceback': traceback.format_exc()}


async def adebug_log(
    msg: str = 'debugging event',
    *,
    enabled: bool = False,
    logger_name: str = 'arcanum.debug',
    **kwargs: Any,
) -> None:
    """Log a debugging event asynchronously.

    Parameters
    ----------
    msg : str, optional
        Message to be logged for the event.
    enabled : bool, optional
        If not `True` the function returns immediately.
    logger_name : str, optional
        Optional name of a logger to be used for logging.
    """

    if not enabled:
        return
    import inspect

    if (obj := (kwargs or {}).get('obj')) is not None:
        kwargs['obj_type'] = type(obj)
    if (frame := inspect.currentframe()) and (back := frame.f_back) and (code := back.f_code):
        kwargs.update(
            {
                'function_name': code.co_name,
                'file_name': code.co_filename,
                'line_no': code.co_firstlineno,
            }
        )

    _logger: BoundLogger = _get_logger(logger_name)
    await _logger.adebug(msg, **kwargs)


def debug_log(
    msg: str = 'debugging event',
    *,
    enabled: bool = False,
    logger_name: str = 'arcanum.debug',
    **kwargs: Any,
) -> None:
    """Log a debugging event synchronously.

    Parameters
    ----------
    msg : str, optional
        Message to be logged for the event.
    enabled : bool, optional
        If not `True` the function returns immediately.
    logger_name : str, optional
        Optional name of a logger to be used for logging.
    """

    if not enabled:
        return
    import inspect

    if (obj := (kwargs or {}).get('obj')) is not None:
        kwargs['obj_type'] = type(obj)
    if (frame := inspect.currentframe()) and (back := frame.f_back) and (code := back.f_code):
        kwargs.update(
            {
                'function_name': code.co_name,
                'file_name': code.co_filename,
                'line_no': code.co_firstlineno,
            }
        )

    _logger: BoundLogger = _get_logger(logger_name)
    _logger.debug(msg, **kwargs)


def awith_logging[T, **P](
    *,
    enabled: bool = False,
    logger_name: str = 'arcanum.debug',
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Return a type-safe decorator to add logging to an asynchronous function.

    Parameters
    ----------
    enabled : bool
        If `False`, return immediately without doing anything. By default, `False`.
    logger_name : str
        Name of a logger to be used, by default `'arcanum.debug'`.
    """

    def decorator(fn: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        async def inner(*args: P.args, **kwargs: P.kwargs) -> T:
            if not enabled:
                return await fn(*args, **kwargs)

            fn_start, debug_info = None, {}
            import time

            debug_start = time.perf_counter()
            logger = _get_logger(logger_name)
            debug_info.update({'args': list(args), 'kwargs': {**kwargs}, **_collect_metadata(fn)})

            try:
                fn_start = time.perf_counter()
                result = await fn(*args, **kwargs)
                fn_end = time.perf_counter()

                debug_info.update(
                    {
                        'debug_setup_time': _format_duration(fn_start - debug_start),
                        'execution_time': _format_duration(fn_end - fn_start),
                        **_collect_result_info(result, fn),
                    }
                )

            except Exception as exc:
                fn_end = time.perf_counter()
                execution_time = _format_duration(fn_end - fn_start) if fn_start else None
                debug_info.update({'execution_time': execution_time, **_collect_error_info(exc)})
                raise

            debug_end = time.perf_counter()
            debug_info.update(
                {
                    'debug_cleanup_time': _format_duration(debug_end - fn_end),
                    'total_debug_time': _format_duration(debug_end - debug_start),
                    'debug_overhead_ratio': f'{((debug_end - debug_start) / (fn_end - fn_start)):.2f}x',
                }
            )

            await logger.adebug('debugging event', **debug_info)
            return result

        return inner

    return decorator


def with_logging[T, **P](
    *,
    enabled: bool = False,
    logger_name: str = 'arcanum.debug',
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Return a type-safe decorator to add logging to a synchronous function.

    Parameters
    ----------
    enabled : bool
        If `False`, return immediately without doing anything. By default, `False`.
    logger_name : str
        Name of a logger to be used, by default `'arcanum.debug'`.
    """

    def decorator(fn: Callable[P, T]) -> Callable[P, T]:
        def inner(*args: P.args, **kwargs: P.kwargs) -> T:
            if not enabled:
                return fn(*args, **kwargs)

            fn_start, debug_info = None, {}
            import time

            debug_start = time.perf_counter()
            logger = _get_logger(logger_name)
            debug_info.update({'args': list(args), 'kwargs': {**kwargs}, **_collect_metadata(fn)})

            try:
                fn_start = time.perf_counter()
                result = fn(*args, **kwargs)
                fn_end = time.perf_counter()

                debug_info.update(
                    {
                        'debug_setup_time': _format_duration(fn_start - debug_start),
                        'execution_time': _format_duration(fn_end - fn_start),
                        **_collect_result_info(result, fn),
                    }
                )

            except Exception as exc:
                fn_end = time.perf_counter()
                execution_time = _format_duration(fn_end - fn_start) if fn_start else None
                debug_info.update({'execution_time': execution_time, **_collect_error_info(exc)})
                raise

            debug_end = time.perf_counter()
            debug_info.update(
                {
                    'total_debug_time': _format_duration(debug_end - debug_start),
                    'debug_cleanup_time': _format_duration(debug_end - fn_end),
                    'debug_overhead_ratio': f'{((debug_end - debug_start) / (fn_end - fn_start)):.2f}x',
                }
            )

            logger.debug('debugging event', **debug_info)
            return result

        return inner

    return decorator
