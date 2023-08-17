#
# 
#
"""
"""


from datetime import timedelta
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from typing import Mapping

from media.abstract_mp3 import AbstractMP3
from media.lrc import Lrc


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
