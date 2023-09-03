#
# 
#
"""
"""


import tkinter as tk
from tkinter import ttk
from typing import Iterable


class LyricsView(ttk.Frame):
    def __init__(
            self,
            master: tk.Misc,
            highlightable: bool = False,
            highlight_color: str = 'white',
            sep_line_height: int = 1,
            sep_line_color: str = 'thistle4',
            gap: int = 5,
            padx_line: int = 25,
            ipadx: int = 5,
            ipady: int = 5,
            **kwargs
           ) -> None:
        kwargs['relief'] = 'sunken'
        kwargs['borderwidth'] = 2
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
        self._padxLine = padx_line
        """The vertical margin of separator lines."""
        self._ipadx = ipadx
        self._ipady = ipady
        self._cnvsWidth: int = 1
        self._cnvsHeight: int = 1
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
        self._scrolled: bool = False
        """Specifies whether the scrollbar is shown or not."""

        self._InitGui()

        self._cnvs.bind('<Configure>', self._OnCnvsResized)
    
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
        """self._vscrlbr.grid(
            column=1,
            row=0,
            sticky=tk.NSEW)"""
        #
        msg = tk.Message(
            master=self._cnvs,
            justify=tk.CENTER)
        self._msgs.append(msg)
        self._heights = [0, 0]
        self._cnvs.create_window(0, 0, window=msg)

        self._defaultColor = msg.cget('bg')
    
    def _OnCnvsResized(self, event: tk.Event) -> None:
        cnvsWidth = self._GetCnvsWidth(event.width)
        cnvsHeight = self._GetCnvsHeight(event.height)
        if self._cnvsWidth != cnvsWidth or self._cnvsHeight != cnvsHeight:
            self._RedrawCnvs(cnvsWidth, cnvsHeight)
    
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

        If the view is highlightable and:
        * if `idx < 0`, no lyrics will be highlighted.
        * if `idx >= number of lyrics`, the last lyrics will be highlighted. 

        #### Exceptions:
        * `TypeError`: `idx` is NOT an integer.
        """
        if not self._highlightable:
            return
        if not isinstance(idx, int):
            raise TypeError("'idx' must be an integer")
        if idx != self._idx:
            nLrcs = len(self._lyrics)
            self._cnvs.update_idletasks()
            cnvsHeight = self._cnvs.winfo_height()
            if idx < 0:
                idx = -1
            elif idx >= nLrcs:
                idx = nLrcs - 1
            # Removing highlight from previous lyrics...
            self._msgs[self._idx]['bg'] = self._defaultColor
            # Scrolling the canvas to the highlighted lyrics...
            if idx < 0:
                self._cnvs.yview_moveto(0)
            else:
                self._cnvs.yview_moveto(
                    self._heights[idx] / (self._heights[nLrcs] + cnvsHeight))
            # Highlighting the new lyrics:
            if idx >= 0:
                self._msgs[idx]['bg'] = self._highlightColor
            self._idx = idx

    def Clear(self) -> None:
        """Clears this lyrics view out of all lyrics."""
        self._HideScrollbar()
        self._lyrics.clear()
        self._cnvs.delete('all')
        self._highlightable = False
        self._cnvs.update_idletasks()
        self._cnvsWidth = self._GetCnvsWidth()
        self._cnvsHeight = self._GetCnvsHeight()
    
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
        self._RedrawCnvs()

    def _RedrawCnvs(
            self,
            cnvs_width: int | None = None,
            cnvs_height: int | None = None,
            ) -> None:
        """Redraws the internal canvas. If the width and height of the
        canvas are not provided, first it reads those valies.
        """
        self._cnvs.delete('all')
        if self._highlightable and self._scrolled:
            self._HideScrollbar()
            self._cnvs.update_idletasks()
        nLyrics = len(self._lyrics)
        if nLyrics <= 0:
            # No lyrics to show, returning, the canvas cleared...
            return
        # Removing possible highlight...
        if self._idx >= 0:
            self._msgs[self._idx]['bg'] = self._defaultColor
        # Reading the size of the canvas...
        cnvsWidth = self._GetCnvsWidth(cnvs_width)
        self._cnvsWidth = cnvsWidth
        cnvsHeight = self._GetCnvsHeight(cnvs_height)
        self._cnvsHeight = cnvsHeight
        cnvsHalfHeight = cnvsHeight // 2
        cnvsHalfWidth = cnvsWidth // 2
        # Instantiating necessary tkMessage widgets...
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
                self._padxLine,
                y,
                cnvsWidth - self._padxLine,
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
        elif self._heights[nLyrics] > cnvsHeight:
            self._cnvs['scrollregion'] = (
                0,
                cnvsHalfHeight,
                cnvsWidth,
                self._heights[nLyrics] + cnvsHalfHeight)
            self._ShowScrollbar()
        else:
            delta = self._heights[nLyrics] // 2
            self._cnvs['scrollregion'] = (
                0,
                delta,
                cnvsWidth,
                self._heights[nLyrics] + cnvsHeight - delta)
            self._HideScrollbar()
    
    def _ShowScrollbar(self) -> None:
        """Makes the vertical scroll bar appear in the lyrics view."""
        if not self._scrolled:
            self._vscrlbr.update_idletasks()
            scrlWidth = self._vscrlbr.winfo_width()
            self._cnvs.update_idletasks()
            cnvsWidth = self._cnvs.winfo_width()
            self._cnvs['width'] = cnvsWidth - scrlWidth
            self._vscrlbr.grid(
                column=1,
                row=0,
                sticky=tk.NSEW)
            self._scrolled = True
    
    def _HideScrollbar(self) -> None:
        """Hides the vertical scroll bar in the lyrics view."""
        if self._scrolled:
            self._vscrlbr.grid_forget()
            self._scrolled = False
    
    def _GetCnvsWidth(self, width: int | None = None) -> int:
        """Gets the 'available' width (suitable for drawing) of the
        internal canvas."""
        if width is None:
            self._cnvs.update_idletasks()
            width = self._cnvs.winfo_width()
        return (
            width - 4
            + (int(self._cnvs['bd']) << 1))
    
    def _GetCnvsHeight(self, height: int | None = None) -> int:
        """Gets the 'available' height (suitable for drawing) of the
        internal canvas."""
        self._cnvs.update_idletasks()
        if height is None:
            self._cnvs.update_idletasks()
            height = self._cnvs.winfo_height()
        return (
            height - 4
            + (int(self._cnvs['bd']) << 1))

    def __del__(self) -> None:
        del self._scrolled
        del self._highlightable
        self._lyrics.clear()
        del self._lyrics
        self._msgs.clear()
        del self._msgs
