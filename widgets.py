from pathlib import Path
import tkinter as tk
from tkinter import ttk
from tkinter.font import nametofont
from typing import Callable

from PIL.ImageTk import PhotoImage


class TreeviewMp3(ttk.Treeview):
    def __init__(
            self,
            master: tk.Tk,
            image: PhotoImage,
            select_callback: Callable[[str], None],
            **kwargs) -> None:

        kwargs['selectmode'] = 'browse'
        super().__init__(master, **kwargs)

        # Getting the font of the tree view...
        self._font = None
        try:
            self._font = self['font']
        except tk.TclError:
            self._font = nametofont('TkDefaultFont')

        self.heading('#0', anchor=tk.W)
        self.column(
            '#0',
            width=200,
            stretch=False,
            anchor=tk.W)
        
        self._IMG = image
        self._dir: str | None
        self._selectCallback = select_callback
        self._noSelectCallback: bool

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
        self._noSelectCallback = True
        if select_idx is not None:
            self.selection_add(
                self.get_children('')[select_idx])
        # Scrolling the treeview to the selected item...
        self.yview_moveto(select_idx / len(filenames))

    def _Clear(self) -> None:
        """Makes the treeview empty."""
        for iid in self.get_children(''):
            self.delete(iid)
    
    def _OnItemSelectionChanged(self, event: tk.Event) -> None:
        if self._noSelectCallback:
            self._noSelectCallback = False
        else:
            selectedItemID = self.selection()
            if selectedItemID:
                text = self.item(selectedItemID[0], option='text')
                self._selectCallback(
                    str(Path(self._dir) / text))


class WaitFrame(ttk.Frame):
    def __init__(
            self,
            master: tk.Misc,
            wait_gif: list[PhotoImage],
            cancel_callback: Callable[[], None],
            **kwargs
            ) -> None:
        super().__init__(master, **kwargs)

        self._master = master
        self._IMG_WAIT = wait_gif
        self._cancelCallback = cancel_callback

        self._afterID: str | None = None
        self._TIME_INTERVAL = 40

        self.columnconfigure(
            index=0,
            weight=1)
        self.rowconfigure(
            index=0,
            weight=1)
        
        #
        self._lbl_wait = ttk.Label(
            master=self,
            image=self._IMG_WAIT[0])
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
            self._TIME_INTERVAL,
            self._AnimateGif,
            1)

    def Close(self) -> None:
        self.after_cancel(self._afterID)
        self._cancelCallback = None
        self.place_forget()
    
    def _Cancel(self) -> None:
        self._btn_cancel['text'] = 'Canceling...'
        self._btn_cancel['state'] = tk.DISABLED
        self._cancelCallback()
    
    def _AnimateGif(self, idx: int) -> None:
        try:
            self._lbl_wait['image'] = self._IMG_WAIT[idx]
        except IndexError:
            idx = 0
            self._lbl_wait['image'] = self._IMG_WAIT[idx]
        self._afterID = self.after(
            self._TIME_INTERVAL,
            self._AnimateGif,
            idx + 1)
