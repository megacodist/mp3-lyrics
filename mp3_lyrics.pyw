from pathlib import Path

from asyncio_thrd import AsyncioThrd
from mp3_lyrics_win import Mp3LyricsWin
from app_utils import ConfigureLogging, AppSettings, SetUnsupFile


# Definning global variables...
_MODULE_DIR = Path(__file__).resolve().parent


if __name__ == '__main__':
    # Configuring logging...
    ConfigureLogging(_MODULE_DIR / 'log.log')

    # Configuring unsupported values...
    filename = _MODULE_DIR / 'unsup.txt'
    if not filename.exists():
        with open(file=filename, mode='x') as fileobj:
            pass
    SetUnsupFile(filename)

    # Loading application settings...
    filename = _MODULE_DIR / 'bin.bin'
    if not filename.exists():
        with open(file=filename, mode='x') as fileobj:
            pass
    AppSettings().Load(filename)

    # Starting the Async I/O thread...
    asyncioThrd = AsyncioThrd(name='AsyncioThrd')
    asyncioThrd.start()

    # running the application...
    mp3TagsWin = Mp3LyricsWin(
        res_dir=_MODULE_DIR / 'res',
        asyncio_thrd=asyncioThrd)
    mp3TagsWin.mainloop()

    # Finalizing...
    AppSettings().Save()
    asyncioThrd.close()
