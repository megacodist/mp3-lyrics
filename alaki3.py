"""Swapping artists for albums in ID3 tags of MP3 files in a directory.
"""

from fractions import Fraction
from pathlib import Path

from mutagen.id3 import ID3, TALB, TPE1

def main() -> None:
    from random import random
    import tkinter as tk
    from tkinter import ttk

    TIME_INTERVAL = 100

    def _PrintScrl(fraction: tuple[int, int]) -> None:
        print('=' * 50)
        a = fraction[0] / fraction[1]
        print(a)
        listbox.yview_moveto(a)
        print(listbox.yview())
        fraction = (fraction[0] + 1, fraction[1],)
        if fraction[0] <= fraction[1]:
            win.after(TIME_INTERVAL, _PrintScrl, fraction)

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
    win.after(TIME_INTERVAL, _PrintScrl, (0, 200,))
    win.mainloop()

if __name__ == '__main__':
    main()