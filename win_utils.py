from concurrent.futures import Future
from enum import IntEnum

from attrs import define, field

from widgets import WaitFrame


class AfterProcessInfo:
    def __init__(
            self,
            future : Future,
            afterID: str,
            waitFrame: WaitFrame | None = None
            ) -> None:
        self.future = future
        self.afterID = afterID
        self.waitFrame = waitFrame
    
    def __del__(self) -> None:
        self.waitFrame = None
        del self.future
        del self.afterID


@define
class LoadingFolderInfo:
    folder: str
    mp3s: list[str]
    selectIdx: int | None = field(
        default=None)
