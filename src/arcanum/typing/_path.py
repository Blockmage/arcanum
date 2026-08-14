from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import os

    from arcanum.stdlib.path import Path

type StrPath = os.PathLike[str] | str
type BytesPath = os.PathLike[bytes] | bytes
type PathLike[T: (StrPath, BytesPath, Path) = Path] = T
type AnyPathLike = PathLike[str] | PathLike[bytes] | PathLike[Path]
