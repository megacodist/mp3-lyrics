#
# 
#
"""This module offers the following:

#### Classes:
1. `PlaylistItem`

#### Widgets:
1. `PlaylistView`
"""


import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
from typing import Any, Callable, Iterable


class PlaylistItem:
    """Objects of this class represent items in a `PlaylistView`
    widget.
    """
    def __init__(
            self,
            name: str,
            tags: dict[str, Iterable[str]] | None = None
            ) -> None:
        self.name = name
        """The name of the item in the playlist."""
        self.tags: dict[str, Iterable[str]] = tags
        """The key-values pairs of this playlist view item."""
    
    def __del__(self) -> None:
        del self.name
        del self.tags


class _PlvwItem(tk.Frame):
    FILE_FONT: tkfont.Font
    """The font of the file name label."""
    TAG_COLOR = 'grey'
    """The color of the tag in the item."""

    """Represents a playlist view item."""
    def __init__(
            self,
            master: tk.Misc,
            idx: int,
            item: PlaylistItem,
            select_cb: Callable[[int], Any],
            hover_color: str = 'white',
            **kwargs
            ) -> None:
        kwargs['cursor'] = 'hand1'
        kwargs['borderwidth'] = 2
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
        self._hoverBack = hover_color
        """The background color of items when mouse pointer hovers them
        or when they are selected.
        """
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
        #self.Selected = True
        self._selectCb(self._idx)
    
    def _InitGui(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)
        # Adding name...
        try:
            self._lbl_name = tk.Label(
                self,
                font=_PlvwItem.FILE_FONT,
                text=str(self._item.name))
        except AttributeError:
            _PlvwItem.FILE_FONT = tkfont.nametofont('TkDefaultFont').copy()
            _PlvwItem.FILE_FONT.config(weight='bold')
            _PlvwItem.FILE_FONT.config(
                size=_PlvwItem.FILE_FONT.cget('size') + 1)
            self._lbl_name = tk.Label(
                self,
                font=_PlvwItem.FILE_FONT,
                text=str(self._item.name))
        self._lbl_name.bind("<Button-1>", self._OnMouseClicked)
        self._lbl_name.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky=tk.W)
        # Adding key-value pairs...
        row = 0
        for key in self._item.tags:
            row += 1
            # Adding tag label...
            lblTag = ttk.Label(
                self,
                text=(key + ':'),
                foreground=_PlvwItem.TAG_COLOR)
            lblTag.bind("<Button-1>", self._OnMouseClicked)
            lblTag.grid(
                row=row,
                column=0,
                sticky=tk.NE)
            # Adding values label...
            lblValues = ttk.Label(self)
            try:
                lblValues['text'] = '\n'.join(self._item.tags[key])
            except TypeError:
                lblValues['text'] = '\n'.join(
                    str(value) for value in self._item.tags[key])
            lblValues.bind("<Button-1>", self._OnMouseClicked)
            lblValues.grid(
                row=row,
                column=1,
                sticky=tk.NW)
    
    def __del__(self) -> None:
        # Freeing simple attributes...
        del self._idx
        del self._selectCb
        del self._selected
        del self._item
        del self._defaultBack
        del self._hoverBack


