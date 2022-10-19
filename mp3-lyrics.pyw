from pathlib import Path

from asyncio_thrd import AsyncioThrd
from mp3_lyrics_win import Mp3LyricsWin
from app_utils import AbstractPlayer, AppSettings
from app_utils import ConfigureLogging, SetUnsupFile
import player


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

    # Finding & loading the implementation of Player...
    playerClass: type = None
    for entity in dir(player):
        entity = getattr(player, entity)
        try:
            if AbstractPlayer in entity.__bases__:
                playerClass = entity
                break
        except AttributeError:
            pass

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
        asyncio_thrd=asyncioThrd,
        playrClass=playerClass)
    mp3TagsWin.mainloop()

    # Finalizing...
    AppSettings().Save()
    asyncioThrd.close()
