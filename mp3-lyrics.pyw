from pathlib import Path

from abstract_mp3_lib import AbstractMP3Info, AbstractMP3Player
from abstract_mp3_lib import AbstractMP3Editor
from asyncio_thrd import AsyncioThrd
import mp3_lib
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

    '''# Finding & loading the implementation of Player...
    playerClass: type = None
    for entity in dir(player):
        entity = getattr(player, entity)
        try:
            if AbstractPlayer in entity.__bases__:
                playerClass = entity
                break
        except AttributeError:
            pass'''
    
    # Finding & loading implementations of MP3 library...
    mp3LibStuff = dir(mp3_lib)
    # Looking for the MP3 info implementation...
    for item in mp3LibStuff:
        item = getattr(mp3_lib, item)
        try:
            if AbstractMP3Info in item.__bases__:
                mp3InfoClass = item
                break
        except AttributeError:
            pass
    # Looking for the MP3 player implementation...
    for item in mp3LibStuff:
        item = getattr(mp3_lib, item)
        try:
            if AbstractMP3Player in item.__bases__:
                mp3PlayerClass = item
                break
        except AttributeError:
            pass
    # Looking for the MP3 editor implementation...
    for item in mp3LibStuff:
        item = getattr(mp3_lib, item)
        try:
            if AbstractMP3Editor in item.__bases__:
                mp3EditorClass = item
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
        mp3InfoClass=mp3InfoClass,
        mp3PlayrClass=mp3PlayerClass,
        mp3EditorClass=mp3EditorClass)
    mp3TagsWin.mainloop()

    # Finalizing...
    AppSettings().Save()
    asyncioThrd.close()
