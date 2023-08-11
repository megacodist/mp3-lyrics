"""This module provide APIs to handle asynchronous operations smoothly.

Dependecies:
-----------
1. Python 3.10+
2. Pillow 9.3
"""

from concurrent.futures import Future
from enum import IntEnum
import tkinter as tk
from tkinter import Misc, Widget
from tkinter import ttk
from typing import Callable

from PIL.ImageTk import PhotoImage


class AsyncOPIDCollision(IntEnum):
    CancelingPrev = 1
    Pending = 2
    AsyncExec = 3


class AsyncOpInfo:
    def __init__(
            self,
            future: Future,
            widgets: list[Widget],
            id: str | None = None
            ) -> None:
        self.widgets = widgets
        """Specifies a list of Tkinter Widgets that depend upon the
        completion of this opeartion.
        """
        self.future = future
        self.id = id
    
    def __del__(self) -> None:
        # Deallocating inside resources...
        del self._future
        del self._widgets
        del self._id


class WaitFrame(ttk.Frame):
    def __init__(
            self,
            master: tk.Misc,
            wait_gif: list[PhotoImage],
            cancel_handler: Callable[[], None],
            **kwargs
            ) -> None:
        super().__init__(master, **kwargs)
        self['relief'] = tk.RIDGE

        # Storing inbound references...
        self._master = master
        self._GIF_WAIT = wait_gif
        self._cancelCallback = cancel_handler

        self._afterID: str | None = None
        self._TIME_AFTER = 40

        # Configuring the grid geometry manager...
        self.columnconfigure(index=0, weight=1)
        self.rowconfigure(index=0, weight=1)
        
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


class AsyncOpManager:
    def __init__(
            self,
            master: Misc,
            cancel_handler: Callable[[], None]
            ) -> None:
        self._master = master
        self._cancelHandler = cancel_handler
        self._operations: list[AsyncOpInfo] = []
        self._waitFrames: list[WaitFrame] = []
        self._pendings: dict[str, list[AsyncOpInfo]] = {}
        self._idGen: int = 0
    
    def AddOp(
            self,
            startAction: Callable[[], Future],
            doneAction: Callable,
            widgets: list[Widget],
            id: str | None = None,
            collision: AsyncOPIDCollision = AsyncOPIDCollision.AsyncExec
            ) -> None:
        """Adds an asynchronous operation to the manager."""
        if id is None:
            self._idGen += 1
            id = str(self._idGen)
        operationsID = [op.id for op in self._operations]
        if id in operationsID:
            if collision == AsyncOPIDCollision.CancelingPrev:
                self.Cancel(id)
            if collision != AsyncOPIDCollision.AsyncExec:
                pass

    def Cancel(self, id: str) -> None:
        """Calncels the async operation with the specified ID."""
        pass
