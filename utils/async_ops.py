#
# 
#
"""This module provides asynchronous operations for the application."""

from __future__ import annotations
from concurrent.futures import Future, ThreadPoolExecutor
from enum import IntEnum
from queue import Queue, Empty
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Iterable

from utils.types import GifImage


class MsgQManager:
    """Message queue manager."""
    def __init__(self) -> None:
        self._qlst: list[Queue] = []
        """The internal list of allocated Queue objects."""
    
    def Allocate(self, n: int = 0) -> Queue:
        """Allocates a message-exchanging Queue for a multithreading
        situation. The allocated Queue must be released with a call to
        'Free' method. 'n' is the maximum size of the queue.
        """
        try:
            while self._qlst[-1] is None:
                self._qlst.pop()
        except IndexError:
            pass
        q = Queue(n)
        self._qlst.append(q)
        return q

    def Free(self, q: Queue) -> None:
        """Fress the provided Queue from the internal list. If the list
        does not find, it raises ValueError.
        """
        try:
            idx = self._qlst.index(q)
            del q
            q = self._qlst[idx]
            self._qlst[idx] = None
            del q
        except ValueError:
            raise ValueError('The specified Queue was not found.')


class AfterOpStatus(IntEnum):
    PENDING = 0
    """The operation if pending for execution."""
    RUNNING = 1
    """The operation is in progress."""
    FINISHED = 2
    """The operation was finished or canceled."""


class AfterOp:
    """Represents a asynchronous (on another thread) operation which
    usually makes updates in the GUI with the use of 'after' method of
    the window.
    """
    def __init__(
            self,
            thrd_pool: ThreadPoolExecutor,
            wait_gif: GifImage,
            start_callback: Callable[[], Any],
            finished_callback: Callable[[], None] | None = None,
            cancel_callback: Callable[[Any], None] | None = None,
            widgets: Iterable[tk.Widget] = (),
            ) -> None:
        self._thPool = thrd_pool
        self._GIF_WAIT = wait_gif
        self._cbStart = start_callback
        self._cbFinished = finished_callback
        self._cbCanceled = cancel_callback
        self._widgets = widgets
        self._q = Queue()
        """Messaging queue for the asynchronous operation."""
        self._future: Future | None = None
        self._ststus = AfterOpStatus.PENDING
        self._waitFrames: list[WaitFrame] = []
    
    def Start(self) -> None:
        """Starts this asynchronous ('after') operation."""
        self._future = self._thPool.submit(self._cbStart, self._q)
        self._ststus = AfterOpStatus.RUNNING
        for wdgt in self._widgets:
            waitFrame = WaitFrame(
                wdgt,
                self._GIF_WAIT,
                self._q,
                self._future.cancel)
            self._waitFrames.append(waitFrame)
            waitFrame.Show()
    
    def CloseWaitFrames(self) -> None:
        for waitFrame in self._waitFrames:
            waitFrame.Close()
    
    def HasDone(self) -> bool:
        """Returns True if the operation has finished or canceled,
        otherwise False."""
        return self._future.done()
    
    def HasCanceled(self) -> bool:
        """Returns True if the operation has canceled, otherwise False."""
        return self._future.cancelled()


