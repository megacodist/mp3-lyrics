#
# 
#
"""
"""


from concurrent.futures._base import Future
import logging
from os import PathLike, fspath
from pathlib import Path
from pprint import pprint
import re
import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askopenfilename
from tkinter.messagebox import askyesno
from typing import Any, Literal, Type

from megacodist.keyboard import Modifiers, KeyCodes
import PIL.Image
import PIL.ImageTk

from media.abstract_mp3 import AbstractMp3, MP3NotFoundError
from app_utils import AppSettings
from asyncio_thrd import AsyncioThrd
from media import AbstractPlaylist
from media.lrc import Lrc, Timestamp
from utils.async_ops import AsyncOpManager, AsyncOp
from utils.sorted_list import SortedList, CollisionPolicy
from utils.types import (
    AppStatus,
    GifImage,
    JumpDirection,
    JumpStep,
    CopyType,
    Prefrences,
    AfterPlayed)
from widgets.ab_view import ABView
from widgets.info_view import InfoView
from widgets.lyrics_editor import LyricsEditor
from widgets.lyrics_view import LyricsView
from widgets.message_view import MessageType, MessageView
from widgets.playlist_view import PlaylistItem, PlaylistView


class Mp3LyricsWin(tk.Tk):
    def __init__(
            self,
            res_dir: str | Path,
            asyncio_thrd: AsyncioThrd,
            mp3_class: Type[AbstractMp3],
            screenName: str | None = None,
            baseName: str | None = None,
            className: str = 'Tk',
            useTk: bool = True,
            sync: bool = False,
            use: str | None = None
            ) -> None:
        super().__init__(screenName, baseName, className, useTk, sync, use)
        self.title('MP3 Lyrics')
        # Reading & applying MP3-Lyrics Window (MLW) settings...
        settings = self._ReadSettings()
        self.geometry(
            f"{settings['MLW_WIDTH']}x{settings['MLW_HEIGHT']}"
            + f"+{settings['MLW_X']}+{settings['MLW_Y']}")
        self.state(settings['MLW_STATE'])
        # Initializing attributes...
        self._Mp3Class: Type[AbstractMp3] = mp3_class
        """Specifies a class to instantiate objects bound to MP3
        processing and functionalities.
        """
        self._audio: AbstractMp3 | None = None
        """Specifies the MP3 object to perform related processing and
        functionalities.
        """
        self._lrc: Lrc | None = None
        """The LRC object associated with the current MP3 file."""
        self._playlist: PathLike | AbstractPlaylist | None = None
        """Specifies the playlist object or its path during loading the
        playlist.
        """
        self._RES_DIR = res_dir
        """Specifies the resource folder of the application."""
        self._asyncThrd = asyncio_thrd
        """Specifies the asyncio thread capable of performing operations
        related to this application.
        """
        self._status = AppStatus.NONE
        """Specifies the different statuses of the application."""
        self._TIME_OPERATIONS = 40
        """Specifies a time interval in millisecond for operations
        methods.
        """
        self._TIME_PLAYBACK: int = 30
        """Specifies a time interval in millisecond for palyback
        methods.
        """
        self._syncPTAfterID: str | None = ''
        """Specifies an after ID for synchronization of play-time
        slider with the music playback.
        """
        self._keepPTAfterID: str | None = ''
        """Specifies an after ID to keep play-time slider at a specific
        position.
        """
        self._pos: float = 0.0
        """Specifies the playback position of MP3"""
        self._ndigits: int = 2
        """Specifies number of digits after decimal point that the
        position of the playback must be rounded to.
        """
        self._afterPlayed = tk.IntVar(
            master=self,
            value=settings['MLW_AFTER_PLAYED'])
        """Specifies what to do when the playback of the current file
        finishes. Its value is integer number of AfterPlayed enumeration.
        """
        self._timestamps: SortedList[float] = SortedList(
            cp=CollisionPolicy.END)
        """The timestamps of the loaded LRC files."""
        # Loading resources...
        self._IMG_PLAY: PIL.ImageTk.PhotoImage
        self._HIMG_PLAY: PIL.Image.Image
        self._IMG_PAUSE: PIL.ImageTk.PhotoImage
        self._HIMG_PAUSE: PIL.Image.Image
        self._IMG_STOP: PIL.ImageTk.PhotoImage
        self._HIMG_STOP: PIL.Image.Image
        self._IMG_PREV: PIL.ImageTk.PhotoImage
        self._HIMG_PREV: PIL.Image.Image
        self._IMG_NEXT: PIL.ImageTk.PhotoImage
        self._HIMG_NEXT: PIL.Image.Image
        self._IMG_VOLUME: PIL.ImageTk.PhotoImage
        self._HIMG_VOLUME: PIL.Image.Image
        self._IMG_MP3: PIL.ImageTk.PhotoImage
        self._HIMG_MP3: PIL.Image.Image
        self._HIMG_CLOSE: PIL.Image.Image
        self._IMG_CLOSE: PIL.ImageTk.PhotoImage
        self._GIF_WAIT: GifImage
        self._LoadRes()
        # Initializing the rest of attributes...
        self._asyncManager = AsyncOpManager(
            self,
            self._GIF_WAIT)
        """The manager of asynchronous operations."""
        self._playlistAsyncOp: AsyncOp | None = None
        """The async op of loading playlist object."""
        self._lrcAsyncOp: AsyncOp | None = None
        """The async op of loading LRC object."""
        self._audioAsyncOp: AsyncOp | None = None
        """The async op of loading audio object."""
        self._fileInfoAsyncOp: AsyncOp | None = None
        """The async op of loading file info."""
        self._preferences = Prefrences()
        """The preferences of the application"""
        # Initializing the GUI...
        self._InitGui()
        # Applying the rest of settings...
        self._lastAudio: Path | None = settings['MLW_LAST_FILE']
        """Specifies the last played audio or maybe the current playing.
        """
        self._slider_volume.set(settings['MLW_VOLUME'])
        self._lrcedt.set_column_widths([
            settings['MLW_TS_COL_WIDTH'],
            settings['MLW_LT_COL_WIDTH']])
        self._pwin_info.sashpos(0, settings['MLW_INFO_EVENTS_WIDTH'])
        self.update_idletasks()
        self._pwin_mp3Player.sashpos(0, settings['MLW_LRC_VIEW_WIDTH'])
        # Bindings...
        self.bind(
            '<Key>',
            self._OnKeyPressed)
        self._slider_playTime.bind(
            '<ButtonPress-1>',
            self._OnPTSliderPressed)
        self._slider_playTime.bind(
            '<B1-Motion>',
            self._OnPTSliderDraged)
        self._slider_playTime.bind(
            '<ButtonRelease-1>',
            self._OnPTSliderRelease)
        self.protocol('WM_DELETE_WINDOW', self._OnWinClosing)

        # Loading last playlist & audio...
        self._LoadPlaylist(Path(settings['MLW_PLAYLIST_PATH']))
    
    def _LoadRes(self) -> None:
        # Loading 'volume.png'...
        self._HIMG_VOLUME = self._RES_DIR / 'volume.png'
        self._HIMG_VOLUME = PIL.Image.open(self._HIMG_VOLUME)
        self._HIMG_VOLUME = self._HIMG_VOLUME.resize(size=(24, 24,))
        self._IMG_VOLUME = PIL.ImageTk.PhotoImage(image=self._HIMG_VOLUME)
        # Loading 'play.png'...
        self._HIMG_PLAY = self._RES_DIR / 'play.png'
        self._HIMG_PLAY = PIL.Image.open(self._HIMG_PLAY)
        self._HIMG_PLAY = self._HIMG_PLAY.resize(size=(24, 24,))
        self._IMG_PLAY = PIL.ImageTk.PhotoImage(image=self._HIMG_PLAY)
        # Loading 'pause.png'...
        self._HIMG_PAUSE = self._RES_DIR / 'pause.png'
        self._HIMG_PAUSE = PIL.Image.open(self._HIMG_PAUSE)
        self._HIMG_PAUSE = self._HIMG_PAUSE.resize(size=(24, 24,))
        self._IMG_PAUSE = PIL.ImageTk.PhotoImage(image=self._HIMG_PAUSE)
        # Loading 'stop.png'...
        self._HIMG_STOP = self._RES_DIR / 'stop.png'
        self._HIMG_STOP = PIL.Image.open(self._HIMG_STOP)
        self._HIMG_STOP = self._HIMG_STOP.resize(size=(24, 24,))
        self._IMG_STOP = PIL.ImageTk.PhotoImage(image=self._HIMG_STOP)
        # Loading 'prev.png'...
        self._HIMG_PREV = self._RES_DIR / 'prev.png'
        self._HIMG_PREV = PIL.Image.open(self._HIMG_PREV)
        self._HIMG_PREV = self._HIMG_PREV.resize(size=(24, 24,))
        self._IMG_PREV = PIL.ImageTk.PhotoImage(image=self._HIMG_PREV)
        # Loading 'next.png'...
        self._HIMG_NEXT = self._RES_DIR / 'next.png'
        self._HIMG_NEXT = PIL.Image.open(self._HIMG_NEXT)
        self._HIMG_NEXT = self._HIMG_NEXT.resize(size=(24, 24,))
        self._IMG_NEXT = PIL.ImageTk.PhotoImage(image=self._HIMG_NEXT)
        # Loading 'mp3.png'...
        self._HIMG_MP3 = self._RES_DIR / 'mp3.png'
        self._HIMG_MP3 = PIL.Image.open(self._HIMG_MP3)
        self._HIMG_MP3 = self._HIMG_MP3.resize(size=(16, 16,))
        self._IMG_MP3 = PIL.ImageTk.PhotoImage(image=self._HIMG_MP3)
        # Loading 'close.png...
        self._HIMG_CLOSE = self._RES_DIR / 'close.png'
        self._HIMG_CLOSE = PIL.Image.open(self._HIMG_CLOSE)
        self._HIMG_CLOSE = self._HIMG_CLOSE.resize(size=(16, 16,))
        self._IMG_CLOSE = PIL.ImageTk.PhotoImage(image=self._HIMG_CLOSE)
        # Loading 'wait.gif...
        self._GIF_WAIT = GifImage(self._RES_DIR / 'wait.gif')
    
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
            self._ntbk_infoEvents,
            self._IMG_CLOSE)
        self._ntbk_infoEvents.add(
            self._msgvw,
            text='Messages')
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
            command=self._PlayPause)
        self._btn_palyPause.pack(side=tk.LEFT)
        #
        self._btn_stop = ttk.Button(
            self._frm_controls,
            image=self._IMG_STOP,
            state=tk.DISABLED,
            command=self._StopPlaying)
        self._btn_stop.pack(side=tk.LEFT)
        #
        self._sep_playerPlylst = ttk.Separator(
            self._frm_controls,
            orient=tk.VERTICAL)
        self._sep_playerPlylst.pack(
            side=tk.LEFT,
            padx=3)
        #
        self._btn_prev = ttk.Button(
            self._frm_controls,
            image=self._IMG_PREV,
            state=tk.DISABLED,
            command=self._PlayPrevAudio)
        self._btn_prev.pack(side=tk.LEFT)
        #
        self._btn_next = ttk.Button(
            self._frm_controls,
            image=self._IMG_NEXT,
            state=tk.DISABLED,
            command=self._PlayNextAudio)
        self._btn_next.pack(side=tk.LEFT)
        #
        self._sep_plylstVolume = ttk.Separator(
            self._frm_controls,
            orient=tk.VERTICAL)
        self._sep_plylstVolume.pack(
            side=tk.LEFT,
            padx=3)
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
        self._pwin_mp3Player = ttk.PanedWindow(
            master=self._notebook,
            orient=tk.HORIZONTAL)
        self._notebook.add(
            self._pwin_mp3Player,
            text='Player')
        #
        self._lrcvw = LyricsView(
            master=self._pwin_mp3Player,
            width=200)
        self._lrcvw.pack(
            side=tk.LEFT,
            fill=tk.Y)
        self._pwin_mp3Player.add(
            self._lrcvw,
            weight=1)
        # Packing PlaylistView...
        self._plvw = PlaylistView(
            self._pwin_mp3Player,
            self._LoadPlaylistIndex)
        self._pwin_mp3Player.add(
            self._plvw,
            weight=1)
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
        self._menu_app = tk.Menu(
            master=self._menubar,
            tearoff=0)
        self._menubar.add_cascade(
            label='Application',
            menu=self._menu_app)
        self._menu_app.add_command(
            label='Clear messages',
            command=self._msgvw.Clear)        
        # Creating Playlist menu...
        self._menu_playlist = tk.Menu(
            master=self._menubar,
            tearoff=0)
        self._menubar.add_cascade(
            label='Playlist',
            menu=self._menu_playlist)
        self._menu_playlist.add_command(
            label='Open an MP3...',
            accelerator='Ctrl+O',
            command=self._OpenFile)
        self._menu_playlist.add_separator()
        self._menu_playlist.add_command(
            label='Previous',
            command=self._PlayPrevAudio)
        self._menu_playlist.add_command(
            label='Next',
            command=self._PlayNextAudio)
        # Ceating 'After played' submenu...
        self._menu_afterPlayed = tk.Menu(
            master=self._menubar,
            tearoff=0)
        self._menu_afterPlayed.add_radiobutton(
            label='Stop playing',
            value=AfterPlayed.STOP.value,
            variable=self._afterPlayed)
        self._menu_afterPlayed.add_radiobutton(
            label='Loop over current audio',
            value=AfterPlayed.LOOP.value,
            variable=self._afterPlayed)
        self._menu_afterPlayed.add_radiobutton(
            label='Next audio, stop at  the end',
            value=AfterPlayed.NEXT.value,
            variable=self._afterPlayed)
        self._menu_afterPlayed.add_radiobutton(
            label='Next audio, loop at  the end',
            value=AfterPlayed.NEXT_LOOP.value,
            variable=self._afterPlayed)
        self._menu_afterPlayed.add_radiobutton(
            label='Previous audio, stop at  the beginning',
            value=AfterPlayed.PREV.value,
            variable=self._afterPlayed)
        self._menu_afterPlayed.add_radiobutton(
            label='Previous audio, loop at  the beginning',
            value=AfterPlayed.PREV_LOOP.value,
            variable=self._afterPlayed)
        
        # Creating 'Player' menu...
        self._menu_mp3Player = tk.Menu(
            master=self._menubar,
            tearoff=0)
        self._menubar.add_cascade(
            label='Player',
            menu=self._menu_mp3Player)
        self._menu_mp3Player.add_command(
            label='Play/pause',
            accelerator='Ctrl+P',
            command=self._PlayPause)
        self._menu_mp3Player.add_command(
            label='Stop',
            accelerator='Ctrl+Q',
            command=self._StopPlaying)
        self._menu_mp3Player.add_separator()
        self._menu_mp3Player.add_command(
            label='Set A',
            accelerator='Shift+A',
            command=self._SetA)
        self._menu_mp3Player.add_command(
            label='Set B',
            accelerator='Shift+B',
            command=self._SetB)
        self._menu_mp3Player.add_command(
            label='Remove A-B',
            command=self._RemoveABRepeat)
        self._menu_mp3Player.add_separator()
        self._menu_mp3Player.add_cascade(
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
        self._menu_editor = tk.Menu(
            master=self._menubar,
            tearoff=0)
        self._menubar.add_cascade(
            label='Editor',
            menu=self._menu_editor)
        self._menu_editor.add_command(
            label='Save/create LRC',
            accelerator='Ctrl+S',
            command=self._SaveCreateLrc)
        self._menu_editor.add_command(
            label='Discard changes')
        self._menu_editor.add_command(
            label='Delete LRC',
            command=self._DeleteLrc)
        self._menu_editor.add_separator()
        self._menu_editor.add_command(
            label='Select all',
            accelerator='Ctrl+A',
            command=self._lrcedt.select_all)
        self._menu_editor.add_command(
            label='Deselect',
            accelerator='Ctrl+D',
            command=self._lrcedt.Deselect)
        self._menu_editor.add_separator()
        self._menu_editor.add_command(
            label='Copy lyrics only',
            accelerator='Ctrl+C',
            command=self._lrcedt.CopyLyricsOnly)
        self._menu_editor.add_command(
            label='Copy lyrics and/or timestamps',
            accelerator='Ctrl+Shift+C',
            command=self._lrcedt.CopyLyricsTimestamps)
        self._menu_editor.add_command(
            label='Paste-override lyrics only',
            accelerator='Ctrl+U',
            command=self._lrcedt.PasreOverrideLyrics)
        self._menu_editor.add_command(
            label='Paste-insert',
            accelerator='Ctrl+I',
            command=self._lrcedt.PasteInsert)
        self._menu_editor.add_separator()
        self._menu_editor.add_cascade(
            label='Insert a row',
            menu=self._menu_insertRow)
        self._menu_editor.add_command(
            label='Clear cell(s)',
            accelerator='Del')
        self._menu_editor.add_command(
            label='Remove row(s)',
            accelerator='Shift+Del',
            command=self._lrcedt.RemoveRows)

        self.update_idletasks()
    
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
            if event.keycode == KeyCodes.C:
                self._lrcedt.CopyLyricsTimestamps()
        # Checking Alt...
        elif (event.state & Modifiers.ALT) == Modifiers.ALT:
            if event.keycode == KeyCodes.RIGHT:
                self._JumpAudio(JumpDirection.FORWARD, JumpStep.LARGE)
            elif event.keycode == KeyCodes.LEFT:
                self._JumpAudio(JumpDirection.BACKWARD, JumpStep.LARGE)
        # Checking Ctrl...
        elif (event.state & Modifiers.CONTROL) == Modifiers.CONTROL:
            # Checking Ctrl+O...
            if event.keycode == KeyCodes.O:
                self._OpenFile()
            # Checking Ctrl+K...
            elif event.keycode == KeyCodes.K:
                self._lrcedt.InsertRowAbove()
            # Checking Ctrl+L...
            elif event.keycode == KeyCodes.L:
                self._lrcedt.InsertRowBelow()
            # Checking Ctrl+S...
            elif event.keycode == KeyCodes.S:
                self._SaveCreateLrc()
            # Checking Ctrl+V...
            elif event.keycode == KeyCodes.U:
                self._lrcedt.PasreOverrideLyrics()
            # Checking Ctrl+I...
            elif event.keycode == KeyCodes.I:
                self._lrcedt.PasteInsert()
            elif event.keycode == KeyCodes.C:
                self._lrcedt.CopyLyricsOnly()
            elif event.keycode == KeyCodes.P:
                self._PlayPause()
            elif event.keycode == KeyCodes.A:
                self._lrcedt.select_all()
            elif event.keycode == KeyCodes.Q:
                self._StopPlaying()
            elif event.keycode == KeyCodes.D:
                self._lrcedt.Deselect()
            elif event.keycode == KeyCodes.RIGHT:
                self._JumpAudio(JumpDirection.FORWARD, JumpStep.SMALL)
            elif event.keycode == KeyCodes.LEFT:
                self._JumpAudio(JumpDirection.BACKWARD, JumpStep.SMALL)
        # Checking Shift...
        elif (event.state & Modifiers.SHIFT) == Modifiers.SHIFT:
            if event.keycode == KeyCodes.A:
                self._SetA()
            elif event.keycode == KeyCodes.B:
                self._SetB()
            elif event.keycode == KeyCodes.DELETE:
                self._lrcedt.RemoveRows()
            elif event.keycode == KeyCodes.RIGHT:
                self._JumpAudio(JumpDirection.FORWARD, JumpStep.MEDIUM)
            elif event.keycode == KeyCodes.LEFT:
                self._JumpAudio(JumpDirection.BACKWARD, JumpStep.MEDIUM)
        # No Alt, Ctrl, or Shift...
        else:
            if event.keycode == KeyCodes.DELETE:
                self._lrcedt.ClearCells()
            elif event.keycode == KeyCodes.F5:
                self._lrcedt.SetTimestamp(self._pos)
    
    def _CopyLyricsItem(self, type_: CopyType) -> None:
        pass
    
    def _OpenFile(self) -> None:
        """Pops up 'Browse for a file' dialog, loads the MP3 into
        the player, and also other MP3s in the folder into the Folder
        view.
        """
        from media import FilenameToPlypathAudio
        folder = fspath(self._playlist) if self._playlist else None
        filename = askopenfilename(
            title='Browse for a file',
            filetypes=[
                ('MP3 files', '*.mp3'),
                ('Playlist files', ['*.m3u8', '*.m3u']),
                ('All supported files', ['*.mp3', '*.m3u8', '*.m3u'])],
            initialdir=folder)
        if filename:
            try:
                pthPlaylist, audio = FilenameToPlypathAudio(filename)
            except ValueError:
                msg = f"'{filename}' does not represent a valid audio" \
                    ' or a playlist.'
                self._msgvw.AddMessage(
                    title='Invalid audio or playlist',
                    message=msg,
                    type_=MessageType.ERROR)
            else:
                self._lastAudio = audio
                self._LoadPlaylist(pthPlaylist)
    
    def _LoadPlaylist(self, playlist: Path,) -> None:
        """Loads the playlist and upon completion `_OnPlaylistLoaded`
        gets triggered.
        """
        # Declaring variables -----------------------------
        from utils.ops import LoadPlaylist
        # Processing --------------------------------------
        self._DisablePlaylist_Gui()
        if self._playlistAsyncOp is None:
            self._WithdrawAudio_Gui()
            # Canceling any ongoing operation...
            if self._lrcAsyncOp is not None:
                self._lrcAsyncOp.Cancel()
            if self._audioAsyncOp is not None:
                self._audioAsyncOp.Cancel()
            if self._fileInfoAsyncOp is not None:
                self._fileInfoAsyncOp.Cancel()
            # Loading new playlist...
            self._playlist = playlist
            self._playlistAsyncOp = self._asyncManager.InitiateOp(
                start_cb=LoadPlaylist,
                start_args=(playlist, self,),
                finish_cb=self._OnPlaylistLoaded,
                cancel_cb=self._OnPlaylistLoadingCanceled,
                cancel_args=(playlist,),
                widgets=(self._plvw,))
        elif not self._playlistAsyncOp.HasCanceled():
            self._playlistAsyncOp.cancelArgs = tuple([
                *self._playlistAsyncOp.cancelArgs,
                playlist])
            self._playlistAsyncOp.Cancel()
    
    def _OnPlaylistLoaded(
            self,
            future: Future[tuple[AbstractPlaylist, list[PlaylistItem]]],
            ) -> None:
        """This callback gets triggered whenever loading of the playlist
        has finished.
        """
        self._playlistAsyncOp = None
        try:
            self._playlist, items = future.result()
        except FileNotFoundError:
            self._msgvw.AddMessage(
                title='Playlist not found',
                message=f"The playlist '{self._playlist}' did not find.",
                type_=MessageType.ERROR)    
        else:
            self._plvw.Populate(items)
            self._EnablePlaylist_Gui()
            self._CheckAudioInPlaylist()
    
    def _OnPlaylistLoadingCanceled(
            self,
            old_playlist: PathLike,
            new_playlist: PathLike | None = None,
            ) -> None:
        """This callback is triggered when loading of a playlist has
        been canceled.
        """
        msg = f"Loading the playlist '{old_playlist}' was canceled."
        self._msgvw.AddMessage(message=msg)
        self._playlistAsyncOp = None
        if new_playlist is not None:
            self._LoadPlaylist(new_playlist)
    
    def _CheckAudioInPlaylist(self) -> None:
        """Checks existence of `_lastAudio` in the `_playlist`."""
        if self._lastAudio is None:
            # No audio, doing nothing...
            return
        indices = self._playlist.GetIndices(self._lastAudio)
        nIndices = len(indices)
        if nIndices == 0:
            msg = f"'{self._lastAudio}' did not find in " \
                f"'{self._playlist.Path}'"
            self._msgvw.AddMessage(
                title='Missing audio',
                message=msg,
                type_=MessageType.ERROR)
        elif nIndices > 1:
            msg = f"{nIndices} audio with the name of'{self._lastAudio}'" \
                f"was found in '{self._playlist.Path}'"
            self._msgvw.AddMessage(
                title='Duplicate audio',
                message=msg,
                type_=MessageType.ERROR)
        else:
            self._plvw.SelectedIdx = indices[0]
    
    def _LoadPlaylistIndex(self, idx: int) -> None:
        """Loads `idx`th audio from the playlist into the GUI. This
        function is called whenever an item in the playlist is
        selected.
        """
        self._lastAudio = self._playlist.GetAudio(idx)
        audio_file = self._playlist.GetFullPath(idx)
        # Stopping the audio which is already playing...
        self._LoadLrc(audio_file)
        if self._audio and self._audio.playing:
            self._StopPlaying()
            # Forcing the audio, which is pending to load, to play...
            self._status |= AppStatus.PENDING_PLAY
        self._LoadAudio(audio_file)
    
    def _LoadLrc(self, audio_file: PathLike) -> None:
        """Loads the associated LRC file of `audio_file` into the GUI
        asynchronously.
        """
        from utils.ops import LoadLrc
        pthLrc = Lrc.GetLrcFilename(audio_file)
        self._WithdrawLrc_Gui()
        if self._lrcAsyncOp is None:
            self._lrcAsyncOp = self._asyncManager.InitiateOp(
                start_cb=LoadLrc,
                start_args=(pthLrc,),
                finish_cb=self._OnLrcLoaded,
                cancel_cb=self._OnLoadingLrcCanceled,
                cancel_args=(pthLrc,),
                widgets=(self._lrcvw, self._lrcedt, self._infovw,))
        elif not self._lrcAsyncOp.HasCanceled():
            self._lrcAsyncOp.cancelArgs = tuple([
                *self._lrcAsyncOp.cancelArgs,
                pthLrc])
            self._lrcAsyncOp.Cancel()

    def _OnLrcLoaded(self, obj: Future[Lrc] | Lrc) -> None:
        """This callback must be fired whenever an LRC object is loaded
        or when the `Lrc` object has changed and we want to reflect the
        changes in the GUI.
        ."""
        self._lrcAsyncOp = None
        if isinstance(obj, Future):
            try:
                self._lrc = obj.result()
            except FileNotFoundError:
                self._msgvw.AddMessage(
                    title='No LRC',
                    message=f"No LRC file was found for '{self._lastAudio}'",
                    type_=MessageType.ERROR)
                return
        elif isinstance(obj, Lrc):
            self._lrc = obj
        else:
            logging.error('E-1-2', stack_info=True)
            return
        self._ExhibitLrc_Gui()
    
    def _OnLoadingLrcCanceled(
            self,
            old_lrc: PathLike,
            new_lrc: PathLike | None = None,
            ) -> None:
        """This callback is triggered when loading of a playlist has
        been canceled.
        """
        msg = f"Loading the LRC file '{old_lrc}' was canceled."
        self._msgvw.AddMessage(message=msg)
        self._lrcAsyncOp = None
        if new_lrc is not None:
            self._LoadLrc(new_lrc)

    def _LoadAudio(self, audio: PathLike) -> None:
        """Loads the specified audio both as an object into `_audio` and
        into the player as well.
        """
        # Declaring variables -----------------------------
        from utils.ops import LoadAudio
        # Loading audio -----------------------------------
        self._WithdrawAudio_Gui()
        if self._audioAsyncOp is None:
            self._audioAsyncOp = self._asyncManager.InitiateOp(
                start_cb=LoadAudio,
                start_args=(audio, self._Mp3Class,),
                finish_cb=self._OnAudioLoaded,
                cancel_cb=self._OnLoadingAudioCanceled,
                cancel_args=(audio,),
                widgets=(self._infovw,))
        elif not self._audioAsyncOp.HasCanceled():
            self._audioAsyncOp.cancelArgs = tuple([
                *self._audioAsyncOp.cancelArgs,
                audio])
            self._audioAsyncOp.Cancel()

    def _OnAudioLoaded(self, future: Future[AbstractMp3]) -> None:
        self._audioAsyncOp = None
        self._audio = future.result()
        self._ExhibitAudio_Gui()
        if self._status & AppStatus.PENDING_PLAY:
            self._status &= (~AppStatus.PENDING_PLAY)
            self._PlayPause()
    
    def _OnLoadingAudioCanceled(
            self,
            old_audio: PathLike,
            new_audio: PathLike| None = None,
            ) -> None:
        msg = f"Loading the audio '{old_audio}' was canceled."
        self._msgvw.AddMessage(msg)
        self._audioAsyncOp = None
        if new_audio:
            self._LoadAudio(new_audio)
    
    def _LoadFileInfo(self) -> dict[str, Any]:
        pass

    def _OnFileInfoLoaded(self, future: Future[dict[str, Any]]) -> None:
        pass

    def _SyncPTSlider(self) -> None:
        try:
            self._pos = self._audio.pos
            self._ShowAudioPos_Gui(self._pos)
        except ValueError:
            logging.error(
                f"There was a problem converting {self._pos}"
                + f" to a {Timestamp} object")
        # Checking whether the MP3 has finished or not...
        if not self._audio.playing:
            # The MP3 finished, deciding on the action...
            self._DecideAfterPlayed()
            return
        # Looking for A-B repeat...
        if self._abvw.IsSet() and (not self._abvw.IsInside(self._pos)):
            # The A-B repeat is set & slider is outside of it...
            self._SeekAudio(self._abvw.a)
        else:
            # The MP3 not finished
            # Updating Play Time slider...
            self._slider_playTime.set(self._pos)
        # Highlighting the current lyrics...
        _, idx = self._timestamps.index(self._pos)
        try:
            self._lrcvw.Highlight(idx - 1)
        except TypeError:
            msg = '\n'.join((
                'E-2-1',
                repr(self._timestamps),
                f"idx: {idx}"))
            logging.error('\n'.join(msg), stack_info=True)
            print(msg)
        self._syncPTAfterID = self.after(
            self._TIME_PLAYBACK,
            self._SyncPTSlider)
    
    def _KeepPTSliderAt(self, __pos: float, /) -> None:
        """Keeps play-time slider at the specified position."""
        self._slider_playTime.set(__pos)
        self._keepPTAfterID = self.after(
            self._TIME_PLAYBACK,
            self._KeepPTSliderAt,
            __pos)
    
    def _StopSyncingPTSlider(self) -> None:
        """Stops updating play-time slider. That is it removes any schedule
        of _SyncPTSlider method from Tkinter event loop and sets
        _syncPTAfterID to None.
        """
        self.after_cancel(self._syncPTAfterID)
        del self._syncPTAfterID
        self._syncPTAfterID = None
    
    def _GetMp3PosBySiderX(self, x: int) -> int:
        """Returns the offset of the MP3 by the X coordinate of the Play Time
        slider. For MP3 files this offset must be a whole second, without any
        fraction, to be suitable for playback.
        """
        return round(
            x * self._slider_playTime['to']
            / self._slider_playTime.winfo_width())
    
    def _OnPTSliderDraged(self, event: tk.Event) -> None:
        """Triggered when play-time slider dragged."""
        # Defining a new position for play-time slider to stick to...
        pos = self._GetMp3PosBySiderX(event.x)
        self.after_cancel(self._keepPTAfterID)
        self._keepPTAfterID = self.after(
            self._TIME_OPERATIONS,
            self._KeepPTSliderAt,
            pos)
        # Updating the GUI & the playback...
        self._SeekAudio(pos)
    
    def _OnPTSliderPressed(self, event: tk.Event) -> None:
        # Stoping syncing of play-time slider...
        if self._audio:
            self._SeekAudio(self._GetMp3PosBySiderX(event.x))
            if self._audio.playing:
                self._StopSyncingPTSlider()
        # Sticking play-time slider at this position...
        self._keepPTAfterID = self.after(
            self._TIME_PLAYBACK,
            self._KeepPTSliderAt,
            self._GetMp3PosBySiderX(event.x))
        # Detecting A-B repeat changes...
        if event.state & Modifiers.CONTROL == Modifiers.CONTROL:
            self._abvw.a = self._GetMp3PosBySiderX(event.x)
        elif event.state & Modifiers.ALT == Modifiers.ALT:
            self._abvw.b = self._GetMp3PosBySiderX(event.x)
    
    def _OnPTSliderRelease(self, event: tk.Event) -> None:
        # Removing _KeepPTSliderAt schedule from Tkinter event loop...
        self.after_cancel(self._keepPTAfterID)
        del self._keepPTAfterID
        self._keepPTAfterID = None
        # Updating the GUI & the playback...
        pos = self._GetMp3PosBySiderX(event.x)
        self._SeekAudio(pos)
        if self._audio and self._audio.playing:
            self._syncPTAfterID = self.after(
                self._TIME_PLAYBACK,
                self._SyncPTSlider)
    
    def _DecideAfterPlayed(self) -> None:
        match self._afterPlayed.get():
            case AfterPlayed.STOP.value:
                self._StopPlaying()
            case AfterPlayed.LOOP.value:
                self._SeekAudio(0.0)
                self._audio.Play()
                self._syncPTAfterID = self.after(
                    self._TIME_PLAYBACK,
                    self._SyncPTSlider)
            case AfterPlayed.NEXT.value:
                self._PlayNextAudio(loop=False, pending_play=True)
            case AfterPlayed.NEXT_LOOP.value:
                self._PlayNextAudio(loop=True, pending_play=True)
            case AfterPlayed.PREV.value:
                self._PlayPrevAudio(loop=False, pending_play=True)
            case AfterPlayed.PREV_LOOP.value:
                self._PlayPrevAudio(loop=True, pending_play=True)

    def _PlayPause(self) -> None:
        if self._audio is None:
            self._msgvw.AddMessage(
                message='No audio has been loaded to play/pause',
                title='Play/pause audio',
                type_=MessageType.ERROR)
            return
        # Checking if the MP3 is palying or not...
        if self._audio.playing:
            # The audio is playing...
            self._btn_palyPause['image'] = self._IMG_PLAY
            self._audio.Pause()
            self._StopSyncingPTSlider()
        else:
            # The audio is not playing...
            self._btn_palyPause['image'] = self._IMG_PAUSE
            pos = round(self._slider_playTime.get())
            self._slider_playTime.set(pos)
            self._audio.pos = pos
            self._audio.Play()
            # Updating play-time slider...
            self._syncPTAfterID = self.after(
                self._TIME_PLAYBACK,
                self._SyncPTSlider)
    
    def _StopPlaying(self) -> None:
        """Stops the playback of the loaded audio and reflects it in
        the GUI.
        """
        if self._audio is None:
            self._msgvw.AddMessage(
                message='No audio has been loaded to stop',
                title='Stop audio',
                type_=MessageType.ERROR)
            return
        if self._audio.playing:
            self._StopSyncingPTSlider()
        self._audio.Stop()
        self._pos = 0.0
        self._ShowAudioPos_Gui(0.0)
        self._btn_palyPause['image'] = self._IMG_PLAY
        self._RemoveABRepeat()

    def _SeekAudio(self, __pos: float, /) -> None:
        """Seeks the playback of the audio to the specified position
        and updating GUI to reflect the new position.
        """
        self._audio.pos = __pos
        self._pos = __pos
        self._ShowAudioPos_Gui(__pos)
    
    def _JumpAudio(
            self,
            direction: JumpDirection,
            step: JumpStep,
            ) -> None:
        """Jumps the audio either forward or backward, with the specified
        step.
        """
        if step == JumpStep.SMALL:
            offset = self._preferences.smallJumpForward
        elif step == JumpStep.MEDIUM:
            offset = self._preferences.mediumJumpForward
        elif step == JumpStep.LARGE:
            offset = self._preferences.largeJumpForward
        else:
            logging.error(f"Invalid jump stem: '{step}'")
            return
        if direction == JumpDirection.FORWARD:
            pos = self._pos + offset
            if pos > self._audio.Duration:
                pos = self._audio.Duration
        elif direction == JumpDirection.BACKWARD:
            pos = self._pos - offset
            if pos < 0.0:
                pos = 0.0
        else:
            logging.error(f"Invalid jump direction: '{direction}'")
            return
        self._SeekAudio(pos)
    
    def _PlayNextAudio(
            self,
            loop: bool = False,
            pending_play: bool = False,
            ) -> None:
        """Plays next audio in the playlist. If the playlist reaches to
        the end, it stops playing unless `loop` is set to `True` which
        forces to play from the start of the playlist. If `pending_play`
        is set to `True`; the new selected audio, if any, will be marked
        to play.
        """
        if not isinstance(loop, bool):
            raise TypeError("'loop' argument must be 'bool', given "\
                f"'{type(loop)}'")
        # Selecting next audio in the playlist view...
        nItems = self._plvw.ItemsCount
        idx = self._plvw.SelectedIdx
        idx += 1
        if idx >= nItems:
            if loop:
                idx = 0
            else:
                return
        if pending_play:
            self._status |= AppStatus.PENDING_PLAY
        self._plvw.SelectedIdx = idx
    
    def _PlayPrevAudio(
            self,
            loop: bool = False,
            pending_play: bool = False,
            ) -> None:
        """Plays previous audio in the playlist. If the playlist reaches
        to the beginning, it stops playing unless `loop` is set to `True`
        which forces to play from the end of the playlist. If `pending_play`
        is set to `True`; the new selected audio, if any, will be marked
        to play.
        """
        if not isinstance(loop, bool):
            raise TypeError("'loop' argument must be 'bool', given "\
                f"'{type(loop)}'")
        # Selecting previous audio in the playlist view...
        nItems = self._plvw.ItemsCount
        idx = self._plvw.SelectedIdx
        idx -= 1
        if idx < 0:
            if loop:
                idx = nItems - 1
            else:
                return
        if pending_play:
            self._status |= AppStatus.PENDING_PLAY
        self._plvw.SelectedIdx = idx
    
    def _ChangeVolume(self, value: str) -> None:
        if self._audio:
            self._audio.volume = float(value) * 10
    
    def _ReadSettings(self) -> None:
        # Considering MP3 Lyrics Window (MLW) default settings...
        defaults = {
            'MLW_WIDTH': 900,
            'MLW_HEIGHT': 600,
            'MLW_X': 200,
            'MLW_Y': 200,
            'MLW_STATE': 'normal',
            'MLW_LAST_FILE': Path('res/Tarantella abballa abballa.mp3'),
            'MLW_PLAYLIST_PATH': '.',
            'MLW_VOLUME': 5.0,
            'MLW_TS_COL_WIDTH': 150,
            'MLW_LT_COL_WIDTH': 300,
            'MLW_AFTER_PLAYED': 0,
            'MLW_INFO_EVENTS_WIDTH': 200,
            'MLW_LRC_VIEW_WIDTH': 200,}
        return AppSettings().Read(defaults)

    def _OnWinClosing(self) -> None:
        # Closing the MP3 file...
        if self._audio:
            self._audio.Close()
        # Saving LRC if changed...
        if self._audio and self._lrcedt.HasChanged():
            toSave = askyesno(message='Do you want to save the LRC?')
            if toSave:
                self._SaveCreateLrc(exhibit_gui=False)
        # Saving settings...
        settings: dict[str, Any] = {}
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
        settings['MLW_LAST_FILE'] = self._lastAudio
        if self._playlist:
            settings['MLW_PLAYLIST_PATH'] = fspath(self._playlist)
        settings['MLW_VOLUME'] = self._slider_volume.get()
        colsWidth = self._lrcedt.get_column_widths()
        settings['MLW_TS_COL_WIDTH'] = colsWidth[0]
        settings['MLW_LT_COL_WIDTH'] = colsWidth[1]
        settings['MLW_AFTER_PLAYED'] = self._afterPlayed.get()
        settings['MLW_INFO_EVENTS_WIDTH'] = self._pwin_info.sashpos(0)
        settings['MLW_LRC_VIEW_WIDTH'] = self._pwin_mp3Player.sashpos(0)
        # Saving settings...
        AppSettings().Update(settings)
        # Closing images...
        self._HIMG_VOLUME.close()
        self._HIMG_MP3.close()
        self._HIMG_PAUSE.close()
        self._HIMG_PLAY.close()
        self._HIMG_STOP.close()
        self._HIMG_PREV.close()
        self._HIMG_NEXT.close()
        self._HIMG_CLOSE.close()
        del self._GIF_WAIT

        self.destroy()
    
    def _RemoveABRepeat(self) -> None:
        if self._audio is not None:
            self._abvw.a = 0.0
            self._abvw.b = self._audio.Duration
            self._abvw.length = self._audio.Duration
        else:
            self._abvw.Reset()
    
    def _SetA(self) -> None:
        self._abvw.a = self._pos
    
    def _SetB(self) -> None:
        self._abvw.b = self._pos
    
    def _SaveCreateLrc(self, exhibit_gui: bool = True) -> None:
        """Saves the LRC or creates an LRC object. `exhibit_gui` specifies
        whether the saved LRC must be reflected in the GUI.
        """
        if self._audio and self._lrcedt.HasChanged():
            if self._lrc is None:
                lrcFilename = Lrc.GetLrcFilename(self._audio.Filename)
                Lrc.CreateLrc(lrcFilename)
                self._lrc = Lrc(lrcFilename, True, True)
            self._lrc.lyrics = self._lrcedt.GetAllLyricsItems()
            self._lrc['by'] = 'https://twitter.com/megacodist'
            self._lrc['re'] = 'https://github.com/megacodist/mp3-lyrics'
            self._lrc.Save()
            if exhibit_gui:
                self._timestamps.clear()
                self._OnLrcLoaded(self._lrc)
        elif self._audio:
            self._msgvw.AddMessage(
                title='Save/create command',
                message='No change has been made in the lyrics editor.',
                type_=MessageType.INFO)
        else:
            msg = 'No audio is loaded to save these lyrics for it.'
            self._msgvw.AddMessage(msg, type_=MessageType.ERROR)
    
    def _DeleteLrc(self) -> None:
        # Insert code here to delete the LRC file...
        pLrc = Path(Lrc.GetLrcFilename(self._lastAudio))
        if pLrc.exists():
            toDelete = askyesno(message='Do you want to delete the LRC?')
            if toDelete:
                pLrc.unlink()
                del self._lrc
                self._lrc = None
                self._ExhibitLrc_Gui()
    
    def _DiscardChanges(self) -> None:
        if self._lrc and self._lrcedt.HasChanged():
            toDiscard = askyesno(
                title='Discard LRC changes',
                message='Do you want to discard LRC changes?')
            if toDiscard:
                self._LoadLrc(self._audio.Filename)
        elif self._lrc:
            self._msgvw.AddMessage(
                title='No changes',
                message=f"No changes were found in '{self._lrc.filename}'.",
                type_=MessageType.WARNING)
        else:
            self._msgvw.AddMessage(
                title='No LRC',
                message="No LRC file was loaded to revert to.",
                type_=MessageType.WARNING)

    def _ShowAudioLength_Gui(self, __leng: float) -> None:
        """Shows the length of the audio in the GUI."""
        timestamp = Timestamp.FromFloat(__leng, ndigits=self._ndigits)
        self._lbl_lengthMin['text'] = str(timestamp.minutes)
        self._lbl_lengthSec['text'] = str(timestamp.seconds)
        # Ensuring that milisecond part has two digits...
        length = str(timestamp.milliseconds)[2:]
        if len(length) == 1:
            length += '0'
        self._lbl_lengthMilli['text'] = length

    def _ExhibitAudio_Gui(self) -> None:
        """Makes the player section of the GUI ready to play."""
        self._btn_palyPause['state'] = tk.NORMAL
        self._menu_mp3Player.entryconfigure(
            'Play/pause',
            state=tk.NORMAL)
        self._btn_stop.config(state=tk.NORMAL)
        self._menu_mp3Player.entryconfigure(
            'Stop',
            state=tk.NORMAL)
        self._slider_playTime.config(state='enable')
        self._audio.volume = self._slider_volume.get() * 10
        self._slider_playTime['to'] = self._audio.Duration
        self._ShowAudioLength_Gui(self._audio.Duration)
        self._abvw.length = self._audio.Duration
        self._abvw.b = self._abvw.length
        self._audio.pos = 0.0
        self._pos = 0.0
        self._ShowAudioPos_Gui(0.0)
        self.title(f'{Path(self._lastAudio).name} - MP3 Lyrics')
        self._infovw.PopulateAudioInfo(self._audio)

    def _WithdrawAudio_Gui(self) -> None:
        """Withdraws the audio from the GUI so PLAYER will be disables."""
        self._btn_palyPause['state'] = tk.DISABLED
        self._menu_mp3Player.entryconfigure(
            'Play/pause',
            state=tk.DISABLED)
        self._btn_stop.config(state=tk.DISABLED)
        self._menu_mp3Player.entryconfigure(
            'Stop',
            state=tk.DISABLED)
        self._pos = 0.0
        self._ShowAudioPos_Gui(0.0)
        self._ShowAudioLength_Gui(0.0)
        self._slider_playTime.config(state='disable')
        self.title('MP3 Lyrics')
        self._infovw.ClearAudioInfo()
        self._audio = None
    
    def _WithdrawLrc_Gui(self) -> None:
        """Withdraws the loaded LRC object from the GUI and unload
        the LRC object from the application.
        """
        if self._audio and self._lrcedt.HasChanged():
            toSave = askyesno(
                title='Unsaved lyrics',
                message='Do you want to save/create the lyrics?')
            if toSave:
                self._SaveCreateLrc(exhibit_gui=False)
        self._timestamps.clear()
        self._lrcvw.Clear()
        self._lrcedt.ClearContent()
        self._lrcedt.SetChangeOrigin()
        self._infovw.ClearLrcInfo()
        self._lrc = None
    
    def _ExhibitLrc_Gui(self) -> None:
        """Updates the GUI to show the content of the loaded `_lrc`.
        This method must not be called until an LRC file successfully
        loaded.
        """
        # Populating the lyrics view...
        self._timestamps.clear()
        allLyrics = [li.text for li in self._lrc.lyrics]
        if self._lrc.AreTimstampsOk():
            self._lrcvw.Populate(allLyrics, True)
            self._timestamps.merge([
                lrcItem.timestamp.ToFloat()
                for lrcItem in self._lrc.lyrics])
        else:
            self._lrcvw.Populate(allLyrics, False)
        # Populating the lyrics editor...
        self._lrcedt.Populate(self._lrc.lyrics)
        self._lrcedt.SetChangeOrigin()
        # Populating the info view...
        self._infovw.PopulateLrcInfo(self._lrc)
        # Adding a message if necessary...
        if self._lrc.errors:
            message = [
                str(idx) + '. ' + error
                for idx, error in enumerate(self._lrc.GetErrors(), 1)]
            message.insert(0, str(self._lrc.filename) + '\n')
            self._msgvw.AddMessage(
                title='LRC error',
                message='\n'.join(message),
                type_=MessageType.WARNING)

    def _ShowAudioPos_Gui(self, __pos: float, /) -> None:
        """Reflects the provided value in the play-time slider and clock.
        """
        # Updating the play-time slider...
        self._slider_playTime.set(__pos)
        # Updating the play-time clock...
        try:
            timestamp = Timestamp.FromFloat(__pos, ndigits=self._ndigits)
        except ValueError:
            # The argument was negative, replacing 0.0...
            timestamp = Timestamp.FromFloat(0.0)
        self._lbl_posMin['text'] = str(timestamp.minutes)
        self._lbl_posSec['text'] = str(timestamp.seconds)
        self._lbl_posMilli['text'] = str(timestamp.milliseconds)[2:]

    def _EnablePlaylist_Gui(self) -> None:
        """Enables the playlist GUI."""
        self._btn_prev.config(state=tk.NORMAL)
        self._menu_playlist.entryconfigure(
            'Previous',
            state=tk.NORMAL)
        self._btn_next.config(state=tk.NORMAL)
        self._menu_playlist.entryconfigure(
            'Next',
            state=tk.NORMAL)
    
    def _DisablePlaylist_Gui(self) -> None:
        """Disables the playlist GUI."""
        self._btn_prev.config(state=tk.DISABLED)
        self._menu_playlist.entryconfigure(
            'Previous',
            state=tk.DISABLED)
        self._btn_next.config(state=tk.DISABLED)
        self._menu_playlist.entryconfigure(
            'Next',
            state=tk.DISABLED)
