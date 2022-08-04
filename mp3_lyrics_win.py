from concurrent.futures import CancelledError, Future
from enum import IntEnum
import logging
from pathlib import Path
from pprint import pprint
import re
import tkinter as tk
from tkinter import PhotoImage, ttk
from tkinter.filedialog import askopenfilename
from tkinter.messagebox import showerror

from mutagen.mp3 import MP3, HeaderNotFoundError
import PIL.Image
import PIL.ImageTk
from pygame import init, USEREVENT
import pygame.event
from pygame.mixer import music, quit

from app_utils import AppSettings
from asyncio_thrd import AsyncioThrd
from lrc import Lrc
from megacodist.keyboard import Modifiers
from sorted_list import SortedList
from widgets import InfoView, MessageType, MessageView, LyricsView, FolderView
from widgets import LyricsEditor, WaitFrame
from win_utils import AfterProcessInfo, LoadingFolderAfterInfo, LoadingLrcAfterInfo


class AfterPlayed(IntEnum):
    STOP_PLAYING = 0
    REPEAT = 1
    PLAY_FOLDER = 2
    REPEAT_FOLDER = 3


class Mp3LyricsWin(tk.Tk):
    def __init__(
            self,
            res_dir: str | Path,
            asyncio_thrd: AsyncioThrd,
            screenName: str | None = None,
            baseName: str | None = None,
            className: str = 'Tk',
            useTk: bool = True,
            sync: bool = False,
            use: str | None = None
            ) -> None:
        super().__init__(screenName, baseName, className, useTk, sync, use)
        self.title('MP3 Lyrics')

        # Reading & applying Lyrics Editor Window (MLW) settings...
        settings = self._ReadSettings()
        self.geometry(
            f"{settings['MLW_WIDTH']}x{settings['MLW_HEIGHT']}"
            + f"+{settings['MLW_X']}+{settings['MLW_Y']}")
        self.state(settings['MLW_STATE'])

        # Specifies whether the MP3 is playing or not
        self._isPlaying: bool = False
        # Specifies time interval in millisecond for paly methods
        self._TIME_PLAY: int = 30
        # Specifies after ID
        self._playAfterID: str
        # Specifies the end of MP3
        self._MUSIC_END = USEREVENT + 1
        # Specifies the position of MP3
        self._pos: float = 0.0

        self._RES_DIR = res_dir
        self._TIME_AFTER = 40
        self._asyncThrd = asyncio_thrd
        self._loadingFolder: LoadingFolderAfterInfo | None = None
        self._loadingLrc: LoadingLrcAfterInfo | None = None

        self._afterPlayed = tk.IntVar(
            master=self,
            value=settings['MLW_AFTER_PLAYED'])
        self._lrc: Lrc | None = None
        self._lrcLoaded: bool = False
        self._timestamps: SortedList[float] = []

        self._IMG_PLAY: PIL.ImageTk.PhotoImage
        self._IMG_PAUSE: PIL.ImageTk.PhotoImage
        self._IMG_VOLUME: PIL.ImageTk.PhotoImage
        self._IMG_MP3: PIL.ImageTk.PhotoImage
        self._IMG_LRC: PIL.ImageTk.PhotoImage
        self._IMG_WAIT: list[PIL.ImageTk.PhotoImage]

        self._LoadRes()
        self._InitGui()
        self._InitPygame()

        # Applying the rest of settings...
        self._lastFile = settings['MLW_LAST_FILE']
        self._slider_volume.set(settings['MLW_VOLUME'])
        self._lrcedt.set_column_widths([
            settings['MLW_TS_COL_WIDTH'],
            settings['MLW_LT_COL_WIDTH']])
        self._pwin_info.sashpos(0, settings['MLW_INFO_EVENTS_WIDTH'])
        self.update_idletasks()
        self._pwin_player.sashpos(0, settings['MLW_LRC_VIEW_WIDTH'])

        # Bindings...
        self.bind(
            '<Key>',
            self._OnKeyPressed)
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

        self._InitPlayer(self._lastFile)
        self._LoadFolder(self._lastFile)
    
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

        # Loading 'mp3.png'...
        self._IMG_MP3 = self._RES_DIR / 'mp3.png'
        self._IMG_MP3 = PIL.Image.open(self._IMG_MP3)
        self._IMG_MP3 = self._IMG_MP3.resize(size=(16, 16,))
        self._IMG_MP3 = PIL.ImageTk.PhotoImage(image=self._IMG_MP3)

        '''# Loading 'lyrics.png'...
        self._IMG_LRC = self._RES_DIR / 'lyrics.png'
        self._IMG_LRC = PIL.Image.open(self._IMG_LRC)
        self._IMG_LRC = self._IMG_LRC.resize(size=(16, 16,))
        self._IMG_LRC = PIL.ImageTk.PhotoImage(image=self._IMG_LRC)'''

        # Loading 'wait.gif...
        gifFile = self._RES_DIR / 'wait.gif'
        gifFile = PIL.Image.open(gifFile)
        self._IMG_WAIT: list[PhotoImage] = []
        idx = 0
        while True:
            try:
                gifFile.seek(idx)
                self._IMG_WAIT.append(
                    PIL.ImageTk.PhotoImage(image=gifFile))
                idx += 1
            except EOFError :
                break
    
    def _InitGui(self) -> None:      
        #
        self._frm_container = ttk.Frame(
            master=self)
        self._frm_container.pack(
            fill=tk.BOTH,
            expand=True,
            padx=7,
            pady=7)
        
        #
        self._pwin_info = ttk.PanedWindow(
            master=self._frm_container,
            orient=tk.HORIZONTAL)
        self._pwin_info.pack(
            fill=tk.BOTH,
            expand=1)
        
        #
        self._frm_main = ttk.Frame(
            master=self._pwin_info)
        self._frm_main.rowconfigure(
            index=2,
            weight=1)
        self._frm_main.columnconfigure(
            index=0,
            weight=1)
        self._frm_main.pack(
            padx=7,
            pady=7,
            side=tk.LEFT,
            fill=tk.Y)
        self._pwin_info.add(
            self._frm_main,
            weight=1)
        
        #
        self._ntbk_infoEvents = ttk.Notebook(
            master=self._pwin_info)
        self._ntbk_infoEvents.pack(
            side=tk.RIGHT,
            fill=tk.Y)
        self._pwin_info.add(
            self._ntbk_infoEvents,
            weight=1)
        
        #
        self._msgvw = MessageView(
            master=self._ntbk_infoEvents)
        self._ntbk_infoEvents.add(
            self._msgvw,
            text='Events')
        
        #
        self._frm_controls = ttk.Frame(
            master=self._frm_main)
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
            master=self._frm_main)
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
        self._frm_notebook = ttk.Frame(
            master=self._frm_main)
        self._frm_notebook.grid(
            column=0,
            row=2,
            sticky=tk.NSEW)
        
        #
        self._notebook = ttk.Notebook(
            master=self._frm_notebook)
        self._notebook.pack(
            fill=tk.BOTH,
            expand=1)
        
        #
        self._pwin_player = ttk.PanedWindow(
            master=self._notebook,
            orient=tk.HORIZONTAL)
        self._notebook.add(
            self._pwin_player,
            text='Player')
        
        #
        self._lrcvw = LyricsView(
            master=self._pwin_player,
            width=200)
        self._lrcvw.pack(
            side=tk.LEFT,
            fill=tk.Y)
        self._pwin_player.add(
            self._lrcvw,
            weight=1)
        
        #
        self._frm_mp3s = ttk.Frame(
            master=self._pwin_player)
        self._frm_mp3s.columnconfigure(
            index=0,
            weight=1)
        self._frm_mp3s.rowconfigure(
            index=0,
            weight=1)
        self._frm_mp3s.pack(
            side=tk.RIGHT,
            fill=tk.Y)
        self._pwin_player.add(
            self._frm_mp3s,
            weight=1)
        
        #
        self._hscrlbr_mp3s = ttk.Scrollbar(
            master=self._frm_mp3s,
            orient='horizontal')
        self._vscrlbr_mp3s = ttk.Scrollbar(
            master=self._frm_mp3s,
            orient='vertical')
        self._trvw_mp3s = FolderView(
            master=self._frm_mp3s,
            image=self._IMG_MP3,
            select_callback=self._InitPlayer,
            xscrollcommand=self._hscrlbr_mp3s.set,
            yscrollcommand=self._vscrlbr_mp3s.set)
        self._trvw_mp3s.grid(
            column=0,
            row=0,
            sticky=tk.NSEW)
        self._hscrlbr_mp3s['command'] = self._trvw_mp3s.xview
        self._vscrlbr_mp3s['command'] = self._trvw_mp3s.yview
        self._hscrlbr_mp3s.grid(
            column=0,
            row=1,
            sticky=tk.EW)
        self._vscrlbr_mp3s.grid(
            column=1,
            row=0,
            sticky=tk.NS)
        self._trvw_mp3s.grid(
            column=0,
            row=0,
            sticky=tk.NSEW)
        
        #
        self._lrcedt = LyricsEditor(
            self)
        self._notebook.add(
            self._lrcedt,
            text='Editor')
        
        #
        self._infovw = InfoView(
            self)
        self._notebook.add(
            self._infovw,
            text='Info')
        
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
        
        # Ceating 'After played' submenu...
        self._menu_afterPlayed = tk.Menu(
            master=self._menubar,
            tearoff=0)
        self._menu_afterPlayed.add_radiobutton(
            label='Stop playing',
            value=int(AfterPlayed.STOP_PLAYING),
            variable=self._afterPlayed)
        self._menu_afterPlayed.add_radiobutton(
            label='Repeat',
            value=int(AfterPlayed.REPEAT),
            variable=self._afterPlayed)
        self._menu_afterPlayed.add_radiobutton(
            label='Play folder',
            value=int(AfterPlayed.PLAY_FOLDER),
            variable=self._afterPlayed)
        self._menu_afterPlayed.add_radiobutton(
            label='Repeat folder',
            value=int(AfterPlayed.REPEAT_FOLDER),
            variable=self._afterPlayed)
        
        # Creating 'Player' menu...
        self._menu_player = tk.Menu(
            master=self._menubar,
            tearoff=0)
        self._menubar.add_cascade(
            label='Player',
            menu=self._menu_player)
        self._menu_player.add_cascade(
            label='After played',
            menu=self._menu_afterPlayed)

        # Ceating 'Insert a row' submenu...
        self._menu_insertRow = tk.Menu(
            master=self._menubar,
            tearoff=0)
        self._menu_insertRow.add_command(
            label='Above',
            accelerator='Ctrl+K',
            command=self._lrcedt.InsertRowAbove)
        self._menu_insertRow.add_command(
            label='Below',
            accelerator='Ctrl+L',
            command=self._lrcedt.InsertRowBelow)

        # Creating 'Editor' menu...
        self._menu_etitor = tk.Menu(
            master=self._menubar,
            tearoff=0)
        self._menubar.add_cascade(
            label='Editor',
            menu=self._menu_etitor)
        self._menu_etitor.add_command(
            label='Create/save LRC',
            accelerator='Ctrl+S',
            command=self._CreateSaveLrc)
        self._menu_etitor.add_cascade(
            label='Insert a row',
            menu=self._menu_insertRow)
        self._menu_etitor.add_separator()
        self._menu_etitor.add_command(
            label='Clear cell(s)',
            accelerator='Del')
        self._menu_etitor.add_command(
            label='Remove row(s)',
            accelerator='Shift+Del',
            command=self._lrcedt.RemoveRows)
        self._menu_etitor.add_separator()
        self._menu_etitor.add_command(
            label='Paste clipboard',
            command=self._PasteClipboard)
    
    def _OnKeyPressed(self, event: tk.Event) -> None:
        altCtrlShift = (
            Modifiers.ALT
            | Modifiers.CONTROL
            | Modifiers.SHIFT)
        altCtrl = Modifiers.ALT | Modifiers.CONTROL
        altShift = Modifiers.ALT | Modifiers.SHIFT
        ctrlShift = Modifiers.CONTROL | Modifiers.SHIFT
        keySymLower = event.keysym.lower()

        # Checking for keyboard modefiers...
        # Checking Alt+Ctrl+Shift...
        if (event.state & altCtrlShift) == altCtrlShift:
            pass
        # Checking Alt+Ctrl...
        elif (event.state & altCtrl) == altCtrl:
            pass
        # Checking Alt+Shift...
        elif (event.state & altShift) == altShift:
            pass
        # Checking Ctrl+Shift...
        elif (event.state & ctrlShift) == ctrlShift:
            pass
        # Checking Alt...
        elif (event.state & Modifiers.ALT) == Modifiers.ALT:
            pass
        # Checking Ctrl...
        elif (event.state & Modifiers.CONTROL) == Modifiers.CONTROL:
            # Checking Ctrl+O...
            if keySymLower == 'o':
                self._OpenFile()
            # Checking Ctrl+K...
            elif keySymLower == 'k':
                self._lrcedt.InsertRowAbove()
            # Checking Ctrl+L...
            elif keySymLower == 'l':
                self._lrcedt.InsertRowBelow()
            elif keySymLower == 's':
                self._CreateSaveLrc()
        # Checking Shift...
        elif (event.state & Modifiers.SHIFT) == Modifiers.SHIFT:
            if keySymLower == 'delete':
                self._lrcedt.RemoveRows()
        # No Alt, Ctrl, or Shift...
        else:
            if keySymLower == 'delete':
                self._lrcedt.ClearCells()
            elif keySymLower == 'plus':
                self._lrcedt.SetTimestamp(self._pos)

    def _InitPygame(self) -> None:
        # Initializing the 'pygame.mixer' module...
        init()
        music.set_volume(self._slider_volume.get() / 10)
    
    def _InitPlayer(self, mp3_file: str) -> None:
        try:
            self._ChangeGui_NotPlayable()
            music.stop()
            music.load(mp3_file)
            mp3 = MP3(mp3_file)
            self._slider_playTime['to'] = mp3.info.length
            self._lastFile = mp3_file
        except HeaderNotFoundError:
            self._msgvw.AddMessage(
                title='MP3 error',
                message=f"Problem loading '{mp3_file}'",
                type=MessageType.ERROR)
        else:
            self._ChangeGui_Playable()
            self._LoadLrc(mp3_file)
    
    def _OpenFile(self) -> None:
        if self._lastFile:
            folder = str(Path(self._lastFile).resolve().parent)
        else:
            folder = None
        mp3File = askopenfilename(
            filetypes=[
                ('MP3 files', '*.mp3'),
                ('Lyrics files', '*.lrc')],
            initialdir=folder)
        if mp3File:
            self._lastFile = mp3File
            self._InitPlayer(mp3File)
            self._LoadFolder(mp3File)
    
    def _LoadFolder(self, folder: str) -> None:
        future = self._asyncThrd.LoadFolder(folder)
        waitFrame = WaitFrame(
            master=self._trvw_mp3s,
            wait_gif=self._IMG_WAIT,
            cancel_callback=self._LoadFolder_cancel)
        afterID = self.after(
            self._TIME_AFTER,
            self._LoadFolder_after)
        self._loadingFolder = LoadingFolderAfterInfo(
            future,
            afterID,
            waitFrame)
        self._loadingFolder.folder = folder
        self._loadingFolder.waitFrame.Show()
    
    def _LoadFolder_after(self) -> None:
        if self._loadingFolder.future.done():
            self._loadingFolder.waitFrame.Close()
            try:
                folderInfo = self._loadingFolder.future.result()
                self._trvw_mp3s.AddFilenames(
                    folderInfo.folder,
                    folderInfo.mp3s,
                    folderInfo.selectIdx)
            finally:
                del self._loadingFolder
                self._loadingFolder = None
        else:
            self._loadingFolder.afterID = self.after(
                self._TIME_AFTER,
                self._LoadFolder_after)
    
    def _LoadFolder_cancel(self) -> None:
        self._loadingFolder.future.cancel()
        self.after_cancel(self._loadingFolder.afterID)
        self.after(
            self._TIME_AFTER,
            self._LoadFolder_cancel_after)
    
    def _LoadFolder_cancel_after(self) -> None:
        if not self._loadingFolder.future.cancelled():
            self.after(
                self._TIME_AFTER,
                self._LoadFolder_cancel_after)
        else:
            self._loadingFolder.waitFrame.Close()
            del self._loadingFolder
            self._loadingFolder = None
    
    def _LoadLrc(self, mp3_file: str) -> None:
        if self._loadingLrc is None:
            self._SaveLrc()
            self._lrcLoaded = False

            future = self._asyncThrd.LoadLrc(Lrc.GetLrcFilename(mp3_file))
            vwWaitFrame = WaitFrame(
                master=self._lrcvw,
                wait_gif=self._IMG_WAIT,
                cancel_callback=self._LoadLrc_cancel)
            edtWaitFrame = WaitFrame(
                master=self._lrcedt,
                wait_gif=self._IMG_WAIT,
                cancel_callback=self._LoadLrc_cancel)
            afterID = self.after(
                self._TIME_AFTER,
                self._LoadLrc_after)
            self._loadingLrc = LoadingLrcAfterInfo(
                future,
                afterID,
                mp3_file,
                [vwWaitFrame, edtWaitFrame,])
            self._loadingLrc.ShowWaitFrames()
        else:
            self._LoadLrc_cancel(mp3_file)

    def _LoadLrc_after(self) -> None:
        if self._loadingLrc.future.done():
            del self._lrc
            self._lrc = None
            self._loadingLrc.CloseWaitFrames()
            try:
                self._lrc = self._loadingLrc.future.result()
                self._lrc.toSaveNoTimestamps = True
                self._lrcLoaded = True
            except FileNotFoundError: 
                self._msgvw.AddMessage(
                    title='No LRC',
                    message=(
                        f"'{self._loadingLrc.mp3File}' does not have"
                        + ' associated LRC.'),
                    type=MessageType.ERROR)
            except CancelledError as err:
                print(str(err))
            finally:
                self._UpdateGui_Lrc()
                del self._loadingLrc
                self._loadingLrc = None
        else:
            self._loadingLrc.afterID = self.after(
                self._TIME_AFTER,
                self._LoadLrc_after)
    
    def _LoadLrc_cancel(
            self,
            mp3_file: str | None = None
            ) -> None:
        self._loadingLrc.CancelWaitFrames()
        self._loadingLrc.future.cancel()
        self.after_cancel(self._loadingLrc.afterID)
        self.after(
            self._TIME_AFTER,
            self._LoadLrc_cancel_after,
            mp3_file)
    
    def _LoadLrc_cancel_after(
            self,
            mp3_file: str | None = None
            ) -> None:
        if not self._loadingLrc.future.cancelled():
            self.after(
                self._TIME_AFTER,
                self._LoadLrc_cancel_after,
                mp3_file)
        else:
            self._loadingLrc.CloseWaitFrames()
            del self._loadingLrc
            self._loadingLrc = None
            self._lrcLoaded = False
            if mp3_file:
                self._LoadLrc(mp3_file)
    
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
                self._TIME_PLAY,
                self._UpdatePlayTimeSlider,
                pos)
        else:
            # The MP3 is not playing...
            self._btn_palyPause['image'] = self._IMG_PLAY
            music.pause()
            self.after_cancel(self._playAfterID)
    
    def _UpdatePlayTimeSlider(self, start_offset: float) -> None:
        self._pos = (music.get_pos() / 1_000) + start_offset
        # Checking whether the MP3 has finished or not...
        for event in pygame.event.get():
            if event.type == self._MUSIC_END:
                # The MP3 finished, deciding on the action...
                self._DecideAfterPlayed()
                break
        else:
            # The MP3 not finished
            # Updating Play Time slider...
            self._slider_playTime.set(self._pos)
            # Highlighting the current lyrics...
            _, idx = self._timestamps.index(self._pos)
            self._lrcvw.Highlight(idx - 1)
            self._playAfterID = self.after(
                self._TIME_PLAY,
                self._UpdatePlayTimeSlider,
                start_offset)
    
    def _DecideAfterPlayed(self) -> None:
        match self._afterPlayed.get():
            case int(AfterPlayed.STOP_PLAYING):
                self._ResetPlayTimeSlider()
            case int(AfterPlayed.REPEAT):
                music.rewind()
                music.play()
                self._slider_playTime.set(0)
                self._playAfterID = self.after(
                    self._TIME_PLAY,
                    self._UpdatePlayTimeSlider,
                    0)
            case int(AfterPlayed.PLAY_FOLDER):
                pass
            case int(AfterPlayed.REPEAT_FOLDER):
                pass
    
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
                self._TIME_PLAY,
                self._UpdatePlayTimeSlider,
                pos)
    
    def _ReadSettings(self) -> None:
        # Considering Duplicate Finder Window (DFW) default settings...
        defaults = {
            'MLW_WIDTH': 900,
            'MLW_HEIGHT': 600,
            'MLW_X': 200,
            'MLW_Y': 200,
            'MLW_STATE': 'normal',
            'MLW_LAST_FILE': '',
            'MLW_VOLUME': 5.0,
            'MLW_TS_COL_WIDTH': 150,
            'MLW_LT_COL_WIDTH': 300,
            'MLW_AFTER_PLAYED': 0,
            'MLW_INFO_EVENTS_WIDTH': 200,
            'MLW_LRC_VIEW_WIDTH': 200,}
        return AppSettings().Read(defaults)

    def _OnClosingWin(self) -> None:
        # Unloading the MP3 file...
        music.unload()
        # Uninitializing the 'pygame.mixer' module...
        quit()

        if self._lrc and self._lrc.changed:
            self._SaveLrc()

        # Saving settings...
        settings = {}
        # Getting the geometry of the MP3 Lyrics Window (MLW)...
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
            settings['MLW_WIDTH'] = int(match.group('width'))
            settings['MLW_HEIGHT'] = int(match.group('height'))
            settings['MLW_X'] = int(match.group('x'))
            settings['MLW_Y'] = int(match.group('y'))
        else:
            logging.error(
                'Cannot get the geometry of the window.')
        
        # Getting other MP3 Lyrics Window (MLW) settings...
        settings['MLW_STATE'] = self.state()
        settings['MLW_LAST_FILE'] = self._lastFile
        settings['MLW_VOLUME'] = self._slider_volume.get()
        colsWidth = self._lrcedt.get_column_widths()
        settings['MLW_TS_COL_WIDTH'] = colsWidth[0]
        settings['MLW_LT_COL_WIDTH'] = colsWidth[1]
        settings['MLW_AFTER_PLAYED'] = self._afterPlayed.get()
        settings['MLW_INFO_EVENTS_WIDTH'] = self._pwin_info.sashpos(0)
        settings['MLW_LRC_VIEW_WIDTH'] = self._pwin_player.sashpos(0)

        AppSettings().Update(settings)
        self.destroy()

    def _SaveLrc(self) -> None:
        self._lrcedt.ApplyLyrics()
        if self._lrc and self._lrc.changed:
            self._lrc.Save()
    
    def _CreateSaveLrc(self) -> None:
        if self._lrc:
            self._SaveLrc()
        elif self._lrcLoaded:
            pass
        else:
            self._LoadLrc(self._lastFile)
    
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

    def _ChangeGui_Playable(self) -> None:
        self._btn_palyPause['state'] = tk.NORMAL

    def _ChangeGui_Pausable(self) -> None:
        pass

    def _ChangeGui_NotPlayable(self) -> None:
        self._btn_palyPause['state'] = tk.DISABLED
    
    def _UpdateGui_Lrc(self) -> None:
        # Setting timestamps...
        del self._timestamps
        self._timestamps = SortedList()
        if self._lrc and self._lrc.AreTimstampsOk():
            self._timestamps.merge([
                lrcItem.timestamp.ToFloat()
                for lrcItem in self._lrc.lyrics])
    
        # Populating lyrics widgets...
        # Populating the LyricsView...
        self._lrcvw.Populate(self._lrc)

        # Populating the lyrics editor...
        self._lrcedt.Populate(self._lrc)

        # Populating the InofView...
        self._infovw.PopulateLrc(self._lrc)

        # Adding a message if necessary...
        if self._lrc and self._lrc.errors:
            message = [
                str(idx) + '. ' + error
                for idx, error in enumerate(self._lrc.GetErrors(), 1)]
            message.insert(0, self._lrc.filename + '\n')
            self._msgvw.AddMessage(
                title='LRC error',
                message='\n'.join(message),
                type=MessageType.WARNING)
