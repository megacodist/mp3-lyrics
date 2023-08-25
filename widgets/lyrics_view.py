#
# 
#
"""
"""


import tkinter as tk
from tkinter import ttk
from typing import Iterable

from media.lrc import Lrc


class LyricsView(ttk.Frame):
    def __init__(
            self,
            master: tk.Misc,
            highlightable: bool = False,
            highlight_color: str = 'white',
            sep_line_height: int = 1,
            sep_line_color: str = 'thistle4',
            gap: int = 5,
            ipadx: int = 5,
            ipady: int = 5,
            **kwargs
           ) -> None:
        super().__init__(master, **kwargs)
        self._highlightable = highlightable
        """Specifies whether the lyrics are able to be highlighted by
        `Highlight` method or not.
        """
        self._highlightColor = highlight_color
        """The background color of highlighted lyrics item."""
        self._defaultColor: str
        """The default background color of lyrics items."""
        self._sepLineHeight = sep_line_height
        """The height of separator lines between lyrics items."""
        self._sepLineColor = sep_line_color
        """The color of separator lines between lyrics items."""
        self._gap = gap
        """The height of gaps between lines and lyrics items."""
        self._ipadx = ipadx
        self._ipady = ipady
        self._width: int
        self._height: int
        self._lyrics: list[str] = []
        """The lyrics of this lyrics view."""
        self._msgs: list[tk.Message] = []
        self._heights: list[int] = []
        """The accumulated height of lyrics items before `index`th item
        (index is zero based).
        """
        self._idx: int = -1
        """The index of highlighted item in the lyrics view. Negative
        values means no highlighted item."""

        self._InitGui()

        self._cnvs.bind('<Configure>', self._OnCnvsSizeChanged)
    
    def _InitGui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        #
        self._vscrlbr = tk.Scrollbar(
            self,
            orient=tk.VERTICAL)
        self._cnvs = tk.Canvas(
            self,
            yscrollcommand=self._vscrlbr.set)
        self._vscrlbr['command'] = self._cnvs.yview
        self._cnvs.grid(
            column=0,
            row=0,
            sticky=tk.NSEW)
        #
        msg = tk.Message(
            master=self._cnvs,
            justify=tk.CENTER)
        self._msgs.append(msg)
        self._heights = [0, 0]
        self._cnvs.create_window(0, 0, window=msg)

        self._defaultColor = msg.cget('bg')
    
    def _OnCnvsSizeChanged(self, event: tk.Event) -> None:
        try:
            if self._width != event.width or self._height != event.height:
                self._width = event.width
                self._height = event.height
                self._Redraw()
        except AttributeError:
            self._width = event.width
            self._height = event.height
    
    @property
    def Highlightable(self) -> bool:
        """Gets or sets the highlightable attribute of this lyrics view."""
        return self._highlightable
    
    @Highlightable.setter
    def Highlightable(self, __hl: bool, /) -> None:
        raise NotImplementedError()
    
    def Highlight(self, idx: int) -> None:
        """Highlights the `idx`th lyrics item in the view. Nothing takes
        place if `highlightable` attribute is `False`. `idx` must be
        zero-based.

        #### Exceptions:
        * `TypeError`: `idx` is NOT an integer.
        * `IndexError`: `idx` is greater than or equal to the number of
        items in the lyrics view.
        """
        if not self._highlightable:
            return
        if not isinstance(idx, int):
            raise TypeError("'idx' must be an integer")
        if idx != self._idx:
            if idx >= len(self._lyrics):
                raise IndexError("'idx' must be less than the numbers of"
                    " items in the view.")
            if idx < 0:
                self._cnvs.yview_moveto(0)
                if self._idx >= 0:
                    self._msgs[self._idx]['bg'] = self._defaultColor
                    self._idx = -1
                return
            
            if self._idx >= 0:
                self._msgs[self._idx]['bg'] = self._defaultColor
            if idx >= 0:
                self._msgs[idx]['bg'] = self._highlightColor
                cnvsHeight = self._GetCnvsHeight()
                self._cnvs.yview_moveto(
                    self._heights[idx] / (self._heights[-1] + cnvsHeight))
            self._idx = idx

    def Clear(self) -> None:
        """Clears this lyrics view out of all lyrics and ensures removal
        of the vertical scroll bar.
        """
        self._cnvs.delete('all')
        self._HideScrollbar()
    
    def Populate(
            self,
            lyrics: Iterable[str],
            highlightable: bool | None = None,
            ) -> None:
        """Populates the lyrics in the view. If optional `highlightable`
        parameter is specified, it changes the current value, otherwise
        the current value is used.
        """
        self._lyrics = list(lyrics)
        if isinstance(highlightable, bool):
            self._highlightable = highlightable
        elif highlightable is not None:
            raise TypeError("'highlightable' parameter must be boolean.")
        self._Redraw()

    def _Redraw(self) -> None:
        self.Clear()
        nLyrics = len(self._lyrics)
        if nLyrics <= 0:
            # No lyrics to show, returning, the canvas cleared...
            return
        cnvsWidth = self._GetCnvsWidth()
        cnvsHeight = self._GetCnvsHeight()
        cnvsHalfHeight = cnvsHeight // 2
        cnvsHalfWidth = cnvsWidth // 2
        # Instantiating necessary tkMessage widgets...
        nLyrics = len(self._lyrics)
        for _ in range(len(self._msgs), nLyrics):
            msg = tk.Message(
                master=self._cnvs,
                anchor=tk.CENTER,
                justify=tk.CENTER)
            self._msgs.append(msg)
            self._heights.append(self._heights[-1])
        # Drawing the first lyrics item...
        y = cnvsHalfHeight
        self._msgs[0]['width'] = cnvsWidth
        self._msgs[0]['text'] = self._lyrics[0]
        self._msgs[0].update_idletasks()
        self._cnvs.create_window(
            cnvsHalfWidth,
            y,
            anchor=tk.N,
            width=cnvsWidth,
            window=self._msgs[0])
        y += self._msgs[0].winfo_reqheight()
        self._heights[1] = y - cnvsHalfHeight
        # Drawing the rest of Messages (lyrics)...
        for idx in range(1, nLyrics):
            # Drawing the separator line...
            y += self._gap
            self._cnvs.create_line(
                0,
                y,
                cnvsWidth,
                y,
                fill=self._sepLineColor,
                width=self._sepLineHeight)
            y += (self._gap + self._sepLineHeight)
            # Drawing the idx-th item in the canvas...
            self._msgs[idx]['width'] = cnvsWidth
            self._msgs[idx]['text'] = self._lyrics[idx]
            self._msgs[idx].update_idletasks()
            self._cnvs.create_window(
                cnvsHalfWidth,
                y,
                anchor=tk.N,
                width=cnvsWidth,
                window=self._msgs[idx])
            y += self._msgs[idx].winfo_reqheight()
            self._heights[idx + 1] = y - cnvsHalfHeight
        y += cnvsHalfHeight
        # Setting the scroll region...
        if self._highlightable:
            self._cnvs['scrollregion'] = (0, 0, cnvsWidth, y)
        elif self._heights[-1] > cnvsHeight:
            self._cnvs['scrollregion'] = (
                0,
                cnvsHalfHeight,
                cnvsWidth,
                self._heights[-1] + cnvsHalfHeight)
            self._ShowScrollbar()
        else:
            delta = self._heights[-1] // 2
            self._cnvs['scrollregion'] = (
                0,
                delta,
                cnvsWidth,
                self._heights[-1] + cnvsHeight - delta)
    
    def _ShowScrollbar(self) -> None:
        """Makes the vertical scroll bar appear in the lyrics view."""
        self._vscrlbr.grid(
            column=1,
            row=0,
            sticky=tk.NSEW)
    
    def _HideScrollbar(self) -> None:
        """Hides the vertical scroll bar in the lyrics view."""
        self._vscrlbr.grid_forget()
    
    def _GetCnvsWidth(self) -> int:
        """Gets the available width of canvas for drawing."""
        self._cnvs.update_idletasks()
        return (
            self._cnvs.winfo_width()
            - 4
            + (int(self._cnvs['bd']) << 1))
    
    def _GetCnvsHeight(self) -> int:
        """Gets the available height of canvas for drawing."""
        self._cnvs.update_idletasks()
        return (
            self._cnvs.winfo_height()
            - 4
            + (int(self._cnvs['bd']) << 1))

    def __del__(self) -> None:
        del self._highlightable
        if self._lyrics:
            del self._lyrics
        self._msgs.clear()
        del self._msgs


