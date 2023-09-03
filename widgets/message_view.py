#
# 
#
"""This module offers the following items:

1. `MessageType`
2. `MessageView`
"""


import enum
import logging
from threading import RLock
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

from utils.types import TkImg


class MessageType(enum.Enum):
    """This enumeration lists all supported severities of a message."""
    INFO = 'LightBlue1'
    WARNING = '#e9e48f'
    ERROR = '#e5a3a3'


class _MessageData:
    """This class packs and offers information for each message in the
    message view.
    """

    _mtx_hash = RLock()
    """This mutex is used to ensure uniqueness of hash values among
    objects of tis class.
    """

    @classmethod
    def _GetHash(cls) -> int:
        """Returns a unique hash for every call."""
        from datetime import datetime
        cls._mtx_hash.acquire()
        curDateTime = datetime.now()
        cls._mtx_hash.release()
        return hash(curDateTime)

    def __init__(
            self,
            message: str,
            title: str | None = None,
            type_: MessageType = MessageType.INFO,
            ) -> None:
        self._hash = _MessageData._GetHash()
        self._message = message
        self._title = title
        self._type = type_

    def __del__(self) -> None:
        del self._hash
        del self._message
        del self._title
        del self._type


class _MessageItem(tk.Canvas):
    def __init__(
            self,
            master: tk.Misc,
            close_img: TkImg,
            close_cb: Callable[[], None],
            *,
            img_size: int = 16,
            **kwargs
            ) -> None:
        super().__init__(master, **kwargs)
        # Removing border...
        self.config(borderwidth=0, highlightthickness=0)
        self._IMG_CLOSE = close_img
        """The image of the close button."""
        self._cbClose = close_cb
        self._imgSize: int = img_size
        """The quantity of width and height of the close image."""
        self._msgData : _MessageData | None = None
        """The message data associated with this message item."""
        self._msg_title = tk.Message(
            self,
            justify=tk.CENTER)
        self._msg_msg = tk.Message(
            self,
            justify=tk.LEFT)
        self._lbl_close = ttk.Label(
            self,
            cursor='hand1',
            image=self._IMG_CLOSE,
            width=self._imgSize)
        # Binding events...
        self._lbl_close.bind("<Button-1>", self._OnCloseClicked)
    
    def _OnCloseClicked(self, _: tk.Event) -> None:
        if self._msgData is None:
            logging.error('E-1-1', stack_info=True)
            return
        self._cbClose(self._msgData)
    
    def Populate(self, msg_data: _MessageData) -> None:
        self._msgData = msg_data
        self._RedrawCnvs(
            title=msg_data._title if msg_data._title else \
                msg_data._type.name.title(),
            message=msg_data._message,
            background=msg_data._type.value)

    def _RedrawCnvs(self, title: str, message: str, background: str) -> None:
        self.delete('all')
        self.update_idletasks()
        cnvsWidth = self.winfo_reqwidth()
        self['background'] = background
        # Drawing the close image...
        imgSize = self._imgSize + 4
        self._lbl_close['background'] = background
        self.create_window(
            cnvsWidth - imgSize,
            0,
            window=self._lbl_close,
            anchor=tk.NW)
        # Drawing title...
        titleWidth = cnvsWidth - imgSize
        self._msg_title['width'] = titleWidth
        self._msg_title['background'] = background
        self._msg_title['text'] = title
        self.create_window(
            titleWidth // 2,
            0,
            window=self._msg_title,
            anchor=tk.N)
        self._msg_title.update_idletasks()
        y = self._msg_title.winfo_reqheight()
        y = y if y > imgSize else imgSize
        # Drawing a separator...
        y += 1
        self.create_line(0, y, cnvsWidth, y)
        y += 2
        # Drawing the message...
        self._msg_msg['width'] = cnvsWidth
        self._msg_msg['background'] = background
        self._msg_msg['text'] = message
        self.create_window(
            0,
            y,
            window=self._msg_msg,
            anchor=tk.NW)
        self._msg_msg.update_idletasks()
        y += self._msg_msg.winfo_reqheight()
        self.config(height=y)
        self.update_idletasks()
    
    def destroy(self) -> None:
        # Cleaing up simple attributes...
        del self._IMG_CLOSE
        del self._cbClose
        del self._imgSize
        del self._msgData
        # Cleaing up children widgets...
        self._lbl_close.destroy()
        self._msg_msg.destroy()
        self._msg_title.destroy()
        # Going on the cleaning procedure into super object...
        super().destroy()


