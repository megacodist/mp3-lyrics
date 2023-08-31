#
# 
#
"""
"""


from concurrent.futures._base import Future
import logging
from os import PathLike
from pathlib import Path
import re
import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askopenfilename
from tkinter.messagebox import askyesno
from typing import Any, Type

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
from utils.types import GifImage
from widgets.ab_view import ABView
from widgets.info_view import InfoView
from widgets.lyrics_editor import LyricsEditor
from widgets.lyrics_view import LyricsView
from widgets.message_view import MessageType, MessageView
from widgets.playlist_view import PlaylistItem, PlaylistView
from win_utils import AfterPlayed


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
        self._mp3: AbstractMp3 | None = None
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
        """Specifies whether the MP3 is playing right now or not."""
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
        self._lrcLoaded: bool = False
        """Specifies whether the LRC file has been loaded or not. This flag
        in conjuction with _lrc object can determine whether the LRC file
        exists or not.
        """
        self._timestamps: SortedList[float] = SortedList(
            cp=CollisionPolicy.END)
        """The timestamps of the loaded LRC files."""
        # Loading resources...
        self._IMG_PLAY: PIL.ImageTk.PhotoImage
        self._HIMG_PLAY: PIL.Image.Image
        self._IMG_PAUSE: PIL.ImageTk.PhotoImage
        self._HIMG_PAUSE: PIL.Image.Image
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
        self._LoadPlaylist(settings['MLW_PLAYLIST_PATH'])
    
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
            label='Save/create LRC',
            accelerator='Ctrl+S',
            command=self._SaveCreateLrc)
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
                self._SaveCreateLrc()
            # Checking Ctrl+V...
            elif event.keycode == KeyCodes.U:
                self._lrcedt.OverrideFromClipboard()
            # Checking Ctrl+I...
            elif event.keycode == KeyCodes.I:
                self._lrcedt.InsertFromClipboard()
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
    
    def _OpenFile(self) -> None:
        """Pops up 'Browse for a file' dialog, loads the MP3 into
        the player, and also other MP3s in the folder into the Folder
        view.
        """
        from media import FilenameToPlypathAudio
        folder = self._playlist.Path if self._playlist else None
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
        # Populating the playlistview...
        if self._playlistAsyncOp is None:
            self._WithdrawAudio_Gui()
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
        args = future.result()
        playlist = args[0]
        items = args[1]
        self._playlistAsyncOp = None
        self._playlist = playlist
        self._plvw.Populate(items)
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
            self._plvw.SelectItem(indices[0])
    
    def _LoadPlaylistIndex(self, idx: int) -> None:
        """Loads `idx`th audio from the playlist into the GUI. This
        function is called whenever an item in the playlist is
        selected.
        """
        self._lastAudio = self._playlist.GetAudio(idx)
        audio_file = self._playlist.GetFullPath(idx)
        self._LoadLrc(audio_file)
        # Loading audio...
        if self._isPlaying:
            self._StopPlaying()
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
        """Loads the specified audio both as an object into `_mp3` and
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
        self._mp3 = future.result()
        self._ExhibitAudio_Gui()
        if self._isPlaying:
            self._mp3.Play()
    
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
    
    def _StopPlaying(self) -> None:
        self._btn_palyPause['image'] = self._IMG_PLAY
        self._isPlaying = False
        self._mp3.Stop()
        self._slider_playTime.set(0.0)
        self._RemoveABRepeat()
        self._StopSyncingPTSlider()
    
    def _SyncPTSlider(self) -> None:
        try:
            self.pos = self._mp3.pos
        except ValueError:
            logging.error(
                f"There was a problem converting {self._pos}"
                + f" to a {Timestamp} object")
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
        # Considering MP3 Lyrics Window (MLW) default settings...
        defaults = {
            'MLW_WIDTH': 900,
            'MLW_HEIGHT': 600,
            'MLW_X': 200,
            'MLW_Y': 200,
            'MLW_STATE': 'normal',
            'MLW_LAST_FILE': Path('res/Tarantella abballa abballa.mp3'),
            'MLW_PLAYLIST_PATH': Path('.'),
            'MLW_VOLUME': 5.0,
            'MLW_TS_COL_WIDTH': 150,
            'MLW_LT_COL_WIDTH': 300,
            'MLW_AFTER_PLAYED': 0,
            'MLW_INFO_EVENTS_WIDTH': 200,
            'MLW_LRC_VIEW_WIDTH': 200,}
        return AppSettings().Read(defaults)

    def _OnWinClosing(self) -> None:
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
        if self._playlist:
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
        self._HIMG_CLOSE.close()
        del self._GIF_WAIT

        self.destroy()
    
    def _RemoveABRepeat(self) -> None:
        self._abvw.length = self._mp3.Duration
    
    def _SetA(self) -> None:
        self._abvw.a = self.pos
    
    def _SetB(self) -> None:
        self._abvw.b = self.pos
    
    def _CloseViewsEditors(self) -> None:
        """Closes (clears) the lyrics view, the info view, and the lyrics
        editor.
        """
        # Clearing the lyrics editor...
        if self._mp3 and self._lrcedt.HasChanged():
            mode = 'save changes to the' if self._lrc else 'create an'
            toSave = askyesno(
                title='Unsaved changes',
                message=f'Do you want {mode} LRC file?')
            if toSave:
                self._SaveCreateLrc()
        self._lrcedt.ClearContent()
        self._lrcedt.SetChangeOrigin()
        # Closing the info view...
        self._infovw.Clear()
        # Clearing the lyrics view...
        self._lrcvw.Clear()
    
    def _SaveCreateLrc(self) -> None:
        """Saves the LRC or creates an LRC object."""
        if self._mp3 and self._lrcedt.HasChanged():
            if self._lrc is None:
                lrcFilename = Lrc.GetLrcFilename(self._mp3.Filename)
                Lrc.CreateLrc(lrcFilename)
                self._lrc = Lrc(lrcFilename, True, True)
            self._lrc.lyrics = self._lrcedt.GetAllLyricsItems()
            self._lrc['by'] = 'https://twitter.com/megacodist'
            self._lrc['re'] = 'https://github.com/megacodist/mp3-lyrics'
            self._lrc.Save()
            self._OnLrcLoaded(self._lrc)
        elif self._mp3:
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
                self._lrcLoaded = True
                self._ExhibitLrc_Gui()
    
    def _DiscardChanges(self) -> None:
        self._LoadLrc(self._lastAudio)
    
    def _UpdateGui_Pausable(self) -> None:
        pass

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

    '''def _InitPlayer(self) -> None:
        """Makes the player section of the GUI ready to play."""
        self._WithdrawAudio_Gui()
        self._mp3.volume = self._slider_volume.get() * 10
        self._slider_playTime['to'] = self._mp3.Duration
        self._ShowAudioLength_Gui(self._mp3.Duration)
        self._abvw.length = self._mp3.Duration
        self._abvw.b = self._abvw.length
        self.pos = 0
        self.title(f'{Path(self._lastAudio).name} - MP3 Lyrics')
        self._ExhibitAudio_Gui()'''

    def _ExhibitAudio_Gui(self) -> None:
        """Makes the player section of the GUI ready to play."""
        self._btn_palyPause['state'] = tk.NORMAL
        self._menu_mp3Player.entryconfigure(
            'Play/pause',
            state=tk.NORMAL)
        self._slider_playTime.config(state='enable')
        self._mp3.volume = self._slider_volume.get() * 10
        self._slider_playTime['to'] = self._mp3.Duration
        self._ShowAudioLength_Gui(self._mp3.Duration)
        self._abvw.length = self._mp3.Duration
        self._abvw.b = self._abvw.length
        self.pos = 0
        self.title(f'{Path(self._lastAudio).name} - MP3 Lyrics')
        self._infovw.PopulateAudioInfo(self._mp3)

    def _WithdrawAudio_Gui(self) -> None:
        """Withdraws the audio from the GUI so PLAYER will be disables."""
        self._btn_palyPause['state'] = tk.DISABLED
        self._menu_mp3Player.entryconfigure(
            'Play/pause',
            state=tk.DISABLED)
        self._ShowAudioLength_Gui(0)
        self.pos = 0
        self._slider_playTime.config(state='disable')
        self.title('MP3 Lyrics')
        self._infovw.ClearAudioInfo()
    
    def _WithdrawLrc_Gui(self) -> None:
        """Withdraws the loaded LRC object from the GUI."""
        if self._mp3 and self._lrcedt.HasChanged():
            toSave = askyesno(
                title='Unsaved lyrics',
                message='Do you want to save/create the lyrics?')
            if toSave:
                self._SaveCreateLrc()
        self._timestamps.clear()
        self._lrcvw.Clear()
        self._lrcedt.ClearContent()
        self._lrcedt.SetChangeOrigin()
        self._infovw.ClearLrcInfo()
    
    def _ExhibitLrc_Gui(self) -> None:
        """Updates the GUI to show the content of the loaded `_lrc`.
        This method must not be called until an LRC file successfully
        loaded.
        """
        # Populating the lyrics view...
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