class LyricsView_old(ttk.Frame):
    def __init__(
            self,
            master: tk.Misc,
            *,
            highlightable: bool = False,
            highlightColor: str = 'yellow',
            sepLineWidth: int = 1,
            sepColor: str = 'thistle4',
            gap: int = 5,
            ipadx: int = 5,
            ipady: int = 5,
            **kwargs
            ) -> None:
        super().__init__(master, **kwargs)
        self['relief'] = tk.SUNKEN

        self._lyrics: list[str] = []
        self._heights: list[int] = [0]
        self._extraHeight: int
        self._idx = -1
        self._highlightable = highlightable
        self.highlightColor = highlightColor
        self._defaultColor: str
        self._sepLineWidth = sepLineWidth
        self._sepColor = sepColor
        self._gap = gap
        self._ipadx = ipadx
        self._ipady = ipady
        self._width: int
        self._height: int
        self._redrawRequested: bool = False

        self._vscrlbr: ttk.Scrollbar
        self._cnvs: tk.Canvas
        self._msgs: list[tk.Message] = []

        self._InitGui()

        self._cnvs.bind(
            '<Configure>',
            self._OnCnvsSizeChanged)
    
    def _InitGui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._vscrlbr = ttk.Scrollbar(
            master=self,
            orient=tk.VERTICAL)
        self._cnvs = tk.Canvas(
            master=self,
            yscrollcommand=self._vscrlbr.set)
        self._vscrlbr['command'] = self._cnvs.yview
        self._cnvs.grid(
            column=0,
            row=0,
            padx=self._ipadx,
            pady=self._ipady,
            sticky=tk.NSEW)
        self._vscrlbr.grid(
            column=1,
            row=0,
            sticky=tk.NSEW)
        
        msg = tk.Message(
            master=self._cnvs,
            justify=tk.CENTER)
        self._msgs.append(msg)
        self._cnvs.create_window(0, 0, window=msg)

        self._defaultColor = msg.cget('bg')
    
    def _OnCnvsSizeChanged(self, event: tk.Event) -> None:
        try:
            if self._width != event.width or self._height != event.height:
                self._width = event.width
                self._height = event.height
                for idx in range(len(self._lyrics)):
                    self._msgs[idx]['width'] = event.width
                if not self._redrawRequested:
                    self._redrawRequested = True
                    self._Redraw()
        except AttributeError:
            self._width = event.width
            self._height = event.height
    
    @property
    def sepLineWidth(self) -> int:
        """Gets or sets the width of line separator, which delimits
        lyrics from each other.
        """
        return self._sepLineWidth
    
    @sepLineWidth.setter
    def sepLineWidth(self, __value: int) -> None:
        if not isinstance(__value, int):
            raise TypeError("'sepLineWidth' must be an integer")
        if self._sepLineWidth != __value:
            self._sepLineWidth = __value
            self._Redraw()

    @property
    def lyrics(self) -> list[str]:
        """Gets a copy of lyrics."""
        import copy
        return copy.deepcopy(self._lyrics)
    
    def Populate(
            self,
            lrc: Lrc,
            highlightable: bool | None = None
            ) -> None:
        """Populates the Lyrics View with an Lrc object. It is possible
        to specifies the highlightability. If highlightable parameter
        is None, the highlightability of this instance is determine
        by AreTimstampsOk method of the Lrc object. If the Lrc object is
        None, then this method clears the Lyrics View.
        """
        if lrc:
            # Setting highlightable...
            if highlightable is not None:
                self._highlightable = highlightable
            else:
                self._highlightable = lrc.AreTimstampsOk()
            # Setting lyrics...
            self._lyrics = [
                lyricsItem.text
                for lyricsItem in lrc.lyrics]
            self._Redraw()
        else:
            # No Lrc object, clearing the Lyrics View...
            self._lyrics = []
            self._cnvs.delete('all')
            self._cnvs['scrollregion'] = (
                0,
                0,
                self._GetCnvsWidth(),
                self._GetCnvsHeight())
    
    @property
    def gap(self) -> int:
        return self._gap
    
    @property
    def highlightable(self) -> bool:
        return self._highlightable
    
    @highlightable.setter
    def highlightable(self, __hlght: bool, /) -> None:
        if self._highlightable != __hlght:
            self._highlightable = __hlght
            self._Redraw()
    
    def Highlight(self, idx: int) -> None:
        if not self.highlightable:
            return
        if not isinstance(idx, int):
            raise TypeError("'idx' must be an integer")
        if idx != self._idx:
            if idx >= len(self._lyrics):
                raise ValueError("Invalid value for 'idx'")
            if idx < 0:
                self._cnvs.yview_moveto(0)
                if self._idx >= 0:
                    self._msgs[self._idx]['bg'] = self._defaultColor
                    self._idx = -1
                return
            
            if self._idx >= 0:
                self._msgs[self._idx]['bg'] = self._defaultColor
            if idx >= 0:
                self._msgs[idx]['bg'] = self.highlightColor
                self._cnvs.yview_moveto(
                        self._heights[idx] / self._extraHeight)
            self._idx = idx

    def _GetCnvsWidth(self) -> int:
        """Gets the available width of canvas for drawing."""
        self._cnvs.update_idletasks()
        return (
            self._cnvs.winfo_reqwidth()
            - 4
            + (int(self._cnvs['bd']) << 1))
    
    def _GetCnvsHeight(self) -> int:
        """Gets the available height of canvas for drawing."""
        self._cnvs.update_idletasks()
        return (
            self._cnvs.winfo_reqheight()
            - 4
            + (int(self._cnvs['bd']) << 1))
    
    def _Redraw(self) -> None:
        if self._highlightable:
            # We have to remove the scrollbar...
            if self._vscrlbr.winfo_ismapped():
                self._vscrlbr.grid_remove()
        else:
            # We have to be sure the scrollbar is mapped...
            if not self._vscrlbr.winfo_ismapped():
                self._vscrlbr.grid(
                    column=1,
                    row=0,
                    sticky=tk.NSEW)

        cnvsWidth = self._GetCnvsWidth()
        cnvsHalfWidth = cnvsWidth >> 1
        cnvsHeight = self._GetCnvsHeight()
        cnvsHalfHeight = cnvsHeight >> 1

        nLyrics = len(self._lyrics)
        self._cnvs.delete('all')
        if nLyrics <= 0:
            # No lyrics to show, returning after clearing the canvas...
            return
        for idx in range(len(self._msgs), nLyrics):
            msg = tk.Message(
                master=self._cnvs,
                anchor=tk.CENTER,
                justify=tk.CENTER)
            self._msgs.append(msg)
        
        # Drawing the first Message (lyric)...
        y = cnvsHalfHeight
        #self._msgs[0]['width'] = cnvsWidth
        self._msgs[0]['text'] = self._lyrics[0]
        self._cnvs.create_window(
            cnvsHalfWidth,
            y,
            anchor=tk.N,
            width=cnvsWidth,
            window=self._msgs[0])
        self._cnvs.update()
        y += self._msgs[0].winfo_reqheight()
        
        # Drawing the rest of Messages (lyrics)...
        for idx in range(1, nLyrics):
            y += self._gap
            self._cnvs.create_line(
                0,
                y,
                cnvsWidth,
                y,
                fill=self._sepColor,
                width=self._sepLineWidth)

            y += (self._gap + self._sepLineWidth)
            try:
                self._heights[idx] = y - cnvsHalfHeight
            except IndexError:
                self._heights.append(y - cnvsHalfHeight)
            #self._msgs[idx]['width'] = cnvsWidth
            self._msgs[idx]['text'] = self._lyrics[idx]
            self._cnvs.create_window(
                cnvsHalfWidth,
                y,
                anchor=tk.N,
                width=cnvsWidth,
                window=self._msgs[idx])
            self._cnvs.update()
            y += self._msgs[idx].winfo_reqheight()
        
        # Setting the scroll region...
        self._extraHeight = y + cnvsHalfHeight
        if self._highlightable:
            scrollRegion = (0, 0, cnvsWidth, self._extraHeight)
        else:
            if (y - cnvsHalfHeight) < cnvsHeight:
                halfDiff = (cnvsHeight - y + cnvsHalfHeight) >> 1
                scrollRegion = (
                    0,
                    cnvsHalfHeight - halfDiff,
                    cnvsWidth,
                    y + halfDiff)
            else:
                scrollRegion = (0, cnvsHalfHeight, cnvsWidth, y)
        self._cnvs['scrollregion'] = scrollRegion
        self._cnvs.yview_moveto(0)
        self._redrawRequested = False
