"""Settings (auto-saved JSON via qfluentwidgets' QConfig) and the "Start with Windows" entry."""
import os
import shlex
import sys
import winreg
from pathlib import Path

from qfluentwidgets import (BoolValidator, ConfigItem, OptionsConfigItem, OptionsValidator, QConfig,
                            RangeConfigItem, RangeValidator, qconfig)

from . import APP_ID, CONFIG_FILE
from .horizontal import BACK, FORWARD, Settings

TRIGGERS = {
    "either": frozenset({BACK, FORWARD}),
    "back": frozenset({BACK}),
    "forward": frozenset({FORWARD}),
}
TRIGGER_TEXTS = {"either": "Back or Forward", "back": "Back", "forward": "Forward"}


class Config(QConfig):
    # App-wide
    disableInFullscreen = ConfigItem("General", "DisableInFullscreen", True, BoolValidator())
    trayHintShown = ConfigItem("General", "TrayHintShown", False, BoolValidator())

    # Horizontal Scroll
    horizontalEnabled = ConfigItem("HorizontalScroll", "Enabled", True, BoolValidator())
    trigger = OptionsConfigItem("HorizontalScroll", "Trigger", "either", OptionsValidator(list(TRIGGERS)))
    toggleMode = ConfigItem("HorizontalScroll", "ToggleMode", False, BoolValidator())
    horizontalReverse = ConfigItem("HorizontalScroll", "Reverse", False, BoolValidator())
    horizontalSpeed = RangeConfigItem("HorizontalScroll", "Speed", 10, RangeValidator(5, 30))  # tenths: 10 = 1.0x


cfg = Config()


def load():
    qconfig.load(CONFIG_FILE, cfg)


def horizontal_settings() -> Settings:
    return Settings(
        buttons=TRIGGERS[cfg.trigger.value],
        toggle_mode=cfg.toggleMode.value,
        skip_fullscreen=cfg.disableInFullscreen.value,
        reverse=cfg.horizontalReverse.value,
        speed=cfg.horizontalSpeed.value / 10,
    )


# -- Start with Windows (HKCU Run key, no admin rights needed) ---------------

# MOUSEPLUS_RUN_KEY points autostart (and its migration) at a scratch key, so a test build
# never touches the real entry. Together with a temporary APPDATA it sandboxes a test run.
RUN_KEY = os.environ.get("MOUSEPLUS_RUN_KEY", r"Software\Microsoft\Windows\CurrentVersion\Run")


def launch_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --tray'
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    main = Path(__file__).resolve().parent.parent / "main.py"
    return f'"{pythonw}" "{main}" --tray'


def run_value(name: str = APP_ID, key_path: str = RUN_KEY):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            return winreg.QueryValueEx(key, name)[0]
    except OSError:
        return None


def delete_run_value(name: str, key_path: str = RUN_KEY):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, name)
    except FileNotFoundError:
        pass


def is_autostart() -> bool:
    return run_value() is not None


def set_autostart(on: bool, key_path: str = RUN_KEY):
    if not on:
        delete_run_value(APP_ID, key_path)
        return
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, APP_ID, 0, winreg.REG_SZ, launch_command())


def refresh_autostart():
    """Re-point the entry at this copy if the program it names no longer exists."""
    value = run_value()
    if not value:
        return
    try:
        target = shlex.split(value, posix=False)[0].strip('"')
    except ValueError:
        target = ""
    if not Path(target).exists():
        try:
            set_autostart(True)
        except OSError:
            pass
