import copy
from datetime import timedelta
from enum import IntEnum
from pathlib import Path
import tkinter as tk
from tkinter import Frame, Misc, ttk
from tkinter.font import nametofont, Font
from typing import Callable, Mapping

from megacodist.keyboard import Modifiers
from PIL.ImageTk import PhotoImage
from tksheet import Sheet
from tksheet._tksheet_other_classes import EditCellEvent

from abstract_mp3 import AbstractMP3
from media.lrc import Lrc, LyricsItem, Timestamp


class MessageType(IntEnum):
    INFO = 0
    WARNING = 1
    ERROR = 2


class Mp3ListView(tk.Frame):
    def __init__(
                self,
                master: tk.Tk,
                select_callback: Callable[[str], None],
                **kwargs
                ) -> None:
        from tkinterweb import HtmlFrame
        super().__init__(master, **kwargs)
        self._webvw = HtmlFrame(
            self,
            vertical_scrollbar=True,
            horizontal_scrollbar=True,
            messages_enabled=False)


class WaitFrame(ttk.Frame):
    def __init__(
            self,
            master: tk.Misc,
            wait_gif: list[PhotoImage],
            cancel_callback: Callable[[], None],
            **kwargs
            ) -> None:
        super().__init__(master, **kwargs)
        self['relief'] = tk.RIDGE

        # Storing inbound references...
        self._master = master
        self._GIF_WAIT = wait_gif
        self._cancelCallback = cancel_callback

        self._afterID: str | None = None
        self._TIME_AFTER = 40

        # Configuring the grid geometry manager...
        self.columnconfigure(
            index=0,
            weight=1)
        self.rowconfigure(
            index=0,
            weight=1)
        
        #
        self._lbl_wait = ttk.Label(
            master=self,
            image=self._GIF_WAIT[0])
        self._lbl_wait.grid(
            column=0,
            row=0,
            padx=8,
            pady=(8, 4,))
        
        #
        self._btn_cancel = ttk.Button(
            master=self,
            text='Cancel',
            command=self._Cancel)
        self._btn_cancel.grid(
            column=0,
            row=1,
            padx=8,
            pady=(4, 8,))
    
    def Show(self) -> None:
        self.place(
            relx=0.5,
            rely=0.5,
            anchor=tk.CENTER)
        self._afterID = self.after(
            self._TIME_AFTER,
            self._AnimateGif,
            1)

    def Close(self) -> None:
        self.after_cancel(self._afterID)
        self._cancelCallback = None
        self.place_forget()
        self.destroy()
    
    def ShowCanceling(self) -> None:
        self._btn_cancel['text'] = 'Canceling...'
        self._btn_cancel['state'] = tk.DISABLED
    
    def _Cancel(self) -> None:
        self.ShowCanceling()
        self._cancelCallback()
    
    def _AnimateGif(self, idx: int) -> None:
        try:
            self._lbl_wait['image'] = self._GIF_WAIT[idx]
        except IndexError:
            idx = 0
            self._lbl_wait['image'] = self._GIF_WAIT[idx]
        self._afterID = self.after(
            self._TIME_AFTER,
            self._AnimateGif,
            idx + 1)
    
    def __del__(self) -> None:
        # Breaking inbound references...
        self._master = None
        self._GIF_WAIT = None
        self._cancelCallback = None
        # Deallocating inside resources...
        del self._TIME_AFTER
        del self._btn_cancel
        del self._lbl_wait
        del self._afterID


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

        
class MessageView(Frame):
    _colors = {
        MessageType.INFO: 'LightBlue1',
        MessageType.WARNING: '#e9e48f',
        MessageType.ERROR: '#e5a3a3'}

    def __init__(
            self,
            master: tk.Misc,
            *,
            padx=5,
            pady=5,
            gap=10,
            max_events: int = 20,
            **kwargs
            ) -> None:
        super().__init__(master, **kwargs)

        # Getting the font of the tree view...
        try:
            self._font = master['font']
        except tk.TclError:
            self._font = nametofont('TkDefaultFont')

        self._mouseInside: bool = False
        self._msgs: list[tk.Message] = []
        self.max_events = max_events
        self._padx = padx
        self._pady = pady
        self._gap = gap

        self._InitGui()
        
        # Bindings...
        self.bind(
            '<Enter>',
            self._OnMouseEntered)
        self.bind(
            '<Leave>',
            self._OnMouseLeft)
        self._cnvs.bind_all(
            '<MouseWheel>',
            self._OnMouseWheel)
        self._cnvs.bind(
            '<Configure>',
            self._OnCnvsSizeChanged)
    
    def _InitGui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        #
        self._vscrlbr = ttk.Scrollbar(
            self,
            orient=tk.VERTICAL)
        self._cnvs = tk.Canvas(
            self,
            yscrollcommand=self._vscrlbr.set)  
        self._vscrlbr['command'] = self._cnvs.yview
        self._cnvs.grid(
            column=0,
            row=0,
            padx=5,
            pady=5,
            sticky=tk.NSEW)
        self._vscrlbr.grid(
            column=1,
            row=0,
            sticky=tk.NSEW)
    
    def _OnMouseEntered(self, _: tk.Event) -> None:
        self._mouseInside = True
    
    def _OnMouseLeft(self, _: tk.Event) -> None:
        self._mouseInside = False
    
    def _OnMouseWheel(self, event: tk.Event) -> None:
        if self._mouseInside:
            self._cnvs.yview_scroll(
                int(-1 * (event.delta / 24)),
                'units')
    
    def _OnCnvsSizeChanged(self, event: tk.Event) -> None:
        width = (
            event.width
            - (int(self._cnvs['bd']) << 1)
            - 4
            - (self._padx << 1))
        for msg in self._msgs:
            msg['width'] = width
        self._Redraw()
    
    def AddMessage(
            self,
            message: str,
            title: str | None = None,
            type: MessageType = MessageType.INFO
            ) -> None:

        text = ''
        if title:
            text = f'{title}\n\n'
        text += message

        msg = tk.Message(
            self._cnvs,
            anchor=tk.NW,
            background=MessageView._colors[type],
            width=self._GetInternalWidth(),
            text=text)
        self._msgs.insert(0, msg)

        while len(self._msgs) > self.max_events:
            self._msgs[-1].destroy()
            self._msgs.pop()
        
        self._cnvs.create_window(0, 0, window=msg)
        self.update()
        self._Redraw()
    
    def _Redraw(self) -> None:
        self._cnvs.delete('all')
        cnvsWidth = self._GetInternalWidth()
        cnvsHalfWidth = cnvsWidth >> 1
        cnvsHeight = self._GetInternalHeight()
        y = self._pady
        if self._msgs:
            self._cnvs.create_window(
                cnvsHalfWidth,
                y,
                anchor=tk.N,
                window=self._msgs[0])
            y += self._msgs[0].winfo_height()
        idx = 1
        while idx < len(self._msgs):
            y += self._gap
            self._cnvs.create_window(
                cnvsHalfWidth,
                y,
                anchor=tk.N,
                window=self._msgs[idx])
            y += self._msgs[idx].winfo_height()
            idx += 1
        y += self._pady
        if y < cnvsHeight:
            y = cnvsHeight
        self._cnvs['scrollregion'] = (0, 0, cnvsWidth, y)
    
    def _GetInternalWidth(self) -> int:
        return (
            self._cnvs.winfo_width()
            - 4
            - (self._padx << 1)
            + (int(self._cnvs['bd']) << 1))
    
    def _GetInternalHeight(self) -> int:
        return (
            self._cnvs.winfo_height()
            - 4
            - (self._pady << 1)
            + (int(self._cnvs['bd']) << 1))


