#
# 
#
"""

### Constants:
1. `AUDIO_EXT`
2. `LYRICS_EXT`
3. `PLAYLIST_EXTS`

#### Functions:
1. `FilenameToPlypathAudio`
2. `PathToPlaylist`

#### Interfaces:
1. `AbstractPlaylist`

#### Classes:
1. `FolderPlaylist`
2. `M3u8Playlist`
"""


from abc import abstractmethod
from os import PathLike
from pathlib import Path
from tkinter import Misc
from types import TracebackType
from typing import Any, Callable, Iterable

from utils.fs_watcher import FsWatcher
from utils.types import FileExt, FileName


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
    def GetIndexFullPath(self, audio: Path) -> tuple[int, Path]:
        """Gets the index andfull path of the audio in this folder
        playlist respectively. It raises `ValueError` if it is not
        present in the object.
        """
        pass


class FolderPlaylist(AbstractPlaylist):
    """This class encapsulates accessing and using peer MP3 files in
    a folder.

    If you have done with objects of this class, call `Close` method to
    release resources.
    """
    def __init__(
            self,
            master: Misc,
            dir_: PathLike,
            *,
            key: Callable[[Path], Any] | None = None,
            added_cb: Callable[[Path], None] | None = None,
            changed_cb: Callable[[Path], None] | None = None,
            deleted_cb: Callable[[Path], None] | None = None,
            ) -> None:
        """Initializes a new instance of this `FolderPlaylist`. Arguments
        are as follow:

        * `key`: the sorting function of audios in this `FolderPlaylist`.
        * `added_cb`, `changed_cb`, and `deleted_cb`: callabcks to be
        called when corresponding events are detected. At least one of
        them must be set for observing functionality.
        """
        from utils.funcs import PathLikeToPath
        self._master: master
        """A widget, typically the main window, that exposes Tk/Tcl
        APIs.
        """
        self._dir = PathLikeToPath(dir_)
        """The target directory of this folder palylist."""
        self._key = key
        """The sorting function of the underlying sorted list."""
        self._addedCb = added_cb
        """The callback is to be called when one audio is added to the
        underlying folder of this `FolderPlaylist` object.
        """
        self._changedCb = changed_cb
        """The callback is to be called when one audio is modified in
        the underlying folder of this `FolderPlaylist` object.
        """
        self._deletedCb = deleted_cb
        """The callback is to be called when one audio is removed from the
        underlying folder of this `FolderPlaylist` object.
        """
        self._dirWatcher: FsWatcher | None = None
        """The directory watcher."""
        self._audios = list(self._dir.glob('*.mp3')).sort(key=self._key)
        """The audios of this folder playlist."""
        if any([self._addedCb, self._changedCb, self._deletedCb]):
            self._dirWatcher = FsWatcher(self._master)
            self._dirWatcher.Monitor(self._dir)
            self._dirWatcher.Subscribe(
                dir_=self._dir,
                recursive=False,
                creation_cb=self._OnCreated,
                deletion_cb=self._OnDeleted,
                modification_cb=self._OnChanged,
                rename_from_cb=self._OnDeleted,
                rename_to_cb=self._OnCreated)

    @property
    def Audios(self) -> tuple[Path, ...]:
        if not self._audios:
            self.Load()
        return tuple(self._audios)
    
    def GetIndexFullPath(self, audio: Path) -> tuple[int, Path]:
        """Gets the index andfull path of the audio in this folder
        playlist respectively. It raises `ValueError` if it is not
        present in the object.
        """
        try:
            return self._audios.index(audio), self._dir / audio
        except ValueError as err:
            err.args[0] = f'{audio} not found in {self}'
            raise err
    
    def Close(self) -> None:
        """Releases resources of this object."""
        self._dirWatcher.Close()
    
    def _OnCreated(self, items: Iterable[str]) -> None:
        if self._addedCb:
            for item in items:
                self._addedCb(Path(item))

    def _OnChanged(self, items: Iterable[str]) -> None:
        if self._changedCb:
            for item in items:
                self._changedCb(Path(item))

    def _OnDeleted(self, items: Iterable[str]) -> None:
        if self._deletedCb:
            for item in items:
                self._deletedCb(Path(item))
    
    def __repr__(self) -> str:
        return f"<{type(self).__qualname__} dir={str(self._dir)}>"
    
    def __exit__(
            self,
            exctype: type[BaseException] | None,
            excinst: BaseException | None,
            exctb: TracebackType | None,
            ) -> bool:
        self.Close()
        # Not suppressing possible exception...
        return False
    
    def __del__(self) -> None:
        del self._master
        del self._key
        del self._addedCb
        del self._changedCb
        del self._deletedCb


class M3u8Playlist(AbstractPlaylist):
    def __init__(self, filename: PathLike) -> None:
        self._m3u8 = filename


def FilenameToPlypathAudio(filename: PathLike) -> tuple[Path, Path | None]:
    """Converts the filename into a 2-tuple of a path to a playlist and
    an optional audio in the playlist repectively. Raises `ValueError`
    if filename is invalid.
    """
    from utils.funcs import PathLikeToPath
    pthFile = PathLikeToPath(filename)
    if FileExt(pthFile.suffix) in PLAYLIST_EXTS:
        return pthFile, None
    elif pthFile.is_dir():
        return pthFile.parent, FileName(pthFile.suffix)
    raise ValueError(f"'{filename}' is an invalid path to a playlist")


def PathToPlaylist(filename: PathLike) -> AbstractPlaylist:
    """This factory function returns a concrete `AbstractPlaylist` object
    related to the path provided. It raises `ValueError` if path is
    invalid.
    """
    from utils.funcs import PathLikeToPath
    pth = PathLikeToPath(filename)
    if FileExt(pth.suffix) in PLAYLIST_EXTS:
        return M3u8Playlist(pth)
    elif pth.is_dir():
        return FolderPlaylist(pth)
    raise ValueError(f"'{filename}' is an invalid path to a playlist")
