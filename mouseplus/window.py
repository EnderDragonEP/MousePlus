"""Settings window: one tab per feature in a left rail (PyQt6-Fluent-Widgets MSFluentWindow, Mica on Windows 11)."""
from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices, QFont, QGuiApplication
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget
from qfluentwidgets import (BodyLabel, ComboBoxSettingCard, ExpandLayout, FluentIcon as FIF, HyperlinkLabel, InfoBar,
                            InfoBarIcon, InfoBarPosition, MessageBox, MSFluentWindow, NavigationItemPosition,
                            PrimaryPushSettingCard, PushButton, RangeSettingCard, ScrollArea, SettingCard,
                            SettingCardGroup, SwitchSettingCard, TitleLabel, setCustomStyleSheet, setFont)

from . import APP_NAME, REPO_URL, __version__, config, icons
from .applist import AppListCard
from .config import BYPASS_TEXTS, GLIDE_TEXTS, TRIGGER_TEXTS, cfg
from .monitormap import MonitorMap
from .updates import UpdateChecker, is_newer

LICENSES_URL = f"{REPO_URL}/blob/main/THIRD_PARTY_NOTICES.md"
CHANGELOG_URL = f"{REPO_URL}/blob/main/CHANGELOG.md"


class Group(SettingCardGroup):
    """Setting card group with a Windows 11 Settings style header (14 px semibold)."""

    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        setFont(self.titleLabel, 14, QFont.Weight.DemiBold)
        self.titleLabel.adjustSize()

    def adjustSize(self):
        h = self.cardLayout.heightForWidth(self.width()) + self.titleLabel.height() + 12
        return self.resize(self.width(), h)


class SliderCard(RangeSettingCard):
    """Slider card that shows its value as `valueText()` says."""

    def __init__(self, configItem, icon, title, content, parent=None):
        super().__init__(configItem, icon, title, content, parent)
        self.slider.setMinimumWidth(180)
        self._show(configItem.value)

    def setValue(self, value):
        super().setValue(value)
        self._show(value)

    def valueText(self, value) -> str:
        return str(value)

    def _show(self, value):
        self.valueLabel.setText(self.valueText(value))
        self.valueLabel.adjustSize()


class MultiplierCard(SliderCard):
    """A value stored in tenths, shown as a multiplier ("1.0×")."""

    def valueText(self, value) -> str:
        return f"{value / 10:.1f}×"


class NotchesCard(SliderCard):
    """A number of wheel notches ("3 notches")."""

    def valueText(self, value) -> str:
        return f"{value} notches"


