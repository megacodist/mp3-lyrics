"""This module implements the functionalities of abstract_mp3.py
by the use of FFmpeg project.

Dependencies:
1. Python 3.10+
2. FFmpeg must be installed on the machine and its directory is also
required to be added the path environment variable.
"""

from asyncio import AbstractEventLoop
from datetime import timedelta
from json import loads
from math import isnan
from pathlib import Path
import subprocess
from typing import Any

from media.abstract_mp3 import AbstractMP3, MP3NotFoundError


class FFmpegMP3(AbstractMP3):
    """Implements AbstractMP3Info by using FFmpeg project."""
    def __init__(
            self,
            filename: str | Path,
            loop: AbstractEventLoop | None = None
            ) -> None:
        """Initializes new instance of this class from 'filename' in
        the file system.

        Exceptions:
        FileNotFoundError: the file has not found 
        """
        if not Path(filename).exists():
            raise FileNotFoundError(f"'{filename}' has not found")

        # Initializing other attributes...
        self._filename = filename
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
        self._rawData: dict[str, Any] | None = None
        """A JSON object (a dictionary) containing all raw multimedia
        attributes about the file.
        """

        # Getting information of the file & putting them into an object...
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
        # Checking the input file is an MP3...
        if self._rawData['format'].get('format_name', None).lower() != 'mp3':
            raise MP3NotFoundError(f"'{filename}' is not an MP3 file.")
    
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
        for stream in self._rawData['streams']:
            if stream['codec_name'] == 'mp3':
                if 'tags' in stream:
                    return stream['tags'].get('encoder', None)
                else:
                    break
    
    @property
    def Tags(self) -> dict[str, str]:
        return self._rawData['format'].get('tags', {})
    
    @property
    def nStreams(self) -> int:
        return self._rawData['format'].get('nb_streams', None)
    
    @property
    def RawData(self) -> dict:
        return self._rawData
    
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
            self._filename,
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
