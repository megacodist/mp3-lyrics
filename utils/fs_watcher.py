#
# 
#
"""This module contains the following items:

#### Classes:
1. `FsWatcher`: Use this class to watch a folder for changes.
"""
from __future__ import annotations
from bisect import bisect_right
from collections import defaultdict
from enum import IntEnum, IntFlag
from os import PathLike, fspath
from pathlib import Path
from queue import Queue
from threading import RLock
import threading
import tkinter as tk
from typing import Any, Callable, Iterable

from .dir_observer import DirObserver, ItemChange, FsChangeType


class NotMonitoringError(Exception):
    """This exception specifies adding a subscriber to the watcher that
    has NOT been monitored.
    """
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class DirStatus(IntEnum):
        """Specifies the status of a given folder in the internal
        subscribers list of FsWatcher.
        """
        EXISTED = 1
        """The folder has been added to the subscribers."""
        IN_RECURSIVE = 2
        """The folder has NOT been added to the subscribersis but rather
        a recursive subscriber is watching its events.
        """
        NOT_EXISTED = 3
        """The path has been neither added to the subscribers nor watched
        by a recursive.
        """


class _SubStatus(IntFlag):
    """Specifies some conditions and status of Subscriber objects."""

    NONE = 0x00
    """No special status is applied."""
    RECURSION = 0x01
    """The subscriber is responsible for monitoring subfolders."""
    PENDING_OPERATION = 0x02
    """Some dispatching operations are pending."""
    PENDING_DELETION = 0x04
    """Deletion of this subscriber is pending."""


class FsEvent:
    """Specifies afile system event."""
    def __init__(
            self,
            name: str,
            dir_: Path,
            type_: FsChangeType,
            ) -> None:
        """Initializes a new instance with the following arguments:
        
        * name: the name of the item either filename or folder name,
        excluding the folder.
        * dir_: the folder of the item relative to the observing
        directory.
        * type_: an instance of FsChangeType that specifies the kind
        of event.
        """
        self.name = name
        self.dir = dir_
        self.type = type_
    
    def __eq__(self, __obj: object, /) -> bool:
        """Checks the equality of this object and another FsEvent object."""
        if not isinstance(__obj, FsEvent):
            raise TypeError(f"unsupported operand type(s) for == check: "
                f"'FsEvent' and '{type(__obj).__qualname__}'")
        return all([
            self.name == __obj.name,
            self.dir == __obj.dir,
            self.type == __obj.type])
    
    def __ne__(self, __obj: object, /) -> bool:
        """Checks the equality of this object and another FsEvent object."""
        if not isinstance(__obj, FsEvent):
            raise TypeError(f"unsupported operand type(s) for == check: "
                f"'FsEvent' and '{type(__obj).__qualname__}'")
        return any([
            self.name == __obj.name,
            self.dir == __obj.dir,
            self.type == __obj.type])


class _Ignoree:
    """Specifies a file system event that must NOT dispatch."""
    def __init__(
            self,
            item: Path,
            ) -> None:
        self.item = item
        self.afterId: str
    
    def _RaiseUnsupportedOp(self, __op: str, __obj: Any, /) -> None:
        """Raises a TypeError exception for an unsupported operation."""
        raise TypeError((
            f"unsupported operand type(s) for {__op} check: "
            + f"'_Ignoree' and '{type(__obj).__qualname__}'"))
    
    def __eq__(self, __obj: object, /) -> bool:
        """Checks the equality of this object and another _Ignoree object."""
        if not isinstance(__obj, _Ignoree):
            self._RaiseUnsupportedOp('==', __obj)
        return self.item == __obj.item
    
    def __ne__(self, __obj: object, /) -> bool:
        if not isinstance(__obj, _Ignoree):
            self._RaiseUnsupportedOp('!=', __obj)
        return self.item != __obj.item


