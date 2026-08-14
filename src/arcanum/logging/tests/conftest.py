from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
import structlog
from structlog.testing import LogCapture

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Generator


@pytest.fixture
def anyio_backend() -> str:
    """Configure anyio to use asyncio backend for tests."""
    return 'asyncio'


@pytest.fixture(name='log_output')
def fixture_log_output() -> LogCapture:
    """Create a LogCapture instance for testing logging functionality."""
    return LogCapture()


@pytest.fixture(autouse=True)
def fixture_configure_structlog(log_output: LogCapture) -> Generator[None, Any]:
    """Configure structlog for testing with log capture.

    Parameters
    ----------
    log_output : LogCapture
        The log capture instance to use for testing.

    Yields
    -------
    None
        Cleanup is performed automatically after test completion.
    """

    orig_processors = structlog.get_config().get('processors', [])
    structlog.configure(processors=[log_output])

    yield

    structlog.configure(processors=orig_processors)


@pytest.fixture
def sample_synchronous_function() -> tuple[
    Callable[..., int],
    Callable[..., int],
]:
    """Create a sample synchronous function for testing decorators.

    Returns
    -------
    tuple[callable, callable]
        A tuple containing (original_function, function_that_raises)
    """

    def sample_function(a: int, b: int) -> int:
        """Sample function that adds two numbers."""
        return a + b

    def function_that_raises(a: int, b: int) -> int:  # noqa: ARG001
        """Sample function that raises an exception."""
        msg = 'Test exception'
        raise ValueError(msg)

    return sample_function, function_that_raises


@pytest.fixture
def sample_async_function() -> tuple[
    Callable[..., Coroutine[Any, Any, int]],
    Callable[..., Coroutine[Any, Any, int]],
]:
    """Create a sample asynchronous function for testing decorators.

    Returns
    -------
    tuple[callable, callable]
        A tuple containing (original_async_function, async_function_that_raises)
    """

    async def sample_async_function(a: int, b: int) -> int:
        """Sample async function that adds two numbers."""
        return a + b

    async def async_function_that_raises(a: int, b: int) -> int:  # noqa: ARG001
        """Sample async function that raises an exception."""
        msg = 'Test exception'
        raise ValueError(msg)

    return sample_async_function, async_function_that_raises
