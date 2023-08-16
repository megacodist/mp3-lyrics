#
# 
#
"""
"""


from pathlib import Path
import tkinter as tk
from tkinter import ttk
from tkinter.font import Font, nametofont
from typing import Callable

from utils.types import TkImg



class FolderView(ttk.Treeview):
    @classmethod
    def GetComparer(cls, filename: str) -> tuple[str, str]:
        """Returns a tuple which the first element is file name without
        path and extension and the second element is the extension. For
        example for the file name 'some/path/stem.ext', it returns
        ('stem', '.ext',)
        """
        pFilename = Path(filename)
        return pFilename.stem.lower(), pFilename.suffix.lower()

    def __init__(
            self,
            master: tk.Tk,
            image: TkImg,
            select_callback: Callable[[str], None],
            **kwargs) -> None:

        kwargs['selectmode'] = 'browse'
        super().__init__(master, **kwargs)

        self.heading('#0', anchor=tk.W)
        self.column(
            '#0',
            width=200,
            stretch=False,
            anchor=tk.W)

        # Getting the font of the tree view...
        self._font: Font
        """Specifies the font of the FolderView."""
        try:
            self._font = self['font']
        except tk.TclError:
            self._font = nametofont('TkDefaultFont')
        
        self._IMG = image
        """Specifies the image of all items in the FolderView."""
        self._dir: str | None = None
        """Specifies the directory of the FolderView."""
        self._selectCallback: Callable[[str], None] = select_callback
        """Specifies a callback which is called when an item is selected in
        the FolderView
        """
        self._toIgnoreNextSelect: bool = False
        """Specifies whether to ignore the next Select event."""
        self._prevSelectedItem: str = ''
        """Specifies the previous selected item. it helps avoid firing
        Select event for the selected item. So to stimulate the Select
        event, you have to select another item in the list.
        """

        self.bind(
            '<<TreeviewSelect>>',
            self._OnItemSelectionChanged)
    
    def AddFilenames(
            self,
            folder: str,
            filenames: list[str],
            select_idx: int | None = None
            ) -> None:
        
        self._dir = folder
        # Writing folder in the heading...
        self.heading('#0', text=folder)
        # Adding filenames...
        self._Clear()
        minColWidth = self.winfo_width() - 4
        for filename in filenames:
            itemWidth = 40 + self._font.measure(filename)
            if itemWidth > minColWidth:
                minColWidth = itemWidth
            self.insert(
                parent='',
                index=tk.END,
                text=filename,
                image=self._IMG)
        # Setting the minimu width of the column...
        self.column('#0', width=minColWidth)
        # Selecting the specified file...
        self._toIgnoreNextSelect = True
        if select_idx is not None:
            self.selection_add(
                self.get_children('')[select_idx])
        # Scrolling the FolderView to the selected item...
        try:
            self.yview_moveto(select_idx / len(filenames))
        except TypeError:
            pass

    def _Clear(self) -> None:
        """Makes the FolderView empty."""
        for iid in self.get_children(''):
            self.delete(iid)
    
    def _OnItemSelectionChanged(self, event: tk.Event) -> None:
        selectedItemID = self.selection()
        if selectedItemID:
            selectedItemID = selectedItemID[0]
            if not self._toIgnoreNextSelect:
                if self._prevSelectedItem != selectedItemID:
                    text = self.item(selectedItemID, option='text')
                    self._selectCallback(
                        str(Path(self._dir) / text))
            else:
                self._toIgnoreNextSelect = False
            self._prevSelectedItem = selectedItemID