class MessageView(ttk.Frame):
    def __init__(
            self,
            master: tk.Misc,
            close_img: TkImg,
            *,
            max_msgs: int = 20,
            padx: int = 8,
            pady: int = 8,
            ) -> None:
        super().__init__(master)
        self._master = master
        """The parent widget of this `MessageView` object."""
        self._IMG_CLOSE = close_img
        """The close image."""
        self._scrollRegion: tuple[int, int, int, int] = (0, 0, 0, 0)
        """The scrollable region of the internal canvas in the form of
        `(x0, y0, x1, y1)` where `(x0, y0)` is the coordinates of upper
        left corner of the scrollable region and `(x1, y1)` is the lower
        right corner.
        """
        self._cnvsWidth: int
        """The width of the internal canvas."""
        self._cnvsHeight: int
        """The height of the internal canvas."""
        self._msgsData: list[_MessageData] = []
        self._msgsWdgts: list[_MessageItem] = []
        self._padx = padx
        self._pady = pady
        self._maxMsgs = max_msgs
        """Specifies maximum number of messages in the view."""
        self._InitGui()
        self._cnvs.bind('<Configure>', self._OnResized)
    
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
            sticky=tk.NSEW)
        self._vscrlbr.grid(
            column=1,
            row=0,
            sticky=tk.NSEW)
        #
        self._frm_container = tk.Frame(self._cnvs)
        self._frm_container.columnconfigure(0, weight=1)
    
    def _OnResized(self, event: tk.Event) -> None:
        try:
            if (self._cnvsWidth != event.width or
                    self._cnvsHeight != event.height):
                self._cnvsWidth = event.width
                self._cnvsHeight = event.height
                self._Resize()
        except AttributeError:
            self._cnvsWidth = event.width
            self._cnvsHeight = event.height
    
    def AddMessage(
            self,
            message: str,
            title: str | None = None,
            type_: MessageType = MessageType.INFO,
            ) -> None:
        """Adds a message to the view. Arguments are as follow:
        * `message`: Necessary. The body of the message.
        * `title`: Optional. The title of the message if it is NOT
        present, the string representation of the `type` will be used.
        * `type_`: Optional. The type of the message.
        """
        # Adding data of the new message to the view...
        msgData = _MessageData(message, title, type_)
        self._msgsData.insert(0, msgData)
        while len(self._msgsData) > self._maxMsgs:
            del self._msgsData[-1]
        # Preparing widget of the new message...
        if len(self._msgsWdgts) > len(self._msgsData):
            widget = self._msgsWdgts.pop()
            self._msgsWdgts.insert(0, widget)
        else:
            widget = _MessageItem(
                self,
                self._IMG_CLOSE,
                self.RemoveMessage)
            self._msgsWdgts.insert(0, widget)
        self._RedrawCnvs()
    
    def RemoveMessage(self, msg_data: _MessageData) -> None:
        idx = self._msgsData.index(msg_data)
        del self._msgsData[idx]
        msgItem = self._msgsWdgts.pop(idx)
        self._msgsWdgts.append(msgItem)
        self._RedrawCnvs()
    
    def Clear(self) -> None:
        """Clears the whole content."""
        self._cnvs.delete('all')
        self._msgsData.clear()
        self._scrollRegion = (
            0,
            0,
            self._GetCnvsWidth(),
            self._GetCnvsHeight())
        self._cnvs['scrollregion'] = self._scrollRegion
    
    def _RedrawCnvs(self) -> None:
        self._cnvs.delete('all')
        self._cnvs.update_idletasks()
        cnvsWidth = self._GetCnvsWidth()
        msgItemWidth = cnvsWidth - 2 * self._pady
        y = self._padx
        for idx in range(len(self._msgsData)):
            self._msgsWdgts[idx].config(width=msgItemWidth)
            self._msgsWdgts[idx].Populate(self._msgsData[idx])
            self._cnvs.create_window(
                self._pady,
                y,
                anchor=tk.NW,
                window=self._msgsWdgts[idx])
            self._msgsWdgts[idx].update_idletasks()
            y += (self._padx + self._msgsWdgts[idx].winfo_height())
        self._scrollRegion = (
            0,
            0,
            cnvsWidth,
            y)
        self._cnvs['scrollregion'] = self._scrollRegion

    def _Resize(self) -> None:
        for idx in range(len(self._msgsData)):
            self._msgsWdgts[idx].Populate(self._msgsData[idx])

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
    
    def destroy(self) -> None:
        # Cleaning up simple attributes ---------------
        del self._master
        del self._IMG_CLOSE
        del self._maxMsgs
        del self._scrollRegion
        # Cleaning up data structures -----------------
        # Freeing '_msgsData'...
        self._msgsData.clear()
        del self._msgsData
        # Freeing '_msgsWdgts'...
        for widget in self._msgsWdgts:
            widget.destroy()
        self._msgsWdgts.clear()
        del self._msgsWdgts
        # Destroying children widgets -----------------
        self._vscrlbr.destroy()
        del self._vscrlbr
        self._cnvs.destroy()
        del self._cnvs
        # Calling the parent destructor ---------------
        super().destroy()
