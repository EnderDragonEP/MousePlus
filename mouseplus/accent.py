"""The Windows accent color: the exact shades Windows uses, and a watcher for changes."""
import threading
import winreg
from ctypes import wintypes

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QColor

from . import winapi as w

ACCENT_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Accent"
# AccentPalette holds 8 RGBA colors: Light3, Light2, Light1, Accent, Dark1, Dark2, Dark3, (unused)
_LIGHT2, _DARK1 = 1, 4


def windows_accent(dark: bool) -> QColor:
    """The accent shade Windows 11 uses for controls: AccentLight2 on dark, AccentDark1 on light."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, ACCENT_KEY) as key:
            palette = winreg.QueryValueEx(key, "AccentPalette")[0]
        i = (_LIGHT2 if dark else _DARK1) * 4
        return QColor(palette[i], palette[i + 1], palette[i + 2])
    except (OSError, IndexError, TypeError):
        return QColor("#60CDFF" if dark else "#005FB8")  # Windows' default blue


class AccentWatcher(QObject):
    """Emits `changed` whenever Windows writes the accent settings (Settings app or wallpaper)."""

    changed = pyqtSignal()

    def __init__(self, parent=None, key: str = ACCENT_KEY):
        super().__init__(parent)
        self._key = key
        self._stop = None
        self._thread = None

    def start(self):
        if self._thread is None:
            self._stop = w.CreateEventW(None, True, False, None)
            self._thread = threading.Thread(target=self._run, name="AccentWatcher", daemon=True)
            self._thread.start()

    def stop(self):
        if self._thread is not None:
            w.SetEvent(self._stop)
            self._thread.join(1)
            self._thread = None
            w.CloseHandle(self._stop)

    def _run(self):
        changed = w.CreateEventW(None, False, False, None)
        handles = (wintypes.HANDLE * 2)(changed, self._stop)
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._key) as key:
                while True:
                    if w.RegNotifyChangeKeyValue(key.handle, False, w.REG_NOTIFY_CHANGE_LAST_SET, changed, True):
                        return
                    if w.WaitForMultipleObjects(2, handles, False, w.INFINITE) != w.WAIT_OBJECT_0:
                        return  # stop requested
                    self.changed.emit()
        except OSError:
            pass
        finally:
            w.CloseHandle(changed)
