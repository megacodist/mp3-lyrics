from __future__ import annotations
from enum import IntFlag
from math import modf
from pathlib import Path
import re
from time import time

import attrs


class Timestamp:
    """Specifies a timestamp in the form of mm:ss.xx where mm and ss are
    integers and """
    @classmethod
    def FromString(cls, timestamp: str) -> Timestamp:
        """Converts strings in the form of mm:ss.xx to an instance of
        Timestamp. In the case of failure it returns None.
        """
        TIMESTAMP_REGEX = r'^(?P<mm>\d+):(?P<ss>\d+)(?P<xx>\.\d+)$'
        timeMatch = re.match(
            TIMESTAMP_REGEX,
            timestamp)
        if timeMatch:
            try:
                return Timestamp(
                    minutes=int(timeMatch['mm']),
                    seconds=int(timeMatch['ss']),
                    milliseconds=float(timeMatch['xx']))
            except Exception:
                pass

    @classmethod
    def FromFloat(cls, seconds: float) -> Timestamp:
        """Converts a floating-pont number to an instance of Timastamp, for
        examle 87.3 will be converted to 1:17.3.
        """
        xx, secs = modf(seconds)
        mm, ss = divmod(int(secs), 60)
        return Timestamp(minutes=mm, seconds=ss, milliseconds=xx)

    def __init__(
            self,
            minutes: int = 0,
            seconds: int = 0,
            milliseconds: float = 0.0
            ) -> None:
        self._minutes: int
        self._seconds: int
        self._milliseconds: float

        # Setting attribute...
        self.minutes = minutes
        self.seconds = seconds
        self.milliseconds = milliseconds
    
    @property
    def minutes(self) -> int:
        return self._minutes
    
    @minutes.setter
    def minutes(self, __mm: int) -> None:
        # Setting minutes attribute...
        if not isinstance(__mm, int):
            raise TypeError("'minutes' must be an integer")
        if __mm < 0:
            raise ValueError("'minutes' must be positive")
        self._minutes = __mm
    
    @property
    def seconds(self) -> None:
        return self._seconds
    
    @seconds.setter
    def seconds(self, __ss: int) -> None:
        if not isinstance(__ss, int):
            raise TypeError("'seconds' must be an integer")
        if not (0 <= __ss < 60):
            raise ValueError("0 <= seconds < 60 must be true")
        self._seconds = __ss
    
    @property
    def milliseconds(self) -> float:
        return self._milliseconds
    
    @milliseconds.setter
    def milliseconds(self, __xx: float) -> None:
        if not isinstance(__xx, float):
            raise TypeError("'milliseconds' must be a floating-point number")
        if not (0.0 <= __xx < 1.0):
            raise ValueError("0.0 <= milliseconds < 1.0 must be true")
        self._milliseconds = __xx
    
    def ToFloat(self) -> float:
        return 60 * self._minutes + self._seconds + self._milliseconds

    def __str__(self) -> str:
        xx = str(self.milliseconds).lstrip('0')
        return f'{self.minutes:02}:{self.seconds:02}{xx}'
    
    def __repr__(self) -> str:
        return f'<{self.__class__} object {str(self)}>'
    
    def __lt__(self, timestamp: Timestamp) -> bool:
        a = (self.minutes, self.seconds, self.milliseconds,)
        b = (timestamp.minutes, timestamp.seconds, timestamp.milliseconds,)
        return a < b
    
    def __gt__(self, timestamp: Timestamp) -> bool:
        a = (self.minutes, self.seconds, self.milliseconds,)
        b = (timestamp.minutes, timestamp.seconds, timestamp.milliseconds,)
        return a > b
    
    def __le__(self, timestamp: Timestamp) -> bool:
        a = (self.minutes, self.seconds, self.milliseconds,)
        b = (timestamp.minutes, timestamp.seconds, timestamp.milliseconds,)
        return a <= b
    
    def __ge__(self, timestamp: Timestamp) -> bool:
        a = (self.minutes, self.seconds, self.milliseconds,)
        b = (timestamp.minutes, timestamp.seconds, timestamp.milliseconds,)
        return a >= b
    
    def __eq__(self, timestamp: Timestamp) -> bool:
        a = (self.minutes, self.seconds, self.milliseconds,)
        b = (timestamp.minutes, timestamp.seconds, timestamp.milliseconds,)
        return a == b
    
    def __ne__(self, timestamp: Timestamp) -> bool:
        a = (self.minutes, self.seconds, self.milliseconds,)
        b = (timestamp.minutes, timestamp.seconds, timestamp.milliseconds,)
        return a != b


class _LrcErrors(IntFlag):
    No_ERROR = 0
    DUPLICATE_TAGS = 1
    UNKNOWN_TAGS = 2
    BAD_DATA = 4
    NO_TIMESTAMP = 8
    BAD_LAYOUT = 16
    OUT_OF_ORDER = 32