class InfoView(ttk.Frame):
    def __init__(
            self,
            master: tk.Misc | None = ...,
            **kwargs) -> None:
        super().__init__(master, **kwargs)

        self._filename: str | Path | None = None
        self._mp3: AbstractMP3 | None = None
        self._lrc: Lrc | None = None

        self._InitGui()
    
    def _InitGui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._vscrlbr = ttk.Scrollbar(
            self,
            orient=tk.VERTICAL)
        self._hscrlbr = ttk.Scrollbar(
            self,
            orient=tk.HORIZONTAL)
        self._trvw = ttk.Treeview(
            self,
            columns=['#1'],
            xscrollcommand=self._hscrlbr.set,
            yscrollcommand=self._vscrlbr.set)
        self._hscrlbr['command'] = self._trvw.xview
        self._vscrlbr['command'] = self._trvw.yview
        self._trvw.grid(
            column=0,
            row=0,
            padx=5,
            pady=5,
            sticky=tk.NSEW)
        self._vscrlbr.grid(
            column=1,
            row=0,
            sticky=tk.NSEW)
        self._hscrlbr.grid(
            column=0,
            row=1,
            sticky=tk.NSEW)
        
        # Adding columns & headers...
        self._trvw.column('#0', width=150, stretch=False)
        self._trvw.heading('#0', anchor=tk.E)
        self._trvw.column('#1', width=350, stretch=False)
        self._trvw.heading('#1', anchor=tk.W)

        #
        self._iid_fileProp = self._trvw.insert(
            '',
            index='end',
            text='File properties',
            open=True)
        self._iid_mp3Info = self._trvw.insert(
            '',
            index='end',
            text='MP3 information',
            open=True)
        self._iid_mp3Tags = self._trvw.insert(
            '',
            index='end',
            text='MP3 tags',
            open=True)
        self._iid_lrcErrors = self._trvw.insert(
            '',
            index='end',
            text='LRC errors',
            open=True)
        self._iid_lrcTags = self._trvw.insert(
            '',
            index='end',
            text='LRC tags',
            open=True)
        self._iids_streams: list[str] = []
    
    def PopulateFileInfo(self, __filename: str | Path, /) -> None:
        # Saving the MP3Info object...
        self._filename = __filename
        # Clearing 'MP3 information' item...
        for item in self._trvw.get_children(self._iid_fileProp):
            self._trvw.delete(item)

    def PopulateMp3Info(self, __mp3Info: AbstractMP3, /) -> None:
        # Saving the MP3Info object...
        self._mp3 = __mp3Info
        # Clearing 'MP3 information' item...
        for item in self._trvw.get_children(self._iid_mp3Info):
            self._trvw.delete(item)
        # Adding MP3 infprmation...
        if self._mp3.Duration is not None:
            duration = timedelta(seconds=self._mp3.Duration)
            self._trvw.insert(
                parent=self._iid_mp3Info,
                index='end',
                text='Duration',
                values=(duration,))
        if self._mp3.BitRate is not None:
            self._trvw.insert(
                parent=self._iid_mp3Info,
                index='end',
                text='Bitrate',
                values=(self._mp3.BitRate,))
        if self._mp3.Encoder is not None:
            self._trvw.insert(
                parent=self._iid_mp3Info,
                index='end',
                text='Encoder',
                values=(self._mp3.Encoder,))
        try:
            if self._mp3.RawData['streams']:
                self._trvw.insert(
                    parent=self._iid_mp3Info,
                    index='end',
                    text='Number of streams',
                    values=(self._mp3.nStreams,))
        except Exception:
            pass
        # Clearing 'MP3 tags' item...
        for item in self._trvw.get_children(self._iid_mp3Tags):
            self._trvw.delete(item)
        # Adding MP3 tags...
        if self._mp3.Tags:
            for tag, value in self._mp3.Tags.items():
                self._trvw.insert(
                    parent=self._iid_mp3Tags,
                    index='end',
                    text=tag,
                    values=(value,))
        # Adding streams...
        self._trvw.delete(*self._iids_streams)
        self._iids_streams.clear()
        for stream in self._mp3.RawData['streams']:
            iidStream = self._trvw.insert(
                parent='',
                index='end',
                open=False,
                text=('Stream #' + str(stream['index'])))
            self._iids_streams.append(iidStream)
            self._PopulateStream_Recursively(iidStream, stream)
    
    def _PopulateStream_Recursively(
            self,
            iid: str,
            info: Mapping
            ) -> None:
        """Populates the the stream item in the treeview with 'iid' by
        using 'info' json, recursively.
        """
        for key, value in info.items():
            itemIid = self._trvw.insert(
                parent=iid,
                index='end',
                text=key)
            if isinstance(value, Mapping):
                self._PopulateStream_Recursively(itemIid, value)
            else:
                self._trvw.item(itemIid, values=(value,))

    def PopulateLrcInfo(self, __lrc: Lrc, /) -> None:
        # Clearing 'LRC error' item...
        for item in self._trvw.get_children(self._iid_lrcErrors):
            self._trvw.delete(item)
        for item in self._trvw.get_children(self._iid_lrcTags):
            self._trvw.delete(item)
        self._lrc = __lrc
        if not self._lrc:
            return
        for error in self._lrc.errors:
            self._trvw.insert(
                parent=self._iid_lrcErrors,
                index='end',
                text=error.name)
        for tag, value in self._lrc.tags.items():
            self._trvw.insert(
                parent=self._iid_lrcTags,
                index='end',
                text=tag,
                values=(value,))


