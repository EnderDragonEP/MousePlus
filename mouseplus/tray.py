"""Notification-area icon with a Fluent menu: a status header, pause, a switch per feature and app commands."""
from PyQt6.QtCore import QSize, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices
from PyQt6.QtWidgets import QSystemTrayIcon, QVBoxLayout, QWidget
from qfluentwidgets import (Action, BodyLabel, CaptionLabel, CheckableSystemTrayMenu, FluentIcon as FIF,
                            StrongBodyLabel, qconfig, setFont, themeColor)

from . import APP_NAME, __version__, icons
from .config import TRIGGER_TEXTS, cfg

_SECONDARY = (QColor(96, 96, 96), QColor(206, 206, 206))  # light, dark
_CHECK_COLUMN = 26  # a checkable menu insets every item this much to make room for the check marks
_ITEM_PADDING = 24  # extra room after each item's text, so the menu doesn't end right at the longest one


class TrayMenu(CheckableSystemTrayMenu):
    def _adjustItemText(self, item, action):
        super()._adjustItemText(item, action)  # sizes the item to fit its text, every time the text changes
        item.setSizeHint(item.sizeHint() + QSize(_ITEM_PADDING, 0))


def active_features() -> list:
    """Names of the features that are switched on."""
    features = [("Horizontal Scroll", cfg.horizontalEnabled.value),
                ("Monitor Cursor", cfg.cursorEnabled.value),
                ("Scroll Inertia", cfg.smoothEnabled.value)]
    return [name for name, on in features if on]


class StatusHeader(QWidget):
    """The top of the menu: the state, a hint when the state needs one, and the version."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.title = StrongBodyLabel(self)
        self.detail = BodyLabel(self)
        setFont(self.detail, 16)
        self.caption = CaptionLabel(self)
        self.caption.setTextColor(*_SECONDARY)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 8, 16, 8)  # text lines up with the menu icons
        layout.setSpacing(2)
        for label in (self.title, self.detail, self.caption):
            layout.addWidget(label)

    def setStatus(self, title: str, detail: str, caption: str, active: bool):
        self.title.setText(title)
        self.detail.setText(detail)
        self.detail.setVisible(bool(detail))
        if active:
            self.detail.setTextColor(themeColor(), themeColor())
        else:
            self.detail.setTextColor(*_SECONDARY)
        self.caption.setText(caption)


class Tray(QSystemTrayIcon):
    settingsRequested = pyqtSignal()
    updateCheckRequested = pyqtSignal()
    pauseRequested = pyqtSignal()  # toggles pause for every feature; the app owns the state
    exitRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._latched = False
        self._paused = False
        self._release = None     # a newer version found by an update check
        self._messageUrl = None  # opened when the latest notification is selected

        self.header = StatusHeader()
        self.pauseAction = Action(FIF.PAUSE, "Pause Mouse Plus", triggered=lambda: self.pauseRequested.emit())
        # Each feature's on/off switch, the same setting as the first card on its tab.
        self.featureActions = [self._switch(cfg.horizontalEnabled, icons.glyph_icon(), "Horizontal Scroll"),
                               self._switch(cfg.cursorEnabled, icons.monitors_icon(), "Monitor Cursor"),
                               self._switch(cfg.smoothEnabled, FIF.SCROLL, "Scroll Inertia")]
        self.settingsAction = Action(FIF.SETTING, "Settings", triggered=lambda: self.settingsRequested.emit())
        self.updateAction = Action(FIF.UPDATE, "Check for updates", triggered=self._onUpdateAction)
        self.quitAction = Action(FIF.POWER_BUTTON, "Quit", triggered=lambda: self.exitRequested.emit())

        self.menu = TrayMenu()
        self.menu.addWidget(self.header, selectable=False)
        self.menu.addSeparator()
        self.menu.addAction(self.pauseAction)
        self.menu.addSeparator()
        self.menu.addActions([action for _, action in self.featureActions])
        self.menu.addSeparator()
        self.menu.addActions([self.settingsAction, self.updateAction])
        self.menu.addSeparator()
        self.menu.addAction(self.quitAction)
        self.setContextMenu(self.menu)

        self.activated.connect(self._onActivated)
        self.messageClicked.connect(self._onMessageClicked)
        for item in (*cfg.featureItems(), cfg.trigger):
            item.valueChanged.connect(self.refresh)
        self.refresh()

    def _switch(self, item, icon, text: str):
        action = Action(icon, text, checkable=True)
        action.triggered.connect(lambda checked: qconfig.set(item, checked))
        return item, action

    def notify(self, title: str, text: str, icon=None, msecs: int = 5000, url: str = None):
        """Show a Windows notification (the app icon unless `icon` is given); selecting it opens `url`."""
        self._messageUrl = url
        self.showMessage(title, text, icons.app_icon() if icon is None else icon, msecs)

    def setLatched(self, on: bool):
        self._latched = on
        self.refresh()

    def setPaused(self, on: bool):
        self._paused = on
        self.refresh()

    def setUpdate(self, release):
        """A newer version is out: the menu offers to download it."""
        self._release = release
        self.refresh()

    def refresh(self, *_):
        state, tip, title, detail = "on", "On", "Mouse Plus is on", ""  # no hint needed
        if self._paused:
            state, tip, title, detail = "off", "Paused", "Mouse Plus is paused", "Resume to turn features back on"
        elif not active_features():
            state, tip, title, detail = "off", "No features on", "No features are on", "Turn one on below"
        elif self._latched:  # toggle mode locked horizontal scrolling on: say why the wheel scrolls sideways
            state, tip = "latched", "Horizontal scrolling locked on"
            title, detail = "Horizontal scrolling locked on", f"Click {TRIGGER_TEXTS[cfg.trigger.value]} to release"
        if self._release:
            caption = f"Version {self._release.version} is available"
        else:
            caption = f"Version {__version__}"

        self.setIcon(icons.tray_icon(state))
        self.setToolTip(f"{APP_NAME} – {tip}")
        self.header.setStatus(title, detail, caption, state != "off")
        self._fitHeader()
        self.pauseAction.setText("Resume Mouse Plus" if self._paused else "Pause Mouse Plus")
        self.pauseAction.setIcon(FIF.PLAY if self._paused else FIF.PAUSE)
        for item, action in self.featureActions:
            action.setChecked(item.value)
        if self._release:
            self.updateAction.setText(f"Download version {self._release.version}")
            self.updateAction.setIcon(FIF.DOWNLOAD)

    def _fitHeader(self):
        """The header is the menu's first item; resize that item when the text changes."""
        view = self.menu.view
        # The menu style insets every item by 6 px margin + 10 px padding on each side, plus the check column.
        view.item(0).setSizeHint(self.header.sizeHint() + QSize(32 + _CHECK_COLUMN, 0))
        # Separators keep the menu width from when they were added, which would stop
        # the menu from shrinking; give them no width of their own so they follow it.
        for i in range(1, view.count()):
            item = view.item(i)
            if not item.text():
                item.setSizeHint(QSize(0, item.sizeHint().height()))
        view.setMinimumWidth(0)  # adjustSize() never shrinks below the last fixed width
        view.adjustSize()
        self.menu.adjustSize()

    def _onActivated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.settingsRequested.emit()

    def _onUpdateAction(self):
        if self._release:
            QDesktopServices.openUrl(QUrl(self._release.url))
        else:
            self.updateCheckRequested.emit()

    def _onMessageClicked(self):
        if self._messageUrl:
            QDesktopServices.openUrl(QUrl(self._messageUrl))
