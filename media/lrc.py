"""This module exposes API to parse and work with LRC files which are
accompanying resource for some MP3 files.
"""

from __future__ import annotations
from copy import deepcopy
from enum import IntFlag
from math import modf
from os import PathLike
from pathlib import Path
import re
from typing import overload


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
    def FromFloat(
            cls,
            seconds: float,
            *,
            ndigits: int = 2
            ) -> Timestamp:
        """Converts a floating-pont number to an instance of Timastamp, for
        examle 87.3 will be converted to 1:17.3. The 'ndigits' keyword
        specifies number of digits after decimal point to kep.
        """
        seconds = round(seconds, ndigits)
        xx, secs = modf(seconds)
        mm, ss = divmod(int(secs), 60)
        return Timestamp(
            minutes=mm,
            seconds=ss,
            milliseconds=round(xx, ndigits))

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
    DUPLICATE_TIMESTAMPS= 0x40
    OUT_OF_ORDER = 0x80


_lrcErrorMessages = {
    LrcErrors.DUPLICATE_TAGS: 'Some tags exist more than once.',
    LrcErrors.UNKNOWN_TAGS: 'There are some unknown tags.',
    LrcErrors.BAD_DATA:
        'Some lines of the LRC file do not have a well-formed structure.',
    LrcErrors.BAD_LAYOUT: 'Some tags are scattered throughout the LRC file.',
    LrcErrors.NO_TIMESTAMP: 'Some lyrics do not have a timestamp.',
    LrcErrors.BAD_TIMESTAMP: 'Some timestamps are not valid.',
    LrcErrors.DUPLICATE_TIMESTAMPS: 'Some lyrics have the same timestamps.',
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

    def __setitem__(self, __idx: int, __value: str | Timestamp, /) -> None:
        if __idx == 0:
            if isinstance(__value, str):
                if __value == '':
                    self.timestamp = None
                else:
                    self.timestamp = Timestamp.FromString(__value)
            elif isinstance(__value, Timestamp):
                self.timestamp = __value
            else:
                raise TypeError(
                    "Item for index 0 of a 'LyricsItem' must be Timestamp")
        elif __idx == 1:
            if not isinstance(__value, str):
                raise TypeError(
                    "Item for index 0 of a 'LyricsItem' must be string")
            self.text = __value
        else:
            raise TypeError(
                "Item assignment for 'LyricsItem' only supports 0 or 1")
    
    def __len__(self) -> int:
        return 2
    
    def __repr__(self) -> str:
        return (
            f'<{self.__class__.__module__}.{self.__class__.__name__} object '
            + f'timestamp: {str(self.timestamp)}, '
            + f'text: {self.text}'
            + '>')


class Lrc:
    """Parses and manipulates LRC files. To load an LRC file, you must pass
    its file system address to the constructor. To get the LRC file
    associated with a file, pass that file name to the GetLrcFilename class
    method. Instances of this class are not thread safe.

    Use subscript to manipulate tags (read, set, or delete a specified tag)
    but to do operations with LyricsItems, get a snapshot from lyrics
    property, apply changes you want and set it to lyrics property.
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
    def GetLrcFilename(cls, filename: PathLike) -> Path:
        """Returns the probably LRC file name associated with 'filename'
        parameter. This LRC file might exist or not.
        """
        pth = filename if isinstance(filename, Path) else Path(filename)
        return pth.with_suffix('.lrc')
    
    @classmethod
    def CreateLrc(cls, filename: str | Path) -> None:
        """Creates the specified LRC file.
        
        Exceptions:
        TypeError: 'filename' is not either a string or a Path object
        ValueError: 'filename' does not have '.lrc' extension
        """
        # Checking the correctness of 'filename' parameter...
        if isinstance(filename, str):
            filename = Path(filename)
        elif not isinstance(filename, Path):
            raise TypeError(
                "'filename' must be either a string or a Path object")
        if filename.suffix != '.lrc':
            raise ValueError("'filename' does not have '.lrc' extension")
        
        # Creating the LRC file...
        with open(filename, mode='xt') as lrcFileObj:
            pass

    def __init__(
            self,
            filename: str | Path,
            toSaveUnknownTags: bool = False,
            toSaveNoTimestamps: bool = False,
            ) -> None:
        """Loads the specified 'filename' as LRC file and returns an Lrc
        object. 
        """
        self._nDuplicates: int = 0

        # Initializing properties...
        self._filename: str | Path = filename
        self._errors = LrcErrors.No_ERROR
        self._tags: dict[str, str | list[str]] = {}
        self._unknownTags: dict[str, str | list[str]] = {}
        self._lyrics: list[LyricsItem] = []
        self._changed: bool = False

        # Initializing attributes...
        self._toSaveUnknownTags: bool
        self.toSaveUnknownTags = toSaveUnknownTags
        self._toSaveNoTimestamps: bool
        self.toSaveNoTimestamps = toSaveNoTimestamps

        self._Parse()
    
    @property
    def filename(self) -> str | Path:
        """Gets the filename (file system address) of this Lrc object."""
        return self._filename
    
    @property
    def toSaveUnknownTags(self) -> bool:
        """Gets or sets a boolean value indicating unknown tags must be
        saved via 'Save' method.
        """
        return self._toSaveUnknownTags

    @toSaveUnknownTags.setter
    def toSaveUnknownTags(self, __snt: bool, /) -> None:
        if not isinstance(__snt, bool):
            raise TypeError("'toSaveUnknownTags' must be boolean")
        self._toSaveUnknownTags = __snt
    
    @property
    def toSaveNoTimestamps(self) -> bool:
        """Gets or sets  a boolean value indicating LyricsItems with no
        timestamps must be saved via 'Save' method.
        """
        return self._toSaveNoTimestamps

    @toSaveNoTimestamps.setter
    def toSaveNoTimestamps(self, __snt: bool, /) -> None:
        if not isinstance(__snt, bool):
            raise TypeError("'toSaveNoTimestamps' must be boolean")
        self._toSaveNoTimestamps = __snt
    
    @property
    def tags(self) -> dict[str, str | list[str]]:
        """Gets a dictinary containing all tags of this object. Every tag
        correspond to a string (tag value) or a list of string (in the case
        of LrcErrors.DUPLICATE_TAGS error). This is a copy of the underlying
        attribute.
        """
        return deepcopy(self._tags)
    
    @property
    def unknownTags(self) -> dict[str, str | list[str]]:
        """Gets a dictinary containing all unknown tags of this object.
        Every tag correspond to a string (tag value) or a list of string
        (in the case of LrcErrors.DUPLICATE_TAGS error).  This is a copy of
        the underlying attribute.
        """
        return deepcopy(self._unknownTags)
    
    @property
    def errors(self) -> LrcErrors:
        return self._errors
    
    @property
    def changed(self) -> bool:
        """Gets a boolean value specifying whether this object has been
        modified after instantiation or last Save method.
        """
        return self._changed
    
    @property
    def lyrics(self) -> list[LyricsItem]:
        """Gets or sets lyrics items of this Lrc object. It returns a copy
        of the list of LyricsItems of this Lrc object. To change LyricsItems
        of this object, first get a copy by this property, apply changes you
        want and set it to this property.
        
        Exceptions:
        ⬤ TypeError: The r-value is not a list of LyricsItems.
        ⬤ ValueError: Some timestamps in r-value are either unspecified or
        duplicate or out of order.
        """
        return deepcopy(self._lyrics)
    
    @lyrics.setter
    def lyrics(self, lrcs: list[LyricsItem]) -> None:
        # Backing up the errors...
        backup: LrcErrors = self._errors
        # Checking lrcs data accuracy...
        try:
            for lrcItem in lrcs:
                if not isinstance(lrcItem.text, str):
                    raise Exception()
            self._CheckTimestamps(lrcs)
        except Exception:
            self._errors = backup
            raise TypeError(
                "'lrcs' is expected to be a list of 'LyricsItem's")
        if (
                not self._toSaveNoTimestamps
                and self._errors & LrcErrors.NO_TIMESTAMP == 
                    LrcErrors.NO_TIMESTAMP):
            self._errors = backup
            raise ValueError("Timestamps must be specified")
        tsErrors = (
            LrcErrors.BAD_TIMESTAMP
            | LrcErrors.DUPLICATE_TIMESTAMPS
            | LrcErrors.OUT_OF_ORDER)
        if self._errors & tsErrors:
            self._errors = backup
            raise ValueError(
                "Timestamps must be specified, unique, and in order")
        # Setting lyrics...
        self._lyrics = lrcs
        self._changed = True

    def _Parse(self) -> None:
        """Parses the file and initializes the attributes."""
        if self._filename is None:
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
        with open(self._filename, mode='rt', encoding='utf-8') as lrcFile:
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
                                if tag in self._unknownTags:
                                    try:
                                        self._unknownTags[tag].append(
                                            tagMatch['value'])
                                    except AttributeError:
                                        self._unknownTags[tag] = [
                                            self._unknownTags[tag],
                                            tagMatch['value']]
                                        self._nDuplicates += 1
                                    self._errors |= LrcErrors.DUPLICATE_TAGS
                                else:
                                    self._unknownTags[tag] = tagMatch['value']
                            elif tag in self._tags:
                                self._errors |= LrcErrors.DUPLICATE_TAGS
                                try:
                                    self._tags.append(tagMatch['value'])
                                except AttributeError:
                                    self._tags[tag] = [
                                            self._tags[tag],
                                            tagMatch['value']]
                            else:
                                self._tags[tag] = tagMatch['value']
                            if nonTagMatched:
                                self._errors |= LrcErrors.BAD_LAYOUT
                        elif not inside:
                            self._errors |= LrcErrors.NO_TIMESTAMP
                            self._lyrics.append(LyricsItem(
                                text=bracMatch['suffix']))
                            nonTagMatched = True
                        else:
                            self._errors |= LrcErrors.BAD_DATA
        
        # Looking for timestamps errors...
        self._CheckTimestamps(self._lyrics)
    
    def _CheckTimestamps(self, lrcs: list[LyricsItem]) -> None:
        """Checks a list of LyricsItems for NO_TIMESTAMP, OUT_OF_ORDER,
        and DUPLICATE_TIMESTAMPS errors.
        """
        lrcs_ = [
            lrcItem.timestamp
            for lrcItem in lrcs
            if lrcItem.timestamp is not None]
        # Looking for NO_TIMESTAMP...
        if len(lrcs_) < len(lrcs):
            self._errors |= LrcErrors.NO_TIMESTAMP
        else:
            self._errors &= (~LrcErrors.NO_TIMESTAMP)
        # Looking for OUT_OF_ORDER...
        idx = 0
        while True:
            try:
                if lrcs_[idx] > lrcs_[idx + 1]:
                    self._errors |= LrcErrors.OUT_OF_ORDER
                    break
                idx += 1
            except IndexError:
                self._errors &= (~LrcErrors.OUT_OF_ORDER)
                break
        # Looking for DUPLICATE_TIMESTAMPS...
        lrcs_.sort()
        idx = 0
        while True:
            try:
                if lrcs_[idx] == lrcs_[idx + 1]:
                    self._errors |= LrcErrors.DUPLICATE_TIMESTAMPS
                    break
                idx += 1
            except IndexError:
                self._errors &= (~LrcErrors.DUPLICATE_TIMESTAMPS)
                break
    
    def AreTimstampsOk(self) -> bool:
        """Specifies whether timestamps are Ok and there is no error
        associated with them.
        """
        return not(
            self._errors & LrcErrors.NO_TIMESTAMP
            | self._errors & LrcErrors.BAD_TIMESTAMP
            | self._errors & LrcErrors.DUPLICATE_TIMESTAMPS
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
        return errors

    def Save(self) -> None:
        """Saves this object to the filename and sets changed property to
        False. It also resolves BAD_DATA, BAD_LAYOUT, and DUPLICATE_TAGS if
        there are, and hence removes their flags. Before calling this API,
        it is possible to change toSaveUnknownTags attribute.
        """
        with open(self._filename, mode='wt', encoding='utf-8') as lrcFile:
            # Writing tags to the file...
            for tag, value in self._tags.items():
                if isinstance(value, str):
                    lrcFile.write(f'[{tag}:{value}]\n')
                else:
                    lrcFile.write(f'[{tag}:{value[-1]}]\n')
            nAllTags = len(self._tags)

            # Writing unknown tags to the file...
            if self.toSaveUnknownTags and self._unknownTags:
                for tag, value in self._unknownTags.items():
                    if isinstance(value, str):
                        lrcFile.write(f'[{tag}:{value}]\n')
                    else:
                        lrcFile.write(f'[{tag}:{value[-1]}]\n')
                nAllTags += len(self._unknownTags)
                self._errors |= LrcErrors.UNKNOWN_TAGS
            else:
                # Removing UNKNOWN_TAGS flag...
                self._errors &= (~LrcErrors.UNKNOWN_TAGS)
            
            # Printing an empty line between tags & lyrics...
            if nAllTags:
                lrcFile.write('\n')

            # Writing lyrics to the file...
            for lyricsItem in self._lyrics:
                if lyricsItem.timestamp is None:
                    timestamp = ''
                else:
                    timestamp = lyricsItem.timestamp
                lrcFile.write(
                    f'[{str(timestamp)}]{lyricsItem.text}\n')

        # Removing some flags...
        self._changed = False
        self._errors &= (~LrcErrors.BAD_DATA)
        self._errors &= (~LrcErrors.BAD_LAYOUT)
        self._errors &= (~LrcErrors.DUPLICATE_TAGS)
    
    @overload
    def __getitem__(self, __tag: str, /) -> str | list[str]:
        ...
    
    @overload
    def __getitem__(self, __idx: int, /) -> LyricsItem:
        ...

    def __getitem__(
            self,
            __value: str | int,
            /
            ) -> str | list[str] | LyricsItem:
        """Subscript can be used to get tag values or LyricsItems.
        If the argument is a string, it returns the tag's value, if the
        argument is an integer, it returns the LyricsItem in lyrics property
        at that index.

        Exceptions:
        ⬤ KeyError: if '__value' is a string and does not exist in either
        tags or unknown tags dictionaries.
        ⬤ IndexError: if '__value' is an integer and does not exist in the
        lyrics property.
        ⬤ TypeError: if '__value' is not either string or integer objects.
        """
        if isinstance(__value, str):
            try:
                return self._tags[__value]
            except KeyError:
                try:
                    return self._unknownTags[__value]
                except KeyError:
                    raise KeyError(
                        f"'{__value}' does not exist"
                        + " in tags nor unknown tags.")
            allTags = {**self._tags, **self._unknownTags}
            return allTags[__value]
        elif isinstance(__value, int):
            return self._lyrics[__value]
        else:
            raise TypeError(
                f"Expected 'str' or 'int' got '{type(__value).__name__}'")
    
    def __setitem__(self, __tag: str, __text: str, /) -> None:
        """Assigning to subscript is required to perform with tags and
        unknown tags not lyrics.
        """
        if not isinstance(__tag, str):
            raise TypeError("The subscript must ba a string")
        if not isinstance(__text, str):
            raise TypeError(
                "Only strings are allowed to be assigned to subscript")
        if __tag in Lrc.TAGS:
            try:
                if __text != self._tags[__tag]:
                    self._changed = True
            except Exception:
                self._changed = True
            self._tags[__tag] = __text
        else:
            try:
                if __text != self._unknownTags[__tag]:
                    self._changed = True
            except Exception:
                self._changed = True
            self._unknownTags[__tag] = __text
            self._errors |= LrcErrors.UNKNOWN_TAGS
    
    def __delitem__(self, __value: str | int) -> None:
        """Deletes the specified tag or index at lyrics property."""
        if isinstance(__value, str):
            try:
                del self._tags[__value]
                self._changed = True
            except KeyError:
                try:
                    del self._unknownTags[__value]
                    self._changed = True
                    if not self._unknownTags:
                        self._errors &= (~LrcErrors.UNKNOWN_TAGS)
                except KeyError:
                    raise KeyError(
                        f"'{__value}' does not exist"
                        + " in tags nor unknown tags.")
        elif isinstance(__value, int):
            del self._lyrics[__value]
            self._changed = True
        else:
            raise TypeError(
                f"Expected 'str' or 'int' got '{type(__value).__name__}'")
    
    def RemoveDupElem(self, tag: str, idx: int) -> None:
        """
        Exceptions:
        ⬤ TypeError: Invalid object types for arguments.
        ⬤ ValueError: tag is not duplicate
        ⬤ IndexError: if '__value' is not either string or integer objects.
        """
        if not isinstance(tag, str):
            raise TypeError("'tag' must be a string")
        if not isinstance(idx, int):
            raise TypeError("'idx' must be an integer")
        allTags = {**self._tags, **self._unknownTags}
        if tag in allTags:
            if isinstance(allTags, str):
                raise ValueError("'tag' is not duplicate")
            del allTags[tag][idx]
            if len(allTags[tag]) == 1:
                allTags[tag] = allTags[tag][0]
                self._nDuplicates -= 1
                if self._nDuplicates == 0:
                    self._errors &= (~LrcErrors.DUPLICATE_TAGS)
        else:
            raise ValueError("'tag' is not available")
    
    def __repr__(self) -> str:
        return (
            f'{super().__repr__()}'
            + f'\nFile name: {self._filename}'
            + f'\nErrors: {self._errors.name}'
            + f'\nTags: {self._tags}'
            + f'\nUnknown tags: {self._unknownTags}'
            + f'\nLyrics: {self._lyrics}')
