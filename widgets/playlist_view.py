#
# 
#
"""This module offers the following:

#### Classes:
1. `PlaylistItem`

#### Widgets:
1. `PlaylistView`
"""


from pathlib import Path
import tkinter as tk
from typing import Iterable

from tkinterweb import HtmlFrame


class PlaylistItem:
    """Objects of this class represent audio items in a `PlaylistView`
    widget.
    """
    def __init__(self) -> None:
        self.filename: Path | None = None
        """The path of the audio in the playlist."""
        self.artist: str | None = None
        """The artist of the audio in the playlist."""
        self.album: str | None = None
        """The album of the audio in the playlist."""
        self.title: str | None = None
        """The title of the audio in the playlist."""


class PlaylistView(tk.Frame):
    def __init__(
            self,
            master: tk.Misc,
            template_dir: Path,
            template_name: str,
            **kwargs,
            ) -> None:
        super().__init__(master, **kwargs)
        self._templateDir = template_dir
        """The directory of templates."""
        self._templateName = template_name
        """The name of the template."""
        self._items: list[PlaylistItem] = []
        self._InitGui()
    
    def _InitGui(self) -> None:
        #
        self._htmlFrame = HtmlFrame(
            self,
            vertical_scrollbar=True,
            horizontal_scrollbar=True,
            messages_enabled=False,)
        self._htmlFrame.pack(
            fill=tk.BOTH,
            expand=True,)
    
    def Populate(self, items: list[PlaylistItem]) -> None:
        """Firstly clears the `PlaylistView`, then populates the new,
        provided items in the view.
        """
        self._items.clear()
        self._items = items
        self._PopulateJinja()

    def Clear(self) -> None:
        """Clears the `PlaylistView` from all items."""
        self._items.clear()
        self._PopulateJinja()

    def _PopulateJinja(self) -> None:
        # Declaring variables -----------------------------
        from jinja2 import FileSystemLoader, Environment
        # Populating --------------------------------------
        fsLoader = FileSystemLoader(searchpath=self._templateDir)
        env = Environment(loader=fsLoader)
        tmplt = env.get_template(name=self._templateName)
        result_ = tmplt.render(items=self._items)
        self._htmlFrame.load_html(
            html_source=result_,
            base_url='https://me.me')