class LyricsItem:
    def __init__(
            self,
            text: str,
            timestamp: Timestamp | None = None
            ) -> None:
        self.text = text
        self.timestamp = timestamp
    
    def __getitem__(self, __value: int) -> str | Timestamp:
        """Returns timestamp attribute for 0 and text for 1. For any other
        values, it raises TypeError or ValueError.
        """
        if not isinstance(__value, int):
            raise TypeError('Index must be an integer')
        if __value == 0:
            return self.timestamp if self.timestamp is not None else ''
        elif __value == 1:
            return self.text
        else:
            raise ValueError('Index is only allowed to be 0 or 1')


class Lrc:
    """Parses and manipulates LRC files. To load an LRC file, you must pass
    its file system address to the constructor.
    """
    TAGS: list[str] = [
        'ar',
        'al',
        'ti',
        'au',
        'length',
        'offset',
        'by',
        're',
        've',]
    
    @classmethod
    def GetLrcFilename(cls, filename: str) -> str:
        """Returns the probably LRC file name associated with 'filename'
        parameter. This LRC file might exist or not.
        """
        pathObj = Path(filename)
        extLength = len(pathObj.suffix)
        if extLength:
            return filename[:-extLength] + '.lrc'
        else:
            return filename + '.lrc'

    def __init__(
            self,
            filename: str | Path | None = None
            ) -> None:
        self.filename = filename
        self._errors = _LrcErrors.No_ERROR
        self.tags: dict[str, str] = {}
        self._unknownTags: dict[str, str] = {}
        self.lyrics: list[LyricsItem] = []

        self._Parse()

    def _Parse(self) -> None:
        if self.filename is None:
            # No file system address is provided, Doing nothing...
            return

        BRAC_REGEX = r'''
            ^(?P<prefix>[^\[\]]*)
            \[
            (?P<inside>[^\[\]]*)
            \]
            (?P<suffix>.*)'''
        TAG_REGEX = r'^(?P<tag>\w+):(?P<value>.*)$'
        bracPattern = re.compile(BRAC_REGEX, re.VERBOSE)
        tagPattern = re.compile(TAG_REGEX)

        # Reading the content of the LRC file...
        with open(self.filename, mode='rt') as lrcFile:
            lines = lrcFile.readlines()
        
        nonTagMatched = False
        for line in lines:
            bracMatch = bracPattern.match(line)
            if not bracMatch:
                data = line.strip()
                if data:
                    self._errors |= _LrcErrors.NO_TIMESTAMP
                    self.lyrics.append(LyricsItem(line.strip()))
                    nonTagMatched = True
            else:
                prefix = bracMatch['prefix'].strip()
                if prefix:
                    self._errors |= _LrcErrors.BAD_DATA
                else:
                    inside = bracMatch['inside']
                    # Matching against timestamp (mm:ss.xx)...
                    timestamp = Timestamp.FromString(inside)
                    if timestamp:
                        self.lyrics.append(LyricsItem(
                            timestamp=timestamp,
                            text=bracMatch['suffix']))
                        nonTagMatched = True
                    else:
                        # Matching agianst tag pattern...
                        tagMatch = tagPattern.match(inside)
                        if tagMatch:
                            tag = tagMatch['tag']
                            if tag not in Lrc.TAGS:
                                self._errors |= _LrcErrors.UNKNOWN_TAGS
                                self._unknownTags[tag] = tagMatch['value']
                            elif tag in self.tags:
                                self._errors |= _LrcErrors.DUPLICATE_TAGS
                                self.tags[tag] = tagMatch['value']
                            else:
                                self.tags[tag] = tagMatch['value']
                            if nonTagMatched:
                                self._errors |= _LrcErrors.BAD_LAYOUT
                        elif not inside:
                            self._errors |= _LrcErrors.NO_TIMESTAMP
                            self.lyrics.append(LyricsItem(
                                text=bracMatch['suffix']))
                            nonTagMatched = True
                        else:
                            self._errors |= _LrcErrors.BAD_DATA
        
        # Looking for out of order timestamps...
        idx = 0
        while idx < len(self.lyrics):
            if self.lyrics[idx].timestamp is not None:
                prevTime = self.lyrics[idx].timestamp
                idx += 1
                break
            idx += 1
        while idx < len(self.lyrics):
            if self.lyrics[idx].timestamp <= prevTime:
                self._errors |= _LrcErrors.OUT_OF_ORDER
                break
            else:
                prevTime = self.lyrics[idx].timestamp
            idx += 1

    def Save(self) -> None:
        raise NotImplementedError()
    
    def errors(self) -> list[str]:
        raise NotImplementedError()
    
    def __repr__(self) -> str:
        return (
            f'{super().__repr__()}'
            + f'\nFile name: {self.filename}'
            + f'\nErrors: {self._errors.name}'
            + f'\nTags: {self.tags}'
            + f'\nUnknown tags: {self._unknownTags}'
            + f'\nLyrics: {self.lyrics}')
