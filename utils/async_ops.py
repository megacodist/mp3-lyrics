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
from typing import Any, Callable, Iterable, TypeVar, ParamSpec

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


_ReturnType = TypeVar('_ReturnType')
_Param = ParamSpec('_Param')


class AsyncOp:
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
            start_cb: Callable[_Param, _ReturnType],
            start_args: tuple[Any, ...] = (),
            start_kwargs: dict[str, Any] | None = None,
            finish_cb: Callable[[Future[_ReturnType]], None] | None = None,
            cancel_cb: Callable[_Param, None] | None = None,
            cancel_args: tuple[Any, ...] = (),
            cancel_kwargs: dict[str, Any] | None = None,
            widgets: Iterable[tk.Widget] = (),
            ) -> None:
        self._hash = AsyncOp._GetHash()
        """The unique hash of this instance."""
        self._thrdPool = thrd_pool
        """The Async I/O thread."""
        self.cbStart = start_cb
        """The callback which starts this async operation."""
        self.startArgs = start_args
        """The positional arguments for the start callback."""
        self.startKwargs = {} if start_kwargs is None else start_kwargs
        """The keyword arguments for the start callback."""
        self.cbFinished = finish_cb
        """The callback which is called upon completion of this async
        operation.
        """
        self.cbCancel = cancel_cb
        """The callback which is called upon cancelation of this async
        operation.
        """
        self.cancelArgs = cancel_args
        """The positional arguments for the cancel callback."""
        self.cancelKwargs = {} if cancel_kwargs is None else cancel_kwargs
        """The keyword arguments for the cancel callback."""
        self._widgets = widgets
        """The widgets that this operation has a effect on them."""
        self._q = q
        """Messaging queue for the asynchronous operation."""
        self._future: Future | None = None
        """The future object which represents the due result of this
        asynchronous operation.
        """
        self._status = AfterOpStatus.PENDING
        """Status of this `AsyncOp` object."""
    
    def Start(self) -> None:
        """Starts this asynchronous ('after') operation."""
        args = tuple([self._q, *self.startArgs])
        self._future = self._thrdPool.submit(
            self.cbStart,
            *args,
            **self.startKwargs)
        self._status = AfterOpStatus.RUNNING
    
    def HasDone(self) -> bool:
        """Returns True if the operation has finished or canceled,
        otherwise False."""
        return self._future.done()
    
    def Cancel(self) -> None:
        self._status = AfterOpStatus.CANCELED
        self._future.cancel()
    
    def CallCancelCallback(self) -> None:
        """Calls the cancel callback of this asynchronous operation."""
        if self.cbCancel:
            self.cbCancel(*self.cancelArgs, **self.cancelKwargs)
    
    def HasCanceled(self) -> bool:
        """Returns True if the operation has canceled, otherwise False."""
        return self._future.cancelled() or \
            self._status == AfterOpStatus.CANCELED
    
    def __hash__(self) -> int:
        return self._hash
    
    def __del__(self) -> None:
        # Freeing simple attributes...
        del self._hash
        del self._thrdPool
        del self.cbCancel
        del self.cancelArgs
        del self.cbFinished
        del self.cbStart
        del self.startArgs
        del self._status
        del self._q
        del self._future
        del self._widgets
        # Freeing data structures...
        self.startKwargs.clear()
        del self.startKwargs
        self.cancelKwargs.clear()
        del self.cancelKwargs


class _WidgetAssets:
    def __init__(
            self,
            widget: tk.Widget,
            wait_gif: GifImage,
            ) -> None:
        self.widget = widget
        """The `Widget` that this object holds its assets."""
        self.q = Queue()
        """The messaging queue associated with this widget."""
        self.ops: set[AsyncOp] = set()
        """The operations associated with this widget."""
        self.waitFrame = WaitFrame(widget, wait_gif, self.q, self)
        """The wait frame associated with this widget."""
    
    def __del__(self) -> None:
        del self.widget
        del self.q
        self.ops.clear()
        del self.ops
        del self.waitFrame


