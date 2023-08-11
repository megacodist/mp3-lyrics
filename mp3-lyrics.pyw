from inspect import isabstract
import logging
from pathlib import Path
import sys
from typing import Type

from abstract_mp3 import AbstractMP3
from asyncio_thrd import AsyncioThrd
try:
    import mp3
except ImportError:
    sys.stderr.write("'mp3.py' has not been found")
    sys.exit(1)
from mp3_lyrics_win import Mp3LyricsWin
from app_utils import AppSettings
from app_utils import ConfigureLogging, SetUnsupFile


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
    
    # Finding & loading implementations of MP3 library...
    mp3LibStuff = dir(mp3)
    # Looking for the MP3 implementation...
    mp3Class: Type[AbstractMP3] | None = None
    for item in mp3LibStuff:
        item = getattr(mp3, item)
        if issubclass(item, AbstractMP3):
            if not isabstract(item):
                mp3Class = item
                break
    else:
        msg_noAbsImpl = "Invalid 'mp3.py', no AbstractMP3 implementation"
        sys.stderr.write(msg_noAbsImpl)
        logging.critical(msg_noAbsImpl)
        sys.exit(1)

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
        mp3Class=mp3Class)
    mp3TagsWin.mainloop()

    # Finalizing...
    AppSettings().Save()
    asyncioThrd.close()
