#
# 
#
"""
"""


import tkinter as tk
from typing import Callable


class Mp3ListView(tk.Frame):
    def __init__(
                self,
                master: tk.Tk,
                select_callback: Callable[[str], None],
                **kwargs
                ) -> None:
        from tkinterweb import HtmlFrame
        super().__init__(master, **kwargs)
        self._webvw = HtmlFrame(
            self,
            vertical_scrollbar=True,
            horizontal_scrollbar=True,
            messages_enabled=False)
