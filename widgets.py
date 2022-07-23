from enum import IntEnum
from pathlib import Path
import tkinter as tk
from tkinter import Frame, ttk
from tkinter.font import nametofont
from typing import Callable

from PIL.ImageTk import PhotoImage
from tkhtmlview import HTMLLabel
from tksheet import Sheet


class MessageType(IntEnum):
    INFO = 0
    WARNING = 1
    ERROR = 2


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


class LyricsView(ttk.Frame):
    def __init__(
            self,
            master: tk.Misc,
            highlightable: bool = False,
            sepWidth: int = 3,
            sepColor: str = 'black',
            gap: int = 5,
            **kwargs
            ) -> None:
        super().__init__(master, **kwargs)
        self['relief'] = tk.SUNKEN

        self._lyrics: list[str] = []
        self._highlightable = highlightable
        self._sepWidth = sepWidth
        self._sepColor = sepColor
        self._gap = gap

        self._vscrllbr: ttk.Scrollbar
        self._cnvs: tk.Canvas
        self._msgs: list[tk.Message] = []

        self._InitGui()
    
    def _InitGui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._vscrlbr = ttk.Scrollbar(
            master=self,
            orient=tk.VERTICAL)
        self._cnvs = tk.Canvas(
            master=self,
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
    
    @property
    def sepWidth(self) -> int:
        return self._sepWidth
    
    @sepWidth.setter
    def sepWidth(self, __value: int) -> None:
        pass

    @property
    def lyrics(self) -> list[str]:
        return self._lyrics
    
    @lyrics.setter
    def lyrics(
            self,
            lyrics: list[str],
            highlightable: bool | None = None
            ) -> None:
        self._lyrics = lyrics
        if highlightable is not None:
            self._highlightable = highlightable
        self._Redraw()
    
    @property
    def gap(self) -> int:
        return self._gap
    
    def Highlight(self, idx: int) -> None:
        pass

    def _GetWidth(self) -> int:
        return (
            self._cnvs.winfo_width()
            - 4
            + (int(self._cnvs['bd']) << 1))
    
    def _GetInternalHeight(self) -> int:
        return (
            self._cnvs.winfo_height()
            - 4
            + (int(self._cnvs['bd']) << 1))
    
    def _Redraw(self) -> None:
        self._cnvs.delete('all')
        cnvsWidth = self._GetWidth()
        cnvsHeight = self._GetHeight()
        y = 0
        if len(self._lyrics) < 1:
            return
        try:
            idx = 0
            # Changing the first Message widget...
            self._msgs[idx]['text'] = self._lyrics[idx]
            x = (cnvsWidth - self._msgs[idx].winfo_width()) >> 1
            self._cnvs.create_window(
                x,
                y,
                anchor=tk.NW,
                window=self._msgs[idx])
            y += self._msgs[idx].winfo_height()

            # Changing the first the rest of Message widgets
            # alongside their upper lines...
            while idx < len(self._lyrics):
                self._msgs[idx]['text'] = self._lyrics[idx]

                # Drawing the upper line...
                y += self._gap
                self._cnvs.create_line(
                    0,
                    y,
                    cnvsWidth,
                    y,
                    fill=self._sepColor,
                    width=self._sepWidth)

                # Drawing the Message widget...
                y += (self._gap + self._sepWidth)
                x = (cnvsWidth - self._msgs[idx].winfo_width()) >> 1
                self._cnvs.create_window(
                    x,
                    y,
                    anchor=tk.NW,
                    window=self._msgs[idx])
        except IndexError:
            pass
        self._cnvs[]

        
class MessageView(Frame):
    _colors = {
        MessageType.INFO: 'LightBlue1',
        MessageType.WARNING: 'gold',
        MessageType.ERROR: '#e47e8f'}

    def __init__(
            self,
            master: tk.Misc,
            *,
            padx=5,
            pady=5,
            gap=10,
            max_events: int = 20,
            **kwargs
            ) -> None:
        super().__init__(master, **kwargs)

        # Getting the font of the tree view...
        try:
            self._font = master['font']
        except tk.TclError:
            self._font = nametofont('TkDefaultFont')

        self._msgs: list[HTMLLabel] = []
        self.max_events = max_events
        self._padx = padx
        self._pady = pady
        self._gap = gap

        self._InitGui()
        
        self._cnvs.bind_all(
            '<MouseWheel>',
            self._OnMouseWheel)
        self._cnvs.bind(
            '<Configure>',
            self._OnSizeChanged)
    
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
            padx=5,
            pady=5,
            sticky=tk.NSEW)
        self._vscrlbr.grid(
            column=1,
            row=0,
            sticky=tk.NSEW)
    
    def _OnMouseWheel(self, event: tk.Event) -> None:
        self._cnvs.yview_scroll(
            int(-1*(event.delta/120)),
            'units')
    
    def _OnSizeChanged(self, event: tk.Event) -> None:
        width = (
            event.width
            - (int(self._cnvs['bd']) << 1)
            - 4
            - (self._padx << 1))
        for msg in self._msgs:
            msg['width'] = width
        self._Redraw()
    
    def AddMessage(
            self,
            message: str,
            title: str | None = None,
            type: MessageType = MessageType.INFO
            ) -> None:

        text = ''
        if title:
            text = f'{title}\n\n'
        text += message

        msg = tk.Message(
            self._cnvs,
            anchor=tk.NW,
            background=MessageView._colors[type],
            width=self._GetInternalWidth(),
            text=text)
        self._msgs.insert(0, msg)

        while len(self._msgs) > self.max_events:
            self._msgs[-1].destroy()
            self._msgs.pop()
        
        self._cnvs.create_window(0, 0, window=msg)
        self.update_idletasks()
        self._Redraw()
    
    def _Redraw(self) -> None:
        self._cnvs.delete('all')
        cnvsWidth = self._GetInternalWidth()
        cnvsHeight = self._GetInternalHeight()
        y = self._pady
        if self._msgs:
            x = self._padx + ((cnvsWidth - self._msgs[0].winfo_width()) >> 1)
            self._cnvs.create_window(
                x,
                y,
                anchor=tk.NW,
                window=self._msgs[0])
            y += self._msgs[0].winfo_height()
        idx = 1
        while idx < len(self._msgs):
            x = self._padx + (
                (cnvsWidth - self._msgs[idx].winfo_width()) >> 1)
            y += self._gap
            self._cnvs.create_window(
                x,
                y,
                anchor=tk.NW,
                window=self._msgs[idx])
            y += self._msgs[idx].winfo_height()
            idx += 1
        y += self._pady
        if y < cnvsHeight:
            y = cnvsHeight
        self._cnvs['scrollregion'] = (0, 0, cnvsWidth, y)
    
    def _GetInternalWidth(self) -> int:
        return (
            self._cnvs.winfo_width()
            - 4
            - (self._padx << 1)
            + (int(self._cnvs['bd']) << 1))
    
    def _GetInternalHeight(self) -> int:
        return (
            self._cnvs.winfo_height()
            - 4
            - (self._pady << 1)
            + (int(self._cnvs['bd']) << 1))


class LyricsEditor(Sheet):
    def __init__(self, parent, **kwargs) -> None:
        super().__init__(parent, **kwargs)

        self.headers([
            'Timestap',
            'Lyrics/text'])
        self.enable_bindings(
            'row_select',
            'drag_select',
            'single_select',
            'column_width_resize',
            'double_click_column_resize',
            'edit_cell')
