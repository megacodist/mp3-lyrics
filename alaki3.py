"""Swapping artists for albums in ID3 tags of MP3 files in a directory.
"""
from pathlib import Path

from mutagen.id3 import ID3, TALB, TPE1

def main() -> None:
    from random import random
    import tkinter as tk
    from tkinter import ttk

    def _PrintScrl() -> None:
        print(listbox.yview())
        rand = random()
        print(rand)
        listbox.yview_moveto(rand)
        win.after(4_000, _PrintScrl)

    win = tk.Tk()
    yscrl = ttk.Scrollbar(win, orient=tk.VERTICAL)
    listbox = tk.Listbox(win, yscrollcommand=yscrl.set)
    yscrl['command'] = listbox.yview
    win.columnconfigure(0, weight=1)
    win.rowconfigure(0, weight=1)
    yscrl.grid(column=1, row=0, sticky=tk.NS)
    listbox.grid(column=0, row=0, sticky=tk.NSEW)

    for idx in range(200):
        listbox.insert('end', idx)
    win.after(500, _PrintScrl)
    win.mainloop()

if __name__ == '__main__':
    main()