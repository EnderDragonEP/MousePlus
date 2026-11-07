"""Settings window: one tab per feature in a left rail (PyQt6-Fluent-Widgets MSFluentWindow, Mica on Windows 11)."""
from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices, QFont, QGuiApplication
from PyQt6.QtWidgets import QHBoxLayout, QWidget
from qfluentwidgets import (BodyLabel, ComboBoxSettingCard, ExpandLayout, FluentIcon as FIF, HyperlinkLabel, InfoBar,
                            InfoBarPosition, MessageBox, MSFluentWindow, NavigationItemPosition,
                            PrimaryPushSettingCard, RangeSettingCard, ScrollArea, SettingCard, SettingCardGroup,
                            SwitchSettingCard, TitleLabel, setCustomStyleSheet, setFont)

from . import APP_NAME, REPO_URL, __version__, config, icons
from .config import BYPASS_TEXTS, DURATION_TEXTS, GLIDE_TEXTS, TRIGGER_TEXTS, cfg
from .updates import UpdateChecker, is_newer


class Group(SettingCardGroup):
    """Setting card group with a Windows 11 Settings style header (14 px semibold)."""

    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        setFont(self.titleLabel, 14, QFont.Weight.DemiBold)
        self.titleLabel.adjustSize()

    def adjustSize(self):
        h = self.cardLayout.heightForWidth(self.width()) + self.titleLabel.height() + 12
        return self.resize(self.width(), h)


class MultiplierCard(RangeSettingCard):
    """Slider card that shows a value stored in tenths as a multiplier ("1.0×")."""

    def __init__(self, configItem, icon, title, content, parent=None):
        super().__init__(configItem, icon, title, content, parent)
        self.slider.setMinimumWidth(180)
        self._show(configItem.value)

    def setValue(self, value):
        super().setValue(value)
        self._show(value)

    def _show(self, value):
        self.valueLabel.setText(f"{value / 10:.1f}×")
        self.valueLabel.adjustSize()


class AboutCard(PrimaryPushSettingCard):
    """App name, then the version with a "View source" link, plus the update button."""

    def __init__(self, parent=None):
        super().__init__("Check for updates", icons.app_icon(), APP_NAME, f"Version {__version__}  ·", parent)
        self.sourceLink = HyperlinkLabel(QUrl(REPO_URL), "View source", self)
        # Match the description text; the card's QPushButton rule would make the link 14 px.
        link_size = "HyperlinkLabel { font-size: 11px; }"
        setCustomStyleSheet(self.sourceLink, link_size, link_size)
        # Put the link on the version line, next to the card's description.
        row = QHBoxLayout()
        row.setSpacing(6)
        self.vBoxLayout.removeWidget(self.contentLabel)
        row.addWidget(self.contentLabel, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self.sourceLink, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addStretch(1)
        self.vBoxLayout.addLayout(row)


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
        self.layoutCard = SettingCard(FIF.TILES, "Detected monitors", "…", self.monitors)
        self.monitors.addSettingCard(self.layoutCard)

        self.addWidgets(self.enableCard, self.monitors)
        self.setHint("When the cursor moves to another monitor, it lands at the same relative spot along the "
                     "shared edge, even where the monitors don't line up. It works while dragging, too.")

    def setMonitors(self, monitors):
        monitors = sorted(monitors, key=lambda m: (m.left, m.top))  # as arranged on the desk
        sizes = ", ".join(f"{m.width}×{m.height}" for m in monitors)
        if len(monitors) > 1:
            self.layoutCard.setContent(f"{len(monitors)} monitors · {sizes}")
        else:
            self.layoutCard.setContent(f"1 monitor · {sizes}. Connect another one to use this feature.")


class SmoothPage(Page):
    def __init__(self, parent=None):
        super().__init__("smoothPage", "Smooth Scroll", parent)
        self.enableCard = SwitchSettingCard(
            FIF.SCROLL, "Smooth Scroll", "Turn this feature on or off", cfg.smoothEnabled, self.view)

        self.scrolling = Group("Scrolling", self.view)
        self.animationCard = SwitchSettingCard(
            FIF.SPEED_MEDIUM, "Smooth scrolling", "Each wheel notch scrolls in small steps instead of one jump",
            cfg.smoothAnimation, self.scrolling)
        self.durationCard = ComboBoxSettingCard(
            cfg.smoothDuration, FIF.STOP_WATCH, "Animation time", "How long each notch takes to play out",
            texts=list(DURATION_TEXTS.values()), parent=self.scrolling)
        self.distanceCard = MultiplierCard(cfg.smoothDistance, FIF.SPEED_HIGH, "Scroll distance",
                                           "Distance per wheel notch", self.scrolling)
        self.scrolling.addSettingCards([self.animationCard, self.durationCard, self.distanceCard])

        self.inertia = Group("Inertia", self.view)
        self.inertiaCard = SwitchSettingCard(
            FIF.SEND, "Inertia", "A fast flick keeps scrolling and slows down gradually, like a touchpad",
            cfg.smoothInertia, self.inertia)
        self.glideCard = ComboBoxSettingCard(
            cfg.smoothGlide, FIF.SPEED_OFF, "Glide", "How far a flick keeps going",
            texts=list(GLIDE_TEXTS.values()), parent=self.inertia)
        self.inertia.addSettingCards([self.inertiaCard, self.glideCard])

        self.bypass = Group("Bypass", self.view)
        self.bypassCard = ComboBoxSettingCard(
            cfg.bypassKey, FIF.CANCEL, "Bypass key",
            "Hold it for normal notched scrolling. Ctrl + wheel (zoom) always passes through.",
            texts=list(BYPASS_TEXTS.values()), parent=self.bypass)
        self.bypass.addSettingCard(self.bypassCard)

        self.addWidgets(self.enableCard, self.scrolling, self.inertia, self.bypass)
        self.setHint("The mouse wheel scrolls like a touchpad: smooth steps, and a fast flick keeps going. "
                     "Back/Forward + wheel still scrolls sideways, unsmoothed.")
        cfg.smoothAnimation.valueChanged.connect(self._updateCards)
        cfg.smoothInertia.valueChanged.connect(self._updateCards)
        self._updateCards()

    def _updateCards(self, *_):
        animate = cfg.smoothAnimation.value
        self.durationCard.setEnabled(animate)
        self.inertiaCard.setEnabled(animate)  # inertia continues the animation
        self.glideCard.setEnabled(animate and cfg.smoothInertia.value)


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
        self.about.addSettingCard(self.aboutCard)

        self.addWidgets(self.general, self.about)
        self.setHint("Settings for the whole app. Right-click the tray icon to pause every feature at once.")


class SettingsWindow(MSFluentWindow):
    hiddenToTray = pyqtSignal()

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
        self.addSubInterface(self.smoothPage, FIF.SCROLL, "Smooth")
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
            self.resize(720, min(760, area.height() - 48))
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
        box = MessageBox(f"Version {release.version} is available",
                         f"You have version {__version__}. Open the download page on GitHub?", self)
        box.yesButton.setText("Download")
        box.cancelButton.setText("Later")
        if box.exec():
            QDesktopServices.openUrl(QUrl(release.url))

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
