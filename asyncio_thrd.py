import asyncio
from asyncio import Future
from fractions import Fraction
from pathlib import Path
import sys
from threading import Thread
from typing import Any, Callable, Iterable, Mapping, Optional

from mutagen import MutagenError
from mutagen.mp3 import MP3


class AsyncioThrd(Thread):
    def __init__(
            self,
            group: None = None,
            target: Callable[..., Any] | None = None,
            name: str | None = None,
            args: Iterable[Any] = (),
            kwargs: Mapping[str, Any] | None = {},
            *,
            daemon: bool | None = None
            ) -> None:
        super().__init__(
            group,
            target,
            name,
            args,
            kwargs,
            daemon=daemon)
        self._running = True
        self._TIME_INTRVL = 0.1
    
    def run(self) -> None:
        # Changing default event loop from Proactor to Selector on Windows
        # OS and Python 3.8+...
        if sys.platform.startswith('win'):
            if sys.version_info[:2] >= (3, 8,):
                asyncio.set_event_loop_policy(
                    asyncio.WindowsSelectorEventLoopPolicy())

        while self._running:
            try:
                # Setting up the asyncio event loop...
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                self.loop.run_forever()
            # Catching asyncio-related errors here...
            finally:
                self.loop.close()
    
    def close(self) -> None:
        # Because we definitely call this method from a thread other than
        # the thread initiated by run method, we call
        # self.loop.call_soon_threadsafe(self.loop.stop). But if we were
        # on the same thread, we must have called self.loop.stop()
        self._running = False
        self.loop.call_soon_threadsafe(self.loop.stop)
    
    '''def LoadMp3Files(
            self,
            folder: str,
            columns: list[AbstractSheetColumn],
            callback: Optional[Callable[[Fraction], None]] = None,
            ) -> Future[tuple[list[SheetRow], list[str]]]:
        """Accepts a directory and returns a pair of a list of ID3 tag
        of MP3 files in the directory and a list of filenames of MP3
        files which could not be read.
        """
        return asyncio.run_coroutine_threadsafe(
            self._LoadMp3Files(
                folder,
                columns,
                callback),
            self.loop)

    async def _LoadMp3Files(
            self,
            folder: str,
            columns: list[AbstractSheetColumn],
            callback: Optional[Callable[[Fraction], None]] = None,
            ) ->Future[tuple[list[SheetRow], list[str]]]:

        audios: list[SheetRow] = []
        errs: list[str] = []
        files = list(Path(folder).glob('*.mp3'))
        if not files:
            return audios, errs
        # Informing the start of the operation...
        if callback:
            callback(Fraction(0))
        idx = 0
        for file in files:
            try:
                mp3 = MP3(file)
                audios.append(SheetRow(mp3, columns))
            except MutagenError:
                errs.append(file)
            idx += 1
            if callback:
                callback(Fraction(idx, len(files)))
        return audios, errs'''
