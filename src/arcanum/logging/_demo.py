import sys
import traceback
from collections.abc import Callable, Iterator
from traceback import FrameSummary
from types import FrameType
from typing import Any

import anyio

from ._core import (
    _format_exception_chain,
    _get_cfg_logger_name,
    configure_logging,
    get_logger,
)


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


def _demo_exception_handling() -> None:
    def dummy_inner_function(x: Any, y: Any) -> Any:
        current_frame = sys._getframe()
        frame_summary = traceback.FrameSummary(
            current_frame.f_code.co_filename,
            current_frame.f_lineno,
            current_frame.f_code.co_name,
            line=None,
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
            return dummy_inner_function(10, 0)
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

    dummy_inner_function(10, 0)


async def _demo_async_logging() -> None:
    logger = get_logger(f'{_get_cfg_logger_name()}.DemoAsyncLogger')

    await logger.ainfo('This in an async info message', some_dict={'a': 'value'})
    await logger.awarning('This is an async warning message', some_list=[1, '2', 'three'])
    await logger.aerror('This is an async error message', some_tuple=(1, '2', 'three'))
    await logger.acritical('This is an async critical message', some_set=set({'a', 'b', 'c'}))

    try:
        msg = 'Exception occurred while trying to raise an exception asynchronously'
        raise Exception(msg)  # noqa: TRY002, TRY301
    except Exception as exc:
        await logger.aexception('Exception occurred asynchronously', exc_info=exc)


def _demo_sync_logging() -> None:
    logger = get_logger(f'{_get_cfg_logger_name()}.DemoSyncLogger')

    logger.info('This in an info message', some_dict={'a': 'value'})
    logger.warning('This is a warning message', some_list=[1, '2', 'three'])
    logger.error('This is an error message', some_tuple=(1, '2', 'three'))
    logger.critical('This is a critical message', some_set=set({'a', 'b', 'c'}))

    try:
        msg = 'Exception occurred while trying to raise an exception synchronously'
        raise Exception(msg)  # noqa: TRY002, TRY301
    except Exception as exc:
        logger.exception('Exception occurred', exc_info=exc)


if __name__ == '__main__':
    configure_logging()

    print(f'{("-" * 80)}\n--- SYNC LOGGING DEMO ---\n{("-" * 80)}\n')
    _demo_sync_logging()

    print(f'{("-" * 80)}\n--- ASYNC LOGGING DEMO ---\n{("-" * 80)}\n')
    anyio.run(_demo_async_logging)

    print(f'{("-" * 80)}\n--- EXCEPTION HANDLING DEMO ---\n{("-" * 80)}\n')
    _demo_exception_handling()

    sys.exit(0)