class AboutCard(PrimaryPushSettingCard):
    """App name, then the version with "Changelog", "View source" and "Licenses" links, plus the update button."""

    def __init__(self, parent=None):
        super().__init__("Check for updates", icons.app_icon(), APP_NAME, f"Version {__version__}", parent)
        self.changelogLink = self._link(CHANGELOG_URL, "Changelog")
        self.sourceLink = self._link(REPO_URL, "View source")
        self.licensesLink = self._link(LICENSES_URL, "Licenses")
        # Put the links on the version line, after the card's description: "Version · link · link".
        row = QHBoxLayout()
        row.setSpacing(6)
        self.vBoxLayout.removeWidget(self.contentLabel)
        row.addWidget(self.contentLabel, 0, Qt.AlignmentFlag.AlignVCenter)
        for link in (self.changelogLink, self.sourceLink, self.licensesLink):
            dot = QLabel("·", self)
            dot.setObjectName("contentLabel")  # styled like the version text
            row.addWidget(dot, 0, Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(link, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addStretch(1)
        self.vBoxLayout.addLayout(row)

    def _link(self, url: str, text: str) -> HyperlinkLabel:
        link = HyperlinkLabel(QUrl(url), text, self)
        # Match the description text; the card's QPushButton rule would make the link 14 px.
        size = "HyperlinkLabel { font-size: 11px; }"
        setCustomStyleSheet(link, size, size)
        return link


class Page(ScrollArea):
    """One tab: a fixed title and hint above scrolling setting cards."""

    def __init__(self, objectName: str, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName(objectName)  # the navigation rail routes by object name
        self.view = QWidget()
        self.expand = ExpandLayout(self.view)
        self.title = TitleLabel(title, self)
        self.hint = BodyLabel(self)
        self.hint.setWordWrap(True)
        self.hint.setTextColor(QColor(96, 96, 96), QColor(206, 206, 206))
        self.expand.setSpacing(28)
        self.expand.setContentsMargins(36, 0, 36, 0)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def addWidgets(self, *widgets):
        bottomPadding = QWidget(self.view)  # ExpandLayout ignores the bottom margin
        bottomPadding.setFixedHeight(8)
        for widget in (*widgets, bottomPadding):
            self.expand.addWidget(widget)
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.enableTransparentBackground()

    def setHint(self, text: str):
        self.hint.setText(text)
        self._layoutHeader()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._layoutHeader()

    def _layoutHeader(self):
        width = max(self.width() - 72, 100)
        self.title.move(36, 12)
        self.hint.resize(width, self.hint.heightForWidth(width))
        self.hint.move(36, self.title.geometry().bottom() + 6)
        self.setViewportMargins(0, self.hint.geometry().bottom() + 24, 0, 0)


class HorizontalPage(Page):
    def __init__(self, parent=None):
        super().__init__("horizontalPage", "Horizontal Scroll", parent)
        self.enableCard = SwitchSettingCard(
            icons.glyph_icon(), "Horizontal scrolling", "Turn this feature on or off",
            cfg.horizontalEnabled, self.view)

        self.activation = Group("Activation", self.view)
        self.triggerCard = ComboBoxSettingCard(
            cfg.trigger, FIF.RETURN, "Trigger button", "The mouse button that turns the wheel sideways",
            texts=list(TRIGGER_TEXTS.values()), parent=self.activation)
        self.toggleCard = SwitchSettingCard(
            FIF.PIN, "Toggle mode", "Click the trigger to turn horizontal scrolling on, click again to turn it off",
            cfg.toggleMode, self.activation)
        self.activation.addSettingCards([self.triggerCard, self.toggleCard])

        self.scrolling = Group("Scrolling", self.view)
        self.speedCard = MultiplierCard(cfg.horizontalSpeed, FIF.SPEED_HIGH, "Scroll speed",
                                        "Distance per wheel step", self.scrolling)
        self.reverseCard = SwitchSettingCard(
            FIF.SYNC, "Reverse direction", "Wheel down scrolls left instead of right",
            cfg.horizontalReverse, self.scrolling)
        self.scrolling.addSettingCards([self.speedCard, self.reverseCard])

        self.addWidgets(self.enableCard, self.activation, self.scrolling)
        cfg.trigger.valueChanged.connect(self._updateHint)
        cfg.toggleMode.valueChanged.connect(self._updateHint)
        self._updateHint()

    def _updateHint(self, *_):
        trigger = TRIGGER_TEXTS[cfg.trigger.value]
        if cfg.toggleMode.value:
            text = f"Click {trigger} to turn horizontal scrolling on or off. You can also hold it while rolling the wheel."
        else:
            text = f"Hold {trigger} and roll the wheel to scroll sideways. A quick click still works as usual."
        self.setHint(text)


class CursorPage(Page):
    def __init__(self, parent=None):
        super().__init__("cursorPage", "Monitor Cursor", parent)
        self.enableCard = SwitchSettingCard(
            icons.monitors_icon(), "Proportional cursor", "Turn this feature on or off",
            cfg.cursorEnabled, self.view)

        self.monitors = Group("Monitors", self.view)
        self.mapCard = MonitorMap(self.monitors)
        self.layoutCard = SettingCard(FIF.TILES, "Detected monitors", "…", self.monitors)
        self.monitors.addSettingCards([self.mapCard, self.layoutCard])

        self.addWidgets(self.enableCard, self.monitors)
        self.setHint("When the cursor moves to another monitor, it lands at the same relative spot along the "
                     "shared edge, even where the monitors don't line up. It works while dragging, too.")
        cfg.cursorEnabled.valueChanged.connect(self.mapCard.setActive)
        self.mapCard.setActive(cfg.cursorEnabled.value)

    def setMonitors(self, monitors):
        self.mapCard.setMonitors(monitors)
        monitors = sorted(monitors, key=lambda m: (m.left, m.top))  # as arranged on the desk
        sizes = ", ".join(f"{m.width}×{m.height}" for m in monitors)
        if len(monitors) > 1:
            self.layoutCard.setContent(f"{len(monitors)} monitors · {sizes}")
        else:
            self.layoutCard.setContent(f"1 monitor · {sizes}. Connect another one to use this feature.")


class SmoothPage(Page):
    def __init__(self, parent=None):
        super().__init__("smoothPage", "Scroll Inertia", parent)
        self.inertia = Group("Inertia", self.view)
        self.enableCard = SwitchSettingCard(  # the feature's on/off switch: inertia is all it does
            FIF.SEND, "Inertia", "A fast flick keeps scrolling and slows down, like a free-spinning wheel",
            cfg.smoothEnabled, self.inertia)
        self.flickCard = NotchesCard(cfg.smoothFlick, FIF.FINGERPRINT, "Flick threshold",
                                     "How many quick notches start a glide", self.inertia)
        self.momentumCard = MultiplierCard(cfg.smoothMomentum, FIF.ZOOM_IN, "Inertia multiplier",
                                           "How fast a flick keeps going, and so how far", self.inertia)
        self.glideCard = ComboBoxSettingCard(
            cfg.smoothGlide, FIF.SPEED_OFF, "Glide", "How slowly a flick stops. Free spin coasts like a free wheel",
            texts=list(GLIDE_TEXTS.values()), parent=self.inertia)
        self.brakeCard = SwitchSettingCard(
            FIF.PAUSE, "Reverse wheel stops the glide",
            "Turning the wheel back during a glide just stops it, without scrolling back",
            cfg.smoothBrake, self.inertia)
        self.carryCard = SwitchSettingCard(
            FIF.SHARE, "Carry the glide to other apps",
            "A glide keeps going when the cursor moves to another window",
            cfg.smoothCarry, self.inertia)
        self.inertia.addSettingCards([self.enableCard, self.flickCard, self.momentumCard, self.glideCard,
                                      self.brakeCard, self.carryCard])

        self.bypass = Group("Bypass", self.view)
        self.bypassCard = ComboBoxSettingCard(
            cfg.bypassKey, FIF.CANCEL, "Bypass key",
            "Hold it to scroll without inertia. Ctrl + wheel (zoom) always passes through.",
            texts=list(BYPASS_TEXTS.values()), parent=self.bypass)
        self.appsCard = AppListCard(
            cfg.smoothExcluded, cfg.smoothAppNames, FIF.APPLICATION, "Apps that scroll normally",
            "For apps where a glide gets in the way, like image viewers", self.bypass)
        self.bypass.addSettingCards([self.bypassCard, self.appsCard])

        self.experimental = Group("Experimental", self.view)
        self.bounceCard = SwitchSettingCard(
            FIF.ROTATE, "Overscroll bounce",
            "Only in apps with classic scrollbars, and not in maximized windows",
            cfg.smoothBounce, self.experimental)
        self.experimental.addSettingCard(self.bounceCard)

        self.addWidgets(self.inertia, self.bypass, self.experimental)
        self.setHint("Each notch scrolls as usual, and a fast flick keeps going like a free-spinning wheel.")


class GeneralPage(Page):
    def __init__(self, parent=None):
        super().__init__("generalPage", "General", parent)
        self.general = Group("Behavior", self.view)
        self.fullscreenCard = SwitchSettingCard(
            FIF.FULL_SCREEN, "Disable in full-screen apps",
            "Games and full-screen videos get the normal mouse behavior", cfg.disableInFullscreen, self.general)
        self.startupCard = SwitchSettingCard(
            FIF.POWER_BUTTON, "Start with Windows", "Start in the notification area when you sign in",
            parent=self.general)
        self.general.addSettingCards([self.fullscreenCard, self.startupCard])

        self.about = Group("About", self.view)
        self.aboutCard = AboutCard(self.about)
        self.updateCard = SwitchSettingCard(
            FIF.UPDATE, "Check for updates on startup", "Get a notification when a new version is out",
            cfg.checkUpdates, self.about)
        self.about.addSettingCards([self.aboutCard, self.updateCard])

        self.addWidgets(self.general, self.about)
        self.setHint("Settings for the whole app. Right-click the tray icon to pause every feature at once.")


class SettingsWindow(MSFluentWindow):
    hiddenToTray = pyqtSignal()
    updateFound = pyqtSignal(object)  # Release: "Check for updates" found a newer version

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(icons.app_icon())

        self.horizontalPage = HorizontalPage(self)
        self.cursorPage = CursorPage(self)
        self.smoothPage = SmoothPage(self)
        self.generalPage = GeneralPage(self)
        self.addSubInterface(self.horizontalPage, icons.glyph_icon(), "Horizontal",
                             selectedIcon=icons.glyph_icon(accent=True))
        self.addSubInterface(self.cursorPage, icons.monitors_icon(), "Cursor",
                             selectedIcon=icons.monitors_icon(accent=True))
        self.addSubInterface(self.smoothPage, FIF.SCROLL, "Inertia")
        self.addSubInterface(self.generalPage, FIF.SETTING, "General", position=NavigationItemPosition.BOTTOM)

        self.setMinimumWidth(600)
        self._placed = False

        about = self.generalPage.aboutCard
        self.generalPage.startupCard.setChecked(config.is_autostart())
        self.generalPage.startupCard.checkedChanged.connect(self._setAutostart)
        self.updates = UpdateChecker(self)
        self.updates.finished.connect(self._onUpdateChecked)
        self.updates.failed.connect(self._onUpdateFailed)
        about.clicked.connect(self.checkForUpdates)

    def present(self):
        if not self._placed:
            # Size on first show: the frameless base class's own initial resize
            # can arrive late and override a size set while the window is hidden.
            self._placed = True
            area = QGuiApplication.primaryScreen().availableGeometry()
            self.resize(720, min(860, area.height() - 48))
            self.move(area.center() - self.rect().center())
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, e):
        e.ignore()
        self.hide()
        self.hiddenToTray.emit()

    def checkForUpdates(self):
        self.switchTo(self.generalPage)
        if not self.generalPage.aboutCard.button.isEnabled():
            return  # a check is already running
        self._setChecking(True)
        self.updates.check()

    def _setChecking(self, checking: bool):
        button = self.generalPage.aboutCard.button
        button.setEnabled(not checking)
        button.setText("Checking…" if checking else "Check for updates")

    def _onUpdateChecked(self, release):
        self._setChecking(False)
        if release is None or not is_newer(release.version):  # None: nothing published yet
            InfoBar.success("You're up to date", f"Version {__version__} is the latest version.",
                            orient=Qt.Orientation.Horizontal, isClosable=True,
                            position=InfoBarPosition.TOP, duration=3000, parent=self)
            return
        self.updateFound.emit(release)
        box = MessageBox(f"Version {release.version} is available",
                         f"You have version {__version__}. Open the download page on GitHub?", self)
        box.yesButton.setText("Download")
        box.cancelButton.setText("Later")
        if box.exec():
            QDesktopServices.openUrl(QUrl(release.url))

    def showUpdateAvailable(self, release):
        """The startup check found a newer version while the window is open: say so in the window."""
        bar = InfoBar(InfoBarIcon.INFORMATION, f"Version {release.version} is available",
                      f"You have version {__version__}.", isClosable=True, duration=-1,
                      position=InfoBarPosition.TOP, parent=self)
        download = PushButton("Download", bar)
        download.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(release.url)))
        download.clicked.connect(bar.close)
        bar.addWidget(download)
        bar.show()

    def _onUpdateFailed(self, message: str):
        self._setChecking(False)
        InfoBar.warning("Couldn't check for updates", message, orient=Qt.Orientation.Horizontal,
                        isClosable=True, position=InfoBarPosition.TOP, duration=5000, parent=self)

    def _setAutostart(self, on: bool):
        try:
            config.set_autostart(on)
        except OSError as e:
            card = self.generalPage.startupCard
            card.switchButton.blockSignals(True)
            card.setChecked(not on)
            card.switchButton.blockSignals(False)
            InfoBar.error("Couldn't change the startup setting", str(e), orient=Qt.Orientation.Horizontal,
                          isClosable=True, position=InfoBarPosition.TOP, duration=5000, parent=self)
