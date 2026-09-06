from __future__ import annotations

import inspect
import re
import time
from typing import TYPE_CHECKING, Any
from unittest import mock

import pytest

from arcanum.logging import (
    adebug_log,
    awith_logging,
    debug_log,
    with_logging,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Coroutine

    from structlog.testing import LogCapture


class TestWrapWithLogging:
    def test_returns_original_function_result_when_disabled(
        self,
        sample_synchronous_function: tuple[Callable[..., Any], Callable[..., Any]],
    ) -> None:
        """Test that disabled wrapper returns the original function without changes."""

        _func1, _func2 = sample_synchronous_function
        wrapped = with_logging(enabled=False)(_func1)

        result = wrapped(5, 7)

        assert result == 12

    def test_returns_original_function_result_when_enabled(
        self,
        sample_synchronous_function: tuple[Callable[..., Any], Callable[..., Any]],
        log_output: LogCapture,
    ) -> None:
        """Test that enabled wrapper returns the original function result while logging."""

        _func1, _func2 = sample_synchronous_function
        wrapped = with_logging(enabled=True)(_func1)

        result = wrapped(5, 7)

        assert result == 12
        assert len(log_output.entries) == 1
        assert log_output.entries[0]['event'] == 'debugging event'

    def test_logging_captures_result_metadata(
        self,
        sample_synchronous_function: tuple[Callable[..., Any], Callable[..., Any]],
        log_output: LogCapture,
    ) -> None:
        """Test that logging captures result metadata correctly."""

        _func1, _func2 = sample_synchronous_function

        def typed_function(a: int, b: int) -> int:
            return a + b

        wrapped = with_logging(enabled=True)(typed_function)

        result = wrapped(5, 7)

        assert result == 12

        assert log_output.entries[0]['result'] == 12
        assert log_output.entries[0]['result_type'] == 'int'
        assert log_output.entries[0]['expected_type'] == 'int'

        assert 'result_matches_expected' in log_output.entries[0]

    def test_logging_captures_args_kwargs(
        self,
        sample_synchronous_function: tuple[Callable[..., Any], Callable[..., Any]],
        log_output: LogCapture,
    ) -> None:
        """Test that logging captures function arguments correctly."""

        _func1, _func2 = sample_synchronous_function
        wrapped = with_logging(enabled=True)(_func1)

        wrapped(10, b=20)

        assert log_output.entries[0]['args'] == [10]
        assert log_output.entries[0]['kwargs'] == {'b': 20}

    def test_custom_logger_name(
        self,
        sample_synchronous_function: tuple[Callable[..., Any], Callable[..., Any]],
        log_output: LogCapture,
    ) -> None:
        """Test that custom logger name is used when provided."""

        _func1, _func2 = sample_synchronous_function
        custom_logger = 'custom.logger'
        wrapped = with_logging(enabled=True, logger_name=custom_logger)(_func1)

        with mock.patch('arcanum.logging._debug._get_logger') as mock_get_logger:
            mock_get_logger.return_value = mock.MagicMock()

            wrapped(1, 2)

            mock_get_logger.assert_called_once_with(custom_logger)

    def test_function_metadata_collection(
        self,
        sample_synchronous_function: tuple[Callable[..., Any], Callable[..., Any]],
        log_output: LogCapture,
    ) -> None:
        """Test that function metadata is properly collected."""

        _func1, _func2 = sample_synchronous_function
        wrapped = with_logging(enabled=True)(_func1)

        wrapped(1, 2)

        assert log_output.entries[0]['function'] == 'sample_function'
        assert 'qualname' in log_output.entries[0]
        assert 'module' in log_output.entries[0]

    def test_timing_information(
        self,
        sample_synchronous_function: tuple[Callable[..., Any], Callable[..., Any]],
        log_output: LogCapture,
    ) -> None:
        """Test that timing information is properly collected."""

        _func1, _func2 = sample_synchronous_function

        def slow_function(delay: float) -> float:
            time.sleep(delay)
            return delay

        wrapped = with_logging(enabled=True)(slow_function)

        delay = 0.01
        wrapped(delay)

        assert 'execution_time' in log_output.entries[0]
        assert 'total_debug_time' in log_output.entries[0]
        assert 'debug_setup_time' in log_output.entries[0]
        assert 'debug_cleanup_time' in log_output.entries[0]
        assert 'debug_overhead_ratio' in log_output.entries[0]

        assert (
            re.match(r'^\d+\.\d+ms$', log_output.entries[0]['execution_time'])
            or re.match(r'^\d+\.\d+s$', log_output.entries[0]['execution_time'])
            or re.match(r'^\d+\.\d+µs$', log_output.entries[0]['execution_time'])
            or re.match(r'^\d+\.\d+ns$', log_output.entries[0]['execution_time'])
        )

    def test_error_handling(
        self,
        sample_synchronous_function: tuple[Callable[..., Any], Callable[..., Any]],
        log_output: LogCapture,
    ) -> None:
        """Test that errors are properly logged and re-raised."""

        _func1, _func2 = sample_synchronous_function
        wrapped = with_logging(enabled=True)(_func2)

        mock_logger = mock.MagicMock()
        with mock.patch('arcanum.logging._debug._get_logger') as mock_get_logger:
            mock_get_logger.return_value = mock_logger
            with pytest.raises(ValueError, match='Test exception'):
                wrapped(1, 2)

            if call_args := mock_logger.debug.call_args:
                assert call_args['error'] == 'Test exception'
                assert call_args['error_type'] == 'ValueError'
                assert 'traceback' in call_args


class TestAWrapWithLogging:
    @pytest.mark.anyio
    async def test_disabled_returns_original_function_result(
        self,
        sample_async_function: tuple[
            Callable[..., Coroutine[Any, Any, int]],
            Callable[..., Coroutine[Any, Any, int]],
        ],
    ) -> None:
        """Test that disabled wrapper returns the original async function result."""

        _func1, _func2 = sample_async_function
        wrapped = awith_logging(enabled=False)(_func1)

        result = await wrapped(5, 7)

        assert result == 12

    @pytest.mark.anyio
    async def test_enabled_returns_original_function_result(
        self,
        sample_async_function: tuple[
            Callable[..., Awaitable[Any]],
            Callable[..., Awaitable[Any]],
        ],
        log_output: LogCapture,
    ) -> None:
        """Test that enabled wrapper returns the original async function result while logging."""

        _func1, _func2 = sample_async_function

        with mock.patch('arcanum.logging._debug._get_logger') as mock_get_logger:
            mock_logger = mock.MagicMock()
            mock_logger.adebug = mock.AsyncMock()
            mock_get_logger.return_value = mock_logger

            wrapped = awith_logging(enabled=True)(_func1)
            result = await wrapped(5, 7)

            assert result == 12
            mock_logger.adebug.assert_called_once()

    @pytest.mark.anyio
    async def test_error_handling(
        self,
        sample_async_function: tuple[
            Callable[..., Awaitable[Any]],
            Callable[..., Awaitable[Any]],
        ],
    ) -> None:
        """Test that errors are properly logged and re-raised in async functions."""

        _func1, _func2 = sample_async_function

        with mock.patch('arcanum.logging._debug._get_logger') as mock_get_logger:
            mock_logger = mock.MagicMock()
            mock_logger.adebug = mock.AsyncMock()
            mock_get_logger.return_value = mock_logger

            wrapped = awith_logging(enabled=True)(_func2)

            with pytest.raises(ValueError, match='Test exception'):
                await wrapped(1, 2)

            if call_kwargs := mock_logger.adebug.call_args:
                assert 'error' in call_kwargs
                assert call_kwargs['error'] == 'Test exception'
                assert call_kwargs['error_type'] == 'ValueError'
                assert 'traceback' in call_kwargs


class TestDebugLog:
    def test_disabled_returns_immediately(self) -> None:
        """Test that disabled debug_log returns immediately without logging."""

        with mock.patch('arcanum.logging._debug._get_logger') as mock_get_logger:
            debug_log(enabled=False)
            mock_get_logger.assert_not_called()

    def test_message_and_custom_logger(self, log_output: LogCapture) -> None:
        """Test that message and custom logger are properly used."""

        with mock.patch('arcanum.logging._debug._get_logger') as mock_get_logger:
            mock_logger = mock.MagicMock()
            mock_get_logger.return_value = mock_logger

            custom_message = 'Custom debug message'
            custom_logger = 'custom.logger'

            debug_log(custom_message, enabled=True, logger_name=custom_logger)

            mock_get_logger.assert_called_once_with(custom_logger)
            mock_logger.debug.assert_called_once()
            args, _ = mock_logger.debug.call_args

            assert args[0] == custom_message

    def test_kwargs_are_passed(self, log_output: LogCapture) -> None:
        """Test that kwargs are passed to the logger correctly."""

        with mock.patch('arcanum.logging._debug._get_logger') as mock_get_logger:
            mock_logger = mock.MagicMock()
            mock_get_logger.return_value = mock_logger

            debug_log(enabled=True, test_key='test_value')

            _, kwargs = mock_logger.debug.call_args

            assert kwargs['test_key'] == 'test_value'

    def test_object_type_annotation(self, log_output: LogCapture) -> None:
        """Test that object type is annotated when obj is provided."""

        with mock.patch('arcanum.logging._debug._get_logger') as mock_get_logger:
            mock_logger = mock.MagicMock()
            mock_get_logger.return_value = mock_logger

            test_obj = 'test_string'
            debug_log(enabled=True, obj=test_obj)

            _, kwargs = mock_logger.debug.call_args

            assert kwargs['obj'] == test_obj
            assert kwargs['obj_type'] == str  # noqa: E721

    def test_caller_info_collection(self, log_output: LogCapture) -> None:
        """Test that caller information is properly collected."""

        with mock.patch('arcanum.logging._debug._get_logger') as mock_get_logger:
            mock_logger = mock.MagicMock()
            mock_get_logger.return_value = mock_logger

            debug_log(enabled=True)

            _, kwargs = mock_logger.debug.call_args

            assert 'function_name' in kwargs
            assert 'file_name' in kwargs
            assert 'line_no' in kwargs

            frame = inspect.currentframe()

            assert frame is not None
            assert kwargs['function_name'] == frame.f_code.co_name


class TestADebugLog:
    @pytest.mark.anyio
    async def test_disabled_returns_immediately(self) -> None:
        """Test that disabled adebug_log returns immediately without logging."""

        with mock.patch('arcanum.logging._debug._get_logger') as mock_get_logger:
            await adebug_log(enabled=False)
            mock_get_logger.assert_not_called()

    @pytest.mark.anyio
    async def test_message_and_custom_logger(self) -> None:
        """Test that message and custom logger are properly used in async context."""

        with mock.patch('arcanum.logging._debug._get_logger') as mock_get_logger:
            mock_logger = mock.MagicMock()
            mock_logger.adebug = mock.AsyncMock()
            mock_get_logger.return_value = mock_logger

            custom_message = 'Custom async debug message'
            custom_logger = 'custom.async.logger'

            await adebug_log(custom_message, enabled=True, logger_name=custom_logger)

            mock_get_logger.assert_called_once_with(custom_logger)
            mock_logger.adebug.assert_called_once()

            args, _ = mock_logger.adebug.call_args

            assert args[0] == custom_message

    @pytest.mark.anyio
    async def test_kwargs_are_passed(self) -> None:
        """Test that kwargs are passed to the async logger correctly."""

        with mock.patch('arcanum.logging._debug._get_logger') as mock_get_logger:
            mock_logger = mock.MagicMock()
            mock_logger.adebug = mock.AsyncMock()
            mock_get_logger.return_value = mock_logger

            await adebug_log(enabled=True, test_key='test_value')

            _, kwargs = mock_logger.adebug.call_args
            assert kwargs['test_key'] == 'test_value'

    @pytest.mark.anyio
    async def test_object_type_annotation(self, log_output: LogCapture) -> None:
        """Test that object type is annotated when obj is provided."""

        with mock.patch('arcanum.logging._debug._get_logger') as mock_get_logger:
            mock_logger = mock.MagicMock()
            mock_logger.adebug = mock.AsyncMock()
            mock_get_logger.return_value = mock_logger

            test_obj = 'test_string'
            await adebug_log(enabled=True, obj=test_obj)

            _, kwargs = mock_logger.adebug.call_args

            assert kwargs['obj'] == test_obj
            assert kwargs['obj_type'] == str  # noqa: E721


class TestFormatDuration:
    def test_format_duration(self) -> None:
        """Test that durations are properly formatted with appropriate units."""

        from arcanum.logging._debug import _format_duration

        assert _format_duration(1.234) == '1.234s'
        assert _format_duration(0.5) == '500.000ms'

        assert _format_duration(0.1234) == '123.400ms'
        assert _format_duration(0.001) == '1.000ms'

        assert _format_duration(0.0001234) == '123.400µs'
        assert _format_duration(0.000001) == '1.000µs'

        assert _format_duration(0.0000001234) == '123.400ns'
        assert _format_duration(0.000000001) == '1.000ns'


class TestUtilityFunctions:
    def test_collect_metadata(self) -> None:
        """Test that function metadata is properly collected."""

        from arcanum.logging._debug import _collect_metadata

        def test_function(a: int, b: str) -> float:  # noqa: ARG001
            return 1.0

        metadata = _collect_metadata(test_function)

        assert metadata['function'] == 'test_function'
        assert metadata['qualname'] == 'TestUtilityFunctions.test_collect_metadata.<locals>.test_function'
        assert metadata['annotations'] == {'a': 'int', 'b': 'str', 'return': 'float'}

        with mock.patch('inspect.currentframe', side_effect=Exception('Test metadata error')):
            error_metadata = _collect_metadata(test_function)
            assert 'metadata_error' in error_metadata
            assert error_metadata['metadata_error'] == 'Test metadata error'

    def test_collect_result_info(self) -> None:
        """Test that result information is properly collected."""

        from arcanum.logging._debug import _collect_result_info

        def test_function() -> str:
            return 'test'

        result_info = _collect_result_info('test', test_function)

        assert result_info['result'] == 'test'
        assert result_info['result_type'] == 'str'
        assert result_info['expected_type'] == 'str'

        assert 'result_matches_expected' in result_info
        assert 'str' in result_info['result_type_mro']

        # Intentionally left without a return type annotation
        def unannotated_function():  # noqa: ANN202
            return 'test'

        unannotated_result = _collect_result_info('test', unannotated_function)

        assert 'result' in unannotated_result
        assert 'object' in result_info['result_type_mro']

    def test_collect_error_info(self) -> None:
        """Test that error information is properly collected."""

        from arcanum.logging._debug import _collect_error_info

        test_exception = ValueError('Test error')
        error_info = _collect_error_info(test_exception)

        assert error_info['error'] == 'Test error'
        assert error_info['error_type'] == 'ValueError'
        assert 'traceback' in error_info

        assert isinstance(error_info['traceback'], str)
