#
# 
#
"""This module offers the following types:

1. `FileExt`
2. `FileStem`
3. `FileName`
4. `TkImg`
5. `GifImage`
"""


from os import PathLike
import pathlib

import PIL.ImageTk


FileExt = pathlib.Path
"""The extension part of a file name as a Path object."""


FileStem = pathlib.Path
"""The stem of a file name that is the fully-qualified file name excluding
path (folder) and extension as a Path object.
"""


FileName = pathlib.Path
"""The file name, excluding the folder, as a Path object.
"""


TkImg = PIL.ImageTk.PhotoImage
"""Tkinter compatible image type."""


#GifImage = list[PIL.ImageTk.PhotoImage]
class GifImage:
    """It is actually a list of `PIL.ImageTk.PhotoImage` to hold the
    GIF frames. The objects of this class support zero-based integer
    subscript notation for reading, not setting, GIF frames.
    """
    def __init__(self, gif: PathLike) -> None:
        import PIL.Image
        self._frames: list[PIL.ImageTk.PhotoImage] = []
        """The frames of this GIF image."""
        self._HGIF_WAIT = PIL.Image.open(gif)
        idx = 0
        while True:
            try:
                self._HGIF_WAIT.seek(idx)
                self._frames.append(
                    PIL.ImageTk.PhotoImage(image=self._HGIF_WAIT))
                idx += 1
            except EOFError :
                break
    
    def __getitem__(self, __idx: int, /) -> PIL.ImageTk.PhotoImage:
        return self._frames[__idx]
    
    def __del__(self) -> None:
        self._frames.clear()
        del self._frames
        self._HGIF_WAIT.close()
        del self._HGIF_WAIT
