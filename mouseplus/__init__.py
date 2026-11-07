"""Mouse Plus - horizontal scrolling, proportional cursor movement between monitors and smooth scrolling."""
import os
from pathlib import Path

APP_NAME = "Mouse Plus"
APP_ID = "MousePlus"
__version__ = "2.0.0"
__author__ = "Ender Yang"
REPO_URL = "https://github.com/EnderDragonEP/MousePlus"  # "View source" and the update check

_APPDATA = Path(os.environ.get("APPDATA", Path.home()))
DATA_DIR = _APPDATA / APP_ID
CONFIG_FILE = DATA_DIR / "config.json"
LOG_FILE = DATA_DIR / "error.log"

# The app was called Horizontal Scroll up to 1.0.2; settings and autostart are migrated from it.
OLD_APP_ID = "HorizontalScroll"
OLD_CONFIG_FILE = _APPDATA / OLD_APP_ID / "config.json"