class AsyncOpManager:
    """The manager of asynchronous operations manager.

    Whenever you have finished with objects of this class, call `close`
    to release resources.
    """

    def __init__(
            self,
            master: tk.Misc,
            gif_wait: GifImage,
            ) -> None:
        self._master = master
        """The widget, typically the main window of the application, which
        offers `after` method.
        """
        self._GIF_WAIT = gif_wait
        self._asyncOps: set[AsyncOp] = set()
        """The internal list of `AsyncOp` objects."""
        self._INTRVL = 40
        """The duration of time in millisecond to check status of ongoing
        operations.
        """
        self._widgets: dict[tk.Widget, _WidgetAssets] = {}
        """All the widgets that has any asynchronous operation."""
        self._thrdPool = ThreadPoolExecutor()
        """The thread pool executor for this async operations manager."""
        self._afterID: str = ''
        """Specifies the after ID of scheduled next round of tracking
        of asynchronous operations. If it is the empty string, no scheduling
        is registered.
        """

    def close(self) -> None:
        """Releases resources of this async operations manager."""
        self._thrdPool.shutdown()

    def InitiateOp(
            self,
            start_cb: Callable[_Param, _ReturnType],
            start_args: tuple[Any, ...] = (),
            start_kwargs: dict[str, Any] | None = None,
            finish_cb: Callable[[Future[_ReturnType]], None] | None = None,
            cancel_cb: Callable[_Param, None] | None = None,
            cancel_args: tuple[Any, ...] = (),
            cancel_kwargs: dict[str, Any] | None = None,
            widgets: Iterable[tk.Widget] = (),
            ) -> AsyncOp:
        """Initiates an `after` operation. Arguments are as follow:

        * `start_cb`: Necessary. The callback that actually performs the
        asynchronous operation. If no widget is provided, this callback
        receives `None`; otherwise it receives a `queue.Queue` object.
        This callback must have `start_cb(Queue | None, *start_args,
        **start_kwargs) -> Any` signature.
        * `finish_cb`: Optional. The callback to be called upon
        completion. It must receives a `Future` object resolving to
        the output of the `start_cb` callback.
        * `cancel_cb`: Optional. The callback to be called upon
        cancelation of the operation. This callback must have
        `cancel_cb(*cancel_args, **cancel_kwargs) -> Any` signature.
        * `widgets`: an iterable of widgets that this operation might
        have an effect on them. If this parameter is falsy (`None` or
        empty), `start_cb` receives `None` instead of `queue.Queue`.
        """
        # Making assets for all the involving widgets...
        for widget in widgets:
            if widget not in self._widgets:
                self._widgets[widget] = _WidgetAssets(widget, self._GIF_WAIT)
        # Making an `AsyncOp` object...
        asyncOp = AsyncOp(
            self._thrdPool,
            self._widgets[next(iter(widgets))].q if widgets else None,
            start_cb,
            start_args,
            start_kwargs,
            finish_cb,
            cancel_cb,
            cancel_args,
            cancel_kwargs,
            widgets)
        for widget in widgets:
            self._widgets[widget].ops.add(asyncOp)
        self._asyncOps.add(asyncOp)
        # Starting the asynchronous operation...
        asyncOp.Start()
        for widget in widgets:
            self._widgets[widget].waitFrame.Show()
        # Scheduling next round tracking of async operations...
        if not self._afterID:
            self._afterID = self._master.after(
                self._INTRVL,
                self._TrackAsyncOps,)
        return asyncOp
    
    def _TrackAsyncOps(self) -> None:
        """Tracks the conditions of all ongoing async operations."""
        # Looking for finished or canceled async ops...
        finishedOps: set[AsyncOp] = set()
        canceledOps: set[AsyncOp] = set()
        for asyncOp in self._asyncOps:
            if asyncOp.HasCanceled():
                canceledOps.add(asyncOp)
            elif asyncOp.HasDone():
                finishedOps.add(asyncOp)
        # Processinf finished async ops...
        if finishedOps:
            for asyncOp in finishedOps:
                asyncOp._status = AfterOpStatus.FINISHED
                for widget in asyncOp._widgets:
                    self._widgets[widget].ops.remove(asyncOp)
                asyncOp.cbFinished(asyncOp._future)
            self._asyncOps.difference_update(finishedOps)
        # Processinf canceled async ops...
        if canceledOps:
            for asyncOp in canceledOps:
                for widget in asyncOp._widgets:
                    self._widgets[widget].ops.remove(asyncOp)
                asyncOp.CallCancelCallback()
            self._asyncOps.difference_update(canceledOps)
        # Closing wait frames for finished & canceled async ops...
        if finishedOps or canceledOps:
            self._CloseFinishedWaitFrames()
        # Scheduling next round of tracking async ops...
        if self._asyncOps:
            self._afterID = self._master.after(
                self._INTRVL,
                self._TrackAsyncOps,)
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
    
    def __del__(self) -> None:
        pass


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
        self._msg = tk.Message(
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
        # Checking whether this wait frame has started...
        if self._afterID:
            return
        self.place(
            relx=0.5,
            rely=0.5,
            relwidth=0.5,
            anchor=tk.CENTER)
        self._afterID = self.after(
            self._TIME_AFTER,
            self._UpdateGui,
            0)

    def Close(self) -> None:
        """Closes this WaitFrame."""
        self.after_cancel(self._afterID)
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
        # Scheduing next round of GUI update...
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
