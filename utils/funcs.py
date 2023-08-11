#
# 
#
"""
"""


from os import PathLike, fspath
from pathlib import Path


def PathLikeToPath(__pl: PathLike, /) -> Path:
    """Converts a path-like object to a Path object."""
    return __pl if isinstance(__pl, Path) else Path(fspath(__pl))