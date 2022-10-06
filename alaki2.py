
import asyncio
from asyncio import AbstractEventLoop
from datetime import timedelta
from pathlib import Path

from app_utils import AbstractPlayer

from ffmpeg import FFmpeg


class Player(AbstractPlayer):
    def __init__(
            self,
            audio: str | Path,
            loop: AbstractEventLoop | None = None
            ) -> None:
        super().__init__(audio)

        # Initializing the FFmpeg...
        self._ffmpeg = FFmpeg(
            'ffplay'
        ).option(
            'hide_banner'
        ).option(
            'nodisp'
        ).option(
            'autoexit'
        )
        self._ffmpeg.on('start', self._OnFFmpegStarted)
        self._ffmpeg.on('stderr', self._OnFFmpegStderr)
        self._ffmpeg.on('progress', self._OnFFmpegProgress)
        self._ffmpeg.on('completed', self._OnFFmpegCompleted)
        self._ffmpeg.on('terminated', self._OnFFmpegTerminated)
        self._ffmpeg.on('error', self._OnFFmpegError)

        # Getting this thread asyncio event loop...
        if loop is None or not isinstance(loop, AbstractEventLoop):
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
            # Running the entry point...
            asyncio.set_event_loop(self._loop)
        else:
            self._loop = loop

    def _OnFFmpegStarted(self, args: list[str]) -> None:
        """Will be raised when thew playback starts."""
        pass

    def _OnFFmpegStderr(self, line: str) -> None:
        if not hasattr(self, '_alaki'):
            print('stderr', type(line))
        self._alaki = True

    def _OnFFmpegProgress(self, progress) -> None:
        print('progress', type(progress))

    def _OnFFmpegCompleted(self) -> None:
        """Will be raised when the playback finishes."""
        pass

    def _OnFFmpegTerminated(self) -> None:
        """Will be raised when the playback is terminated by client code."""
        pass

    def _OnFFmpegError(self, error) -> None:
        print('Error', type(error))

    def volumn(self, __volume: int, /) -> None:
        self._volume = __volume
        if self._ffmpeg._executed:
            self._ffmpeg.terminate()
            self.Play()

    def pos(self, __pos: int, /) -> None:
        self._pos = __pos
        if self._ffmpeg._executed:
            self._ffmpeg.terminate()
            self.Play()

    def Play(self) -> None:
        self._ffmpeg = self._ffmpeg.input(
            self._audioLocation,
            ss=str(timedelta(seconds=self._pos)),
            volume=self._volume)
        self._loop.run_until_complete(self._ffmpeg.execute())

    def Pause(self) -> None:
        pass

    def Stop(self) -> None:
        self._pos = 0.0
        self._ffmpeg.terminate()



mmm = Player(r'h:\1.mp3')
mmm.Play()


"""async def main() -> None:
    import subprocess
    CEND = '\33[0m'
    CGREEN = '\33[32m'
    CBLUE = '\33[34m'

    options = (
        '-hide_banner',
        '-nodisp',
        '-autoexit',
        r'h:\1.mp3',
        '-loop', '1')
    audioProc: Process = await asyncio.create_subprocess_exec(
        'ffplay',
        *options,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    while audioProc.returncode is None:
        output, err = await audioProc.communicate()
        output = str(output).strip()
        err = str(err).strip()
        if output:
            print(CBLUE, output, CEND, end='')
        if err:
            print(CGREEN, err, CEND, end='')
        print(end='', flush=True)


if __name__ == '__main__':
    '''# Changing default event loop from Proactor to Selector on Windows
    # OS and Python 3.8+...
    if sys.platform.startswith('win'):
        if sys.version_info[:2] >= (3, 8,):
            asyncio.set_event_loop_policy(
                asyncio.WindowsSelectorEventLoopPolicy())'''
    # Getting this thread asyncio event loop...
    try:
        asyncLoop = asyncio.get_running_loop()
    except RuntimeError:
        asyncLoop = asyncio.new_event_loop()
    # Running the entry point...
    asyncio.set_event_loop(asyncLoop)
    asyncLoop.run_until_complete(main())"""