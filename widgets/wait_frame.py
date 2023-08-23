#
# 
#
"""
"""


import tkinter as tk
from tkinter import ttk
from typing import Callable

from utils.types import TkImg


class WaitFrame(ttk.Frame):
    def __init__(
            self,
            master: tk.Misc,
            wait_gif: list[TkImg],
            cancel_cb: Callable[[], None],
            **kwargs
            ) -> None:
        super().__init__(master, **kwargs)
        self['relief'] = tk.RIDGE

        # Storing inbound references...
        self._master = master
        self._GIF_WAIT = wait_gif
        self._cancelCallback = cancel_cb

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