class Subscriber:
    """Specifies a subscriber to the specific folder in the FsWatcher.
    This class supports arithmetic comparisons and is NOT intended
    to be instantiated directly.
    """
    def __init__(
            self,
            parts: tuple[Path, ...],
            recursive: bool = False,
            creation_cb: Callable[[Iterable[str]], None] | None = None,
            deletion_cb: Callable[[Iterable[str]], None] | None = None,
            modification_cb: Callable[[Iterable[str]], None] | None = None,
            rename_from_cb: Callable[[Iterable[str]], None] | None = None,
            rename_to_cb: Callable[[Iterable[str]], None] | None = None,
            ) -> None:
        """Initializes a new instance of this class. Arguments are as follow:

        * 'parts' is a tuple containing this folder name and its ancestors
        relative to the observing directory. For more information refers
        to pathlib.Path.parts documentation. Because this attribute acts
        as a so-called 'primary key', it can be used to distinguish
        different instances of this type.
        * The callbacks must accept a set of folders' and files' names
        as their first and second parametrs repectively and return nothing.
        at least one of them must be provided.
        """
        # Initializng...
        self._dir: Path
        """The absolute Path of the FsWatcher."""
        self._parts = parts
        """Relative path from watcher's observing directory.
        """
        self._status = _SubStatus.RECURSION if recursive else \
            _SubStatus.NONE
        """Specifies the status of this subscriber."""
        self._cbCreation = creation_cb
        """Callback to be invoked when a CREATION event detected."""
        self._cbDeletion = deletion_cb
        """Callback to be invoked when a DELETION event detected."""
        self._cbModification = modification_cb
        """Callback to be invoked when a MODIFICATION event detected."""
        self._cbRenameFrom = rename_from_cb
        """Callback to be invoked when a RENAME_FROM event detected."""
        self._cbRenameTo = rename_to_cb
        """Callback to be invoked when a RENAME_TO event detected."""
        self._dispatchees: defaultdict[FsChangeType, set[str]] = \
            defaultdict(set)
        """Contains lists of file system events which must disptch."""
        self._afterId: str | None = None
    
    @property
    def Recursive(self) -> bool:
        """Gets whether this object is recursive or not."""
        return bool(self._status & _SubStatus.RECURSION)
    
    @property
    def Parent(self) -> Subscriber:
        """Gets a subscriber watching the parent folder of this subscriber
        and copies callbacks and recursive from this object.
        
        If 'parts'
        attribute is an empty tuple, it will NOT go beyond that and returns
        the same 'parts' attribute.
        """
        return Subscriber(
            self._parts[:-1],
            self.Recursive,
            self._cbCreation,
            self._cbDeletion,
            self._cbModification,
            self._cbRenameFrom,
            self._cbRenameTo,)
    
    def Update(self, __sub: Subscriber, /) -> None:
        """Updates this object with provided instance. All attributes
        are copied except for 'parts'.
        """
        self._cbCreation = __sub._cbCreation
        self._cbDeletion = __sub._cbDeletion
        self._cbModification = __sub._cbModification
        self._cbRenameFrom = __sub._cbRenameFrom
        self._cbRenameTo = __sub._cbRenameTo
        self._status &= (~_SubStatus.RECURSION)
        self._status |= (__sub._status & _SubStatus.RECURSION)
    
    def FlushAll(self) -> None:
        """Flushes all dispatched events kept by this subscriber
        immediately.
        """
        # Dispatching CREATION events...
        if self._cbCreation and self._dispatchees[FsChangeType.CREATION]:
            self._cbCreation(self._dispatchees[FsChangeType.CREATION])
            self._dispatchees[FsChangeType.CREATION].clear()
        # Dispatching DELETION events...
        if self._cbDeletion and self._dispatchees[FsChangeType.DELETION]:
            self._cbDeletion(self._dispatchees[FsChangeType.DELETION])
            self._dispatchees[FsChangeType.DELETION].clear()
        # Dispatching MODIFICATION events...
        if self._cbModification and self._dispatchees[
                FsChangeType.MODIFICATION]:
            self._cbModification(self._dispatchees[FsChangeType.MODIFICATION])
            self._dispatchees[FsChangeType.MODIFICATION].clear()
        # Dispatching RENAME_FROM events...
        if self._cbRenameFrom and self._dispatchees[FsChangeType.RENAME_FROM]:
            self._cbRenameFrom(self._dispatchees[FsChangeType.RENAME_FROM])
            self._dispatchees[FsChangeType.RENAME_FROM].clear()
        # Dispatching RENAME_TO events...
        if self._cbRenameTo and self._dispatchees[FsChangeType.RENAME_TO]:
            self._cbRenameTo(self._dispatchees[FsChangeType.RENAME_TO])
            self._dispatchees[FsChangeType.RENAME_TO].clear()
    
    def AddEvent(self, item: Path, type_: FsChangeType) -> bool:
        """Adds the specified event to the appropriate set.
        'item' must be relative to the FsWatcher. It returns True
        if the event has been added, False otherwise.
        """
        if not self.HasCallback(type_):
            return False
        if item.is_absolute():
            item = item.relative_to(self._dir)
        if self._parts:
            item = str(item.relative_to(Path(*self._parts)))
        else:
            item = str(item)
        self._dispatchees[type_].add(item)
        return True
    
    def HasCallback(self, type_: FsChangeType) -> bool:
        """Checks whether the provided FsChangeType has an associated
        callback or not.
        """
        match type_:
            case FsChangeType.CREATION:
                return bool(self._cbCreation)
            case FsChangeType.DELETION:
                return bool(self._cbDeletion)
            case FsChangeType.MODIFICATION:
                return bool(self._cbModification)
            case FsChangeType.RENAME_FROM:
                return bool(self._cbRenameFrom)
            case FsChangeType.RENAME_TO:
                return bool(self._cbRenameTo)
    
    def _RaiseUnsupportedOp(self, __op: str, __obj: Any, /) -> None:
        """Raises a TypeError exception for an unsupported operation."""
        raise TypeError((
            f"unsupported operand type(s) for {__op} check: "
            + f"'Subscriber' and '{type(__obj).__qualname__}'"))
    
    def __eq__(self, __obj: object, /) -> bool:
        if not isinstance(__obj, Subscriber):
            self._RaiseUnsupportedOp('==', __obj)
        return self._parts == __obj._parts
    
    def __ne__(self, __obj: object, /) -> bool:
        if not isinstance(__obj, Subscriber):
            self._RaiseUnsupportedOp('!=', __obj)
        return self._parts != __obj._parts
    
    def __gt__(self, __obj: object, /) -> bool:
        if not isinstance(__obj, Subscriber):
            self._RaiseUnsupportedOp('>', __obj)
        return self._parts > __obj._parts
    
    def __ge__(self, __obj: object, /) -> bool:
        if not isinstance(__obj, Subscriber):
            self._RaiseUnsupportedOp('>=', __obj)
        return self._parts >= __obj._parts
    
    def __lt__(self, __obj: object, /) -> bool:
        if not isinstance(__obj, Subscriber):
            self._RaiseUnsupportedOp('<', __obj)
        return self._parts < __obj._parts
    
    def __le__(self, __obj: object, /) -> bool:
        if not isinstance(__obj, Subscriber):
            self._RaiseUnsupportedOp('<=', __obj)
        return self._parts <= __obj._parts