class AfterOpManager:
    def __init__(
            self,
            master: tk.Misc,
            gif_wait: GifImage,
            ) -> None:
        self._master = master
        self._GIF_WAIT = gif_wait
        self._afterOps: list[AfterOp] = []
        """The internal list of AfterOp objects."""
        self._INTRVL = 40
        """The duration of time in millisecond"""
        self._thPool = ThreadPoolExecutor()
        """The thread pool to manage asynchronous operations."""
        self._afterID: str = ''
        """Specifies the after ID of scheduled next round of tracking
        of asynchronous operations. If it is the empty string, no scheduling
        is registered.
        """

    def InitiateOp(
            self,
            start_callback: Callable,
            finished_callback: Callable | None = None,
            cancel_callback: Callable | None = None,
            widgets: Iterable[tk.Widget] = (),
            ) -> None:
        """Initiates an 'after' operation."""
        self._afterOps.append(AfterOp(
            self._thPool,
            self._GIF_WAIT,
            start_callback,
            finished_callback,
            cancel_callback,
            widgets))
        # Starting the asynchronous operation...
        self._afterOps[-1].Start()
        # Scheduling the track of 'after' operations...
        if not self._afterID:
            self._afterID = self._master.after(
                self._INTRVL,
                self._TrackAfterOps,)
    
    def _TrackAfterOps(self) -> None:
        for afterOp in self._afterOps:
            if afterOp.HasDone():
                afterOp._ststus = AfterOpStatus.FINISHED
                afterOp.CloseWaitFrames()
                if afterOp.HasCanceled():
                    if afterOp._cbCanceled:
                        afterOp._cbCanceled()
                else:
                    if afterOp._cbFinished:
                        afterOp._cbFinished(afterOp._future.result())
        self._RemoveFinishedOps()
        if self._IsAnyRunning():
            self._afterID = self._master.after(
                self._INTRVL,
                self._TrackAfterOps,)
        else:
            self._afterID = ''

    def _RemoveFinishedOps(self) -> None:
        """Removes finished operations from the internal list."""
        idx = 0
        try:
            while True:
                if self._afterOps[idx]._ststus == AfterOpStatus.FINISHED:
                    del self._afterOps[idx]
                else:
                    idx += 1
        except IndexError:
            pass
    
    def _IsAnyRunning(self) -> bool:
        """Determines if any AfterOp object is in progress or all
        of them is finished.
        """
        return any(
            op._ststus == AfterOpStatus.RUNNING
            for op in self._afterOps)


class WaitFrame(ttk.Frame):
    def __init__(
            self,
            master: tk.Misc,
            wait_gif: GifImage,
            q: Queue,
            cancel_callback: Callable[[], None],
            **kwargs
            ) -> None:
        super().__init__(master, **kwargs)
        self['relief'] = tk.RIDGE

        # Storing inbound references...
        self._master = master
        self._GIF_WAIT = wait_gif
        self._q = q
        self._cbCancel = cancel_callback

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
        self._msg = ttk.Label(
            self,
            anchor=tk.NW,
            justify=tk.LEFT)
        self._msg.grid(
            column=0,
            row=1,
            sticky=tk.NSEW,
            padx=8,
            pady=(8, 4,))
        
        #
        self._btn_cancel = ttk.Button(
            master=self,
            text='Cancel',
            command=self._Cancel)
        self._btn_cancel.grid(
            column=0,
            row=2,
            padx=8,
            pady=(4, 8,))
    
    def Show(self) -> None:
        self.place(
            relx=0.5,
            rely=0.5,
            relwidth=0.5,
            anchor=tk.CENTER)
        self._afterID = self.after(
            self._TIME_AFTER,
            self._UpdateGui,
            1)

    def Close(self) -> None:
        """Closes this WaitFrame."""
        self.after_cancel(self._afterID)
        self._cbCancel = None
        self.place_forget()
        self.destroy()
    
    def ShowCanceling(self) -> None:
        self._btn_cancel['text'] = 'Canceling...'
        self._btn_cancel['state'] = tk.DISABLED
    
    def _Cancel(self) -> None:
        self.ShowCanceling()
        self._cbCancel()
    
    def _UpdateGui(self, idx: int) -> None:
        # Showing next GIF frame...
        try:
            self._lbl_wait['image'] = self._GIF_WAIT[idx]
        except IndexError:
            idx = 0
            self._lbl_wait['image'] = self._GIF_WAIT[idx]
        # Showing the next message...
        try:
            msg = self._q.get_nowait()
            self._msg['text'] = msg
        except Empty:
            pass
        self._afterID = self.after(
            self._TIME_AFTER,
            self._UpdateGui,
            idx + 1)
    
    def __del__(self) -> None:
        del self._master
        del self._GIF_WAIT
        del self._cbCancel
        del self._TIME_AFTER
        del self._btn_cancel
        del self._lbl_wait
        del self._afterID
