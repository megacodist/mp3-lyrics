#
# 
#
"""
"""


from concurrent.futures import ThreadPoolExecutor, Future
import enum
from queue import Queue, Empty
from threading import RLock
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Iterable

from utils.types import GifImage


class AfterOpStatus(enum.IntEnum):
    PENDING = 0
    """The operation if pending for execution."""
    RUNNING = 1
    """The operation is in progress."""
    FINISHED = 2
    """The operation was finished."""
    CANCELED = 3
    """The operation was canceled."""


class _AfterOp:
    """Represents a asynchronous (on another thread) operation which
    usually makes updates in the GUI with the use of 'after' method of
    the window.

    Objects of this class have the following characteristics:
    * hashability
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
            thrd_pool: ThreadPoolExecutor,
            q: Queue | None,
            start_cb: Callable[[Queue | None], Any],
            finish_cb: Callable[[Any], None] | None = None,
            cancel_cb: Callable[[], None] | None = None,
            widgets: Iterable[tk.Widget] = (),
            ) -> None:
        self._hash = _AfterOp._GetHash()
        """The unique hash of this instance."""
        self._thPool = thrd_pool
        """The thread pool executor."""
        self._cbStart = start_cb
        """The callback which starts this async operation."""
        self._cbFinished = finish_cb
        """The callback which is called upon completion of this async
        operation.
        """
        self._cbCanceled = cancel_cb
        """The callback which is called upon cancelation of this async
        operation.
        """
        self._widgets = widgets
        """The widgets that this operation has a effect on them."""
        self._q = q
        """Messaging queue for the asynchronous operation."""
        self._future: Future | None = None
        """The future object which represents the due result."""
        self._status = AfterOpStatus.PENDING
        """Status of this `_AfterOp` object."""
    
    def Start(self) -> None:
        """Starts this asynchronous ('after') operation."""
        self._future = self._thPool.submit(self._cbStart, self._q)
        self._status = AfterOpStatus.RUNNING
    
    def Cancel(self) -> None:
        self._future.cancel()
        self._status = AfterOpStatus.CANCELED
    
    def HasDone(self) -> bool:
        """Returns True if the operation has finished or canceled,
        otherwise False."""
        return self._future.done()
    
    def HasCanceled(self) -> bool:
        """Returns True if the operation has canceled, otherwise False."""
        return self._future.cancelled() or \
            self._status == AfterOpStatus.CANCELED
    
    def __hash__(self) -> int:
        return self._hash
    
    def __del__(self) -> None:
        del self._hash
        del self._thPool
        del self._cbCanceled
        del self._cbFinished
        del self._cbStart
        del self._status
        del self._q
        del self._future
        del self._widgets


class _WidgetAssets:
    def __init__(
            self,
            widget: tk.Widget,
            wait_gif: GifImage,
            ) -> None:
        self.widget = widget
        """The `Widget` that this object holds its assets."""
        self.q = Queue()
        self.ops: set[_AfterOp] = set()
        """The operations """
        self.waitFrame = WaitFrame(widget, wait_gif, self.q, self)
    
    def __del__(self) -> None:
        del self.widget
        del self.q
        self.ops.clear()
        del self.ops
        del self.waitFrame


class AfterOpManager:
    def __init__(
            self,
            master: tk.Misc,
            gif_wait: GifImage,
            ) -> None:
        self._master = master
        self._GIF_WAIT = gif_wait
        self._afterOps: set[_AfterOp] = set()
        """The internal list of `_AfterOp` objects."""
        self._INTRVL = 40
        """The duration of time in millisecond to check status of ongoing
        operations.
        """
        self._widgets: dict[tk.Widget, _WidgetAssets] = {}
        """All the widgets that has any asynchronous operation."""
        self._thPool = ThreadPoolExecutor()
        """The thread pool to manage asynchronous operations."""
        self._afterID: str = ''
        """Specifies the after ID of scheduled next round of tracking
        of asynchronous operations. If it is the empty string, no scheduling
        is registered.
        """

    def InitiateOp(
            self,
            start_cb: Callable[[Queue | None], Any],
            finish_cb: Callable[[Any], None] | None = None,
            cancel_cb: Callable[[], None] | None = None,
            widgets: Iterable[tk.Widget] = (),
            ) -> None:
        """Initiates an `after` operation."""
        # Making assets for all the involving widgets...
        for widget in widgets:
            try:
                self._widgets[widget]
            except KeyError:
                self._widgets[widget] = _WidgetAssets(widget, self._GIF_WAIT)
        # Making an `_AfterOp` object...
        asyncOp = _AfterOp(
            self._thPool,
            self._widgets[widgets[0]].q if widgets else None,
            start_cb,
            finish_cb,
            cancel_cb,
            widgets)
        for widget in widgets:
            self._widgets[widget].ops.add(asyncOp)
        self._afterOps.add(asyncOp)
        # Starting the asynchronous operation...
        asyncOp.Start()
        for widget in widgets:
            self._widgets[widget].waitFrame.Show()
        # Scheduling the track of 'after' operations...
        if not self._afterID:
            self._afterID = self._master.after(
                self._INTRVL,
                self._TrackAfterOps,)
    
    def _TrackAfterOps(self) -> None:
        # Looking for finished async ops...
        finishedOps: set[_AfterOp] = set()
        canceledOps: set[_AfterOp] = set()
        for afterOp in self._afterOps:
            if afterOp.HasDone():
                finishedOps.add(afterOp)
            elif afterOp.HasCanceled():
                finishedOps.add(afterOp)
        if finishedOps:
            for afterOp in finishedOps:
                afterOp._status = AfterOpStatus.FINISHED
                for widget in afterOp._widgets:
                    self._widgets[widget].ops.remove(afterOp)
                afterOp._cbFinished(afterOp._future)
            self._afterOps.difference_update(finishedOps)
        if canceledOps:
            for afterOp in finishedOps:
                for widget in afterOp._widgets:
                    self._widgets[widget].ops.remove(afterOp)
                if afterOp._cbCanceled:
                    afterOp._cbCanceled()
            self._afterOps.difference_update(canceledOps)
        if finishedOps or canceledOps:
            self._CloseFinishedWaitFrames()
        # Scheduling next round of tracking async ops...
        if self._afterOps:
            self._afterID = self._master.after(
                self._INTRVL,
                self._TrackAfterOps,)
        else:
            self._afterID = ''
    
    def _CloseFinishedWaitFrames(self) -> None:
        for widget in self._widgets:
            if self._widgets[widget].ops == set():
                self._widgets[widget].waitFrame.Close()
        self._widgets = {
            widget:assets
            for widget, assets in self._widgets.items()
            if assets.ops}


class WaitFrame(ttk.Frame):
    def __init__(
            self,
            master: tk.Misc,
            wait_gif: GifImage,
            q: Queue,
            assets: _WidgetAssets,
            **kwargs
            ) -> None:
        super().__init__(master, **kwargs)
        self['relief'] = tk.RIDGE

        # Storing inbound references...
        self._master = master
        self._GIF_WAIT = wait_gif
        self._q = q
        self._assets = assets
        self._afterID: str | None = None
        self._TIME_AFTER = 40
        self._shown: bool = False
        """Specifies whether this wait frame has been shown or not."""

        # Configuring the grid geometry manager...
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
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
            command=self.Cancel)
        self._btn_cancel.grid(
            column=0,
            row=2,
            padx=8,
            pady=(4, 8,))
    
    def Show(self) -> None:
        if self._shown:
            return
        self.place(
            relx=0.5,
            rely=0.5,
            relwidth=0.5,
            anchor=tk.CENTER)
        self._afterID = self.after(
            self._TIME_AFTER,
            self._UpdateGui,
            1)
        self._shown = True

    def Close(self) -> None:
        """Closes this WaitFrame."""
        self.after_cancel(self._afterID)
        self._cbCancel = None
        self.place_forget()
        self.destroy()
    
    def _ShowCanceling(self) -> None:
        self._btn_cancel['text'] = 'Canceling...'
        self._btn_cancel['state'] = tk.DISABLED
    
    def Cancel(self) -> None:
        """Cancels the asyncronous operations associated with this wait
        frame.
        """
        self._ShowCanceling()
        for op in self._assets.ops:
            op.Cancel()
    
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
        del self._assets
        del self._TIME_AFTER
        del self._btn_cancel
        del self._lbl_wait
        del self._msg
        del self._afterID
        del self._shown
