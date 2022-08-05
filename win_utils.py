from concurrent.futures import Future
from enum import IntEnum
from pathlib import Path

from attrs import define, field

from widgets import WaitFrame


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
        del self.future
        del self.afterID


class LoadingFolderAfterInfo(AfterProcessInfo):
    def __init__(
            self,
            future: Future,
            afterID: str,
            waitFrame: WaitFrame | None = None
            ) -> None:
        super().__init__(future, afterID)
        self.waitFrame = waitFrame
    
    def __del__(self) -> None:
        self.waitFrame = None
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
        for wf in self.waitFrames:
            wf = None
        del self.mp3File
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
