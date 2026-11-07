"""One-time move from Horizontal Scroll (up to 1.0.2) to Mouse Plus: settings and autostart."""
import json
import logging
from pathlib import Path

from . import CONFIG_FILE, OLD_APP_ID, OLD_CONFIG_FILE, config

log = logging.getLogger("mouseplus")

# (old group, old name) -> (new group, new name)
_KEY_MAP = {
    ("General", "Enabled"): ("HorizontalScroll", "Enabled"),
    ("General", "Trigger"): ("HorizontalScroll", "Trigger"),
    ("General", "ToggleMode"): ("HorizontalScroll", "ToggleMode"),
    ("Scrolling", "Reverse"): ("HorizontalScroll", "Reverse"),
    ("Scrolling", "Speed"): ("HorizontalScroll", "Speed"),
    ("General", "DisableInFullscreen"): ("General", "DisableInFullscreen"),
    ("General", "TrayHintShown"): ("General", "TrayHintShown"),
}


def map_old_settings(old: dict) -> dict:
    """Translate a Horizontal Scroll config.json dict into the Mouse Plus layout.

    Unknown keys (theme mode and color, which are recomputed at startup) are dropped.
    """
    new = {}
    for (group, name), (new_group, new_name) in _KEY_MAP.items():
        section = old.get(group)
        if isinstance(section, dict) and name in section:
            new.setdefault(new_group, {})[new_name] = section[name]
    return new


def migrate_settings(old_file: Path = OLD_CONFIG_FILE, new_file: Path = CONFIG_FILE) -> bool:
    """Copy the old settings once. The old folder is left untouched."""
    if new_file.exists() or not old_file.exists():
        return False
    try:
        old = json.loads(old_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    new_file.parent.mkdir(parents=True, exist_ok=True)
    new_file.write_text(json.dumps(map_old_settings(old), indent=4), encoding="utf-8")
    return True


def migrate_autostart(key_path: str = config.RUN_KEY) -> bool:
    """Replace the old "Start with Windows" entry so the two apps never both start."""
    if config.run_value(OLD_APP_ID, key_path) is None:
        return False
    config.set_autostart(True, key_path)
    config.delete_run_value(OLD_APP_ID, key_path)
    return True


def migrate():
    try:
        if migrate_settings():
            log.info("Settings migrated from %s", OLD_CONFIG_FILE)
    except OSError:
        log.exception("Couldn't migrate the old settings")
    try:
        if migrate_autostart():
            log.info("Autostart entry moved from %s", OLD_APP_ID)
    except OSError:
        log.exception("Couldn't move the old autostart entry")
