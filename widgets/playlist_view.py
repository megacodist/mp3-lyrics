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
from tkinter import ttk
import tkinter.font as tkfont
from typing import Any, Callable

import attrs
from tkinterweb import HtmlFrame


class PlaylistItem:
    """Objects of this class represent audio items in a `PlaylistView`
    widget.
    """
    def __init__(self) -> None:
        self.filename: Path | None = None
        """The path of the audio in the playlist."""
        self.tags: dict[str, list[str]]
    
    def __del__(self) -> None:
        del self.filename
        del self.tags


class _PlvwItem(tk.Frame):
    FILE_FONT: tkfont.Font
    """The font of the file name label."""

    """Represents a playlist view item."""
    def __init__(
            self,
            master: tk.Misc,
            idx: int,
            item: PlaylistItem,
            select_cb: Callable[[int], Any],
            **kwargs
            ) -> None:
        kwargs['cursor'] = 'hand1'
        super().__init__(master, **kwargs)
        self._idx = idx
        """The index of this playlist view item in the playlist view."""
        self._item = item
        """The item of playlist view."""
        self._selected: bool = False
        """Specifies the selection status of this playlist view item."""
        self._selectCb = select_cb
        """The callback to be called upon selection."""
        self._defaultBack = self['background']
        self._hoverBack = 'white'
        self._InitGui()
        self.bind('<Enter>', self._SetBackHover)
        self.bind('<Leave>', self._SetBackDefault)
        self.bind("<Button-1>", self._OnMouseClicked)
    
    @property
    def Selected(self) -> bool:
        """Gets or sets whether this playlist view item is selected."""
        return self._selected
    
    @Selected.setter
    def Selected(self, __sel: bool, /) -> None:
        if __sel is True:
            self['relief'] = 'sunken'
            self['cursor'] = ''
            self._ChnageBackground(self._hoverBack)
            self._selected = True
        elif __sel is False:
            self['relief'] = 'flat'
            self['cursor'] = 'hand1'
            self._ChnageBackground(self._defaultBack)
            self._selected = False
        else:
            raise TypeError("'Selected' property of "
                f"'{type(self).__qualname__}' must be boolean.")
    
    def _ChnageBackground(self, __back: str) -> None:
        self['background'] = __back
        for widget in self.winfo_children():
            widget['background'] = __back
    
    def _SetBackDefault(self, _: tk.Event) -> None:
        if self._selected:
            return
        self._ChnageBackground(self._defaultBack)
    
    def _SetBackHover(self, _: tk.Event) -> None:
        if self._selected:
            return
        self._ChnageBackground(self._hoverBack)
    
    def _OnMouseClicked(self, _: tk.Event) -> None:
        if self._selected:
            return
        self.Selected = True
        self._selectCb(self._idx)
    
    def _InitGui(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)
        #
        try:
            self._lbl_filename = tk.Label(
                self,
                font=_PlvwItem.FILE_FONT,
                text=str(self._item.filename))
        except AttributeError:
            _PlvwItem.FILE_FONT = tkfont.nametofont('TkDefaultFont').copy()
            _PlvwItem.FILE_FONT.config(weight='bold')
            _PlvwItem.FILE_FONT.config(
                size=_PlvwItem.FILE_FONT.cget('size') + 1)
            self._lbl_filename = tk.Label(
                self,
                font=_PlvwItem.FILE_FONT,
                text=str(self._item.filename))
        self._lbl_filename.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky=tk.W)
        row = 0
        # Adding title...
        if 'TIT2' in self._item.tags:
            row += 1
            tagTitle = ttk.Label(self, text='Title:', foreground='grey')
            tagTitle.grid(
                row=row,
                column=0,
                sticky=tk.NE)
            tagValues = ttk.Label(self)
            try:
                tagValues['text'] = '\n'.join(self._item.tags['TIT2'])
            except TypeError:
                tagValues['text'] = '\n'.join(
                    str(value) for value in self._item.tags['TIT2'])
            tagValues.grid(
                row=row,
                column=1,
                sticky=tk.NW)
        # Adding album...
        if 'TALB' in self._item.tags:
            row += 1
            tagTitle = ttk.Label(self, text='Album:', foreground='grey')
            tagTitle.grid(
                row=row,
                column=0,
                sticky=tk.NE)
            tagValues = ttk.Label(self)
            try:
                tagValues['text'] = '\n'.join(self._item.tags['TALB'])
            except TypeError:
                tagValues['text'] = '\n'.join(
                    str(value) for value in self._item.tags['TALB'])
            tagValues.grid(
                row=row,
                column=1,
                sticky=tk.NW)
        # Adding artist...
        if 'TPE1' in self._item.tags:
            row += 1
            tagTitle = ttk.Label(self, text='Artist:', foreground='grey')
            tagTitle.grid(
                row=row,
                column=0,
                sticky=tk.NE)
            tagValues = ttk.Label(self)
            try:
                tagValues['text'] = '\n'.join(self._item.tags['TPE1'])
            except TypeError:
                tagValues['text'] = '\n'.join(
                    str(value) for value in self._item.tags['TPE1'])
            tagValues.grid(
                row=row,
                column=1,
                sticky=tk.NW)
    
    def __del__(self) -> None:
        del self._idx
        del self._selectCb
        del self._item


