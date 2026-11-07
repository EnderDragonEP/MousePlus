"""Fluent-style pill shown when toggle mode switches horizontal scrolling on or off."""
from PyQt6.QtCore import QPropertyAnimation, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QCursor, QFont, QFontMetrics, QGuiApplication, QPainter
from PyQt6.QtWidgets import QWidget
from qfluentwidgets import isDarkTheme, themeColor

from . import icons

_SHADOW = 12  # transparent margin used for the soft shadow
_HEIGHT = 48
_ICON = 20


class Osd(QWidget):
    def __init__(self):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowTransparentForInput
                         | Qt.WindowType.WindowDoesNotAcceptFocus | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        font = QFont()
        font.setFamilies(["Segoe UI Variable Text", "Segoe UI"])
        font.setPixelSize(14)
        self.setFont(font)
        self._on = False
        self._text = ""
        self._timer = QTimer(self, singleShot=True, interval=1200, timeout=lambda: self._fade(0.0))
        self._anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._anim.setDuration(150)
        self._anim.finished.connect(self._on_faded)

    def show_state(self, on: bool):
        self._on = on
        self._text = "Horizontal scrolling on" if on else "Horizontal scrolling off"
        width = 16 + _ICON + 12 + QFontMetrics(self.font()).horizontalAdvance(self._text) + 20 + 2 * _SHADOW
        height = _HEIGHT + 2 * _SHADOW
        self.resize(width, height)
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        area = screen.availableGeometry()
        self.move(area.center().x() - width // 2, area.bottom() - height - 56)
        self.update()
        if not self.isVisible():
            self.setWindowOpacity(0.0)
            self.show()
        self._fade(1.0)
        self._timer.start()

    def _fade(self, target: float):
        self._anim.stop()
        self._anim.setStartValue(self.windowOpacity())
        self._anim.setEndValue(target)
        self._anim.start()

    def _on_faded(self):
        if self._anim.endValue() == 0.0:
            self.hide()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        dark = isDarkTheme()
        pill = QRectF(self.rect()).adjusted(_SHADOW, _SHADOW, -_SHADOW, -_SHADOW)

        # soft shadow, then the layer with a hairline border (Fluent flyout look)
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(_SHADOW, 0, -2):
            p.setBrush(QColor(0, 0, 0, 5 if dark else 3))
            p.drawRoundedRect(pill.adjusted(-i, -i + 4, i, i + 4), 8 + i, 8 + i)
        p.setBrush(QColor(44, 44, 44) if dark else QColor(252, 252, 252))
        p.setPen(QColor(255, 255, 255, 24) if dark else QColor(0, 0, 0, 22))
        p.drawRoundedRect(pill.adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)

        fg = QColor(255, 255, 255) if dark else QColor(0, 0, 0, 228)
        icon_rect = QRectF(pill.left() + 16, pill.center().y() - _ICON / 2, _ICON, _ICON)
        if self._on:
            accent = themeColor()
            icons.paint_glyph(p, icon_rect, accent, fill=accent, wheel=QColor(0, 0, 0) if dark else QColor("white"))
        else:
            icons.paint_glyph(p, icon_rect, QColor(fg.red(), fg.green(), fg.blue(), 160))
        p.setPen(fg)
        p.setFont(self.font())
        text_rect = pill.adjusted(16 + _ICON + 12, 0, -20, 0)
        p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._text)
