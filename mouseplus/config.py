"""Settings (auto-saved JSON via qfluentwidgets' QConfig) and the "Start with Windows" entry."""
import os
import shlex
import sys
import winreg
from pathlib import Path

from qfluentwidgets import (BoolValidator, ConfigItem, ConfigValidator, OptionsConfigItem, OptionsValidator, QConfig,
                            RangeConfigItem, RangeValidator, qconfig)

from . import APP_ID, CONFIG_FILE
from .hook import HookSettings
from .horizontal import BACK, FORWARD, Settings
from .smooth import CONTRASTS, GLIDES, SmoothSettings

TRIGGERS = {
    "either": frozenset({BACK, FORWARD}),
    "back": frozenset({BACK}),
    "forward": frozenset({FORWARD}),
}
TRIGGER_TEXTS = {"either": "Back or Forward", "back": "Back", "forward": "Forward"}
CONTRAST_TEXTS = ("Off", "Low", "Medium", "High")  # the steps of CONTRASTS
GLIDE_TEXTS = {"short": "Short", "medium": "Medium", "long": "Long", "free": "Free spin"}
BYPASS_TEXTS = {"alt": "Alt", "ctrl": "Ctrl", "shift": "Shift", "win": "Win", "ctrl+alt": "Ctrl + Alt",
                "ctrl+shift": "Ctrl + Shift", "alt+shift": "Alt + Shift", "none": "None"}
# Scroll Inertia stays out of these programs at first. Image viewers flip one image per notch, so
# the glide after a quick flick would keep flipping images.
IMAGE_VIEWERS = {
    "xnviewmp.exe": "XnView MP",
    "xnview.exe": "XnView Classic",
    "i_view64.exe": "IrfanView",
    "i_view32.exe": "IrfanView 32-bit",
    "fsviewer.exe": "FastStone Image Viewer",
    "imageglass.exe": "ImageGlass",
    "honeyview.exe": "Honeyview",
    "bandiview.exe": "BandiView",
    "nomacs.exe": "nomacs",
    "jpegview.exe": "JPEGView",
    "qimgv.exe": "qimgv",
}


def program_label(program: str) -> str:
    """How the app list shows a program: "XnView MP (xnviewmp.exe)", or just the file when its name is unknown."""
    name = IMAGE_VIEWERS.get(program) or cfg.smoothAppNames.value.get(program)
    return f"{name} ({program})" if name else program


def program_names(values) -> list:
    """Program file names as stored: lowercase, trimmed, no blanks or duplicates, in order."""
    names = []
    for value in values if isinstance(values, list) else []:
        name = value.strip().lower() if isinstance(value, str) else ""
        if name and name not in names:
            names.append(name)
    return names


class ProgramListValidator(ConfigValidator):
    def validate(self, value):
        return value == program_names(value)

    def correct(self, value):
        return program_names(value)


class ProgramNamesValidator(ConfigValidator):
    """Program file -> name: lowercase files, trimmed names, no blanks."""

    def validate(self, value):
        return value == self.correct(value)

    def correct(self, value):
        if not isinstance(value, dict):
            return {}
        return {program.strip().lower(): name.strip() for program, name in value.items()
                if isinstance(program, str) and isinstance(name, str) and program.strip() and name.strip()}