class InfoView_old(ttk.Frame):
    def __init__(
            self,
            master: tk.Tk,
            gap: int = 12,
            sepLineWidth = 1,
            subitemIndent = 12,
            **kwargs) -> None:

        super().__init__(master, **kwargs)

        self._gap: int = gap
        self._sepLineWidth = sepLineWidth
        self._subitemIndent = subitemIndent
        self._lrc: Lrc | None = None
        self._mp3: AbstractMP3 | None = None

        self._InitGui()

        self._cnvs.bind('<Configure>', self._Redraw)
        self._cnvs.bind('<Map>', self._Redraw)
    
    def _InitGui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        #
        self._vscrlbr = ttk.Scrollbar(
            self,
            orient=tk.VERTICAL)
        self._cnvs = tk.Canvas(
            self,
            yscrollcommand=self._vscrlbr.set)
        self._vscrlbr['command'] = self._cnvs.yview
        self._cnvs.grid(
            column=0,
            row=0,
            padx=5,
            pady=5,
            sticky=tk.NSEW)
        self._vscrlbr.grid(
            column=1,
            row=0,
            sticky=tk.NSEW)
        
        #
        self._msg_fileInfoTitle = tk.Message(
            self._cnvs,
            text='File properties',
            padx=0,
            pady=0,
            justify=tk.LEFT)
        
        #
        self._msg_mp3InfoTitle = tk.Message(
            self._cnvs,
            text='MP3 information',
            padx=0,
            pady=0,
            justify=tk.LEFT)
        
        #
        self._frm_mp3Info = ttk.Frame(
            self._cnvs)
        
        #
        self._msg_mp3InfoKeys = tk.Message(
            self._cnvs,
            text='No MP3 info',
            justify=tk.RIGHT)
        
        #
        self._msg_mp3InfoValues = tk.Message(
            self._cnvs,
            text='',
            justify=tk.LEFT)
        
        #
        self._msg_lrcInfoTitle = tk.Message(
            self._cnvs,
            text='LRC informations',
            padx=0,
            pady=0,
            justify=tk.LEFT)
        
        self._Redraw()
    
    def _GetWidth(self) -> int:
        self._cnvs.update_idletasks()
        return (
            self._cnvs.winfo_width()
            - 4
            + (int(self._cnvs['bd']) << 1))
    
    def _GetHeight(self) -> int:
        self._cnvs.update_idletasks()
        return (
            self._cnvs.winfo_height()
            - 4
            + (int(self._cnvs['bd']) << 1))
    
    def _Redraw(self, event: tk.Event | None = None) -> None:
        cnvsWidth = self._GetWidth()
        cnvsHeight = self._GetHeight()

        self._cnvs.delete('all')
        self._cnvs.update_idletasks()

        # Drawing MP3 info title...
        y = self._gap
        self._cnvs.create_line(
            0,
            y,
            cnvsWidth,
            y,
            width=self._sepLineWidth)
        y += self._sepLineWidth
        self._msg_mp3InfoTitle['width'] = cnvsWidth
        self._cnvs.create_window(
            0,
            y,
            anchor=tk.NW,
            window=self._msg_mp3InfoTitle)
        y += self._msg_mp3InfoTitle.winfo_height()
        self._cnvs.create_line(
            0,
            y,
            cnvsWidth,
            y,
            width=self._sepLineWidth)
        y += self._sepLineWidth

        # Darwing MP3 info pairs...
        self._frm_mp3Info['width'] = round(cnvsWidth * 0.8)
        self._cnvs.create_window(
            cnvsWidth >> 1,
            y,
            anchor=tk.N,
            window=self._frm_mp3Info)
        '''self._cnvs.create_window(
            self._subitemIndent + self._msg_mp3InfoKeys.winfo_width(),
            y,
            anchor=tk.NW,
            window=self._msg_mp3InfoValues)'''
        y += (self._msg_mp3InfoValues.winfo_height() + self._gap)

        # Drawing _msg_lrcInfoTitle...
        y += self._gap
        self._cnvs.create_line(
            0,
            y,
            cnvsWidth,
            y,
            width=self._sepLineWidth)
        y += self._sepLineWidth
        self._msg_lrcInfoTitle['width'] = cnvsWidth
        self._cnvs.create_window(
            0,
            y,
            anchor=tk.NW,
            window=self._msg_lrcInfoTitle)
        y += self._msg_lrcInfoTitle.winfo_height()
        self._cnvs.create_line(
            0,
            y,
            cnvsWidth,
            y,
            width=self._sepLineWidth)
        y += self._sepLineWidth

        self._cnvs['scrollregion'] = (0, 0, cnvsWidth, y)
    
    def PopulateFile(self) -> None:
        pass

    def PopulateMp3(self, __mp3: AbstractMP3, /) -> None:
        self._mp3 = __mp3
        # Clearing previous infos...
        for widget in self._frm_mp3Info.winfo_children():
            widget.destroy()
        self._frm_mp3Info['width'] = self._cnvs.winfo_width()
        # Populating new MP3 infos...
        idx = 0
        if self._mp3.Duration is not None:
            msg = tk.Message(
                self._frm_mp3Info,
                text='Duration',
                justify=tk.RIGHT)
            msg.grid(
                column=0,
                row=idx,
                sticky=tk.W)
            duration = timedelta(seconds=self._mp3.Duration)
            msg = tk.Message(
                self._frm_mp3Info,
                text=str(duration),
                justify=tk.LEFT)
            msg.grid(
                column=1,
                row=idx,
                sticky=tk.E)
        self._msg_mp3InfoKeys['text'] = 'Duration'
        self._msg_mp3InfoValues['text'] = str(self._mp3.Duration)
        self._msg_mp3InfoKeys['text'] += '\nBitRate'
        self._msg_mp3InfoValues['text'] += f'\n{self._mp3.BitRate}'
        self._msg_mp3InfoKeys['text'] += '\nEncoder'
        self._msg_mp3InfoValues['text'] += f'\n{self._mp3.Encoder}'
        self._Redraw()
    
    def PopulateLrc(self, lrc: Lrc) -> None:
        self._lrc = lrc
        '''self._txt_lrc.delete('1.0', 'end')
        if lrc:
            self._txt_lrc.insert('1.0', repr(self._lrc)) '''  
        self._Redraw()         


