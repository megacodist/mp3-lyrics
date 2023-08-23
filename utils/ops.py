#
# 
#
"""This mosule offers operations for `mp3_lyrics_win` module.
"""

from collections import OrderedDict
from os import PathLike
from pathlib import Path
from queue import Queue
import tkinter as tk
from typing import Callable, Iterable

from media import AbstractPlaylist
from media.lrc import Lrc
from widgets.playlist_view import PlaylistItem


_PLVW_TAGS = OrderedDict()
"""This ordered dictionary keeps tags to be shown in the playlist view
widget.
"""
_PLVW_TAGS['TIT2'] = 'Title'
_PLVW_TAGS['TALB'] = 'Album'
_PLVW_TAGS['TPE1'] = 'Artist'


def LoadPlaylist(
        playlist: Path,
        master: tk.Misc,
        q: Queue | None,
        added_cb: Callable[[Path], None] | None = None,
        changed_cb: Callable[[Path], None] | None = None,
        deleted_cb: Callable[[Path], None] | None = None,
        ) -> tuple[AbstractPlaylist, Iterable[PlaylistItem]]:
    """Accepts a `Path` object to a playlist and returns the playlist
    object and all included audios in the playlist as a 2-tuple. It
    returns `(None, None)` on any error.
    """
    from collections import OrderedDict
    from media import PLAYLIST_EXTS, FolderPlaylist, GetAllTags
    if q:
        q.put(f'Loading playlist\n{playlist}')
    if playlist.is_dir():
        playlistObj = FolderPlaylist(
            master=master,
            dir_=playlist,
            added_cb=added_cb,
            changed_cb=changed_cb,
            deleted_cb=deleted_cb)
    elif Path(playlist.suffix) in PLAYLIST_EXTS:
        pass
    else:
        return None, None
    plyItems: list[PlaylistItem] = []
    for pth in playlistObj.Audios:
        tags = OrderedDict()
        tagsRaw = GetAllTags(playlist / pth)
        for key in _PLVW_TAGS:
            if key in tagsRaw:
                tags[_PLVW_TAGS[key]] = tagsRaw[key]
        plyItems.append(PlaylistItem(str(pth), tags))
        tagsRaw.clear()
        del tagsRaw
    return playlistObj, plyItems


def LoadLrc(lrc_file: PathLike, q: Queue | None) -> Lrc:
    """Loads the specified LRC file."""
    if q:
        q.put(f'Loading\n{lrc_file}')
    lrc_file = Lrc.GetLrcFilename(lrc_file)
    return Lrc(lrc_file, True, True)
