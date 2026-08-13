import re
from typing import Literal, Self

__all__ = (
    'ByteSize',
    'SizeUnit',
)

# fmt: off
SizeUnit = Literal[
    'b',   'kb',    'mb',    'gb',    'tb',    'pb',    'eb',
    'B',   'KB',    'MB',    'GB',    'TB',    'PB',    'EB',
           'kib',   'mib',   'gib',   'tib',   'pib',   'eib',
           'KiB',   'MiB',   'GiB',   'TiB',   'PiB',   'EiB',
    'bit', 'kbit',  'mbit',  'gbit',  'tbit',  'pbit',  'ebit',
    'Bit', 'Kbit',  'Mbit',  'Gbit',  'Tbit',  'Pbit',  'Ebit',
           'KBit',  'MBit',  'GBit',  'TBit',  'PBit',  'EBit',
           'kibit', 'mibit', 'gibit', 'tibit', 'pibit', 'eibit',
           'Kibit', 'Mibit', 'Gibit', 'Tibit', 'Pibit', 'Eibit',
           'KiBit', 'MiBit', 'GiBit', 'TiBit', 'PiBit', 'EiBit',
]
# fmt: on

_SIZE_MAP: dict[str, float] = {
    'b': 1,
    'kb': 10**3,
    'mb': 10**6,
    'gb': 10**9,
    'tb': 10**12,
    'pb': 10**15,
    'eb': 10**18,
    'kib': 2**10,
    'mib': 2**20,
    'gib': 2**30,
    'tib': 2**40,
    'pib': 2**50,
    'eib': 2**60,
    'bit': 1 / 8,
    'kbit': 10**3 / 8,
    'mbit': 10**6 / 8,
    'gbit': 10**9 / 8,
    'tbit': 10**12 / 8,
    'pbit': 10**15 / 8,
    'ebit': 10**18 / 8,
    'kibit': 2**10 / 8,
    'mibit': 2**20 / 8,
    'gibit': 2**30 / 8,
    'tibit': 2**40 / 8,
    'pibit': 2**50 / 8,
    'eibit': 2**60 / 8,
}

_SIZE_MAP.update({k.lower()[0]: v for k, v in _SIZE_MAP.items() if 'i' not in k})
_BYTESIZE_RX = re.compile(r'^\s*(\d*\.?\d+)\s*(\w+)?', re.IGNORECASE)


class ByteSize(int):
    """Simplified version of Pydantic's `ByteSize` class."""

    @classmethod
    def from_str(cls, s: str, /) -> Self:
        """Parse a string into a `ByteSize` object instance.

        Parameters
        ----------
        s : str
            String representation of the size in bytes.

        Returns
        -------
        ByteSize
            `ByteSize` object instance.

        Raises
        ------
        ValueError
            If provided an invalid string representation of a size in bytes.
        """

        if (str_match := _BYTESIZE_RX.match(s)) is None:
            msg = 'Invalid byte size string'
            raise ValueError(msg)

        scalar, unit = str_match.groups()
        if unit is None:
            unit = 'b'

        try:
            unit_mult = _SIZE_MAP[unit.lower()]
        except KeyError as exc:
            msg = f"Unable to interpret byte unit: '{unit}'"
            raise ValueError(msg) from exc
        else:
            return cls(int(float(scalar) * unit_mult))

    def to_str(self, *, decimal: bool = False, sep: str = '') -> str:
        """Convert the `ByteSize` object to a human-readable string value.

        Parameters
        ----------
        decimal : bool, optional
            - If `True`, use decimal units (e.g. `1000` bytes per `KB`).
            - If `False`, use binary units (e.g. `1024` bytes per `KiB`).
        sep : str, optional
            Separator string by which to split the value and the unit.

        Returns
        -------
        str
            Human-readable string representation of the size in bytes.
        """

        divisor, units, final_unit = (
            (1000, ('B', 'KB', 'MB', 'GB', 'TB', 'PB'), 'EB')
            if decimal
            else (1024, ('B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB'), 'EiB')
        )

        num = float(self)
        for unit in units:
            if abs(num) < divisor:
                if unit == 'B':
                    return f'{num:0.0f}{sep}{unit}'
                return f'{num:0.1f}{sep}{unit}'
            num /= divisor

        return f'{num:0.1f}{sep}{final_unit}'

    def to_unit(self, unit: SizeUnit, /) -> float:
        """Get the value of the `ByteSize` object instance converted to the specified size `unit`.

        Parameters
        ----------
        unit : SizeUnit
            Target unit for conversion.

        Returns
        -------
        float
            Byte size in the new unit, represented as a `float` value.

        Raises
        ------
        ValueError
            If `unit` is invalid.
        """

        try:
            unit_div = _SIZE_MAP[unit.lower()]
        except KeyError as exc:
            msg = f"Could not interpret byte unit: '{unit}'"
            raise ValueError(msg) from exc

        return self / unit_div
