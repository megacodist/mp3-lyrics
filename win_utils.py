from concurrent.futures import Future
from enum import IntEnum
from pathlib import Path

from attrs import define, field

from widgets.wait_frame import WaitFrame


class AfterPlayed(IntEnum):
    STOP_PLAYING = 0
    REPEAT = 1
    PLAY_FOLDER = 2
    REPEAT_FOLDER = 3


class AfterProcessInfo:
    def __init__(
            self,
            future : Future,
            afterID: str,
            ) -> None:
        self.future = future
        self.afterID = afterID
    
    def __del__(self) -> None:
        # Deallocating inside resources...
        del self.future
        del self.afterID


class LoadingFolderAfterInfo(AfterProcessInfo):
    def __init__(
            self,
            future: Future,
            afterID: str,
            folder: str,
            waitFrame: WaitFrame | None = None
            ) -> None:
        super().__init__(future, afterID)
        self.folder = folder
        self.waitFrame = waitFrame
    
    def __del__(self) -> None:
        # Breaking inbound refrences...
        self.folder = None
        # Deallocating inside resources...
        del self.waitFrame
        # Deallocating 'future' & 'afterID' in super class...
        super().__del__()


class LoadingLrcAfterInfo(AfterProcessInfo):
    def __init__(
            self,
            future: Future,
            afterID: str,
            mp3File: str | Path,
            waitFrames: list[WaitFrame] | None = None
            ) -> None:
        super().__init__(future, afterID)
        self.mp3File = mp3File
        self.waitFrames = waitFrames
    
    def __del__(self) -> None:
        # Breaking inbound refrences...
        self.mp3File = None
        # Deallocating inside resources...
        for wf in self.waitFrames:
            del wf
        # Deallocating 'future' & 'afterID' in super class...
        super().__del__()
    
    def ShowWaitFrames(self) -> None:
        for wf in self.waitFrames:
            wf.Show()
    
    def CancelWaitFrames(self) -> None:
        for wf in self.waitFrames:
            wf.ShowCanceling()
    
    def CloseWaitFrames(self) -> None:
        for wf in self.waitFrames:
            wf.Close()


@define
class LoadingFolderInfo:
    folder: str
    mp3s: list[str]
    selectIdx: int | None = field(
        default=None)
