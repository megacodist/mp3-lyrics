from pathlib import Path

from pygame import init as InitPygame
from pygame import quit as QuitPygame
from pygame import USEREVENT as PYGAME_USER_EVENT
from pygame.event import get as GetPygameEvents
from pygame.mixer import music  as PygameMusic

from app_utils import AbstractPlayer


class PygamePlayer(AbstractPlayer):
    _nInstances = 0
    """Counts number of instances ofthis class"""

    def __init__(
            self,
            audio: str | Path,
            ) -> None:
        # Initializing the object...
        super().__init__(audio)
        # Incrementing number of instances & Pygame...
        PygamePlayer._nInstances += 1
        if PygamePlayer._nInstances == 1:
            InitPygame()
        self._AUDIO_END_EVENT = PYGAME_USER_EVENT + 1
        PygameMusic.set_endevent(self._AUDIO_END_EVENT)
        PygameMusic.load(audio)
        # Initializing other attributes...
        self._audioLocation = audio
        """Specifies the location of the input audio either in the local
        file system or on the network.
        """
        self._pos: float = 0.0
        """Specifies the current position of the stream."""
        self._volume = 50
        """Specifies the volume of the audio which can be any integer
        from 0 to 100.
        """
        self._playing = False
        """Specifies whether the audio is playing at the moment or not."""

    @property
    def volume(self) -> int:
        return self._volume

    @volume.setter
    def volume(self, __volume: int, /) -> int:
        self._volume = __volume
        PygameMusic.set_volume(__volume / 100)
    
    @property
    def pos(self) -> int:
        return self._pos + PygameMusic.get_pos()

    @pos.setter
    def pos(self, __pos: int, /) -> int:
        self._pos = __pos
        if self._playing:
            PygameMusic.play(start=self._pos)

    @property
    def playing(self) -> bool:
        if self._playing == False:
            return self._playing
        for event in GetPygameEvents():
            if event.type == self._AUDIO_END_EVENT:
                self._playing = False
                return self._playing
        return self._playing

    def Play(self) -> None:
        if not self._playing:
            self._playing = True
            PygameMusic.play(start=self._pos)

    def Pause(self) -> None:
        PygameMusic.pause()

    def Stop(self) -> None:
        PygameMusic.stop()

    def Close(self) -> None:
        PygameMusic.unload()
    
    def __del__(self) -> None:
        PygamePlayer._nInstances -= 1
        if PygamePlayer._nInstances == 0:
            QuitPygame()
