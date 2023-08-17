#
# 
#
"""
"""


import tkinter as tk
from tkinter import ttk

from media.lrc import Lrc


class LyricsView(ttk.Frame):
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
        '''width = (
            event.width
            - (int(self._cnvs['bd']) << 1)
            - 4)
        for msg in self._msgs:
            msg['width'] = width
        self._Redraw()'''
    
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
                self._GetWidth(),
                self._GetHeight())
    
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

    def _GetWidth(self) -> int:
        """Gets the available width of canvas for drawing."""
        return (
            self._cnvs.winfo_width()
            - 4
            + (int(self._cnvs['bd']) << 1))
    
    def _GetHeight(self) -> int:
        """Gets the available height of canvas for drawing."""
        return (
            self._cnvs.winfo_height()
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

        cnvsWidth = self._GetWidth()
        cnvsHalfWidth = cnvsWidth >> 1
        cnvsHeight = self._GetHeight()
        cnvsHalfHeight = cnvsHeight >> 1

        '''nMsgs = len(self._msgs)
        nLyrics = len(self._lyrics)
        try:
            for idx in range(nLyrics):
                #self._msgs[idx]['width'] = cnvsWidth
                self._msgs[idx]['text'] = self._lyrics[idx]
                self._cnvs.create_window(0, 0, width=cnvsWidth, window=self._msgs[idx])
        except IndexError:
            while idx < nLyrics:
                msg = tk.Message(
                    master=self._cnvs,
                    anchor=tk.CENTER,
                    justify=tk.CENTER,
                    width=cnvsWidth)
                #msg['width'] = cnvsWidth
                msg['text'] = self._lyrics[idx]
                self._msgs.append(msg)
                self._cnvs.create_window(0, 0, width=cnvsWidth, window=msg)
                idx += 1

        if nMsgs < nLyrics:
            self._cnvs.update()'''
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
        y += self._msgs[0].winfo_height()
        
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
            y += self._msgs[idx].winfo_height()
        
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


