from tkinter import Tk, Event
from lrc import Lrc, LrcErrors, LyricsItem

def OnKeyPressed(event: Event) -> None:
    print(event)


app = Tk()
app.bind('<Key>', OnKeyPressed)
app.mainloop()