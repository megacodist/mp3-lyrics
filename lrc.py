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
        TIMESTAMP_REGEX = r'^(?P<mm>\d+):(?P<ss>\d+)\.(?P<xx>\d+)$'
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
        # Setting minutes attribute...
        if not isinstance(minutes, int):
            raise TypeError("'minutes' must be an integer")
        if minutes < 0:
            raise ValueError("'minutes' must be positive")
        self.minutes = minutes

        # Setting seconds attribute...
        if not isinstance(seconds, int):
            raise TypeError("'seconds' must be an integer")
        if not (0 <= seconds < 60):
            raise ValueError("0 <= seconds < 60 must be true")
        self.seconds = seconds

        # Setting milliseconds attribute...
        if not isinstance(milliseconds, float):
            raise TypeError("'milliseconds' must be a floating-point number")
        if not (0.0 <= milliseconds < 1.0):
            raise ValueError("0.0 <= milliseconds < 1.0 must be true")
        self.milliseconds = milliseconds

    def __str__(self) -> str:
        xx = f'{xx:.2f}'.lstrip('0')
        return f'{self.minutes:02}:{self.seconds:02}{xx}'
    
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
    BAD_CONTENTS = 4
    NO_TIMESTAMP = 8
    BAD_LAYOUT = 16
    OUT_OF_ORDER = 32


@attrs.define
class LyricsItem:
    text: str
    timestamp: Timestamp | None = attrs.field(
        default=None)


class Lrc:
    """Parses and manipulates LRC files. To load an LRC file, you must pass
    its file system address to either the constructor or Load method.
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
                self._errors |= _LrcErrors.NO_TIMESTAMP
                self.lyrics.append(LyricsItem(line.strip()))
                nonTagMatched = True
            else:
                prefix = bracMatch['prefix'].strip()
                if prefix:
                    self._errors |= _LrcErrors.BAD_CONTENTS
                else:
                    inside = bracMatch['inside']
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
                    else:
                        # Matching against mm:ss.xx...
                        timestamp = Timestamp.FromString(inside)
                        if timestamp:
                            self.lyrics.append(LyricsItem(
                                timestamp=timestamp,
                                text=bracMatch['suffix']))
                            nonTagMatched = True
                        elif not inside:
                            self._errors |= _LrcErrors.NO_TIMESTAMP
                            self.lyrics.append(LyricsItem(
                                text=bracMatch['suffix']))
                            nonTagMatched = True
                        else:
                            self._errors |= _LrcErrors.BAD_CONTENTS
        
        # Looking for out of order timestamps...
        idx = 0
        while idx < len(self.lyrics):
            if self.lyrics[idx].timestamp is not None:
                prevTime = self.lyrics[idx].timestamp
                idx += 1
                break
        while idx < len(self.lyrics):
            if self.lyrics[idx].timestamp <= prevTime:
                self._errors |= _LrcErrors.OUT_OF_ORDER
                break
            else:
                prevTime = self.lyrics[idx].timestamp

    def Save(self) -> None:
        raise NotImplementedError()
    
    def errors(self) -> list[str]:
        raise NotImplementedError()
