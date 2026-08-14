# Types
from arcanum.typing._logging import ExcInfoT as ExcInfoT
from arcanum.typing._logging import LogRecordT as LogRecordT

# Core
from ._core import configure_logging as configure_logging
from ._core import get_logger as get_logger

# Debug
from ._debug import adebug_log as adebug_log
from ._debug import awith_logging as awith_logging
from ._debug import debug_log as debug_log
from ._debug import with_logging as with_logging

configure_logging()

__all__ = (
    'ExcInfoT',
    'LogRecordT',
    'adebug_log',
    'awith_logging',
    'configure_logging',
    'debug_log',
    'get_logger',
    'with_logging',
)
