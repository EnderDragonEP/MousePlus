r"""Draw the README banner (.asset/banner.png): the app icon, the name and the slogan.

Run it after changing the name, the slogan or the icon:

    .\.venv\Scripts\python tools\banner.py [out.png]

The icon comes from mouseplus/icons.py, so the banner always matches the app.
The background is transparent, so the banner suits GitHub's light and dark themes.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PyQt6.QtCore import QPointF, Qt  # noqa: E402
from PyQt6.QtGui import QColor, QFont, QFontInfo, QGuiApplication, QImage, QPainter  # noqa: E402

from mouseplus.icons import app_image  # noqa: E402

OUT = ROOT / ".asset" / "banner.png"
WIDTH, HEIGHT = 820, 220
ICON = (0, 10, 180)  # x, y and size
# Text, font (bold), size in px, color, and where the text's baseline starts.
LINES = (
    ("Mouse Plus", "Arial", 72, "#5ecbfe", QPointF(202, 110)),
    ("Get more out of your mouse.", "Segoe UI", 34, "#0269c1", QPointF(202, 163)),
)


def font(family: str, px: int) -> QFont:
    f = QFont(family)
    f.setPixelSize(px)
    f.setBold(True)
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    if QFontInfo(f).family() != family:
        sys.exit(f"The {family} font isn't installed.")
    return f


def banner() -> QImage:
    lines = [(text, font(family, px), QColor(color), origin) for text, family, px, color, origin in LINES]
    img = QImage(WIDTH, HEIGHT, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    x, y, size = ICON
    p.drawImage(x, y, app_image(size))
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    for text, f, color, origin in lines:
        p.setFont(f)
        p.setPen(color)
        p.drawText(origin, text)
    p.end()
    return img


if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT
    if not banner().save(str(out)):
        sys.exit(f"Couldn't write {out}")
    print(f"Wrote {out}")
