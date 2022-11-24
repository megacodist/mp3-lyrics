"""This module implements the basic functionalities of abstract_mp3_lib
by the use of FFmpeg project. It is supposed that FFmpeg is installed
on the machine and the directory is also added the path environment
variable.
"""

from asyncio import AbstractEventLoop
from datetime import timedelta
from json import loads
from math import isnan
from pathlib import Path
import subprocess

from abstract_mp3_lib import AbstractMP3Info, AbstractMP3Player


class FFmpegMP3Info(AbstractMP3Info):
    """Implements AbstractMP3Info by using FFmpeg project."""
    def __init__(self, filename: str | Path) -> None:
        self._filename = filename
        """Specifies the file system address of the MP3 file."""
        # Getting information of the file & putting them into an object...
        self._rawData: dict | None = None
        """A JSON object (a dictionary) containing all raw multimedia
        attributes about the file.
        """
        args = [
            'ffprobe',
            '-hide_banner',
            '-loglevel',
            '0',
            '-print_format',
            'json',
            '-show_format',
            '-show_streams',
            filename]
        popen = subprocess.Popen(
            args=args,
            universal_newlines=True,
            encoding='utf-8',
            bufsize=1,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        jsonData = ''
        while True:
            output = popen.stdout.readline()
            if output:
                jsonData += output
            elif popen.poll() is not None:
                break
        self._rawData = loads(jsonData)
        self._rawData['format']['duration'] = float(
            self._rawData['format']['duration'])
        self._rawData['format']['bit_rate'] = int(
            self._rawData['format']['bit_rate'])
    
    @property
    def Duration(self) -> float:
        return self._rawData['format']['duration']
    
    @property
    def Filename(self) -> str | Path:
        return self._filename

    @property
    def BitRate(self) -> int:
        return self._rawData['format']['bit_rate']

    @property
    def FormatName(self) -> str:
        return self._rawData['format']['format_name']

    @property
    def FormatLongName(self) -> str:
        return self._rawData['format']['format_long_name']

    @property
    def Encoder(self) -> str:
        return self._rawData['streams'][0]['tags']['encoder']
    
    @property
    def Tags(self) -> dict[str, str]:
        return self._rawData['format'].get('tags', {})
    
    @property
    def RawData(self) -> dict:
        return self._rawData


class FFmpegMP3Player(AbstractMP3Player):
    """Implements AbstractMP3Player by the use of FFmpeg project.
    This realization does not need the asyncio event loop.
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
                    if fPos < self._pos:
                        continue
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
        try:
            self._popen.terminate()
        except AttributeError:
            pass
