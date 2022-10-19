import asyncio
from asyncio import AbstractEventLoop
from concurrent.futures import ProcessPoolExecutor, Future
from concurrent.futures import CancelledError
from pathlib import Path
import sys
from threading import Thread
from typing import Any, Callable, Iterable, Mapping

from lrc import Lrc
from win_utils import LoadingFolderInfo


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
        self.loop: AbstractEventLoop
        self.pool: ProcessPoolExecutor
    
    def run(self) -> None:
        '''# Changing default event loop from Proactor to Selector on Windows
        # OS and Python 3.8+...
        if sys.platform.startswith('win'):
            if sys.version_info[:2] >= (3, 8,):
                asyncio.set_event_loop_policy(
                    asyncio.WindowsSelectorEventLoopPolicy())'''

        while self._running:
            try:
                # creating a subprocess per CPU cores/threads...
                self.pool = ProcessPoolExecutor()
                # Setting up the asyncio event loop...
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                self.loop.run_forever()
            # Catching asyncio-related errors here...
            finally:
                self.loop.close()
                self.pool.shutdown()
    
    def close(self) -> None:
        # Because we definitely call this method from a thread other than
        # the thread initiated by run method, we call
        # self.loop.call_soon_threadsafe(self.loop.stop). But if we were
        # on the same thread, we must have called self.loop.stop()
        self._running = False
        self.loop.call_soon_threadsafe(self.loop.stop)
    
    def LoadFolder(
            self,
            mp3_file: str,
            *,
            key: Callable[[str], Any] | None = None
            ) -> Future[LoadingFolderInfo]:
        return asyncio.run_coroutine_threadsafe(
            self._LoadFolder(mp3_file, key=key),
            self.loop)

    async def _LoadFolder(
            self,
            mp3_file: str,
            key: Callable[[str], Any] | None = None
            ) -> Future[LoadingFolderInfo]:
        mp3PathObj = Path(mp3_file).resolve()
        # Getting folder...
        folder = str(mp3PathObj.parent)
        # Getting MP3 files in the folder...
        mp3s = list(Path(folder).glob('*.mp3'))
        mp3s.sort(key=key)
        mp3s = [
            path.name
            for path in mp3s]
        # Getting the index of selected MP3 file...
        try:
            selectIdx = mp3s.index(mp3PathObj.name)
        except ValueError:
            selectIdx = None
        return LoadingFolderInfo(
            folder=folder,
            mp3s=mp3s,
            selectIdx=selectIdx)
    
    def LoadLrc(
            self,
            lrcFile: str,
            toCreate: bool = False
            ) -> Lrc:
        return asyncio.run_coroutine_threadsafe(
            self._LoadLrc(lrcFile, toCreate),
            self.loop)

    async def _LoadLrc(
            self,
            lrcFile: str,
            toCreate: bool = False
            ) -> Lrc:
        try:
            pLrc = Path(lrcFile)
            if toCreate and (not pLrc.exists()):
                Lrc.CreateLrc(lrcFile)
            return await self.loop.run_in_executor(
                self.pool,
                Lrc,
                lrcFile)
        except CancelledError:
            pass
