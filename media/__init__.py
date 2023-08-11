#
# 
#
"""
"""


from abc import abstractmethod
from os import PathLike
from pathlib import Path
from utils.types import FileExt


AUDIO_EXT = FileExt('.mp3')
"""The supported audio format throughout this package."""


LYRICS_EXT = FileExt('.lrc')
"""The supported lyrics format throughout this package."""


PLAYLIST_EXTS = [FileExt('.m3u'), FileExt('.m3u8')]
"""The supported playlist formats throughout this package."""


class AbstractPlaylist:
    @property
    def Audios(self) -> tuple[Path, ...]:
        """Gets a list of all available audios in this playlist."""
        pass

    @abstractmethod
    def GetFullPath(self, audio: Path) -> Path:
        """Gets fully path of the `audio` in this playlist.
        `ValueError` is raised if not found.
        """
        pass

    @abstractmethod
    def Load(self) -> None:
        """Loads content of this playlist."""
        pass


class FolderPlaylist(AbstractPlaylist):
    """This class abstract accessing and using peer MP3 files in a folder.
    """
    def __init__(self, dir_: PathLike) -> None:
        from utils.funcs import PathLikeToPath
        self._dir = PathLikeToPath(dir_)
        """The target directory of this folder palylist."""
        self._audios: list[Path] | None = None
        """The audios of this folder playlist."""

    @property
    def Audios(self) -> list[Path]:
        if not self._audios:
            self.Load()
        return tuple(self._audios)
    
    def Load(self) -> None:
        self._audios = list(self._dir.glob('*.mp3'))
    
    def GetFullPath(self, audio: Path) -> Path:
        try:
            self._audios.index(audio)
        except ValueError as err:
            err.args[0] = f'{audio} not found in {self}'
            raise err
        else:
            return self._dir / audio
    
    def __repr__(self) -> str:
        return f"<{type(self).__qualname__} dir={str(self._dir)}>"


class M3u8Playlist(AbstractPlaylist):
    pass
