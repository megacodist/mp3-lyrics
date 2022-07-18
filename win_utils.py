from asyncio import Future

from attrs import define, field


@define
class AfterProcessInfo:
    future: Future
    afterID: str


@define
class LoadingFolderInfo:
    folder: str
    mp3s: list[str]
    selectIdx: int | None = field(
        default=None)
