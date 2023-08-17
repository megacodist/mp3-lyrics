#
# 
#
"""This mosule offers operations for `mp3_lyrics_win` module.
"""


from pathlib import Path
from queue import Queue
import tkinter as tk
from typing import Callable, Iterable

from media import AbstractPlaylist
from widgets.playlist_view import PlaylistItem


def LoadPlaylist(
        playlist: Path,
        master: tk.Misc,
        q: Queue,
        added_cb: Callable[[Path], None] | None = None,
        changed_cb: Callable[[Path], None] | None = None,
        deleted_cb: Callable[[Path], None] | None = None,
        ) -> tuple[AbstractPlaylist, Iterable[PlaylistItem]]:
    """Accepts a `Path` object to a playlist and returns the playlist
    object and all included audios in the playlist as a 2-tuple. It
    returns `(None, None)` on any error.
    """
    from media import PLAYLIST_EXTS, FolderPlaylist
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
        plyItems.append(PlaylistItem())
        plyItems[-1].filename = pth
    return playlistObj, plyItems