class PlaylistView(tk.Frame):
    def __init__(
            self,
            master: tk.Misc,
            select_bc: Callable[[int], Any],
            **kwargs
            ) -> None:
        kwargs['name'] = 'playlistView'
        super().__init__(master, **kwargs)
        self._margin = 10
        """The margin between items."""
        self._plvwItems: list[_PlvwItem] = []
        """The playlist view items."""
        self._selected: int | None = None
        """Specifies the index of seleceted playlist view item."""
        self._selectCb = select_bc
        """The callback to be called upon selection."""
        self._frame: ttk.Frame | None = None
        """The frame containing the playlist view items."""
        self._InitGui()
    
    def _InitGui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        #
        self._vscrlbr = ttk.Scrollbar(
            self,
            orient=tk.VERTICAL)
        self._hscrlbr = ttk.Scrollbar(
            self,
            orient=tk.HORIZONTAL)
        self._cnvs = tk.Canvas(
            self,
            xscrollcommand=self._hscrlbr.set,
            yscrollcommand=self._vscrlbr.set)  
        self._vscrlbr['command'] = self._cnvs.yview
        self._hscrlbr['command'] = self._cnvs.xview
        self._cnvs.grid(
            column=0,
            row=0,
            ipadx=self._margin,
            ipady=self._margin,
            sticky=tk.NSEW)
        self._vscrlbr.grid(
            column=1,
            row=0,
            sticky=tk.NS)
        self._hscrlbr.grid(
            column=0,
            row=1,
            sticky=tk.EW)
    
    def Populate(self, items: list[PlaylistItem]) -> None:
        """Firstly clears the `PlaylistView`, then populates the new,
        provided items in the view.
        """
        self._cnvs.delete('all')
        if self._frame:
            self._frame.destroy()
        self._frame = ttk.Frame(self._cnvs)
        self._plvwItems.clear()
        nItems = len(items)
        if nItems > 0:
            plvwItem = _PlvwItem(
                self._frame,
                0,
                items[0],
                self.Select)
            plvwItem.pack(
                side=tk.TOP,
                fill=tk.X,
                expand=1)
            self._plvwItems.append(plvwItem)
        for idx in range(1, len(items)):
            separator = ttk.Separator(self._frame, orient=tk.HORIZONTAL)
            separator.pack(
                padx=(2 * self._margin),
                pady=self._margin,
                side=tk.TOP,
                fill=tk.X,
                expand=1)
            plvwItem = _PlvwItem(
                self._frame,
                idx,
                items[idx],
                self.Select)
            plvwItem.pack(
                side=tk.TOP,
                fill=tk.X,
                expand=1)
            self._plvwItems.append(plvwItem)
        self._cnvs.create_window(0, 0, anchor=tk.NW, window=self._frame)
        self._frame.update_idletasks()
        self._cnvs['scrollregion'] = (
            0,
            0,
            self._frame.winfo_reqwidth(),
            self._frame.winfo_reqheight())

    def Select(self, idx: int) -> None:
        if isinstance(self._selected, int):
            self._plvwItems[self._selected].Selected = False
        self._selected = idx
        self._plvwItems[idx].Selected = True
        self._selectCb(idx)

    def __del__(self) -> None:
        del self._margin
        del self._selectCb


class PlaylistView_old(tk.Frame):
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
        provided items in the view."""
        self._items.cleaself._items = items
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
        result_ = tmplt.render(self._items)
        self._htmlFrame.load_html(
            html_source=result_,
            base_url='https://me.me')
