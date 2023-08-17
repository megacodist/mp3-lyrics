#
# 
#
"""
"""


from concurrent.futures import CancelledError
import logging
from pathlib import Path
import re
import tkinter as tk
from tkinter import PhotoImage, ttk
from tkinter.filedialog import askopenfilename
from tkinter.messagebox import askyesno
from typing import Type

from megacodist.keyboard import Modifiers, KeyCodes
import PIL.Image
import PIL.ImageTk

from media.abstract_mp3 import AbstractMP3, MP3NotFoundError
from app_utils import AppSettings
from asyncio_thrd import AsyncioThrd
from media import AbstractPlaylist
from media.lrc import Lrc, Timestamp
from utils.async_ops import AfterOpManager
from utils.sorted_list import SortedList
from widgets.ab_view import ABView
from widgets.folder_view import FolderView
from widgets.info_view import InfoView
from widgets.lyrics_editor import LyricsEditor
from widgets.lyrics_view import LyricsView
from widgets.message_view import MessageType, MessageView
from widgets.playlist_view import PlaylistItem, PlaylistView
from widgets.wait_frame import WaitFrame
from win_utils import LoadingFolderAfterInfo, LoadingLrcAfterInfo
from win_utils import AfterPlayed


class Mp3LyricsWin(tk.Tk):
    def __init__(
            self,
            res_dir: str | Path,
            asyncio_thrd: AsyncioThrd,
            mp3_class: Type[AbstractMP3],
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

        self._Mp3Class: Type[AbstractMP3] = mp3_class
        """Specifies a class to instantiate objects bound to MP3
        processing and functionalities.
        """
        self._mp3: AbstractMP3 | None = None
        """Specifies the MP3 object to perform related processing and
        functionalities.
        """
        self._lrc: Lrc | None = None
        """The LRC object associated with the current MP3 file."""
        self._playlist: AbstractPlaylist | None = None
        """The playlist object."""
        self._RES_DIR = res_dir
        """Specifies the resource folder of the application."""
        self._asyncThrd = asyncio_thrd
        """Specifies the asyncio thread capable of performing operations
        related to this application.
        """
        self._isPlaying: bool = False
        """Specifies whether the MP3 is playing or not."""
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
        self._loadingFolder: LoadingFolderAfterInfo | None = None
        self._loadingLrc: LoadingLrcAfterInfo | None = None

        self._afterPlayed = tk.IntVar(
            master=self,
            value=settings['MLW_AFTER_PLAYED'])
        """Specifies what to do when the playback of the current file
        finishes. Its value is integer number of AfterPlayed enumeration.
        """
        self._lrcLoaded: bool = False
        """Specifies whether the LRC file has been loaded or not. This flag
        in conjuction with _lrc object can determine whether the LRC file
        exists or not.
        """

        self._timestamps: SortedList[float] = SortedList()

        self._IMG_PLAY: PIL.ImageTk.PhotoImage
        self._HIMG_PLAY: PIL.Image.Image
        self._IMG_PAUSE: PIL.ImageTk.PhotoImage
        self._HIMG_PAUSE: PIL.Image.Image
        self._IMG_VOLUME: PIL.ImageTk.PhotoImage
        self._HIMG_VOLUME: PIL.Image.Image
        self._IMG_MP3: PIL.ImageTk.PhotoImage
        self._HIMG_MP3: PIL.Image.Image
        self._GIF_WAIT: list[PIL.ImageTk.PhotoImage]
        self._HGIF_WAIT: PIL.Image.Image

        self._LoadRes()
        self._afterManager = AfterOpManager(self, self._GIF_WAIT)
        """The manager of asynchronous operations."""
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
        self.protocol('WM_DELETE_WINDOW', self._OnClosingWin)

        # Loading last playlist & audio...
        self._OpenPlaylistAudio(
            #settings['MLW_PLAYLIST_PATH'],
            Path('.'),
            self._lastAudio)
    
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
        # Loading 'mp3.png'...
        self._HIMG_MP3 = self._RES_DIR / 'mp3.png'
        self._HIMG_MP3 = PIL.Image.open(self._HIMG_MP3)
        self._HIMG_MP3 = self._HIMG_MP3.resize(size=(16, 16,))
        self._IMG_MP3 = PIL.ImageTk.PhotoImage(image=self._HIMG_MP3)
        # Loading 'wait.gif...
        self._HGIF_WAIT = self._RES_DIR / 'wait.gif'
        self._HGIF_WAIT = PIL.Image.open(self._HGIF_WAIT)
        self._GIF_WAIT: list[PhotoImage] = []
        idx = 0
        while True:
            try:
                self._HGIF_WAIT.seek(idx)
                self._GIF_WAIT.append(
                    PIL.ImageTk.PhotoImage(image=self._HGIF_WAIT))
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
            command=self._PlayPause)
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
        self._plyvw = PlaylistView(
            master=self._pwin_mp3Player,
            template_dir=self._RES_DIR,
            template_name='playlist.html')
        self._pwin_mp3Player.add(
            self._plyvw,
            weight=1)
        
        """#
        self._frm_mp3s = ttk.Frame(
            master=self._pwin_mp3Player)
        self._frm_mp3s.columnconfigure(
            index=0,
            weight=1)
        self._frm_mp3s.rowconfigure(
            index=0,
            weight=1)
        self._frm_mp3s.pack(
            side=tk.RIGHT,
            fill=tk.Y)
        self._pwin_mp3Player.add(
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
            sticky=tk.NSEW)"""
        
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
            accelerator='Ctrl+A',
            command=self._SetA)
        self._menu_mp3Player.add_command(
            label='Set B',
            accelerator='Ctrl+B',
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
            pass
        # Checking Alt...
        elif (event.state & Modifiers.ALT) == Modifiers.ALT:
            pass
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
            elif event.keycode == KeyCodes.P:
                self._PlayPause()
            elif event.keycode == KeyCodes.A:
                self._SetA()
            elif event.keycode == KeyCodes.B:
                self._SetB()
            elif event.keycode == KeyCodes.Q:
                self._StopPlaying()
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
    
    @property
    def pos(self) -> float:
        """Gets or sets the position of the MP3."""
        return self._pos

    @pos.setter
    def pos(self, __pos: float, /) -> None:
        self._pos = __pos
        timestamp = Timestamp.FromFloat(__pos, ndigits=self._ndigits)
        self._lbl_posMin['text'] = str(timestamp.minutes)
        self._lbl_posSec['text'] = str(timestamp.seconds)
        self._lbl_posMilli['text'] = str(timestamp.milliseconds)[2:]
    
    def _InitPlayer(self, mp3File: str) -> None:
        # Declaring variables -----------------------------
        exceptionOccurred: bool = True
        # Starting ----------------------------------------
        try:
            self._UpdateGui_NotPlayable()
            if self._mp3:
                self._mp3.Close()
            self._mp3: AbstractMP3 = self._Mp3Class(
                mp3File,
                self._asyncThrd.loop)
            self._mp3.volume = self._slider_volume.get() * 10
            self._slider_playTime['to'] = self._mp3.Duration
            self._SetLength(self._mp3.Duration)
            self._abvw.length = self._mp3.Duration
            self._abvw.b = self._abvw.length
            self.pos = 0
            self._lastAudio = mp3File
            exceptionOccurred = False
        except FileNotFoundError:
            self._msgvw.AddMessage(
                title='File not found',
                message=f"'{mp3File}' did not found.",
                type=MessageType.ERROR)
        except MP3NotFoundError:
            self._msgvw.AddMessage(
                title='MP3 not found',
                message=f"'{mp3File}' is not a valid MP3 file.",
                type=MessageType.ERROR)
        else:
            self.title(f'{Path(self._lastAudio).name} - MP3 Lyrics')
            self._UpdateGui_Playable()
            self._LoadLrc(mp3File)
        finally:
            if exceptionOccurred:
                self.title('MP3 Lyrics')
    
    def _SetLength(self, __leng: float) -> None:
        """Shows the length of the MP3 in the GUI."""
        timestamp = Timestamp.FromFloat(__leng, ndigits=self._ndigits)
        self._lbl_lengthMin['text'] = str(timestamp.minutes)
        self._lbl_lengthSec['text'] = str(timestamp.seconds)
        # Ensuring that milisecond part has two digits...
        length = str(timestamp.milliseconds)[2:]
        if len(length) == 1:
            length += '0'
        self._lbl_lengthMilli['text'] = length
    
    def _OpenFile(self) -> None:
        """Pops up 'Browse for a file' dialog, loads the MP3 into
        the player, and also other MP3s in the folder into the Folder
        view.
        """
        from media import FilenameToPlypathAudio
        if self._lastAudio:
            folder = str(Path(self._lastAudio).resolve().parent)
        else:
            folder = None
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
                    type=MessageType.ERROR)
            else:
                self._OpenPlaylistAudio(pthPlaylist, audio)
    
    def _OpenPlaylistAudio(
            self,
            playlist: Path,
            audio: Path | None
            ) -> None:
        # Declaring variables -----------------------------
        from functools import partial
        from utils.ops import LoadPlaylist
        # Processing --------------------------------------
        self._lastAudio = audio
        # Populating the playlistview...
        self._afterManager.InitiateOp(
            start_callback=partial(
                LoadPlaylist,
                playlist,
                self),
            finished_callback=self._PopulatePlaylist)
        #self._InitPlayer(filename)
        #self._LoadFolder(filename)
    
    def _PopulatePlaylist(
            self,
            args: tuple[AbstractPlaylist, list[PlaylistItem]],
            ) -> None:
        playlist = args[0]
        items = args[1]
        self._playlist = playlist
        self._plyvw.Populate(items)
    
    def _LoadFolder(self, folder: str) -> None:
        # Stopping dir observing...
        if self._dirObserver:
            self._dirObserver.stop()
            self._dirObserver.join()
        # Loading new dir...
        future = self._asyncThrd.LoadFolder(
            folder,
            key=FolderView.GetComparer)
        waitFrame = WaitFrame(
            master=self._foldervw,
            wait_gif=self._GIF_WAIT,
            cancel_callback=self._LoadFolder_cancel)
        afterID = self.after(
            self._TIME_OPERATIONS,
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
                # Populating the FolderView...
                self._foldervw.AddFilenames(
                    folderInfo.folder,
                    folderInfo.mp3s,
                    folderInfo.selectIdx)
            finally:
                del self._loadingFolder
                self._loadingFolder = None
        else:
            self._loadingFolder.afterID = self.after(
                self._TIME_OPERATIONS,
                self._LoadFolder_after)
    
    def _LoadFolder_cancel(self) -> None:
        self._loadingFolder.future.cancel()
        self.after_cancel(self._loadingFolder.afterID)
        self.after(
            self._TIME_OPERATIONS,
            self._LoadFolder_cancel_after)
    
    def _LoadFolder_cancel_after(self) -> None:
        if not self._loadingFolder.future.cancelled():
            self.after(
                self._TIME_OPERATIONS,
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
                self._TIME_OPERATIONS,
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
                self._lrcLoaded = True
                self._lrc = self._loadingLrc.future.result()
                self._lrc.toSaveNoTimestamps = True
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
                self._TIME_OPERATIONS,
                self._LoadLrc_after)
    
    def _LoadLrc_cancel(
            self,
            mp3_file: str | None = None
            ) -> None:
        self._loadingLrc.CancelWaitFrames()
        self._loadingLrc.future.cancel()
        self.after_cancel(self._loadingLrc.afterID)
        self.after(
            self._TIME_OPERATIONS,
            self._LoadLrc_cancel_after,
            mp3_file)
    
    def _LoadLrc_cancel_after(
            self,
            mp3_file: str | None = None
            ) -> None:
        if not self._loadingLrc.future.cancelled():
            self.after(
                self._TIME_OPERATIONS,
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
        if self._mp3:
            self._mp3.volume = float(value) * 10
    
    def _PlayPause(self) -> None:
        # Checking if the MP3 is palying or not...
        self._isPlaying = not self._isPlaying
        if self._isPlaying:
            # The MP3 is playing...
            self._btn_palyPause['image'] = self._IMG_PAUSE
            pos = round(self._slider_playTime.get())
            self._slider_playTime.set(pos)
            self._mp3.pos = pos
            self._mp3.Play()
            # Updating play-time slider...
            self._syncPTAfterID = self.after(
                self._TIME_PLAYBACK,
                self._SyncPTSlider)
        else:
            # The MP3 is not playing...
            self._btn_palyPause['image'] = self._IMG_PLAY
            self._mp3.Pause()
            self._StopSyncingPTSlider()
    
    def _SyncPTSlider(self) -> None:
        try:
            self.pos = self._mp3.pos
        except ValueError:
            logging.error(
                f"There was a problem converting {self._pos}"
                + f" to a {str(Timestamp.__class__)} object")
        # Checking whether the MP3 has finished or not...
        if not self._mp3.playing:
            # The MP3 finished, deciding on the action...
            self._DecideAfterPlayed()
            return
        # Looking for A-B repeat...
        if self._abvw.IsSet() and (not self._abvw.IsInside(self._pos)):
            # The A-B repeat is set & slider is outside of it...
            self._MoveMp3To(self._abvw.a)
        else:
            # The MP3 not finished
            # Updating Play Time slider...
            self._slider_playTime.set(self._pos)
        # Highlighting the current lyrics...
        _, idx = self._timestamps.index(self._pos)
        self._lrcvw.Highlight(idx - 1)
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
    
    def _MoveMp3To(self, __pos: float, /) -> None:
        """Moves the play-time slider to the specified position
        and also the playback of MP3 if playing."""
        self._slider_playTime.set(__pos)
        self._mp3.pos = __pos
    
    def _DecideAfterPlayed(self) -> None:
        match self._afterPlayed.get():
            case int(AfterPlayed.STOP_PLAYING):
                self._StopPlaying()
            case int(AfterPlayed.REPEAT):
                self._MoveMp3To(0.0)
                self._mp3.Play()
                self._syncPTAfterID = self.after(
                    self._TIME_PLAYBACK,
                    self._SyncPTSlider)
            case int(AfterPlayed.PLAY_FOLDER):
                self._mp3.Close()
                # Place code to play next MP3 in the folder...
                pass
            case int(AfterPlayed.REPEAT_FOLDER):
                self._mp3.Close()
                # Place code to play next MP3 in the folder...
                pass
    
    def _StopPlaying(self) -> None:
        self._btn_palyPause['image'] = self._IMG_PLAY
        if self._isPlaying:
            self._isPlaying = False
            self._mp3.Stop()
            self._slider_playTime.set(0.0)
            self._RemoveABRepeat()
            self._StopSyncingPTSlider()
    
    def _GetMp3PosBySiderX(self, x: int) -> int:
        """Returns the offset of the MP3 by the X coordinate of the Play Time
        slider. For MP3 files this offset must be a whole second, without any
        fraction, to be suitable for playback.
        """
        return round(
            x * self._slider_playTime['to']
            / self._slider_playTime.winfo_width())
    
    def _OnPTSliderDraged(self, event: tk.Event) -> None:
        """Triggers when play-time slider dragged."""
        # Defining a new position for play-time slider to stick to...
        pos = self._GetMp3PosBySiderX(event.x)
        self.after_cancel(self._keepPTAfterID)
        self._keepPTAfterID = self.after(
            self._TIME_OPERATIONS,
            self._KeepPTSliderAt,
            pos)
        # Updating the GUI & the playback...
        self._MoveMp3To(pos)
    
    def _OnPTSliderPressed(self, event: tk.Event) -> None:
        # Stoping syncing of play-time slider...
        if self._isPlaying:
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
        self._MoveMp3To(pos)
        if self._isPlaying:
            self._syncPTAfterID = self.after(
                self._TIME_PLAYBACK,
                self._SyncPTSlider)
    
    def _ReadSettings(self) -> None:
        # Considering Duplicate Finder Window (DFW) default settings...
        defaults = {
            'MLW_WIDTH': 900,
            'MLW_HEIGHT': 600,
            'MLW_X': 200,
            'MLW_Y': 200,
            'MLW_STATE': 'normal',
            'MLW_LAST_FILE': None,
            'MLW_PLAYLIST_PATH': Path('.'),
            'MLW_VOLUME': 5.0,
            'MLW_TS_COL_WIDTH': 150,
            'MLW_LT_COL_WIDTH': 300,
            'MLW_AFTER_PLAYED': 0,
            'MLW_INFO_EVENTS_WIDTH': 200,
            'MLW_LRC_VIEW_WIDTH': 200,}
        return AppSettings().Read(defaults)

    def _OnClosingWin(self) -> None:
        # Closing the MP3 file...
        if self._mp3:
            self._mp3.Close()
        # Saving LRC if changed...
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
        settings['MLW_LAST_FILE'] = self._lastAudio
        settings['MLW_PLAYLIST_PATH'] = self._playlist.Path
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

        self.destroy()
    
    def _RemoveABRepeat(self) -> None:
        self._abvw.length = self._mp3.Duration
    
    def _SetA(self) -> None:
        self._abvw.a = self.pos
    
    def _SetB(self) -> None:
        self._abvw.b = self.pos

    def _SaveLrc(self) -> None:
        if self._lrc:
            self._lrcedt.ApplyLyrics()
            if self._lrc.changed:
                self._lrc['by'] = 'https://twitter.com/megacodist'
                self._lrc['re'] = 'https://github.com/megacodist/mp3-lyrics'
                # Saving LRC to the dick...
                self._lrc.Save()
                # Updating GUI to reflect latest changes...
                self._UpdateGui_Lrc()
    
    def _CreateLrc(self) -> None:
        if self._lrc:
            self._msgvw.AddMessage(
                title='Cannot create LRC',
                message=f"The '{self._lrc.filename}' has been loaded.",
                type=MessageType.WARNING)
        else:
            self._LoadLrc(
                self._lastAudio,
                toCreate=self._lrcLoaded)
    
    def _DeleteLrc(self) -> None:
        # Insert code here to delete the LRC file...
        pLrc = Path(Lrc.GetLrcFilename(self._lastAudio))
        if pLrc.exists():
            toDelete = askyesno(message='Do you want to delete the LRC?')
            if toDelete:
                pLrc.unlink()
                del self._lrc
                self._lrc = None
                self._lrcLoaded = True
                self._UpdateGui_Lrc()
    
    def _DiscardChanges(self) -> None:
        self._LoadLrc(self._lastAudio)

    def _UpdateGui_Playable(self) -> None:
        self._btn_palyPause['state'] = tk.NORMAL
        self._menu_mp3Player.entryconfigure(
            'Play/pause',
            state=tk.NORMAL)

    def _UpdateGui_Pausable(self) -> None:
        pass

    def _UpdateGui_NotPlayable(self) -> None:
        """Updates GUI in a way that PLAY button is disables."""
        self._btn_palyPause['state'] = tk.DISABLED
        self._menu_mp3Player.entryconfigure(
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
        self._infovw.PopulateFileInfo(self._lastAudio)
        self._infovw.PopulateMp3Info(self._mp3)
        self._infovw.PopulateLrcInfo(self._lrc)

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
