from typing import Literal

# ruff: noqa: E501 (line-too-long)

# fmt: off
UpdateTextMode = Literal['r+', '+r', 'rt+', 'r+t', '+rt', 'tr+', 't+r', '+tr', 'w+', '+w', 'wt+', 'w+t', '+wt', 'tw+', 't+w', '+tw', 'a+', '+a', 'at+', 'a+t', '+at', 'ta+', 't+a', '+ta', 'x+', '+x', 'xt+', 'x+t', '+xt', 'tx+', 't+x', '+tx']
UpdateBinaryMode = Literal['rb+', 'r+b', '+rb', 'br+', 'b+r', '+br', 'wb+', 'w+b', '+wb', 'bw+', 'b+w', '+bw', 'ab+', 'a+b', '+ab', 'ba+', 'b+a', '+ba', 'xb+', 'x+b', '+xb', 'bx+', 'b+x', '+bx']
# fmt: on

ReadBinaryMode = Literal['rb', 'br', 'rbU', 'rUb', 'Urb', 'brU', 'bUr', 'Ubr']
ReadTextMode = Literal['r', 'rt', 'tr', 'U', 'rU', 'Ur', 'rtU', 'rUt', 'Urt', 'trU', 'tUr', 'Utr']

WriteBinaryMode = Literal['wb', 'bw', 'ab', 'ba', 'xb', 'bx']
WriteTextMode = Literal['w', 'wt', 'tw', 'a', 'at', 'ta', 'x', 'xt', 'tx']

UpdateMode = Literal[UpdateTextMode, UpdateBinaryMode]
ReadMode = Literal[ReadTextMode, ReadBinaryMode]
WriteMode = Literal[WriteTextMode, WriteBinaryMode]

OpenBinaryMode = Literal[UpdateBinaryMode, ReadBinaryMode, WriteBinaryMode]
OpenTextMode = Literal[UpdateTextMode, WriteTextMode, ReadTextMode]
OpenMode = Literal[ReadMode, WriteMode]
