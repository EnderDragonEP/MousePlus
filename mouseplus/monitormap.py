"""Monitor layout drawn to scale for the Cursor tab, like Windows' Display settings.

Shaded bands join the edges that connect proportionally (in the accent color while Monitor
Cursor is on), and a dot follows the cursor while the tab is visible.
"""
from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QFontMetricsF, QPainter, QPen, QPolygonF
from qfluentwidgets import SimpleCardWidget, getFont, isDarkTheme, qconfig, themeColor

from . import winapi
from .cursor import links, monitor_at

_HEIGHT = 220
_PADDING = 20   # around the drawing
_GAP = 16       # between neighbouring monitors in the drawing; the bands fill it
_RADIUS = 6     # monitor corners
_FPS = 30       # cursor dot updates while visible; nothing runs while the tab is hidden


def _alpha(color: QColor, alpha: int) -> QColor:
    color = QColor(color)
    color.setAlpha(alpha)
    return color


class MonitorMap(SimpleCardWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(_HEIGHT)
        self.setFont(getFont(12))
        self.monitors = []
        self.links = []
        self.active = False  # Monitor Cursor is on
        self.cursor = None   # last cursor position, physical pixels
        self.timer = QTimer(self, interval=1000 // _FPS, timeout=self._followCursor)
        qconfig.themeChanged.connect(self._repaint)
        qconfig.themeColorChanged.connect(self._repaint)

    def setMonitors(self, monitors):
        self.monitors = list(monitors)
        self.links = links(self.monitors)
        self.update()

    def setActive(self, on: bool):
        self.active = on
        self.update()

    def showEvent(self, e):
        super().showEvent(e)
        self.timer.start()
        self._followCursor()

    def hideEvent(self, e):
        super().hideEvent(e)
        self.timer.stop()

    def _repaint(self, *_):
        self.update()

    def _followCursor(self):
        if self.window().isMinimized():
            return
        pos = winapi.cursor_pos()
        if pos != self.cursor:
            self.cursor = pos
            self.update()

    def paintEvent(self, e):
        super().paintEvent(e)  # the card
        if not self.monitors:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        dark = isDarkTheme()
        accent = themeColor()
        ink = QColor(255, 255, 255) if dark else QColor(0, 0, 0)

        # Fit the layout into the card, centred.
        left, top = min(m.left for m in self.monitors), min(m.top for m in self.monitors)
        width = max(m.right for m in self.monitors) - left
        height = max(m.bottom for m in self.monitors) - top
        area = QRectF(self.rect()).adjusted(_PADDING, _PADDING, -_PADDING, -_PADDING)
        scale = min(area.width() / width, area.height() / height)
        ox = area.x() + (area.width() - width * scale) / 2 - left * scale
        oy = area.y() + (area.height() - height * scale) / 2 - top * scale
        g = _GAP / 2

        def frame(m) -> QRectF:
            return QRectF(ox + m.left * scale + g, oy + m.top * scale + g, m.width * scale - _GAP,
                          m.height * scale - _GAP)

        # Bands across the gaps: each side's whole edge maps onto the other side's.
        base = accent if self.active else ink
        fill, guide = _alpha(base, 70 if self.active else 24), _alpha(base, 170 if self.active else 60)
        inset = g + _RADIUS  # keep to the straight part of the edges
        for link in self.links:
            def at(across, along, vertical=link.vertical):
                return QPointF(across, along) if vertical else QPointF(along, across)

            line = (ox if link.vertical else oy) + link.line * scale
            origin = oy if link.vertical else ox
            a0, a1 = origin + link.a[0] * scale + inset, origin + link.a[1] * scale - inset
            b0, b1 = origin + link.b[0] * scale + inset, origin + link.b[1] * scale - inset
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(fill)
            p.drawPolygon(QPolygonF([at(line - g, a0), at(line + g, b0), at(line + g, b1), at(line - g, a1)]))
            p.setPen(QPen(guide, 1.2))
            for t in (0.25, 0.5, 0.75):
                p.drawLine(at(line - g, a0 + t * (a1 - a0)), at(line + g, b0 + t * (b1 - b0)))

        # Monitors, with the one under the cursor highlighted.
        current = monitor_at(self.monitors, *self.cursor) if self.cursor else None
        metrics = QFontMetricsF(self.font())
        for i, m in enumerate(self.monitors):
            r = frame(m)
            if i == current:
                p.setPen(QPen(accent, 2))
                p.setBrush(_alpha(accent, 36))
            else:
                p.setPen(QPen(_alpha(ink, 46 if dark else 40), 1))
                p.setBrush(_alpha(ink, 18 if dark else 10))
            p.drawRoundedRect(r, _RADIUS, _RADIUS)
            text = f"{m.width} × {m.height}"
            if metrics.horizontalAdvance(text) + 12 < r.width() and metrics.height() + 8 < r.height():
                p.setPen(_alpha(ink, 170 if dark else 150))
                p.drawText(r, Qt.AlignmentFlag.AlignCenter, text)

        # The cursor, at the same relative spot on its monitor.
        if current is not None:
            m, r = self.monitors[current], frame(self.monitors[current])
            x, y = self.cursor
            dot = QPointF(r.left() + (x - m.left) / m.width * r.width(), r.top() + (y - m.top) / m.height * r.height())
            p.setPen(QPen(_alpha(ink, 220 if dark else 160), 2))
            p.setBrush(accent)
            p.drawEllipse(dot, 5, 5)