class FsWatcher(threading.Thread):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(name='File system watcher', daemon=True)
        self._master = master
        """The Tkinter engine."""
        self._subs: list[Subscriber] = []
        """A list of subscriber objects which hold information about target
        folder and callbacks.
        """
        self._observer: DirObserver | None = None
        """The actual underlying observer."""
        self._q: Queue[ItemChange] = Queue()
        """The queue for receiving file system changes."""
        self._dir: Path | None = None
        """The directory to be monitored."""
        self._rMutex = RLock()
        """Specifies the re-entrant mutex lock for enabling or disabling of
        dispatching of file system events.
        """
        self._nRMutex: int = 0
        """Specifies number of re-entrant mutex lock by a thread."""
        self._ignorees: dict[FsChangeType, list[_Ignoree]] = {}
        """Contains lists of file system events that must be ignored."""
        self._TIMINT_IGNOREE = 60_000
        """The time interval after which the first 'ignoree' must be
        deleted.
        """
        self._TIMINT_FLUSH = 1_000
        """The time interval after whcih dispatchees of a Subscriber
        object must be flushed.
        """

    def run(self) -> None:
        change: ItemChange
        while True:
            change = self._q.get()
            self.ScheduleEvent(change.fs_item, change.type)
    
    @property
    def Dispatching(self) -> bool:
        """Temporarily disables or re-enables dispatching of file system
        events.
        
        A thread can set False to this property to disable
        dispatching of events. How many times the thread set False
        to this property, it must set True that number to re-enable
        dispatching.
        
        In the meanwhile, if a second thread tries to 
        control this property, it is blocked until the first thread
        is done with it.
        """
        return not bool(self._nRMutex)
    
    @Dispatching.setter
    def Dispatching(self, __value: bool, /) -> None:
        if __value is False:
            self._rMutex.acquire()
            if self._nRMutex == 0:
                self.CancelFlushings()
            self._nRMutex += 1
        elif __value is True:
            if self._nRMutex > 0:
                self._rMutex.release()
                self._nRMutex -= 1
                if self._nRMutex == 0:
                    self.FlushAll()
        else:
            raise TypeError(
                "'Dispatching' property only accepts boolean values.")
    
    def Monitor(self, dir_: PathLike) -> None:
        """Forces this object to monitor the specified path and stop
        watching the current directory if it was on.
        """
        self.Close()
        self._dir = dir_ if isinstance(dir_, Path) else Path(fspath(dir_))
        self._observer = DirObserver(dir_, self._q)
        self._observer.start()
    
    def Close(self) -> None:
        """Forces the watcher to stop watching the directory and clears
        all its subscribers.
        """
        # Terminating the observer...
        if self._observer:
            self._observer.close()
        del self._dir
        self._dir = None
        self._subs.clear()
    
    def Subscribe(
            self,
            dir_: PathLike,
            recursive: bool = False,
            creation_cb: Callable[[Iterable[str]], None] | None = None,
            deletion_cb: Callable[[Iterable[str]], None] | None = None,
            modification_cb: Callable[[Iterable[str]], None] | None = None,
            rename_from_cb: Callable[[Iterable[str]], None] | None = None,
            rename_to_cb: Callable[[Iterable[str]], None] | None = None,
            ) -> None:
        """Adds the specified subscriber object to the watcher. Arguments
        are as follow:

        * dir_: directory that is of interest to be watched. This can
        be absolute or relative to the observing folder.
        * recursive: whether subfolders must be watched or not.
        * callback: callbacks to be invoked for the specified events.

        If subscriber does exist in the list, it updates 'recursive'
        and callbacks. At least one of the callbacks must be provided.

        Exceptions:
        * NotMonitoringError: the watcher is not monitoring. So first
        call 'Monitor' method.
        * ValueError: none of callbacks is provided.
        """
        # Checking parameters...
        if self._dir is None:
            raise NotMonitoringError("the watcher is not monitoring.")
        if not any([creation_cb, deletion_cb, modification_cb]):
            raise ValueError('None of callbacks is provided.')
        # Adding subscriber...
        sub = Subscriber(
            self._PathLikeToParts(dir_),
            recursive,
            creation_cb,
            deletion_cb,
            modification_cb,
            rename_from_cb,
            rename_to_cb,)
        sub._dir = self._dir
        idx = bisect_right(self._subs, sub)
        if idx == 0:
            # Didn't found, proper index: 0
            self._subs.insert(0, sub)
        elif self._subs[idx - 1] == sub:
            # Found, updating it...
            self._subs[idx - 1].Update(sub)
        else:
            # Didn't found, proper index: 0
            self._subs.insert(idx, sub)
    
    def Unsubscribe(self, dir_: PathLike) -> bool:
        """Unsubscribe a folder for file system events. If the folder
        had previously been added, it returns True and remove; otherwise
        if it had not been added or is being watched in a recursive
        folder, the method returns False and nothing happens.
        """
        sub = Subscriber(self._PathLikeToParts(dir_))
        status, idx = self._GetSubIndex(sub)
        if status != DirStatus.EXISTED:
            return False
        if self._subs[idx]._status & _SubStatus.PENDING_OPERATION:
            self._subs[idx]._status |= _SubStatus.PENDING_DELETION
        else:
            del self._subs[idx]
        return True
    
    def Ignore(
            self,
            item: PathLike,
            event: FsChangeType,
            ) -> None:
        """Ignores a file system event. 'item' can be
        either absolute or relative to the observing folder.
        """
        pth = self._PathLikeToPath(item)
        ignoree = _Ignoree(pth)
        self._ignorees[event].append(ignoree)
        ignoree.afterId = self._master.after(
            self._TIMINT_IGNOREE,
            self._DeleteIgnoree,
            event)
    
    def ScheduleEvent(
            self,
            item: PathLike,
            event_type: FsChangeType,
            ) -> None:
        """Schedules an event for the specified item. If the change is
        RENAME, then 'item' argument must be of RenameChange type,
        otherwise 'item' must be a path-like object.
        """
        pthItem = self._PathLikeToPath(item)
        # Firstly looking into ignorees...
        ignoree = _Ignoree(pthItem)
        try:
            idx = self._ignorees[event_type].index(ignoree)
            self._master.after_cancel(self._ignorees[event_type][idx].afterId)
            del self._ignorees[event_type][idx]
            del ignoree
            return
        except KeyError:
            del ignoree
        # The event was not in the ignoress, scheduling dispatch...
        # Getting a temporary Subscriber of the containing folder...
        sub = Subscriber(self._PathLikeToParts(pthItem.parent))
        status, idx = self._GetSubIndex(sub)
        if status == DirStatus.NOT_EXISTED:
            return
        else:
            self._subs[idx].AddEvent(pthItem, event_type)
        if not (self._subs[idx]._status & _SubStatus.PENDING_OPERATION):
            self._subs[idx]._status |= _SubStatus.PENDING_OPERATION
            self._subs[idx]._afterId = self._master.after(
                self._TIMINT_FLUSH,
                self._FlushSub,
                self._subs[idx])
    
    def _PathLikeToParts(self, __item: PathLike, /) -> tuple[Path, ...]:
        """Converts a PathLike object into a tuple of strings which are
        name, parent, and ancestor folders of the provided directory
        in the file system relative to the observing folder. For
        an explanation refers to pathlib.Path.parts documentation.
        The parameter cab be absolute or relative to the observing
        folder.
        """
        pth = __item if isinstance(__item, Path) else Path(fspath(__item))
        if pth.is_absolute():
            pth = pth.relative_to(self._dir)
        return tuple(Path(part) for part in pth.parts)
    
    def _PathLikeToPath(self, __item: PathLike, /) -> Path:
        """Converts a PathLike object into a Path object."""
        pth = __item if isinstance(__item, Path) else Path(fspath(__item))
        if pth.is_absolute():
            pth = pth.relative_to(self._dir)
        return pth
    
    def CancelFlushings(self) -> None:
        """Cancels all pending dispatches (flushings)."""
        for subscriber in self._subs:
            if subscriber._afterId:
                self._master.after_cancel(subscriber._afterId)
                subscriber._afterId = None
    
    def FlushAll(self) -> None:
        """Flushes all dispatchedc events immediately."""
        for subscriber in self._subs:
            subscriber.FlushAll()
    
    def _DeleteIgnoree(self, event_type: FsChangeType) -> None:
        """Deletes the first 'ignoree' in the corresponding list."""
        del self._ignorees[event_type][0]
    
    def _FlushSub(self, __sub: Subscriber, /) -> None:
        """Flushes dispatchees of a subscriber on schedule."""
        __sub.FlushAll()
        if __sub._status & _SubStatus.PENDING_DELETION:
            del self._subs[self._subs.index(__sub)]
        else:
            __sub._status &= (~_SubStatus.PENDING_OPERATION)
    
    def _GetSubIndex(
            self,
            __sub: Subscriber,
            /,
            ) -> tuple[DirStatus, int]:
        """Gets the status and index of the provided Subscriber object
        in the internal list as 2-tuple. Three situations are possible:

        * (DirStatus.NOT_EXISTED, int): the subscriber is NOT in the list
        and the second element is the position to insert.
        * (DirStatus.EXISTED, int): the subscriber is in the list and
        the second element is its position in the list.
        * (DirStatus.IN_RECURSIVE, int): the path existed within one of its
        parent folders.
        """
        idx = bisect_right(self._subs, __sub)
        if idx == 0:
            return DirStatus.NOT_EXISTED, 0
        elif self._subs[idx - 1] == __sub:
            return DirStatus.EXISTED, idx - 1
        else:
            stopIdx = idx - 1
            findable = __sub.Parent
            while stopIdx >= 0:
                i = bisect_right(self._subs, findable, 0, stopIdx)
                if i == 0:
                    return DirStatus.NOT_EXISTED, idx
                elif self._subs[i - 1] == findable and \
                        self._subs[i - 1].Recursive:
                    return DirStatus.IN_RECURSIVE, i - 1
                else:
                    findable = findable.Parent
                    stopIdx = i - 1
            return DirStatus.NOT_EXISTED, idx

    def GetSub(self, dir_: PathLike) -> Subscriber | None:
        """Returns the Subscriber object watching for the events of
        the specified folder. If the folder is not being watched by
        any Subscriber objects, the method returns None.
        """
        from copy import copy
        sub = Subscriber(self._PathLikeToParts(dir_))
        status, idx = self._GetSubIndex(sub)
        if status != DirStatus.NOT_EXISTED:
            return copy(self._subs[idx])
        return None
    