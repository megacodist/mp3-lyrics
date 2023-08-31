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

from media.abstract_mp3 import AbstractMp3
from media.lrc import Lrc


class InfoView(ttk.Frame):
    def __init__(
            self,
            master: tk.Misc | None = ...,
            **kwargs) -> None:
        super().__init__(master, **kwargs)

        self._filename: str | Path | None = None
        self._mp3: AbstractMp3 | None = None
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
        self._iid_fileInfo = self._trvw.insert(
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
    
    def Clear(self) -> None:
        """Clears all the information in this info view."""
        for child in self._trvw.get_children(self._iid_fileInfo):
            self._trvw.delete(child)
        for child in self._trvw.get_children(self._iid_lrcErrors):
            self._trvw.delete(child)
        for child in self._trvw.get_children(self._iid_lrcTags):
            self._trvw.delete(child)
        for child in self._trvw.get_children(self._iid_mp3Info):
            self._trvw.delete(child)
        for child in self._trvw.get_children(self._iid_mp3Tags):
            self._trvw.delete(child)
        for child in self._trvw.get_children(self._iids_streams):
            self._trvw.delete(child)
    
    def ClearFileInfo(self) -> None:
        """Clears file information from the info view."""
        for child in self._trvw.get_children(self._iid_fileInfo):
            self._trvw.delete(child)

    def ClearAudioInfo(self) -> None:
        """Clears audio information from the info view."""
        for child in self._trvw.get_children(self._iid_mp3Info):
            self._trvw.delete(child)
        for child in self._trvw.get_children(self._iid_mp3Tags):
            self._trvw.delete(child)
        self._trvw.delete(*self._iids_streams)
        self._iids_streams.clear()

    def ClearLrcInfo(self) -> None:
        """Clears lyrics information from the info view."""
        for child in self._trvw.get_children(self._iid_lrcErrors):
            self._trvw.delete(child)
        for child in self._trvw.get_children(self._iid_lrcTags):
            self._trvw.delete(child)
    
    def PopulateFileInfo(self, __filename: str | Path, /) -> None:
        # Saving the MP3Info object...
        self._filename = __filename
        # Clearing 'MP3 information' item...
        for item in self._trvw.get_children(self._iid_fileInfo):
            self._trvw.delete(item)

    def PopulateAudioInfo(self, __mp3Info: AbstractMp3, /) -> None:
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
