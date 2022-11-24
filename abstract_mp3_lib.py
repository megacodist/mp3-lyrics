"""This module defines (not implementing) common MP3-related
functionalities such as information about an MP3 file, playing, and also
basic editing.
"""


from asyncio import AbstractEventLoop
from abc import ABC, abstractmethod
from pathlib import Path


class AbstractMP3Info(ABC):
    @abstractmethod
    def __init__(self, filename: str | Path) -> None:
        """Initializes a new instance with the file system address."""
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
        """Gets the encoder of the MP3 file."""
        pass

    @property
    @abstractmethod
    def Tags(self) -> dict[str, str]:
        """Gets tags of the MP3 file."""
        pass

    @property
    @abstractmethod
    def RawData(self) -> dict:
        """Gets all data about the MP3 file as a JOSN object."""
        pass


class AbstractMP3Player(ABC):
    """This class offers an interface to play an MP3 file."""
    @abstractmethod
    def __init__(
            self,
            audio: str | Path,
            loop: AbstractEventLoop | None = None
            ) -> None:
        """Initializes the Player. Any realization must accept location
        of the audio typically in the local file system. Although some
        implementations might accept other locations such as in the cloud.
        The implementation might be built on top of Async IO model.
        """
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
        pass

    @abstractmethod
    def Stop(self) -> None:
        pass

    @abstractmethod
    def Close(self) -> None:
        """Releases resources associated with the player."""
        pass


class AbstractMP3Editor(ABC):
    pass
