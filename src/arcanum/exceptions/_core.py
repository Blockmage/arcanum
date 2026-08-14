from __future__ import annotations

from collections.abc import Sequence
from difflib import get_close_matches
from typing import Any, Never

__all__ = (
    'ArcaneAttributeError',
    'ArcaneError',
    'ArcaneTypeError',
    'ArcaneValueError',
    'DecodeError',
    'DecryptError',
    'EncodeError',
    'EncryptError',
    'InvalidArgumentError',
    'MissingDependencyError',
)

# NOTE: These will likely need to be spruced up a bit/made whole/made to work however they should.
#       Currently, they are as-is, having been copied in to place from other scrapped code/another
#       unrelated codebase, and match/replaced to rename everything to be 'Arcanum-'. - 2025-08-03


def raise_from(
    exc: type[Exception],
    *args: Any,
    from_exc: Exception | BaseExceptionGroup[Exception] | None = None,
) -> Never:
    """Raise `exc` with `args` from `from_exc`.

    Simple helper to allow raising an exception as part of a `return`.

    Notes
    -----
        If `from_exc` is `None`, the exception chain is effectively silenced.
    """
    raise exc(*args) from from_exc


class ArcaneError(Exception):
    """Base `Exception` class from which all `arcanum` application errors inherit."""

    @staticmethod
    def _ensure_str_seq(val: Any) -> Sequence[str]:
        """Convert input value to sequence of non-empty strings.

        Handles single strings, sequences of values, and arbitrary objects by converting
        them to stripped string representations. Filters out empty strings after stripping.
        Bytes values are decoded to strings with fallback handling for decode errors.

        Parameters
        ----------
        val : Any
            Value to convert to string sequence.

        Returns
        -------
        Sequence[str]
            List of non-empty, stripped strings.
        """

        if isinstance(val, bytes):
            try:
                val = val.decode('utf-8')
            except UnicodeDecodeError:
                val = '__failed_to_decode_message__'
        if isinstance(val, str):
            stripped = val.strip()
            return [stripped] if stripped else []
        if isinstance(val, Sequence) and not isinstance(val, (str, bytes)):
            result = []
            for v in val:
                if isinstance(v, bytes):
                    try:
                        v_str = v.decode('utf-8')
                    except UnicodeDecodeError:
                        v_str = '__failed_to_decode_message__'
                else:
                    v_str = str(v)
                if stripped := v_str.strip():
                    result.append(stripped)
            return result
        return [str(val).strip()] if str(val).strip() else []

    @staticmethod
    def get_suggestion(invalid_arg: str, valid_arg_opts: list[str]) -> str | None:
        """Find closest-matching valid option in `valid_arg_opts` for `invalid_arg`."""
        if matches := get_close_matches(invalid_arg, valid_arg_opts, n=1, cutoff=0.6):
            return matches[0]
        return None

    def __init__(self, msg: Sequence[str] | str = '', *args: Any, **kwargs: Any) -> None:
        """Initialize `ArcaneError` with flexible message handling.

        Supports both single messages and multiple message parts that get joined together.
        All message parts are normalized to strings and stripped of whitespace.

        Parameters
        ----------
        msg : Sequence[str] | str, optional
            Primary message or sequence of message parts.
        *args : Any
            Additional message parts to append.
        **kwargs : Any
            Passed to parent `Exception` constructor.
        """
        msg = ' '.join(s for s in [*self._ensure_str_seq(msg), *self._ensure_str_seq(list(args))])
        super().__init__(msg.strip())


class ArcaneTypeError(ArcaneError, TypeError):
    """Base `TypeError` class object for `arcanum` application errors."""


class ArcaneValueError(ArcaneError, ValueError):
    """Base `ValueError` class object for `arcanum` application errors."""


class ArcaneAttributeError(ArcaneError, AttributeError):
    """Base `AttributeError` class object for `arcanum` application errors."""


class InvalidArgumentError(ArcaneAttributeError):
    """Error raised to signal that an argument is not matched to any parameter or attribute."""

    def __init__(
        self,
        invalid_arg: str,
        valid_arg_opts: list[str] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Raise `InvalidArgumentError`.

        Supports "Did you mean?"-style matching if provided `valid_arg_opts`.
        """

        msg = f"\nInvalid argument: '{invalid_arg}' not matched to any parameter or attribute."
        if valid_arg_opts and (suggestion := self.get_suggestion(invalid_arg, valid_arg_opts)):
            msg += f"\nDid you mean: '{suggestion}'?"
        super().__init__(msg, *args)


class MissingDependencyError(ArcaneError, ImportError):
    """Unable to import a required dependency."""

    def __init__(self, pkg_name: str, *args: Any) -> None:
        msg = [
            f"Unable to import required package '{pkg_name}'. ",
            'Please ensure that this package is installed.',
        ]
        super().__init__(msg, *args)


class EncodeError(ArcaneValueError):
    """Failed to encode an object."""

    detail = 'Failed to encode'

    def __init__(self, *args: Any, obj: Any = None, **kwargs: Any) -> None:
        msg = self.detail if not obj else f'{self.detail} object of type {type(obj)!r}'
        super().__init__(msg, *args)


class DecodeError(ArcaneValueError):
    """Failed to decode an object."""

    detail = 'Failed to decode'

    def __init__(self, *args: Any, obj: Any = None, **kwargs: Any) -> None:
        msg = self.detail if not obj else f'{self.detail} object of type {type(obj)!r}'
        super().__init__(msg, *args)


class EncryptError(ArcaneError):
    """Failed to encrypt an object."""

    detail = 'Failed to encrypt'

    def __init__(self, *args: Any, obj: Any = None, **kwargs: Any) -> None:
        msg = self.detail if not obj else f'{self.detail} object of type {type(obj)!r}'
        super().__init__(msg, *args)


class DecryptError(ArcaneError):
    """Failed to decrypt an object."""

    detail = 'Failed to decrypt'

    def __init__(self, *args: Any, obj: Any = None, **kwargs: Any) -> None:
        msg = self.detail if not obj else f'{self.detail} object of type {type(obj)!r}'
        super().__init__(msg, *args)