class LyricsEditor(Sheet):
    def __init__(
            self,
            parent: tk.Misc,
            **kwargs
            ) -> None:
        super().__init__(parent, **kwargs)
        # Creating attributes...
        self._changed: bool = False
        """Specifies whether contents changed after 'Populate' methid."""
        self._hashCols: str
        """The hash of data in the sheet computed column by column."""
        self._hashRows: str
        """The hash of data in the sheet computed row by row."""
        self._lrc: Lrc
        """The LRC object which this editor is supposed to process it."""
        # Configuring the sheet...
        self.headers([
            'Timestap',
            'Lyrics/text'])
        self.enable_bindings(
            'drag_select',
            'single_select',
            'row_drag_and_drop',
            'row_select',
            'column_width_resize',
            'double_click_column_resize',
            'arrowkeys',
            'edit_cell')
    
    def SetChangeOrigin(self) -> None:
        """Sets the current status of the editor as the origin for
        chnage comparisons.
        """
        data = self.get_sheet_data()
        self._hashCols = self._HashCols(data)
        self._hashRows = self._HashRows(data)
    
    def HasChanged(self) -> bool:
        """Determines whether the content of the sheet has changed
        since last origin of change.
        """
        data = self.get_sheet_data()
        hashCols = self._HashCols(data)
        hashRows = self._HashRows(data)
        return all([
            hashCols == self._hashCols,
            hashRows == self._hashRows])

    def _HashCols(self, data: list[LyricsItem]) -> str:
        """Computes the hash of the sheet by concatenating timestamps
        and lyrics respectively.
        """
        from hashlib import sha512
        hash_ = sha512(b'')
        for lyricsItem in data:
            hash_.update(str(lyricsItem[0]).encode())
        for lyricsItem in data:
            hash_.update(str(lyricsItem[1]).encode())
        return hash_.hexdigest()
    
    def _HashRows(self, data: list[LyricsItem]) -> str:
        """Computes the hash of the sheet by concatenating `LyricsItem`s.
        """
        from hashlib import sha512
        hash_ = sha512(b'')
        for lyricsItem in data:
            hash_.update(
                str(lyricsItem[0]).encode() + str(lyricsItem[1]).encode())
        return hash_.hexdigest()
    
    def ApplyLyrics(self) -> None:
        """Applies the changes """
        if self._changed:
            data = self.get_sheet_data()
            self._lrc.lyrics = data
            self._changed = False
    
    def Populate(self, lrc: Lrc) -> None:
        """Populates the provided LRC object into this editor."""
        self._lrc = lrc
        if self._lrc:
            self.set_sheet_data(
                self._lrc.lyrics,
                reset_col_positions=False)
        else:
            self.set_sheet_data(
                [],
                reset_col_positions=False)
    
    def InsertRowAbove(self) -> None:
        if self._lrc:            
            # Getting the selection box...
            data = self.get_sheet_data()
            selectedBox = self.get_all_selection_boxes()
            if selectedBox:
                # There are selected cells,
                # Inserting a row at the start of them...
                rowStart, colStart, rowEnd, colEnd = selectedBox[0]
                data.insert(
                    rowStart,
                    LyricsItem(''))
                # Selecting the inserted row...
                if colEnd - colStart == 1:
                    rowIdx = rowEnd
                    colIdx = colStart
                else:
                    rowIdx = rowStart
                    colIdx = 1
            else:
                # No selected cells,
                # Inserting a row at the strat of the sheet...
                data.insert(
                    0,
                    LyricsItem(''))
                rowIdx = 0
                colIdx = 1

            self._changed = True
            self.set_sheet_data(data, reset_col_positions=False)
            self.select_cell(rowIdx, colIdx)              

    def InsertRowBelow(self) -> None:
        if self._lrc:
            # Getting the selection box...
            data = self.get_sheet_data()
            selectedBox = self.get_all_selection_boxes()
            if selectedBox:
                # There are selected cells,
                # Inserting a row at the end of them...
                rowStart, colStart, rowEnd, colEnd = selectedBox[0]
                data.insert(
                    rowEnd,
                    LyricsItem(''))
                # Selecting the inserted row...
                if colEnd - colStart == 1:
                    rowIdx = rowEnd
                    colIdx = colStart
                else:
                    rowIdx = rowEnd
                    colIdx = 1
            else:
                # No selected cells,
                # Inserting a row at the end of the sheet...
                rowIdx = len(data)
                data.insert(
                    rowIdx,
                    LyricsItem(''))
                colIdx = 1

            self._changed = True
            self.set_sheet_data(data, reset_col_positions=False)
            self.select_cell(rowIdx, colIdx)

    def ClearCells(self) -> None:
        selectedCells = self.get_selected_cells()
        data = self.get_sheet_data()
        for cell in selectedCells:
            rowIdx, colIdx = cell
            if data[rowIdx][colIdx]:
                self._changed = True
                data[rowIdx][colIdx] = ''
        self.set_sheet_data(data, reset_col_positions=False)
    
    def RemoveRows(self) -> None:
        # Getting the selected box...
        selectedBox = self.get_all_selection_boxes()
        if not selectedBox:
            # No selected cells, returning...
            return
        rowStart, _, rowEnd, _ = selectedBox[0]
        data = self.get_sheet_data()
        data = [*data[0:rowStart], *data[rowEnd:]]
        self._changed = True
        self.set_sheet_data(data, reset_col_positions=False)
        self.deselect()
    
    def SetTimestamp(self, pos: float) -> None:
        if self._lrc:
            # Getting the selected box...
            selectedBox = self.get_all_selection_boxes()
            if not selectedBox:
                # No selected cells, returning...
                return
            rowStart, _, rowEnd, _ = selectedBox[0]
            if (rowEnd - rowStart) == 1:
                data = self.get_sheet_data()
                data[rowStart][0] = Timestamp.FromFloat(pos)
                self._changed = True
                self.set_sheet_data(data, reset_col_positions=False)
                if rowEnd < len(data):
                    self.select_cell(rowEnd, 0)
    
    def _GetClipboardAsList(self) -> list[str]:
        clipboard = self.clipboard_get()
        return clipboard.strip().splitlines()
    
    def OverrideFromClipboard(self) -> None:
        if self._lrc:
            data = self.get_sheet_data()
            selectedBox = self.get_all_selection_boxes()
            if not data:
                rowIdx = 0
            elif selectedBox:
                rowIdx, _, _, _ = selectedBox[0]
            else:
                # No selection in the populated sheet, returning...
                return
            
            try:
                clipLines = self._GetClipboardAsList()
                lineIdx = 0
                while True:
                    data[rowIdx][1] = clipLines[lineIdx]
                    lineIdx += 1
                    rowIdx += 1
            except IndexError:
                # Checking whether clipboard exhausted...
                if lineIdx >= len(clipLines):
                    # clipboard exhausted, we've done, returning...
                    return
                # The sheet exhausted, appending the rest of clipboard...
                for idx in range(lineIdx, len(clipLines)):
                    data.append(LyricsItem(clipLines[idx]))
            self.set_sheet_data(data, reset_col_positions=False)

            if clipLines:
                self._changed = True

    def InsertFromClipboard(self) -> None:
        pass


