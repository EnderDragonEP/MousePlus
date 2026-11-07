"""Mouse Plus - horizontal scrolling, proportional cursor movement between monitors and smooth scrolling.

Usage: main.py [--tray]   (--tray starts hidden in the notification area)
"""
import getpass
import logging
import sys
from logging.handlers import RotatingFileHandler

from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon
from qfluentwidgets import SystemThemeListener, Theme, ThemeColor, isDarkTheme, qconfig, setTheme, setThemeColor

from mouseplus import APP_ID, APP_NAME, DATA_DIR, LOG_FILE, OLD_APP_ID, config, migrate, winapi
from mouseplus.accent import AccentWatcher, windows_accent
from mouseplus.config import cfg
from mouseplus.hook import MouseHook
from mouseplus.osd import Osd
from mouseplus.tray import Tray
from mouseplus.window import SettingsWindow

log = logging.getLogger("mouseplus")
SERVER_NAME = f"{APP_ID}-{getpass.getuser()}"
OLD_SERVER_NAME = f"{OLD_APP_ID}-{getpass.getuser()}"


def setup_logging():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(LOG_FILE, maxBytes=256 * 1024, backupCount=1, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(handler)
    if sys.stderr:
        log.addHandler(logging.StreamHandler())
    log.setLevel(logging.WARNING)

    # Log instead of letting PyQt6 abort the app on an exception inside a slot.
    sys.excepthook = lambda *exc_info: log.error("Unhandled exception", exc_info=exc_info)


def signal_running_instance(server: str, show: bool) -> bool:
    """If an instance listens on `server`, optionally ask it to show its window, and return True."""
    sock = QLocalSocket()
    sock.connectToServer(server)
    if not sock.waitForConnected(500):
        return False
    if show:
        winapi.AllowSetForegroundWindow(winapi.ASFW_ANY)  # let it come to the front
        sock.write(b"show")
        sock.waitForBytesWritten(500)
    sock.disconnectFromServer()
    return True


_library_shade = ThemeColor.color
_dark_brightness = 1.0


def _windows_shade(self: ThemeColor) -> QColor:
    """qfluentwidgets forces full brightness on accent shades in dark mode;
    scale them to the brightness of Windows' own dark-mode accent instead."""
    color = _library_shade(self)
    if isDarkTheme():
        h, s, v, a = color.getHsvF()
        color = QColor.fromHsvF(h, s, v * _dark_brightness, a)
    return color


ThemeColor.color = _windows_shade


def sync_accent():
    """Use the accent shade Windows itself uses for the current light/dark mode."""
    global _dark_brightness
    dark = isDarkTheme()
    color = windows_accent(dark)
    if dark:
        # The library also scales saturation by 0.84 in dark mode; compensate for it.
        h, s, v, _ = color.getHsvF()
        _dark_brightness = v
        color = QColor.fromHsvF(max(h, 0.0), min(s / 0.84, 1.0), v)
    setThemeColor(color)


class App(QObject):
    def __init__(self, qapp: QApplication, show_window: bool):
        super().__init__()
        migrate.migrate()  # settings and autostart from Horizontal Scroll, once
        config.load()
        setTheme(Theme.AUTO)
        sync_accent()
        config.refresh_autostart()
        self.paused = False  # tray "Pause": every feature, until resumed or restarted

        # Build all UI before the hook starts so heavy GUI work never stalls mouse input.
        self.window = SettingsWindow()
        self.tray = Tray(self)
        self.osd = Osd()
        self.hook = MouseHook(self)
        self.themeListener = SystemThemeListener(self)
        self.accentWatcher = AccentWatcher(self)
        # Windows writes several accent values in a row; react once they settle.
        self.accentTimer = QTimer(self, singleShot=True, interval=300, timeout=self._onAccentChanged)
        # Plugging in, removing or rearranging monitors also arrives as a burst of signals.
        self.screensTimer = QTimer(self, singleShot=True, interval=300, timeout=self._onScreensChanged)
        self.server = QLocalServer(self)
        self.server.listen(SERVER_NAME)

        self.server.newConnection.connect(self._onConnection)
        self.window.hiddenToTray.connect(self._onHiddenToTray)
        self.tray.settingsRequested.connect(self.window.present)
        self.tray.updateCheckRequested.connect(self._checkForUpdates)
        self.tray.pauseRequested.connect(self._togglePause)
        self.tray.exitRequested.connect(qapp.quit)
        self.hook.latchedChanged.connect(self._onLatched)
        self.hook.failed.connect(self._onHookFailed)
        self.themeListener.systemThemeChanged.connect(self._onAccentChanged)  # dark/light use different shades
        self.accentWatcher.changed.connect(self.accentTimer.start)
        for item in (*cfg.featureItems(), cfg.trigger, cfg.toggleMode, cfg.disableInFullscreen,
                     cfg.horizontalReverse, cfg.horizontalSpeed):
            item.valueChanged.connect(self._apply)
        qapp.screenAdded.connect(self._watchScreen)
        qapp.screenRemoved.connect(lambda *_: self.screensTimer.start())
        for screen in qapp.screens():
            self._watchScreen(screen, refresh=False)
        qapp.aboutToQuit.connect(self._shutdown)

        self.tray.show()
        self.themeListener.start()
        self.accentWatcher.start()
        self._onScreensChanged()
        self._apply()
        if show_window:
            self.window.present()
        if signal_running_instance(OLD_SERVER_NAME, show=False):
            self.tray.showMessage(APP_NAME, "Horizontal Scroll is still running. Quit it from its tray icon, "
                                            "so the two apps don't both react to the mouse.",
                                  self.window.windowIcon(), 8000)

    def _apply(self, *_):
        if not self.paused and config.any_feature_on():
            self.hook.start(config.hook_settings())  # updates the settings if already running
        else:
            self.hook.stop()

    def _watchScreen(self, screen, refresh=True):
        for signal in (screen.geometryChanged, screen.logicalDotsPerInchChanged, screen.physicalDotsPerInchChanged):
            signal.connect(lambda *_: self.screensTimer.start())
        if refresh:
            self.screensTimer.start()

    def _onScreensChanged(self):
        monitors = winapi.monitor_rects()
        self.hook.set_monitors(monitors)
        self.window.cursorPage.setMonitors(monitors)

    def _togglePause(self):
        self.paused = not self.paused
        self.tray.setPaused(self.paused)
        self._apply()

    def _checkForUpdates(self):
        self.window.present()  # the result is shown in the window
        self.window.checkForUpdates()

    def _onAccentChanged(self):
        sync_accent()
        self.tray.refresh()

    def _onLatched(self, on: bool):
        self.tray.setLatched(on)
        if not winapi.foreground_is_fullscreen():
            self.osd.show_state(on)

    def _onHiddenToTray(self):
        if not cfg.trayHintShown.value:
            qconfig.set(cfg.trayHintShown, True)
            self.tray.showMessage(APP_NAME, "Still running in the notification area. Right-click the icon to exit.",
                                  self.window.windowIcon(), 4000)

    def _onHookFailed(self, message: str):
        log.error(message)
        self.tray.showMessage(APP_NAME, message, QSystemTrayIcon.MessageIcon.Warning, 5000)

    def _onConnection(self):
        sock = self.server.nextPendingConnection()
        sock.readyRead.connect(lambda: b"show" in bytes(sock.readAll()) and self.window.present())
        sock.disconnected.connect(sock.deleteLater)

    def _shutdown(self):
        self.hook.stop()
        self.accentWatcher.stop()
        self.themeListener.terminate()
        self.tray.hide()


def main() -> int:
    show_window = "--tray" not in sys.argv
    winapi.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    qapp = QApplication(sys.argv)
    qapp.setApplicationName(APP_NAME)
    qapp.setQuitOnLastWindowClosed(False)
    if signal_running_instance(SERVER_NAME, show_window):
        return 0
    setup_logging()
    qapp.controller = App(qapp, show_window)  # keep a reference for the app's lifetime
    return qapp.exec()


if __name__ == "__main__":
    sys.exit(main())
