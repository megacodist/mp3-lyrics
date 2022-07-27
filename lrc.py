from __future__ import annotations
from cgitb import text
from enum import IntFlag
from math import modf
from pathlib import Path
import re


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
            *,
            minutes: int = 0,
            seconds: int = 0,
            milliseconds: float = 0.0
            ) -> None:
        """Initializes an instance of Timestamp with the specified parts.
        If one of the parts is not of specified type, it raises TypeError.
        If one of the parts is not in the suitable interval, it raises
        ValueError.
        """
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


class LrcErrors(IntFlag):
    No_ERROR = 0x00
    DUPLICATE_TAGS = 0x01
    UNKNOWN_TAGS = 0x02
    BAD_DATA = 0x04
    BAD_LAYOUT = 0x08
    NO_TIMESTAMP = 0x10
    BAD_TIMESTAMP = 0x20
    OUT_OF_ORDER = 0x40


_lrcErrorMessages = {
    LrcErrors.DUPLICATE_TAGS: 'Some tags exist more than once.',
    LrcErrors.UNKNOWN_TAGS: 'There are some unknown tags.',
    LrcErrors.BAD_DATA: (
        'Some lines of the LRC file do not have a well-formed structure.'),
    LrcErrors.BAD_LAYOUT: 'Some tags are scattered throughout the LRC file.',
    LrcErrors.NO_TIMESTAMP: 'Some _lyrics do not have a timestamp.',
    LrcErrors.BAD_TIMESTAMP: 'Some timestamps are not valid.',
    LrcErrors.OUT_OF_ORDER: 'Timestamps are out of order.'}


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
    
    def __repr__(self) -> str:
        return (
            f'<{self.__class__} object '
            + f'timestamp: {str(self.timestamp)}, '
            + f'text: {self.text}'
            + '>')


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
            filename: str | Path | None = None,
            saveUnknownTags: bool = True,
            ) -> None:
        self.filename = filename
        self.saveUnknownTags = saveUnknownTags

        self._errors = LrcErrors.No_ERROR
        self.tags: dict[str, str] = {}
        self._unknownTags: dict[str, str] = {}
        self._lyrics: list[LyricsItem] = []

        self._Parse()
    
    @property
    def errors(self) -> LrcErrors:
        return self._errors
    
    @property
    def lyrics(self) -> list[LyricsItem]:
        return self._lyrics
    
    @lyrics.setter
    def lyrics(self, lrcs: list[LyricsItem]) -> None:
        raise NotImplementedError()

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
        TIME_REGEX = r'^(?P<mm>\d+):(?P<ss>\d+)(?P<xx>\.\d+)$'
        TAG_REGEX = r'^(?P<tag>\w+):(?P<value>.*)$'
        bracPattern = re.compile(BRAC_REGEX, re.VERBOSE)
        timePattern = re.compile(TIME_REGEX)
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
                    self._errors |= LrcErrors.NO_TIMESTAMP
                    self._lyrics.append(LyricsItem(line.strip()))
                    nonTagMatched = True
            else:
                prefix = bracMatch['prefix'].strip()
                if prefix:
                    self._errors |= LrcErrors.BAD_DATA
                else:
                    inside = bracMatch['inside']
                    # Matching against timestamp (mm:ss.xx)...
                    timeMatch = timePattern.match(inside)
                    if timeMatch:
                        try:
                            timestamp = Timestamp(
                                minutes=int(timeMatch['mm']),
                                seconds=int(timeMatch['ss']),
                                milliseconds=float(timeMatch['xx']))
                        except ValueError:
                            timestamp = None
                            self._errors |= LrcErrors.BAD_TIMESTAMP
                        self._lyrics.append(LyricsItem(
                            timestamp=timestamp,
                            text=bracMatch['suffix']))
                        nonTagMatched = True
                    else:
                        # Matching agianst tag pattern...
                        tagMatch = tagPattern.match(inside)
                        if tagMatch:
                            tag = tagMatch['tag']
                            if tag not in Lrc.TAGS:
                                self._errors |= LrcErrors.UNKNOWN_TAGS
                                self._unknownTags[tag] = tagMatch['value']
                            elif tag in self.tags:
                                self._errors |= LrcErrors.DUPLICATE_TAGS
                                self.tags[tag] = tagMatch['value']
                            else:
                                self.tags[tag] = tagMatch['value']
                            if nonTagMatched:
                                self._errors |= LrcErrors.BAD_LAYOUT
                        elif not inside:
                            self._errors |= LrcErrors.NO_TIMESTAMP
                            self._lyrics.append(LyricsItem(
                                text=bracMatch['suffix']))
                            nonTagMatched = True
                        else:
                            self._errors |= LrcErrors.BAD_DATA
        
        # Looking for out of order timestamps...
        idx = 0
        while idx < len(self._lyrics):
            if self._lyrics[idx].timestamp is not None:
                prevTime = self._lyrics[idx].timestamp
                idx += 1
                break
            idx += 1
        while idx < len(self._lyrics):
            if self._lyrics[idx].timestamp <= prevTime:
                self._errors |= LrcErrors.OUT_OF_ORDER
                break
            else:
                prevTime = self._lyrics[idx].timestamp
            idx += 1
    
    def AreTimstampsOk(self) -> bool:
        """Specifies whether timestamps are Ok."""
        return not(
            self._errors & LrcErrors.NO_TIMESTAMP
            | self._errors & LrcErrors.BAD_TIMESTAMP
            | self._errors & LrcErrors.OUT_OF_ORDER)
    
    def GetErrors(self) -> list[str]:
        """Returns a list of errors encountered parsing the LRC file. If
        no error was found, it returns an empty list.
        """
        errors: list[str] = []
        ERRORS: list[LrcErrors] = list(LrcErrors)[1:]
        for flag in ERRORS:
            if self._errors & flag == flag:
                errors.append(_lrcErrorMessages[flag])

    def Save(self) -> None:
        with open(self.filename, mode='wt') as lrcFile:
            # Writing tags...
            for tag, text in self.tags:
                lrcFile.write(f'[{tag}:{text}]\n')
            # Writing unknown tags...
            if self.saveUnknownTags:
                for tag, text in self._unknownTags:
                    lrcFile.write(f'[{tag}:{text}]\n')
            # Writing _lyrics...
            for _lyricsItem in self._lyrics:
                lrcFile.write(
                    f'[{str(_lyricsItem.timestamp)}] {_lyricsItem.text}\n')
    
    def __getitem__(self, __value: str | Timestamp, /) -> str:
        """Subscript can be used to tag values or lyrics at a specified
        timestamp. If the argument is string, it returns the tag's value,
        otherwise KeyError will be raised. If the argument if a Timestamp
        object, it returns the lyrics at that timestamp or raises
        KeyError.
        """
        if isinstance(__value, str):
            allTags = {**self.tags, **self._unknownTags}
            return allTags[__value]
        elif isinstance(__value, Timestamp):
            allLyrics = {
                lrcItem.timestamp:lrcItem.text
                for lrcItem in self._lyrics}
            return allLyrics[__value]
        else:
            raise TypeError(
                f"Expected 'str' or 'Timestamp' got '{type(__value)}'")
    
    def __repr__(self) -> str:
        return (
            f'{super().__repr__()}'
            + f'\nFile name: {self.filename}'
            + f'\nErrors: {self._errors.name}'
            + f'\nTags: {self.tags}'
            + f'\nUnknown tags: {self._unknownTags}'
            + f'\nLyrics: {self._lyrics}')
