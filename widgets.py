from datetime import timedelta
from enum import IntEnum
from pathlib import Path
import tkinter as tk
from tkinter import Frame, Misc, ttk
from tkinter.font import nametofont, Font
from typing import Any, Callable

from megacodist.keyboard import Modifiers
from PIL.ImageTk import PhotoImage
from mutagen.mp3 import MP3
from tksheet import Sheet
from tksheet._tksheet_other_classes import EditCellEvent

from abstract_mp3_lib import AbstractMP3Info
from lrc import Lrc, LyricsItem, Timestamp


class MessageType(IntEnum):
    INFO = 0
    WARNING = 1
    ERROR = 2


class FolderView(ttk.Treeview):
    @classmethod
    def GetComparer(cls, filename: str) -> tuple[str, str]:
        """Returns a tuple which the first element is file name without
        path and extension and the second element is the extension. For
        example for the file name 'some/path/stem.ext', it returns
        ('stem', '.ext',)
        """
        pFilename = Path(filename)
        return pFilename.stem.lower(), pFilename.suffix.lower()

    def __init__(
            self,
            master: tk.Tk,
            image: PhotoImage,
            select_callback: Callable[[str], None],
            **kwargs) -> None:

        kwargs['selectmode'] = 'browse'
        super().__init__(master, **kwargs)

        self.heading('#0', anchor=tk.W)
        self.column(
            '#0',
            width=200,
            stretch=False,
            anchor=tk.W)

        # Getting the font of the tree view...
        self._font: Font
        """Specifies the font of the FolderView."""
        try:
            self._font = self['font']
        except tk.TclError:
            self._font = nametofont('TkDefaultFont')
        
        self._IMG = image
        """Specifies the image of all items in the FolderView."""
        self._dir: str | None = None
        """Specifies the directory of the FolderView."""
        self._selectCallback: Callable[[str], None] = select_callback
        """Specifies a callback which is called when an item is selected in
        the FolderView
        """
        self._toIgnoreNextSelect: bool = False
        """Specifies whether to ignore the next Select event."""
        self._prevSelectedItem: str = ''
        """Specifies the previous selected item. it helps avoid firing
        Select event for the selected item. So to stimulate the Select
        event, you have to select another item in the list.
        """

        self.bind(
            '<<TreeviewSelect>>',
            self._OnItemSelectionChanged)
    
    def AddFilenames(
            self,
            folder: str,
            filenames: list[str],
            select_idx: int | None = None
            ) -> None:
        
        self._dir = folder
        # Writing folder in the heading...
        self.heading('#0', text=folder)
        # Adding filenames...
        self._Clear()
        minColWidth = self.winfo_width() - 4
        for filename in filenames:
            itemWidth = 40 + self._font.measure(filename)
            if itemWidth > minColWidth:
                minColWidth = itemWidth
            self.insert(
                parent='',
                index=tk.END,
                text=filename,
                image=self._IMG)
        # Setting the minimu width of the column...
        self.column('#0', width=minColWidth)
        # Selecting the specified file...
        self._toIgnoreNextSelect = True
        if select_idx is not None:
            self.selection_add(
                self.get_children('')[select_idx])
        # Scrolling the FolderView to the selected item...
        try:
            self.yview_moveto(select_idx / len(filenames))
        except TypeError:
            pass

    def _Clear(self) -> None:
        """Makes the FolderView empty."""
        for iid in self.get_children(''):
            self.delete(iid)
    
    def _OnItemSelectionChanged(self, event: tk.Event) -> None:
        selectedItemID = self.selection()
        if selectedItemID:
            selectedItemID = selectedItemID[0]
            if not self._toIgnoreNextSelect:
                if self._prevSelectedItem != selectedItemID:
                    text = self.item(selectedItemID, option='text')
                    self._selectCallback(
                        str(Path(self._dir) / text))
            else:
                self._toIgnoreNextSelect = False
            self._prevSelectedItem = selectedItemID

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
            highlightable: bool = False,
            highlightColor: str = 'yellow',
            sepWidth: int = 1,
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
        self._sepWidth = sepWidth
        self._sepColor = sepColor
        self._gap = gap
        self._ipadx = ipadx
        self._ipady = ipady
        self._width: int
        self._height: int

        self._vscrlbr: ttk.Scrollbar
        self._cnvs: tk.Canvas
        self._msgs: list[tk.Message] = []

        self._InitGui()

        self._cnvs.bind(
            '<Configure>',
            self._OnSizeChanged)
    
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
    
    def _OnSizeChanged(self, event: tk.Event) -> None:
        try:
            if self._width != event.width or self._height != event.height:
                self._width = event.width
                self._height = event.height
                self._Redraw()
        except AttributeError:
            self._width = event.width
            self._height = event.height
    
    @property
    def sepWidth(self) -> int:
        return self._sepWidth
    
    @sepWidth.setter
    def sepWidth(self, __value: int) -> None:
        pass

    @property
    def lyrics(self) -> list[str]:
        return self._lyrics
    
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
        return (
            self._cnvs.winfo_width()
            - 4
            + (int(self._cnvs['bd']) << 1))
    
    def _GetHeight(self) -> int:
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
        cnvsMidWidth = cnvsWidth >> 1
        cnvsHeight = self._GetHeight()
        cnvsMidHeight = cnvsHeight >> 1

        nMsgs = len(self._msgs)
        nLyrics = len(self._lyrics)
        idx = nMsgs
        while idx < nLyrics:
            msg = tk.Message(
                master=self._cnvs,
                anchor=tk.NW,
                justify=tk.CENTER,
                width=cnvsWidth)
            self._msgs.append(msg)
            self._cnvs.create_window(0, 0, window=msg)
            idx += 1
        if nMsgs < nLyrics:
            self._cnvs.update()
        self._cnvs.delete('all')

        if nLyrics <= 0:
            # No lyrics to show, returning after clearing the canvas...
            return
        
        # Drawing the first Message (lyric)...
        y = cnvsMidHeight
        self._msgs[0]['width'] = cnvsWidth
        self._msgs[0]['text'] = self._lyrics[0]
        self._cnvs.create_window(
            cnvsMidWidth,
            y,
            anchor=tk.N,
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
                width=self._sepWidth)

            y += (self._gap + self._sepWidth)
            try:
                self._heights[idx] = y - cnvsMidHeight
            except IndexError:
                self._heights.append(y - cnvsMidHeight)
            self._msgs[idx]['width'] = cnvsWidth
            self._msgs[idx]['text'] = self._lyrics[idx]
            self._cnvs.create_window(
                cnvsMidWidth,
                y,
                anchor=tk.N,
                window=self._msgs[idx])
            self._cnvs.update()
            y += self._msgs[idx].winfo_height()
        
        # Setting the scroll region...
        self._extraHeight = y + cnvsMidHeight
        if self._highlightable:
            scrollRegion = (0, 0, cnvsWidth, self._extraHeight)
        else:
            if (y - cnvsMidHeight) < cnvsHeight:
                halfDiff = (cnvsHeight - y + cnvsMidHeight) >> 1
                scrollRegion = (
                    0,
                    cnvsMidHeight - halfDiff,
                    cnvsWidth,
                    y + halfDiff)
            else:
                scrollRegion = (0, cnvsMidHeight, cnvsWidth, y)
        self._cnvs['scrollregion'] = scrollRegion
        self._cnvs.yview_moveto(0)

        
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
            self._OnSizeChanged)
    
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
    
    def _OnSizeChanged(self, event: tk.Event) -> None:
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
        cnvsHeight = self._GetInternalHeight()
        y = self._pady
        if self._msgs:
            x = self._padx + ((cnvsWidth - self._msgs[0].winfo_width()) >> 1)
            self._cnvs.create_window(
                x,
                y,
                anchor=tk.NW,
                window=self._msgs[0])
            y += self._msgs[0].winfo_height()
        idx = 1
        while idx < len(self._msgs):
            x = self._padx + (
                (cnvsWidth - self._msgs[idx].winfo_width()) >> 1)
            y += self._gap
            self._cnvs.create_window(
                x,
                y,
                anchor=tk.NW,
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

        self._mp3Info: AbstractMP3Info | None = None
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
        self._trvw.insert(
            '',
            index=0,
            text='File properties',
            open=True)
        self._trvw.insert(
            '',
            index=1,
            text='MP3 information',
            open=True)
        self._trvw.insert(
            '',
            index=2,
            text='MP3 tags',
            open=True)
        self._trvw.insert(
            '',
            index=3,
            text='LRC errors',
            open=True)
    
    def PopulateFileInfo(self) -> None:
        pass

    def PopulateMp3Info(self, __mp3Info: AbstractMP3Info, /) -> None:
        # Saving the MP3Info object...
        self._mp3Info = __mp3Info
        # Clearing 'MP3 information' item...
        mp3InfoIid = self._trvw.get_children('')[1]
        for item in self._trvw.get_children(mp3InfoIid):
            self._trvw.delete(item)
        # Adding MP3 infprmation...
        if self._mp3Info.Duration is not None:
            duration = timedelta(seconds=self._mp3Info.Duration)
            self._trvw.insert(
                parent=mp3InfoIid,
                index='end',
                text='Duration',
                values=(duration,))
        if self._mp3Info.BitRate is not None:
            self._trvw.insert(
                parent=mp3InfoIid,
                index='end',
                text='Bitrate',
                values=(self._mp3Info.BitRate,))
        if self._mp3Info.Encoder is not None:
            self._trvw.insert(
                parent=mp3InfoIid,
                index='end',
                text='Encoder',
                values=(self._mp3Info.Encoder,))
        try:
            if self._mp3Info.RawData['streams']:
                self._trvw.insert(
                    parent=mp3InfoIid,
                    index='end',
                    text='Number of streams',
                    values=(len(self._mp3Info.RawData['streams']),))
        except Exception:
            pass
        # Clearing 'MP3 tags' item...
        mp3TagsIid = self._trvw.get_children('')[2]
        for item in self._trvw.get_children(mp3TagsIid):
            self._trvw.delete(item)
        # Adding MP3 tags...
        if self._mp3Info.Tags:
            for tag, value in self._mp3Info.Tags.items():
                self._trvw.insert(
                    parent=mp3TagsIid,
                    index='end',
                    text=tag,
                    values=(value,))

    def PopulateLrcInfo(self, __lrc: Lrc, /) -> None:
        self._lrc = __lrc
        # Clearing 'LRC error' item...
        lrcError = self._trvw.get_children('')[3]
        for item in self._trvw.get_children(lrcError):
            self._trvw.delete(item)
        for error in self._lrc.errors:
            self._trvw.insert(
                parent=lrcError,
                index='end',
                text=error)


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
        self._mp3Info: AbstractMP3Info | None = None

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

    def PopulateMp3(self, __mp3Info: AbstractMP3Info, /) -> None:
        self._mp3Info = __mp3Info
        # Clearing previous infos...
        for widget in self._frm_mp3Info.winfo_children():
            widget.destroy()
        self._frm_mp3Info['width'] = self._cnvs.winfo_width()
        # Populating new MP3 infos...
        idx = 0
        if self._mp3Info.Duration is not None:
            msg = tk.Message(
                self._frm_mp3Info,
                text='Duration',
                justify=tk.RIGHT)
            msg.grid(
                column=0,
                row=idx,
                sticky=tk.W)
            duration = timedelta(seconds=self._mp3Info.Duration)
            msg = tk.Message(
                self._frm_mp3Info,
                text=str(duration),
                justify=tk.LEFT)
            msg.grid(
                column=1,
                row=idx,
                sticky=tk.E)
        self._msg_mp3InfoKeys['text'] = 'Duration'
        self._msg_mp3InfoValues['text'] = str(self._mp3Info.Duration)
        self._msg_mp3InfoKeys['text'] += '\nBitRate'
        self._msg_mp3InfoValues['text'] += f'\n{self._mp3Info.BitRate}'
        self._msg_mp3InfoKeys['text'] += '\nEncoder'
        self._msg_mp3InfoValues['text'] += f'\n{self._mp3Info.Encoder}'
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

        self._changed: bool = False
        """Specifies whether contents changed after 'Populate' methid."""
        self._lrc: Lrc

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
        
        # Binding...
        self.extra_bindings(
            'end_edit_cell',
            self._OnCellEdited)
        self.extra_bindings(
            'end_row_index_drag_drop',
            self._OnRowDragDroped)
    
    def _OnCellEdited(self, event: EditCellEvent) -> None:
        self._changed = True
    
    def _OnRowDragDroped(self) -> None:
        self._changed = True
    
    def ApplyLyrics(self) -> None:
        if self._changed:
            data = self.get_sheet_data()
            self._lrc.lyrics = data
            self._changed = False
    
    def Populate(self, lrc: Lrc) -> None:
        self._lrc = lrc
        if self._lrc:
            self.set_sheet_data(
                self._lrc.lyrics,
                reset_col_positions=False)
        else:
            self.set_sheet_data(
                [],
                reset_col_positions=False)
        self._changed = False
    
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