class ABView(tk.Canvas):
    def __init__(
            self,
            master: Misc | None = None,
            width: int = 150,
            height: int = 8,
            **kwargs
            ) -> None:
        super().__init__(master, **kwargs)
        self['bd'] = 0
        self['width'] = width
        self['height'] = height
        self['background'] = '#fcf8de'

        # Initializing atrributes...
        self._a: float = 0.0
        """Specifies the A component of the A-B repeat object."""
        self._b: float = 0.0
        """Specifies the B component of the A-B repeat object."""
        self._length: float = 0.0
        """Specifies the maximum length of the A-B repeat object."""

        # Bindings...
        self.bind(
            '<Button-1>',
            self._OnMouseClicked)
    
    @property
    def a(self) -> float:
        """Gets or sets the A component of the A-B repeat object."""
        return self._a
    
    @a.setter
    def a(self, __a, /) -> None:
        if not isinstance(__a, (float, int,)):
            raise TypeError(
                "The A component of a A-B repeat object must be "
                + "a float or an integer")
        if not (0.0 <= __a <= self._length):
            raise ValueError(
                "Out of range value for the A "
                + "component of a A-B repeat object")
        self._a = __a
        if __a > self._b:
            self._b = self._length
        self._Redraw()
    
    @property
    def b(self) -> float:
        """Gets or sets the B component of the A-B repeat object."""
        return self._b
    
    @a.setter
    def b(self, __b, /) -> None:
        if not isinstance(__b, (float, int,)):
            raise TypeError(
                "The B component of a A-B repeat object must be "
                + "a float or an integer")
        if not (0.0 <= __b <= self._length):
            raise ValueError(
                "Out of range value for the B "
                + "component of a A-B repeat object")
        self._b = __b
        if __b < self._a:
            self._a = 0.0
        self._Redraw()
    
    @property
    def length(self) -> float:
        """Gets or sets the 'length' component of this A-B repeat object.
        By setting this property, 'a' and 'b' will be set to 0.0.
        """
        return self._length
    
    @length.setter
    def length(self, __leng, /) -> None:
        if not isinstance(__leng, float):
            raise TypeError(
                "The length component of the A-B "
                + "repeat object must be a float")
        if __leng < 0.0:
            raise ValueError(
                "The length component of the A-B repeat"
                + " object must be positive")
        self._length = __leng
        self._a = 0.0
        self._b = 0.0
        self._Redraw()
    
    def Reset(self) -> None:
        """Resets this A-B repeat object."""
        self._a = 0.0
        self._b = 0.0
        self._length = 0.0
    
    def IsSet(self) -> bool:
        """Specifies whether this A-B repeat object is set or not."""
        return self._length > 0.0 and ((self._b - self._a) > 0.0)
    
    def IsInside(self, __value: float, /) -> bool:
        """Specifies whether the A-B interval is set and the provided
        value is inside the interval.
        """
        return self.IsSet() and (self._a <= __value <= self._b)
    
    def _OnMouseClicked(self, event: tk.Event) -> None:
        cnvsWidth = self.winfo_width()
        # Detecting whether ALT is holding or not...
        if event.state & Modifiers.ALT == Modifiers.ALT:
            if self._length > 0.0:
                self.b = event.x / cnvsWidth * self._length
        # Detecting whether ALT is holding or not...
        elif event.state & Modifiers.CONTROL == Modifiers.CONTROL:
            if self._length > 0.0:
                self.a = event.x / cnvsWidth * self._length
    
    def _Redraw(self) -> None:
        self.delete('all')
        if self.IsSet():
            cnvsWidth = self.winfo_width()
            cnvsHeight = self.winfo_height()
            aX = round(self._a / self._length * cnvsWidth)
            bX = round(self._b / self._length * cnvsWidth)
            self.create_line(
                aX,
                0,
                bX,
                0,
                stipple='gray50',
                width=cnvsHeight)