class Config(QConfig):
    # App-wide
    disableInFullscreen = ConfigItem("General", "DisableInFullscreen", True, BoolValidator())
    checkUpdates = ConfigItem("General", "CheckForUpdates", True, BoolValidator())  # on startup
    trayHintShown = ConfigItem("General", "TrayHintShown", False, BoolValidator())

    # Horizontal Scroll
    horizontalEnabled = ConfigItem("HorizontalScroll", "Enabled", True, BoolValidator())
    trigger = OptionsConfigItem("HorizontalScroll", "Trigger", "either", OptionsValidator(list(TRIGGERS)))
    toggleMode = ConfigItem("HorizontalScroll", "ToggleMode", False, BoolValidator())
    horizontalReverse = ConfigItem("HorizontalScroll", "Reverse", False, BoolValidator())
    horizontalSpeed = RangeConfigItem("HorizontalScroll", "Speed", 10, RangeValidator(5, 30))  # tenths: 10 = 1.0x

    # Monitor Cursor
    cursorEnabled = ConfigItem("MonitorCursor", "Enabled", False, BoolValidator())

    # Scroll Inertia (stored under "SmoothScroll", its first name)
    smoothEnabled = ConfigItem("SmoothScroll", "Enabled", False, BoolValidator())  # the Inertia switch
    smoothGlide = OptionsConfigItem("SmoothScroll", "Glide", "medium", OptionsValidator(list(GLIDE_TEXTS)))
    smoothFlick = RangeConfigItem("SmoothScroll", "FlickNotches", 3, RangeValidator(2, 6))  # quick notches
    smoothContrast = RangeConfigItem("SmoothScroll", "FlickContrast", 1, RangeValidator(0, len(CONTRASTS) - 1))
    smoothMomentum = RangeConfigItem("SmoothScroll", "InertiaMultiplier", 10, RangeValidator(5, 30))  # tenths
    smoothBrake = ConfigItem("SmoothScroll", "ReverseStopsGlide", True, BoolValidator())
    smoothCarry = ConfigItem("SmoothScroll", "CarryToOtherApps", False, BoolValidator())
    bypassKey = OptionsConfigItem("SmoothScroll", "BypassKey", "alt", OptionsValidator(list(BYPASS_TEXTS)))
    smoothExcluded = ConfigItem("SmoothScroll", "ExcludedApps", list(IMAGE_VIEWERS), ProgramListValidator())
    smoothAppNames = ConfigItem("SmoothScroll", "AppNames", {}, ProgramNamesValidator())  # apps added by hand
    smoothBounce = ConfigItem("SmoothScroll", "Bounce", False, BoolValidator())  # experimental

    @classmethod
    def featureItems(cls) -> list:
        """The on/off switch of every feature."""
        return [cls.horizontalEnabled, cls.cursorEnabled, cls.smoothEnabled]

    @classmethod
    def hookItems(cls) -> list:
        """Every setting the mouse hook depends on."""
        return [*cls.featureItems(), cls.trigger, cls.toggleMode, cls.horizontalReverse, cls.horizontalSpeed,
                cls.disableInFullscreen, cls.smoothMomentum, cls.smoothGlide, cls.smoothBrake, cls.smoothCarry,
                cls.smoothFlick, cls.smoothContrast, cls.bypassKey, cls.smoothExcluded, cls.smoothBounce]


cfg = Config()


def load():
    qconfig.load(CONFIG_FILE, cfg)


def any_feature_on() -> bool:
    return any(item.value for item in cfg.featureItems())


def hook_settings() -> HookSettings:
    horizontal = cfg.horizontalEnabled.value
    return HookSettings(
        horizontal=Settings(
            buttons=TRIGGERS[cfg.trigger.value] if horizontal else frozenset(),  # no trigger: feature off
            toggle_mode=horizontal and cfg.toggleMode.value,
            skip_fullscreen=cfg.disableInFullscreen.value,
            reverse=cfg.horizontalReverse.value,
            speed=cfg.horizontalSpeed.value / 10,
        ),
        cursor=cfg.cursorEnabled.value,
        smooth=smooth_settings(),
        bypass=frozenset() if cfg.bypassKey.value == "none" else frozenset(cfg.bypassKey.value.split("+")),
        excluded=frozenset(cfg.smoothExcluded.value),
        skip_fullscreen=cfg.disableInFullscreen.value,
    )


def smooth_settings():
    """None when Scroll Inertia is off."""
    if not cfg.smoothEnabled.value:
        return None
    return SmoothSettings(
        glide=GLIDES.get(cfg.smoothGlide.value, GLIDES["long"]),
        free_spin=cfg.smoothGlide.value == "free",
        momentum=cfg.smoothMomentum.value / 10,
        flick=cfg.smoothFlick.value,
        contrast=CONTRASTS[cfg.smoothContrast.value],
        brake=cfg.smoothBrake.value,
        carry=cfg.smoothCarry.value,
        bounce=cfg.smoothBounce.value,
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
