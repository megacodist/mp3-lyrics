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


GifImage = list[PIL.ImageTk.PhotoImage]
"""It is actually a list of PIL.ImageTk.PhotoImage to hold the GIF frames."""