class PlaylistView(tk.Frame):
    def __init__(
            self,
            master: tk.Misc,
            select_bc: Callable[[int], Any],
            **kwargs
            ) -> None:
        kwargs['name'] = 'playlistView'
        super().__init__(master, **kwargs)
        self._margin = 5
        """The margin between items."""
        self._plvwItems: list[_PlvwItem] = []
        """The playlist view items."""
        self._secelctedIdx: int | None = None
        """Specifies the index of seleceted playlist view item."""
        self._selectCb = select_bc
        """The callback to be called upon selection."""
        self._frame: ttk.Frame | None = None
        """The frame containing the playlist view items."""
        self._scrollRegion: tuple[int, int, int, int] = (0, 0, 0, 0)
        """The scrollable region of this playlist view in the form of
        (x0, y0, x1, y1) where (x0, y0) is the coordinates of upper left
        corner of the scrollable region and (x1, y1) is the lower right
        corner.
        """
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
        self._secelctedIdx = None
        nItems = len(items)
        if nItems > 0:
            plvwItem = _PlvwItem(
                self._frame,
                0,
                items[0],
                self._SelectIdx)
            plvwItem.pack(
                side=tk.TOP,
                fill=tk.X,
                expand=1)
            self._plvwItems.append(plvwItem)
        for idx in range(1, len(items)):
            separator = ttk.Separator(self._frame, orient=tk.HORIZONTAL)
            separator.pack(
                padx=(3 * self._margin),
                pady=self._margin,
                side=tk.TOP,
                fill=tk.X,
                expand=1)
            plvwItem = _PlvwItem(
                self._frame,
                idx,
                items[idx],
                self._SelectIdx)
            plvwItem.pack(
                side=tk.TOP,
                fill=tk.X,
                expand=1)
            self._plvwItems.append(plvwItem)
        self._frame.update_idletasks()
        self._cnvs.create_window(0, 0, anchor=tk.NW, window=self._frame)
        self._scrollRegion = (
            0,
            0,
            self._frame.winfo_reqwidth(),
            self._frame.winfo_reqheight())
        self._cnvs['scrollregion'] = self._scrollRegion
    
    def _SelectIdx(self, __idx: int | None) -> None:
        """"""
        self.SelectedIdx = __idx
    
    @property
    def ItemsCount(self) -> int:
        """Gets the number of items in the view."""
        return len(self._plvwItems)

    @property
    def SelectedIdx(self) -> int | None:
        """Gets or sets the index of selected item in this playlist view.
        If nothing is seleceted, it returns `None`.
        
        The r-value to this property must be `int`, `None`, or any value
        whcih can be converted to `int` witout losing data.

        #### Exceptions:
        1. `TypeError`: an inappropriate value is provided. Refer to the
        aforementioned notes.
        2. `IndexError`: an out-of-bound index is provided.
        """
        return self._secelctedIdx

    @SelectedIdx.setter
    def SelectedIdx(self, __idx: int | None, /) -> None:
        # Validating the r-value...
        if __idx is not None:
            try:
                intIdx = int(__idx)
                if __idx == intIdx:
                    __idx = intIdx
                else:
                    raise TypeError()
            except TypeError as err:
                err.args = "Selected index of a playlist view must be an" \
                    f" integer or None, given: {type(__idx)}"
                raise err
            else:
                if not 0 <= __idx < len(self._plvwItems):
                    raise IndexError("An out-of-bound index is provided to"
                        " the playlist view widget.")
        # From here on, '__idx' is strictly integer or None...
        # De-selecting previous index...
        if self._secelctedIdx is not None:
            self._plvwItems[self._secelctedIdx].Selected = False
        self._secelctedIdx = __idx
        if __idx is not None:
            self._plvwItems[__idx].Selected = True
            # Checking visibility of the playlist view item...
            if not self._IsVisible(__idx):
                self._ScrollTo(__idx)
            self._selectCb(__idx)
    
    def _IsVisible(self, idx: int) -> bool:
        """Checks whether `idx`th item in this playlist view is visible
        in this playlist view widget or not.
        """
        self._plvwItems[idx].update_idletasks()
        itemY0 = self._plvwItems[idx].winfo_y()
        itemY1 = itemY0 + self._plvwItems[idx].winfo_height()
        self._cnvs.update_idletasks()
        cnvsY0 = self._cnvs.canvasy(0)
        cnvsY1 = self._cnvs.canvasy(self._cnvs.winfo_height())
        return (cnvsY0 <= itemY0 <= cnvsY1) or (cnvsY0 <= itemY1 <= cnvsY1)
    
    def _ScrollTo(self, idx: int) -> None:
        """Scrolls the canvas so that `idx`th item will be in the middle
        of the visible region.
        """
        # Declaring variables -----------------------------
        # The height of the canvas
        cnvsH: int
        # The height of the scrollable region of the canvas
        cnvsSRH: int
        # The vertical position of the item in the canvas
        itemY: int
        # The height of the item in the canvas
        itemH: int
        fraction: float
        # Scrolling ---------------------------------------
        self._cnvs.update_idletasks()
        cnvsH = self._cnvs.winfo_height()
        cnvsSRH = self._scrollRegion[3]
        self._plvwItems[idx].update_idletasks()
        itemY = self._plvwItems[idx].winfo_y()
        itemH = self._cnvs.winfo_height()
        if itemH >= cnvsH:
            fraction = itemY / cnvsSRH
        else:
            fraction = (itemY - (cnvsH - itemH) / 2) / cnvsSRH
        self._cnvs.yview_moveto(fraction)
    
    def _GetVisibleRegion(self) -> tuple[int, int, int, int]:
        """Returns `(x0, y0, x1, y1)` where region between `(x0, y0)`
        and `(x1, y1)` is visible in this scrollable widget.
        """
        x0 = self._cnvs.canvasx(0)
        y0 = self._cnvs.canvasy(0)
        x1 = self._cnvs.canvasx(self._cnvs.winfo_width())
        y1 = self._cnvs.canvasy(self._cnvs.winfo_height())
        return (x0, y0, x1, y1)
    
    def destroy(self) -> None:
        # Freeing simple attributes...
        del self._margin
        del self._selectCb
        del self._secelctedIdx
        del self._scrollRegion
        # Destroying children widgets...
        if self._frame:
            self._frame.destroy()
        for widget in self._plvwItems:
            widget.destroy()
        self._plvwItems.clear()
        del self._plvwItems
