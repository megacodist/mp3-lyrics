import tkinter as tk
from tkinter import ttk


class AppWin(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.bind('<Key>', self._OnKeyPressed)
    
    def _OnKeyPressed(self, event: tk.Event):
        print(event.keysym.upper(), '=', event.keycode)


if __name__ == '__main__':
    appWin = AppWin()
    appWin.mainloop()
