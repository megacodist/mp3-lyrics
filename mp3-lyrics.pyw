from inspect import isabstract
import logging
from pathlib import Path
import sys
from typing import Type

from media.abstract_mp3 import AbstractMp3
from asyncio_thrd import AsyncioThrd
try:
    import media.mp3 as mp3Module
except ImportError:
    sys.stderr.write("'mp3.py' has not been found")
    sys.exit(1)
from mp3_lyrics_win import Mp3LyricsWin
from app_utils import AppSettings
from app_utils import ConfigureLogging, SetUnsupFile


# Definning global variables...
_APP_DIR = Path(__file__).resolve().parent


if __name__ == '__main__':
    # Configuring logging...
    ConfigureLogging(_APP_DIR / 'log.log')

    # Configuring unsupported values...
    filename = _APP_DIR / 'unsup.txt'
    if not filename.exists():
        with open(file=filename, mode='x') as fileobj:
            pass
    SetUnsupFile(filename)
    
    # Finding & loading implementations of MP3 library...
    mp3LibStuff = dir(mp3Module)
    # Looking for the MP3 implementation...
    mp3Class: Type[AbstractMp3] | None = None
    for item in mp3LibStuff:
        item = getattr(mp3Module, item)
        if issubclass(item, AbstractMp3):
            if not isabstract(item):
                mp3Class = item
                break
    else:
        msg_noAbsImpl = "Invalid 'mp3.py', no AbstractMp3 implementation"
        sys.stderr.write(msg_noAbsImpl)
        logging.critical(msg_noAbsImpl)
        sys.exit(1)

    # Loading application settings...
    filename = _APP_DIR / 'bin.bin'
    if not filename.exists():
        with open(file=filename, mode='x') as fileobj:
            pass
    AppSettings().Load(filename)

    # Starting the Async I/O thread...
    asyncioThrd = AsyncioThrd(name='AsyncioThrd')
    asyncioThrd.start()

    # running the application...
    mp3LyricsWin = Mp3LyricsWin(
        res_dir=_APP_DIR / 'res',
        asyncio_thrd=asyncioThrd,
        mp3_class=mp3Class)
    mp3LyricsWin.mainloop()

    # Finalizing...
    print('Saving settings...')
    AppSettings().Save()
    print('Closing the Async I/O thread...')
    asyncioThrd.close()
