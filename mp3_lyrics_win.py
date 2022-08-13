from concurrent.futures import CancelledError
import logging
from pathlib import Path
import re
import tkinter as tk
from tkinter import GROOVE, TOP, PhotoImage, ttk
from tkinter.filedialog import askopenfilename
from tkinter.messagebox import askyesno
from typing import Annotated

from mutagen.mp3 import MP3, HeaderNotFoundError
import PIL.Image
import PIL.ImageTk
import pygame
from pygame import init, USEREVENT
import pygame.event
from pygame.mixer import music, quit

from app_utils import AppSettings
from asyncio_thrd import AsyncioThrd
from lrc import Lrc, Timestamp
from megacodist.keyboard import Modifiers, KeyCodes
from sorted_list import SortedList
from widgets import ABView, InfoView, MessageType, MessageView, LyricsView
from widgets import LyricsEditor, WaitFrame, FolderView
from win_utils import LoadingFolderAfterInfo, LoadingLrcAfterInfo
from win_utils import AfterPlayed


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

        self._isPlaying: bool = False
        """Specifies whether the MP3 is playing or not."""
        self._TIME_PLAY: int = 30
        """Specifies time interval in millisecond for paly methods."""
        self._playAfterID: str
        """Specifies after ID for play method"""
        self._MUSIC_END = USEREVENT + 1
        """Specifies the event of the end of MP3"""
        self._pos: float = 0.0
        """Specifies the playback position of MP3"""
        self._nDecimal: int = 2
        """Specifies number of digits after decimal point that the
        position of the playback must be rounded to.
        """
        self._RES_DIR = res_dir
        """Specifies the resource folder of the application."""
        self._TIME_AFTER = 40
        self._asyncThrd = asyncio_thrd
        """Specifies the asyncio thread capable of performing operations
        related to this application.
        """
        self._loadingFolder: LoadingFolderAfterInfo | None = None
        self._loadingLrc: LoadingLrcAfterInfo | None = None

        self._afterPlayed = tk.IntVar(
            master=self,
            value=settings['MLW_AFTER_PLAYED'])
        self._lrc: Lrc | None = None
        """The Lrc object associated with the current MP3 file."""
        self._lrcLoaded: bool = False
        """Specifies whether the LRC file has been loaded or not. This flag
        in conjuction with _lrc object can determine whether the LRC file
        exists or not.
        """
        self._mp3: MP3 | None = None
        """The mutagen.mp3.MP3 object of the _lastFile file."""
        self._timestamps: SortedList[float] = []

        self._IMG_PLAY: PIL.ImageTk.PhotoImage
        self._IMG_PAUSE: PIL.ImageTk.PhotoImage
        self._IMG_VOLUME: PIL.ImageTk.PhotoImage
        self._IMG_MP3: PIL.ImageTk.PhotoImage
        self._IMG_LRC: PIL.ImageTk.PhotoImage
        self._GIF_WAIT: list[PIL.ImageTk.PhotoImage]

        self._LoadRes()
        self._InitGui()
        self._InitPygame()

        # Applying the rest of settings...
        self._lastFile = settings['MLW_LAST_FILE']
        """Specifies the current MP3 file."""
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
        self._GIF_WAIT: list[PhotoImage] = []
        idx = 0
        while True:
            try:
                gifFile.seek(idx)
                self._GIF_WAIT.append(
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
        self._frm_volume = ttk.Frame(
            self._frm_controls,
            relief=tk.GROOVE)
        self._frm_volume.pack(
            side=tk.LEFT,
            ipadx=2,
            ipady=2,
            padx=2)

        #
        self._lbl_volume = ttk.Label(
            master=self._frm_volume,
            image=self._IMG_VOLUME)
        self._lbl_volume.pack(
            side=tk.LEFT,
            padx=1,
            pady=1)

        #
        self._slider_volume = ttk.Scale(
            master=self._frm_volume,
            from_=0.0,
            to=10.0,
            length=100,
            command=self._ChangeVolume)
        self._slider_volume.pack(
            side=tk.LEFT,
            padx=1,
            pady=1)

        #
        self._frm_posLength = ttk.Frame(
            self._frm_controls,
            relief=tk.GROOVE)
        self._frm_posLength.columnconfigure(0, weight=1)
        self._frm_posLength.columnconfigure(2, weight=1)
        self._frm_posLength.columnconfigure(4, weight=1)
        self._frm_posLength.rowconfigure(0, weight=1)
        self._frm_posLength.rowconfigure(1, weight=1)
        self._frm_posLength.pack(
            side=tk.LEFT,
            ipadx=4,
            ipady=4)

        #
        self._lbl_posMin = ttk.Label(
            self._frm_posLength,
            text='0')
        self._lbl_posMin.grid(
            column=0,
            row=0,
            padx=(1, 0,),
            pady=(1, 0,))
        
        #
        self._lbl_posColon = ttk.Label(
            self._frm_posLength,
            text=':')
        self._lbl_posColon.grid(
            column=1,
            row=0,
            padx=0,
            pady=(1, 0,))

        #
        self._lbl_posSec = ttk.Label(
            self._frm_posLength,
            text='0')
        self._lbl_posSec.grid(
            column=2,
            row=0,
            padx=0,
            pady=(1, 0,))
        
        #
        self._lbl_posDot = ttk.Label(
            self._frm_posLength,
            text='.')
        self._lbl_posDot.grid(
            column=3,
            row=0,
            padx=0,
            pady=(1, 0,))

        #
        self._lbl_posMilli = ttk.Label(
            self._frm_posLength,
            text='0')
        self._lbl_posMilli.grid(
            column=4,
            row=0,
            padx=(0, 1,),
            pady=(1, 0,))
        
        #
        self._lbl_lengthMin = ttk.Label(
            self._frm_posLength,
            text='0')
        self._lbl_lengthMin.grid(
            column=0,
            row=1,
            padx=(1, 0,),
            pady=(0, 1))
        
        #
        self._lbl_lengthColon = ttk.Label(
            self._frm_posLength,
            text=':')
        self._lbl_lengthColon.grid(
            column=1,
            row=1,
            padx=0,
            pady=(0, 1))
        
        #
        self._lbl_lengthSec = ttk.Label(
            self._frm_posLength,
            text='0')
        self._lbl_lengthSec.grid(
            column=2,
            row=1,
            padx=0,
            pady=(0, 1))
        
        #
        self._lbl_lengthDot = ttk.Label(
            self._frm_posLength,
            text='.')
        self._lbl_lengthDot.grid(
            column=3,
            row=1,
            padx=0,
            pady=(0, 1))
        
        #
        self._lbl_lengthMilli = ttk.Label(
            self._frm_posLength,
            text='0')
        self._lbl_lengthMilli.grid(
            column=4,
            row=1,
            padx=(0, 1),
            pady=(0, 1))

        #
        self._frm_playTime = ttk.Frame(
            self._frm_main,
            relief=tk.GROOVE)
        self._frm_playTime.grid(
            column=0,
            row=1,
            sticky=tk.NSEW,
            ipadx=4,
            ipady=4)

        #
        self._slider_playTime = ttk.Scale(
            master=self._frm_playTime,
            from_=0)
        self._slider_playTime.pack(
            side=tk.TOP,
            fill=tk.X,
            expand=1,
            padx=2,
            pady=(2, 0))
        
        #
        self._abvw = ABView(self._frm_playTime)
        self._abvw.pack(
            side=tk.TOP,
            fill=tk.X,
            expand=1,
            padx=2,
            pady=(0, 2))
        
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
        self._foldervw = FolderView(
            master=self._frm_mp3s,
            image=self._IMG_MP3,
            select_callback=self._InitPlayer,
            xscrollcommand=self._hscrlbr_mp3s.set,
            yscrollcommand=self._vscrlbr_mp3s.set)
        self._foldervw.grid(
            column=0,
            row=0,
            sticky=tk.NSEW)
        self._hscrlbr_mp3s['command'] = self._foldervw.xview
        self._vscrlbr_mp3s['command'] = self._foldervw.yview
        self._hscrlbr_mp3s.grid(
            column=0,
            row=1,
            sticky=tk.EW)
        self._vscrlbr_mp3s.grid(
            column=1,
            row=0,
            sticky=tk.NS)
        self._foldervw.grid(
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
            label='Open an MP3...',
            accelerator='Ctrl+O',
            command=self._OpenMp3)
        
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
        self._menu_player.add_command(
            label='Play/pause',
            accelerator='P',
            command=self._PlayPauseMp3)
        self._menu_player.add_separator()
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
            label='Create LRC',
            accelerator='Ctrl+N',
            command=self._CreateLrc)
        self._menu_etitor.add_command(
            label='Save LRC',
            accelerator='Ctrl+S',
            command=self._SaveLrc)
        self._menu_etitor.add_command(
            label='Discard changes')
        self._menu_etitor.add_command(
            label='Delete LRC',
            command=self._DeleteLrc)
        self._menu_etitor.add_separator()
        self._menu_etitor.add_cascade(
            label='Insert a row',
            menu=self._menu_insertRow)
        self._menu_etitor.add_command(
            label='Clear cell(s)',
            accelerator='Del')
        self._menu_etitor.add_command(
            label='Remove row(s)',
            accelerator='Shift+Del',
            command=self._lrcedt.RemoveRows)
        self._menu_etitor.add_separator()
        self._menu_etitor.add_command(
            label='Override from clipboard',
            accelerator='Ctrl+U',
            command=self._lrcedt.OverrideFromClipboard)
        self._menu_etitor.add_command(
            label='Insert from clipboard',
            accelerator='Ctrl+I',
            command=self._lrcedt.InsertFromClipboard)
    
    def _OnKeyPressed(self, event: tk.Event) -> None:
        altCtrlShift = (
            Modifiers.ALT
            | Modifiers.CONTROL
            | Modifiers.SHIFT)
        altCtrl = Modifiers.ALT | Modifiers.CONTROL
        altShift = Modifiers.ALT | Modifiers.SHIFT
        ctrlShift = Modifiers.CONTROL | Modifiers.SHIFT

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
            if event.keycode == KeyCodes.O:
                self._OpenMp3()
            # Checking Ctrl+K...
            elif event.keycode == KeyCodes.K:
                self._lrcedt.InsertRowAbove()
            # Checking Ctrl+L...
            elif event.keycode == KeyCodes.L:
                self._lrcedt.InsertRowBelow()
            # Checking Ctrl+S...
            elif event.keycode == KeyCodes.S:
                self._SaveLrc()
            # Checking Ctrl+V...
            elif event.keycode == KeyCodes.U:
                self._lrcedt.OverrideFromClipboard()
            # Checking Ctrl+I...
            elif event.keycode == KeyCodes.I:
                self._lrcedt.InsertFromClipboard()
            # Checking Ctrl+N...
            elif event.keycode == KeyCodes.N:
                self._CreateLrc()
        # Checking Shift...
        elif (event.state & Modifiers.SHIFT) == Modifiers.SHIFT:
            if event.keycode == KeyCodes.DELETE:
                self._lrcedt.RemoveRows()
        # No Alt, Ctrl, or Shift...
        else:
            if event.keycode == KeyCodes.DELETE:
                self._lrcedt.ClearCells()
            elif event.keycode == KeyCodes.F5:
                self._lrcedt.SetTimestamp(self._pos)
            elif event.keycode == KeyCodes.P:
                self._PlayPauseMp3()
    
    @property
    def pos(self) -> float:
        return self._pos

    @pos.setter
    def pos(self, __pos: float, /) -> None:
        self._pos = __pos
        timestamp = Timestamp.FromFloat(__pos,ndigits=self._nDecimal)
        self._lbl_posMin['text'] = str(timestamp.minutes)
        self._lbl_posSec['text'] = str(timestamp.seconds)
        self._lbl_posMilli['text'] = str(timestamp.milliseconds)[2:]

    def _InitPygame(self) -> None:
        # Initializing the 'pygame.mixer' module...
        init()
        music.set_volume(self._slider_volume.get() / 10)
    
    def _InitPlayer(self, mp3File: str) -> None:
        # Definition of variables...
        exceptionOccurred: bool = True

        # Starting...
        try:
            self._UpdateGui_NotPlayable()
            music.stop()
            music.load(mp3File)
            self._mp3 = MP3(mp3File)
            self._slider_playTime['to'] = self._mp3.info.length
            self._SetLength(self._mp3.info.length)
            self.pos = 0
            self._lastFile = mp3File
            exceptionOccurred = False
        except HeaderNotFoundError:
            self._msgvw.AddMessage(
                title='MP3 metadata error',
                message=f"Problem loading '{mp3File}'",
                type=MessageType.ERROR)
        except pygame.error as err:
            self._msgvw.AddMessage(
                title='MP3 file error',
                message=f"{str(err)}",
                type=MessageType.ERROR)
        else:
            self.title(f'{Path(self._lastFile).name} - MP3 Lyrics')
            self._UpdateGui_Playable()
            self._LoadLrc(mp3File)
        finally:
            if exceptionOccurred:
                self.title('MP3 Lyrics')
    
    def _SetLength(self, __leng: float) -> None:
        timestamp = Timestamp.FromFloat(__leng, ndigits=self._nDecimal)
        self._lbl_lengthMin['text'] = str(timestamp.minutes)
        self._lbl_lengthSec['text'] = str(timestamp.seconds)
        self._lbl_lengthMilli['text'] = str(timestamp.milliseconds)[2:]
    
    def _OpenMp3(self) -> None:
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
        future = self._asyncThrd.LoadFolder(
            folder,
            key=FolderView.GetComparer)
        waitFrame = WaitFrame(
            master=self._foldervw,
            wait_gif=self._GIF_WAIT,
            cancel_callback=self._LoadFolder_cancel)
        afterID = self.after(
            self._TIME_AFTER,
            self._LoadFolder_after)
        self._loadingFolder = LoadingFolderAfterInfo(
            future,
            afterID,
            folder,
            waitFrame)
        self._loadingFolder.waitFrame.Show()
    
    def _LoadFolder_after(self) -> None:
        if self._loadingFolder.future.done():
            self._loadingFolder.waitFrame.Close()
            try:
                folderInfo = self._loadingFolder.future.result()
                self._foldervw.AddFilenames(
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
    
    def _LoadLrc(self, mp3File: str, toCreate: bool = False) -> None:
        """Loads the LRC file associated with the specified MP3 file. The
        optional toCreate parameter specifies whether to create the LRC file
        in the case that it does not exist.
        """
        if self._loadingLrc is None:
            if self._lrc and self._lrc.changed:
                toSave = askyesno(message='Do you want to save the LRC?')
                if toSave:
                    self._SaveLrc()
                self._lrcLoaded = False

            future = self._asyncThrd.LoadLrc(
                Lrc.GetLrcFilename(mp3File),
                toCreate)
            vwWaitFrame = WaitFrame(
                master=self._lrcvw,
                wait_gif=self._GIF_WAIT,
                cancel_callback=self._LoadLrc_cancel)
            edtWaitFrame = WaitFrame(
                master=self._lrcedt,
                wait_gif=self._GIF_WAIT,
                cancel_callback=self._LoadLrc_cancel)
            afterID = self.after(
                self._TIME_AFTER,
                self._LoadLrc_after)
            self._loadingLrc = LoadingLrcAfterInfo(
                future,
                afterID,
                mp3File,
                [vwWaitFrame, edtWaitFrame,])
            self._loadingLrc.ShowWaitFrames()
        else:
            # Informing of cancling of loading LRC...
            self._msgvw.AddMessage(
                message=(
                    'Loading LRC of '
                    + f"'{self._loadingLrc.mp3File}' was calceled."),
                title='Canceling loading LRC',
                type=MessageType.INFO)
            self._LoadLrc_cancel(mp3File)
            print('Alaki')
            print(mp3File)

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
        try:
            self.pos = (music.get_pos() / 1_000) + start_offset
        except ValueError:
            logging.error(
                f"There was a problem converting {self._pos}"
                + f" to a {str(Timestamp.__class__)} object")
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
            toSave = askyesno(message='Do you want to save the LRC?')
            if toSave:
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
        if self._lrc:
            self._lrcedt.ApplyLyrics()
            if self._lrc.changed:
                self._lrc['by'] = 'https://twitter.com/megacodist'
                self._lrc['re'] = 'https://github.com/megacodist/mp3-lyrics'
                self._lrc.Save()
    
    def _CreateLrc(self) -> None:
        if self._lrc:
            self._msgvw.AddMessage(
                title='Cannot create LRC',
                message=f"The '{self._lrc.filename}' has been loaded.",
                type=MessageType.WARNING)
        else:
            self._LoadLrc(
                self._lastFile,
                toCreate=self._lrcLoaded)
    
    def _DeleteLrc(self) -> None:
        # Insert code here to delete the LRC file...
        pLrc = Path(Lrc.GetLrcFilename(self._lastFile))
        if pLrc.exists():
            toDelete = askyesno(message='Do you want to delete the LRC?')
            if toDelete:
                pLrc.unlink()
                del self._lrc
                self._lrc = None
                self._lrcLoaded = True
                self._UpdateGui_Lrc()
    
    def _DiscardChanges(self) -> None:
        self._LoadLrc(self._lastFile)

    def _UpdateGui_Playable(self) -> None:
        self._btn_palyPause['state'] = tk.NORMAL
        self._menu_player.entryconfigure(
            'Play/pause',
            state=tk.NORMAL)

    def _UpdateGui_Pausable(self) -> None:
        pass

    def _UpdateGui_NotPlayable(self) -> None:
        self._btn_palyPause['state'] = tk.DISABLED
        self._menu_player.entryconfigure(
            'Play/pause',
            state=tk.DISABLED)
        self._SetLength(0)
        self.pos = 0
    
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
        self._infovw.PopulateMp3(self._mp3)
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
