#
# 
#
"""
"""

import enum
from os import PathLike
from queue import Queue
import threading


class FsChangeType(enum.IntEnum):
    """Specifies the type of change in the file system."""
    CREATION = 1
    DELETION = 2
    MODIFICATION = 3
    RENAME_FROM = 4
    RENAME_TO = 5


class ItemChange:
    """This data structure encompasses information about a change in the
    file system. 'fs_item' contains relative path of the changed item in
    the file system to the observer directory. 'type' specifies the type
    of change in the file system.
    """
    def __init__(self, fs_item: str, type_: FsChangeType) -> None:
        self.fs_item = fs_item
        """The relative file name from observing folder that had some sort
        of change.
        """
        self.type = type_
        """The type of file system change."""
    
    def __repr__(self) -> str:
        return f"<FS change: {self.type.name:>12}, {self.fs_item}>"


class DirObserver(threading.Thread):
    _nums: set[int] = set()
    """This set object tracks all running instances through assigned
    numbers.
    """

    def __init__(
            self,
            dir_: PathLike,
            q: Queue[ItemChange],
            ) -> None:
        # Assigning index to this instance...
        idx = 0
        while idx in DirObserver._nums:
            idx += 1
        DirObserver._nums.add(idx)
        super().__init__(name=f'Directory observer #{idx}', daemon=True)
        self._dir = dir_
        """The folder to be watched."""
        self._q = q
        """The queue for receiving file system changes."""
        self._num = idx
        """Index of this instance."""
        self._closeRequested = False
        """Specifies whether closing is requested."""
        self._tempRename: ItemChange | None = None
        """The temporary object to construct RENAME ItemChange object.
        """

    def run(self) -> None:
        # Declaring variables -----------------------------
        import logging
        from os import fspath
        import win32con
        from win32con import (
            FILE_SHARE_READ,
            FILE_SHARE_WRITE,
            FILE_SHARE_DELETE)
        import win32file
        import pywintypes
        # Watching directory ------------------------------
        # Observing the directory...
        hDir = win32file.CreateFile(
            fspath(self._dir),
            0x0001,
            FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
            None,
            win32con.OPEN_EXISTING,
            win32con.FILE_FLAG_BACKUP_SEMANTICS,
            None,)
        # Starting the directory monitoring loop...
        dwNotifyFilter = win32con.FILE_NOTIFY_CHANGE_FILE_NAME \
            | win32con.FILE_NOTIFY_CHANGE_DIR_NAME \
            | win32con.FILE_NOTIFY_CHANGE_ATTRIBUTES \
            | win32con.FILE_NOTIFY_CHANGE_SIZE \
            | win32con.FILE_NOTIFY_CHANGE_LAST_WRITE \
            | win32con.FILE_NOTIFY_CHANGE_SECURITY
        while True:
            try:
                # Waiting for a change to occur...
                results = win32file.ReadDirectoryChangesW(
                    hDir,
                    1024,
                    True,
                    dwNotifyFilter,
                    None,
                    None,)
                if self._closeRequested:
                    break
                # Handling the changes...
                for type_, file_path in results:
                    if 0 <type_< 6:
                        change = ItemChange(file_path, FsChangeType(type_))
                        print(change)
                        self._q.put(change)
                    else:
                        logging.error("E01-01")
            except pywintypes.error as err:
                # Checking if folder handle closed...
                if err.args[0] == 6:
                    break
    
    def close(self) -> None:
        from tempfile import TemporaryFile
        self._closeRequested = True
        try:
            DirObserver._nums.remove(self._num)
        except KeyError:
            pass
        else:
            with TemporaryFile(dir=self._dir) as tempObj:
                pass
