import logging
from pathlib import Path
import re
import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askopenfilename
from tkinter.messagebox import showerror

from mutagen.mp3 import MP3
import PIL.Image
import PIL.ImageTk
from pygame import init, USEREVENT
import pygame.event
from pygame.mixer import music, quit
from tksheet import Sheet

from asyncio_thrd import AsyncioThrd
from utils import AppSettings


class Mp3LyricsWin(tk.Tk):
    def __init__(
            self,
            res_dir: str | Path,
            asyncio_htd: AsyncioThrd,
            screenName: str | None = None,
            baseName: str | None = None,
            className: str = 'Tk',
            useTk: bool = True,
            sync: bool = False,
            use: str | None = None
            ) -> None:
        super().__init__(screenName, baseName, className, useTk, sync, use)
        self.title('MP3 Lyrics')

        # Reading & applying Lyrics Editor Window (LEW) settings...
        settings = self._ReadSettings()
        self.geometry(
            f"{settings['LEW_WIDTH']}x{settings['LEW_HEIGHT']}"
            + f"+{settings['LEW_X']}+{settings['LEW_Y']}")
        self.state(settings['LEW_STATE'])

        # Specifies whether the MP3 is playing or not
        self._isPlaying: bool = False
        # Specifies time interval in millisecond for after functions/methods
        self._TIME_INTRVL: int = 30
        # Specifies after ID
        self._playAfterID: str
        # Specifies the end of MP3
        self._MUSIC_END = USEREVENT + 1

        self._RES_DIR = res_dir

        self._IMG_PLAY: PIL.ImageTk.PhotoImage
        self._IMG_PAUSE: PIL.ImageTk.PhotoImage
        self._IMG_VOLUME: PIL.ImageTk.PhotoImage

        self._LoadRes()
        self._InitGui()
        self._InitPygame()

        # Applying the rest of settings...
        self._slider_volume.set(settings['LEW_VOLUME'])
        self._sheet.set_column_widths([
            settings['LEW_TS_COL_WIDTH'],
            settings['LEW_LT_COL_WIDTH']])
        
        # Loading the lyrics for this MP3 if any...
        self._LoadLyrics()

        # Bindings...
        self.bind(
            '<Control-o>',
            self._OpenFile)
        self._slider_playTime.bind(
            '<ButtonPress-1>',
            self._OnPlayTimeSliderPressed)
        self._slider_playTime.bind(
            '<B1-Motion>',
            self._DragPlayTimeSlider)
        self._slider_playTime.bind(
            '<ButtonRelease-1>',
            self._OnPlayTimeSliderRelease)
        self.protocol('WM_DELETE_WINDOW', self._OnClosingWin)
    
    def _LoadRes(self) -> None:
        # Loading 'volume.png'...
        self._IMG_VOLUME = self._RES_DIR / 'volume.png'
        self._IMG_VOLUME = PIL.Image.open(self._IMG_VOLUME)
        self._IMG_VOLUME = self._IMG_VOLUME.resize(size=(24, 24,))
        self._IMG_VOLUME = PIL.ImageTk.PhotoImage(image=self._IMG_VOLUME)

        # Loading 'play.png'...
        self._IMG_PLAY = self._RES_DIR / 'play.png'
        self._IMG_PLAY = PIL.Image.open(self._IMG_PLAY)
        self._IMG_PLAY = self._IMG_PLAY.resize(size=(24, 24,))
        self._IMG_PLAY = PIL.ImageTk.PhotoImage(image=self._IMG_PLAY)

        # Loading 'pause.png'...
        self._IMG_PAUSE = self._RES_DIR / 'pause.png'
        self._IMG_PAUSE = PIL.Image.open(self._IMG_PAUSE)
        self._IMG_PAUSE = self._IMG_PAUSE.resize(size=(24, 24,))
        self._IMG_PAUSE = PIL.ImageTk.PhotoImage(image=self._IMG_PAUSE)
    
    def _InitGui(self) -> None:
        # Creating menu bar...
        self._menubar = tk.Menu(
            master=self)
        self['menu'] = self._menubar

        # Creating File menu...
        self._menu_file = tk.Menu(
            master=self._menubar,
            tearoff=0)
        self._menubar.add_cascade(
            label='File',
            menu=self._menu_file)
        self._menu_file.add_command(
            label='Open a file...',
            accelerator='Ctrl+O',
            command=self._OpenFile)

        #
        self._menu_insertRow = tk.Menu(
            master=self._menubar,
            tearoff=0)
        self._menu_insertRow.add_command(
            label='Above')
        self._menu_insertRow.add_command(
            label='Bellow')

        # Creating Sheet menu...
        self._menu_sheet = tk.Menu(
            master=self._menubar,
            tearoff=0)
        self._menubar.add_cascade(
            label='Sheet',
            menu=self._menu_sheet)
        self._menu_sheet.add_cascade(
            label='Insert a row',
            menu=self._menu_insertRow)
        self._menu_sheet.add_separator()
        self._menu_sheet.add_command(
            label='Paste clipboard',
            command=self._PasteClipboard)
        
        #
        self._frm_container = ttk.Frame(
            master=self)
        self._frm_container.rowconfigure(
            index=2,
            weight=1)
        self._frm_container.columnconfigure(
            index=0,
            weight=1)
        self._frm_container.pack(
            padx=7,
            pady=7,
            fill=tk.BOTH,
            expand=1)
        
        #
        self._frm_controls = ttk.Frame(
            master=self._frm_container)
        self._frm_controls.grid(
            column=0,
            row=0,
            ipadx=7,
            ipady=7,
            sticky=tk.NSEW)
        
        #
        self._btn_palyPause = ttk.Button(
            master=self._frm_controls,
            image=self._IMG_PLAY,
            state=tk.DISABLED,
            command=self._PlayPauseMp3)
        self._btn_palyPause.pack(side=tk.LEFT)
        
        #
        self._lbl_volume = ttk.Label(
            master=self._frm_controls,
            image=self._IMG_VOLUME)
        self._lbl_volume.pack(side=tk.LEFT)

        #
        self._slider_volume = ttk.Scale(
            master=self._frm_controls,
            from_=0.0,
            to=10.0,
            length=100,
            command=self._ChangeVolume)
        self._slider_volume.pack(side=tk.LEFT)

        #
        self._frm_playTime = ttk.Frame(
            master=self._frm_container)
        self._frm_playTime.grid(
            column=0,
            row=1,
            sticky=tk.NSEW)

        #
        self._slider_playTime = ttk.Scale(
            master=self._frm_playTime,
            from_=0)
        self._slider_playTime.pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=1)
        
        #
        self._frm_main = ttk.Frame(
            master=self._frm_container)
        self._frm_main.grid(
            column=0,
            row=2,
            sticky=tk.NSEW)
        
        #
        self._notebook = ttk.Notebook(
            master=self._frm_main)
        self._notebook.pack(
            fill=tk.BOTH,
            expand=1)
        
        #
        self._frm_player = ttk.Frame(
            master=self._notebook)
        self._frm_player.columnconfigure(
            index=0,
            weight=2)
        self._frm_player.columnconfigure(
            index=1,
            weight=1)
        self._frm_player.rowconfigure(
            index=0,
            weight=1)
        self._notebook.add(
            self._frm_player,
            text='Player')
        
        #
        self._trvw_mp3s = ttk.Treeview(
            master=self._frm_player)
        self._trvw_mp3s.grid(
            column=1,
            row=0,
            sticky=tk.NSEW)
        
        #
        self._frm_editor = ttk.Frame(
            master=self._notebook)
        self._notebook.add(
            self._frm_editor,
            text='Editor')
        
        #
        self._sheet = Sheet(
            self._frm_editor)
        self._sheet.headers([
            'Timestap',
            'Lyrics/text'])
        self._sheet.insert_row(
            values=('', '',))
        self._sheet.enable_bindings(
            'row_select',
            'drag_select',
            'single_select',
            'column_width_resize',
            'double_click_column_resize',
            'edit_cell')
        self._sheet.pack(
            fill=tk.BOTH,
            expand=1)
        
        #
        self._frm_buttons = ttk.Frame(
            master=self._frm_container)
        self._frm_buttons.grid(
            column=0,
            row=3,
            ipadx=7,
            ipady=7,
            sticky=tk.NSEW)
        
        #
        self._btn_ok = ttk.Button(
            master=self._frm_buttons,
            text='OK',
            command=self._OnOKClicked)
        self._btn_ok.pack(side=tk.RIGHT)

        #
        self._btn_cancel = ttk.Button(
            master=self._frm_buttons,
            text='Cancel',
            command=self._OnClosingWin)
        self._btn_cancel.pack(side=tk.RIGHT)

    def _InitPygame(self) -> None:
        # Initializing the 'pygame.mixer' module...
        init()
        music.set_volume(self._slider_volume.get() / 10)
    
    def _OpenFile(self, *args) -> None:
        mp3File = askopenfilename(
            filetypes=[
                ('MP3 files', '*.mp3'),
                ('Lyrics files', '*.lrc')])
        if mp3File:
            self._InitPlayer(mp3File)
    
    def _InitPlayer(self, mp3_file: str) -> None:
        self._btn_palyPause['state'] = tk.NORMAL
        music.load(mp3_file)
        mp3 = MP3(mp3_file)
        self._slider_playTime['to'] = mp3.info.length
        music.set_volume(self._slider_volume.get() / 10)
    
    def _ChangeVolume(self, value: str) -> None:
        music.set_volume(float(value) / 10)
    
    def _PlayPauseMp3(self) -> None:
        # Checking if the MP3 ispalying or not...
        self._isPlaying = not self._isPlaying
        if self._isPlaying:
            # The MP3 is playing...
            self._btn_palyPause['image'] = self._IMG_PAUSE
            pos = round(self._slider_playTime.get())
            self._slider_playTime.set(pos)
            music.set_endevent(self._MUSIC_END)
            music.play(start=pos)
            self._playAfterID = self.after(
                self._TIME_INTRVL,
                self._UpdatePlayTimeSlider,
                pos)
        else:
            # The MP3 is not playing...
            self._btn_palyPause['image'] = self._IMG_PLAY
            music.pause()
            self.after_cancel(self._playAfterID)
    
    def _UpdatePlayTimeSlider(self, start_offset: float) -> None:
        curPos = (music.get_pos() / 1_000) + start_offset
        # Checking whether the MP3 has finished or not...
        for event in pygame.event.get():
            if event.type == self._MUSIC_END:
                # The MP3 finished, resetting the Play Time slider...
                self._ResetPlayTimeSlider()
                break
        else:
            # The MP3 not finished
            # Updating Play Time slider...
            self._slider_playTime.set(curPos)
            self._playAfterID = self.after(
                self._TIME_INTRVL,
                self._UpdatePlayTimeSlider,
                start_offset)
    
    def _ResetPlayTimeSlider(self) -> None:
        self._isPlaying = False
        self._btn_palyPause['image'] = self._IMG_PLAY
        self._slider_playTime.set(0.0)
    
    def _GetMp3PosBySiderX(self, x: int) -> int:
        """Returns the offset of the MP3 by the X coordinate of the Play Time
        slider. For MP3 files this offset must be a whole second, without any
        fraction, to be suitable for playback.
        """
        return round(
            x * self._slider_playTime['to']
            / self._slider_playTime.winfo_width())
    
    def _DragPlayTimeSlider(self, event: tk.Event) -> None:
        # Finding & rounding pos to the nearest second...
        pos = self._GetMp3PosBySiderX(event.x)
        self._slider_playTime.set(pos)
        if self._isPlaying:
            music.play(start=pos)
    
    def _OnPlayTimeSliderPressed(self, event: tk.Event) -> None:
        if self._isPlaying:
            self.after_cancel(self._playAfterID)
        self._DragPlayTimeSlider(event)
    
    def _OnPlayTimeSliderRelease(self, event: tk.Event) -> None:
        # Finding & rounding pos to the nearest second...
        pos = self._GetMp3PosBySiderX(event.x)
        self._slider_playTime.set(pos)
        if self._isPlaying:
            self._playAfterID = self.after(
                self._TIME_INTRVL,
                self._UpdatePlayTimeSlider,
                pos)
    
    def _ReadSettings(self) -> None:
        # Considering Duplicate Finder Window (DFW) default settings...
        defaults = {
            'LEW_WIDTH': 900,
            'LEW_HEIGHT': 600,
            'LEW_X': 200,
            'LEW_Y': 200,
            'LEW_STATE': 'normal',
            'LEW_VOLUME': 5.0,
            'LEW_TS_COL_WIDTH': 150,
            'LEW_LT_COL_WIDTH': 300,}
        return AppSettings().Read(defaults)

    def _OnClosingWin(self) -> None:
        # Unloading the MP3 file...
        music.unload()
        # Uninitializing the 'pygame.mixer' module...
        quit()

        # Saving settings...
        settings = {}
        # Getting the geometry of the Lyrics Editor Window (LEW)...
        w_h_x_y = self.winfo_geometry()
        GEOMETRY_REGEX = r"""
            (?P<width>\d+)    # The width of the window
            x(?P<height>\d+)  # The height of the window
            \+(?P<x>\d+)      # The x-coordinate of the window
            \+(?P<y>\d+)      # The y-coordinate of the window"""
        match = re.search(
            GEOMETRY_REGEX,
            w_h_x_y,
            re.VERBOSE)
        if match:
            settings['LEW_WIDTH'] = int(match.group('width'))
            settings['LEW_HEIGHT'] = int(match.group('height'))
            settings['LEW_X'] = int(match.group('x'))
            settings['LEW_Y'] = int(match.group('y'))
        else:
            logging.error(
                'Cannot get the geometry of Duplicate Finder Window.')
        
        # Getting other Duplicate Finder Window (DFW) settings...
        settings['LEW_STATE'] = self.state()
        settings['LEW_VOLUME'] = self._slider_volume.get()
        colsWidth = self._sheet.get_column_widths()
        settings['LEW_TS_COL_WIDTH'] = colsWidth[0]
        settings['LEW_LT_COL_WIDTH'] = colsWidth[1]

        AppSettings().Update(settings)
        self.destroy()
    
    def _OnOKClicked(self) -> None:
        self._SaveLyrics()
        self._OnClosingWin()
    
    def _LoadLyrics(self) -> None:
        pass

    def _SaveLyrics(self) -> None:
        pass
    
    def _GetClipboardAsList(self) -> list[str]:
        lyrics = self.clipboard_get()
        return lyrics.strip().splitlines()
    
    def _PasteClipboard(self) -> None:
        lines = self._GetClipboardAsList()
        if not lines:
            showerror(message='No text in clipboard')
            return
    
    def _InsertClipboard(self) -> None:
        pass
