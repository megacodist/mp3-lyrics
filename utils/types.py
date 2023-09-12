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


import enum
from os import PathLike
import pathlib

import PIL.ImageTk


class AppStatus(enum.IntFlag):
    """These flags specify different statuses of the application."""
    NONE = 0x00
    """Specifies no special status for the application."""
    PENDING_PLAY = 0x01
    """Specifies that the audio must be played upon loading.
    """


class AfterPlayed(enum.IntEnum):
    """This enumeration specifies the action upon finishing the playback
    of the current audio in the playlist.
    """
    STOP = 0
    """The player must stop playing the current audio."""
    LOOP = 1
    """The player must loops over the current audio."""
    NEXT = 2
    """The player must play next audio in the playlist.  If it is at
    the end, it must stop playing."""
    NEXT_LOOP = 3
    """The player must play next audio in the playlist. If it is at
    the end, it must start from the beginning.
    """
    PREV = 4
    """The player must play previous audio in the playlist.  If it is at
    the beginning, it must stop playing."""
    PREV_LOOP = 5
    """The player must play previous audio in the playlist. If it is at
    the beginning, it must start from the end.
    """


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
        self._idx: int = 0
        """The index of the next frame."""
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
    
    def NextFrame(self) -> PIL.ImageTk.PhotoImage:
        """Returns the next frame of this gif image. On consecutive
        calls, this methods endlessly loops over all available frames
        jumping from end to the first.
        """
        try:
            frame = self._frames[self._idx]
            self._idx += 1
        except IndexError:
            frame = self._frames[0]
            self._idx = 1
        return frame
    
    def __getitem__(self, __idx: int, /) -> PIL.ImageTk.PhotoImage:
        return self._frames[__idx]
    
    def __del__(self) -> None:
        self._frames.clear()
        del self._frames
        self._HGIF_WAIT.close()
        del self._HGIF_WAIT


class JumpDirection(enum.IntEnum):
    """Specifies the direction of the `jump` operation."""
    FORWARD = 0
    BACKWARD = 1


class JumpStep(enum.IntEnum):
    """Specifies the step of the jump."""
    SMALL = 0
    MEDIUM = 1
    LARGE = 2


class CopyType(enum.Enum):
    LYRICS = 'Lyrics only'
    LYRICS_TIMESTAMPS = 'Lyrics and/or timestamps'


class Prefrences:
    """This class packs the preferences of the application. To get the
    default customization, create an object with no argument.
    """
    def __init__(
            self,
            *,
            small_jump_forward: int = 2,
            small_jump_backward: int = 2,
            medium_jump_forward: int = 5,
            medium_jump_backward: int = 5,
            large_jump_forward: int = 30,
            large_jump_backward: int = 30,
            command_desc: bool = True,
            ) -> None:
        self.smallJumpForward = small_jump_forward
        """Specifies the time interval for small jumping forward."""
        self.smallJumpBackward = small_jump_backward
        """Specifies the time interval for small jumping backward."""
        self.mediumJumpForward = medium_jump_forward
        """Specifies the time interval for medium jumping forward."""
        self.mediumJumpBackward = medium_jump_backward
        """Specifies the time interval for medium jumping backward."""
        self.largeJumpForward = large_jump_forward
        """Specifies the time interval for large jumping forward."""
        self.largeJumpBackward = large_jump_backward
        """Specifies the time interval for large jumping backward."""
        self.commandDesc = command_desc
        """Specifies whether the description of commands to be shown to
        the user.
        """
