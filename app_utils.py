from abc import ABC, abstractmethod
from asyncio import AbstractEventLoop
import base64
import hashlib
import hmac
import logging
from pathlib import Path
import pickle
from threading import RLock
from time import sleep
from typing import Any

from megacodist.singleton import SingletonMeta


# Defining of global variables...
_UNSUP_FILE: Path


class AbstractPlayer(ABC):
    @abstractmethod
    def __init__(
            self,
            audio: str | Path,
            loop: AbstractEventLoop | None = None
            ) -> None:
        """Initializes the Player. Any realization must accept location
        of the audio typically in the local file system. Although some
        implementation might accept other locations such as in the cloud.
        The implementation might be built on top of Async IO model.
        """
        pass
    
    @property
    @abstractmethod
    def volume(self) -> int:
        pass
    
    @volume.setter
    @abstractmethod
    def volume(self, __volume: int, /) -> None:
        pass

    @property
    @abstractmethod
    def pos(self) -> float:
        pass
    
    @pos.setter
    @abstractmethod
    def pos(self, __pos: float, /) -> None:
        pass

    @property
    @abstractmethod
    def playing(self) -> bool:
        """Specifies whether the audio is playing at the moment or not."""
        pass

    @abstractmethod
    def Play(self) -> None:
        pass

    @abstractmethod
    def Pause(self) -> None:
        pass

    @abstractmethod
    def Stop(self) -> None:
        pass

    @abstractmethod
    def Close(self) -> None:
        pass


class AppSettings(object, metaclass=SingletonMeta):
    """Encapsulates APIs for persistence settings between different sessions
    of the application. This class offers a thread-safe singleton object which
    must typically be used as follow:

    Firstly, AppSettings().Load('path/to/the/file') to load settings from
    the specified file.

    Secondly, AppSettings().Read(defaults) with a dictionary-like object whcih
    contains default value for settings (fallback).

    Thirdly, AppSettings().Update(new_values) with a dictionary-like object
    whcih contains new values for settings.

    Finally, AppSettings().Save() to save settings to the file.
    """

    def __init__(self) -> None:
        self.settings: dict[str, Any] = {}
        self.lock = RLock()
        self.file: str | Path

    def Load(self, file: str | Path) -> None:
        """Loads settings from the specified file into the
        singleton object.
        """
        # Getting hold of settings singleton object...
        count = 0
        while not self.lock.acquire(True, 0.25):
            sleep(0.25)
            count += 1
            if count > 16:
                logging.error(
                    'Could not getting hold of settings singleton object')
                return

        # Reading settings from the file...
        self.file = file
        try:
            settingsFileStream = open(
                file,
                mode='rb')
            raw_settings = settingsFileStream.read()

            # Checking the signature...
            try:
                signature_ = hmac.digest(
                    key=b'a-secret-key',
                    msg=raw_settings[44:],
                    digest=hashlib.sha256)
                signature_ = base64.b64encode(signature_)
                isOk = hmac.compare_digest(
                    raw_settings[:44],
                    signature_)
                if isOk:
                    raw_settings = base64.b64decode(raw_settings[44:])
                    self.settings = pickle.loads(raw_settings)
            except Exception:
                # An error occurred checking signature of the settings file
                # Leaving settings dictionary empty...
                pass
        except Exception as err:
            # An error occurred reading the settings file
            # Leaving settings dictionary empty...
            logging.error(f'Loading settings file failed\n{str(err)}')
        finally:
            settingsFileStream.close()
            self.lock.release()

    def Save(self) -> None:
        """Saves settings to the file."""
        # Getting hold of settings singleton object...
        count = 0
        while not self.lock.acquire(True, 0.25):
            sleep(0.25)
            count += 1
            if count > 16:
                logging.error(
                    'Could not getting hold of settings singleton object')
                return

        try:
            # Turning 'settings' to bytes (pickling)...
            binSettings = pickle.dumps(self.settings)
            binSettings = base64.b64encode(binSettings)

            # Signing the settings...
            # signature_ will be 64 bytes long...
            signature_ = hmac.digest(
                key=b'a-secret-key',
                msg=binSettings,
                digest=hashlib.sha256)
            # signature_ will be 86 bytes long...
            signature_ = base64.b64encode(signature_)

            # Writing settings to the file...
            with open(self.file, mode='wb') as settingsFileStream:
                settingsFileStream.write(signature_)
                settingsFileStream.write(binSettings)
        finally:
            self.lock.release()

    def Read(self, defaults: dict[str, Any]) -> dict[str, Any]:
        """Checks settings against defaults. If exists return settings
        otherwise merge defaults into the settings (fallback).
        """
        # Getting hold of settings singleton object...
        count = 0
        while not self.lock.acquire(True, 0.25):
            sleep(0.25)
            count += 1
            if count > 16:
                logging.error(
                    'Could not getting hold of settings singleton object')
                return defaults

        for key, value in defaults.items():
            if ((key not in self.settings) or
                    (not isinstance(self.settings[key], type(value)))):
                self.settings[key] = value

        settings_ = self.settings.copy()
        self.lock.release()
        return settings_

    def Update(self, new_values: dict[str, Any]) -> None:
        """Updates singleton object with new values."""
        # Getting hold of settings singleton object...
        count = 0
        while not self.lock.acquire(True, 0.25):
            sleep(0.25)
            count += 1
            if count > 16:
                logging.error(
                    'Could not getting hold of settings singleton object')
                return

        try:
            for key, value in new_values.items():
                self.settings[key] = value
        finally:
            self.lock.release()


def ConfigureLogging(filename: str | Path) -> None:
    # Getting root logger...
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    '''# Logging platform information...
    loggerFileStream = logging.FileHandler(filename, 'w')
    loggerFormatter = logging.Formatter('%(message)s')
    loggerFileStream.setFormatter(loggerFormatter)
    logger.addHandler(loggerFileStream)

    logNote = (
        f'Operating system: {platform.system()} {platform.release()}'
        + f'(version: {platform.version()}) {platform.architecture()}')
    logging.info(logNote)
    temp = '.'.join(platform.python_version_tuple())
    logNote = f'Python interpreter: {platform.python_implementation()} {temp}'
    logging.info(logNote + '\n\n')

    # Logging program events...
    logger.removeHandler(loggerFileStream)'''
    loggerFileStream = logging.FileHandler(filename, 'a')
    loggerFormatter = logging.Formatter(
        fmt=(
            '[%(asctime)s]  %(module)s  %(threadName)s'
            + '\n%(levelname)8s: %(message)s\n\n'),
        datefmt='%Y-%m-%d  %H:%M:%S')
    loggerFileStream.setFormatter(loggerFormatter)
    logger.addHandler(loggerFileStream)


def SetUnsupFile(file: str | Path) -> None:
    global _UNSUP_FILE
    _UNSUP_FILE = file


def AddUnsupNote(text: str) -> None:
    global _UNSUP_FILE

    with open(_UNSUP_FILE, mode='a') as fileobj:
        fileobj.write(text)
