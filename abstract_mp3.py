"""This module defines an interface (not implementing) common
MP3-related functionalities such as metadata about an MP3 file,
playing the file, and also some basic editing capabilities.
"""


from asyncio import AbstractEventLoop
from abc import ABC, abstractmethod
from pathlib import Path


class MP3NotFoundError(Exception):
    """Raised when the specified file is not an MP3."""
    pass


class AbstractMP3(ABC):
    """This class consolidate all required functionalities to work with
    MP3 files including properties, metadata, playbak, and also some
    editing capabilities.
    """
    @abstractmethod
    def __init__(
            self,
            filename: str | Path,
            loop: AbstractEventLoop | None = None
            ) -> None:
        """Initializes the MP3 instance. Any realization must accept location
        of the audio typically in the local file system. Although some
        implementations might accept other locations such as in the cloud.
        The implementation might be built on top of Async IO model.

        Exceptions:
        FileNotFoundError: the specified file does not exist.
        MP3NotFoundError: the specified is not a valid MP3 file.
        """
        pass

    @property
    @abstractmethod
    def Duration(self) -> float:
        """Gets the duration of the MP3 file."""
        pass

    @property
    @abstractmethod
    def Filename(self) -> str | Path:
        """Gets the file system address of the MP3 file."""
        pass

    @property
    @abstractmethod
    def BitRate(self) -> int:
        """Gets the bit rate of the MP3 file."""
        pass

    @property
    @abstractmethod
    def FormatName(self) -> str:
        """Gets the format name of the MP3 file (typically 'mp3')."""
        pass

    @property
    @abstractmethod
    def FormatLongName(self) -> str:
        """Gets the long name (description) of the format of the MP3 file."""
        pass

    @property
    @abstractmethod
    def Encoder(self) -> str:
        """Gets the encoder of the MP3 file or None if it does not have."""
        pass

    @property
    @abstractmethod
    def Tags(self) -> dict[str, str]:
        """Gets tags of the MP3 file."""
        pass

    @property
    @abstractmethod
    def nStreams(self) -> int:
        """Gets number of streams inside the MP3 or None if it
        does not have.
        """
        pass

    @property
    @abstractmethod
    def RawData(self) -> dict:
        """Gets all data about the MP3 file as a JOSN object."""
        pass

    @property
    @abstractmethod
    def volume(self) -> int:
        """Gets or sets the volume ofthe audio as an integer in the
        range of0 to 100.
        """
        pass
    
    @volume.setter
    @abstractmethod
    def volume(self, __volume: int, /) -> None:
        pass

    @property
    @abstractmethod
    def pos(self) -> float:
        """Gets or sets the position of the stream as seconds in the
        form of a floating-point number.
        """
        pass
    
    @pos.setter
    @abstractmethod
    def pos(self, __pos: float, /) -> None:
        pass

    @property
    @abstractmethod
    def playing(self) -> bool:
        """Specifies whether the audio is playing at the moment or not."""
        pass

    @abstractmethod
    def Play(self) -> None:
        pass

    @abstractmethod
    def Pause(self) -> None:
        """Pauses the playback of the stream. You can resume with 'Play'
        method.
        """
        pass

    @abstractmethod
    def Stop(self) -> None:
        """Stops the playback of the stream and sets the position to the
        start.
        """
        pass

    @abstractmethod
    def Close(self) -> None:
        """Releases resources associated with the player."""
        pass
