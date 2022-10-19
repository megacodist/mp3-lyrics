from asyncio import AbstractEventLoop
from cmath import isnan
from datetime import timedelta
from pathlib import Path
import subprocess

from app_utils import AbstractPlayer


class FFmpegPlayer(AbstractPlayer):
    """Implements a player for the program. This realization does not need
    asyncio event loop.
    """
    def __init__(
            self,
            audio: str | Path,
            loop: AbstractEventLoop | None = None
            ) -> None:
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
        self._popen: subprocess.Popen[str] | None = None
        """Specifies the Popen object wrapping the child process."""

    @property
    def volume(self) -> int:
        return self._volume

    @volume.setter
    def volume(self, __volume: int, /) -> int:
        self._volume = round(__volume)
        if self._playing:
            self._popen.terminate()
            self.Play()
    
    @property
    def pos(self) -> float:
        while self._popen and (self._popen.poll() is None):
            try:
                sPos = self._popen.stdout.readline().strip()
                spaceIdx = sPos.index(' ')
                fPos = float(sPos[:spaceIdx])
            except ValueError:
                pass
            else:
                if not isnan(fPos):
                    self._pos = fPos
                    return fPos
        self._playing = False
        self._pos = 0.0
        return 0.0

    @pos.setter
    def pos(self, __pos: float, /) -> None:
        self._pos = __pos
        if self._playing:
            self._popen.terminate()
            self.Play()

    @property
    def playing(self) -> bool:
        return self._playing

    def Play(self) -> None:
        args = [
            'ffplay',
            '-nodisp',
            '-hide_banner',
            '-autoexit',
            '-i',
            self._audioLocation,
            '-volume',
            str(self._volume),
            '-ss',
            str(timedelta(seconds=self._pos))]
        self._popen = subprocess.Popen(
            args,
            universal_newlines=True,
            encoding='utf-8',
            bufsize=1,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        self._playing = True

    def Pause(self) -> None:
        _ = self.pos
        self._popen.terminate()
        self._playing = False

    def Stop(self) -> None:
        self._popen.terminate()
        self._pos = 0.0
        self._playing = False

    def Close(self) -> None:
        self._popen.terminate()
