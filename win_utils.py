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


@define
class LoadingFolderInfo:
    folder: str
    mp3s: list[str]
    selectIdx: int | None = field(
        default=None)
