"""Settings (auto-saved JSON via qfluentwidgets' QConfig) and the "Start with Windows" entry."""
import os
import shlex
import sys
import winreg
from pathlib import Path

from qfluentwidgets import (BoolValidator, ConfigItem, OptionsConfigItem, OptionsValidator, QConfig,
                            RangeConfigItem, RangeValidator, qconfig)

from . import APP_ID, CONFIG_FILE
from .hook import HookSettings
from .horizontal import BACK, FORWARD, Settings
from .smooth import DURATIONS, GLIDES, SmoothSettings

TRIGGERS = {
    "either": frozenset({BACK, FORWARD}),
    "back": frozenset({BACK}),
    "forward": frozenset({FORWARD}),
}
TRIGGER_TEXTS = {"either": "Back or Forward", "back": "Back", "forward": "Forward"}
DURATION_TEXTS = {"fast": "Fast", "normal": "Normal", "slow": "Slow"}
GLIDE_TEXTS = {"short": "Short", "medium": "Medium", "long": "Long"}
BYPASS_TEXTS = {"alt": "Alt", "ctrl": "Ctrl", "shift": "Shift", "win": "Win", "ctrl+alt": "Ctrl + Alt",
                "ctrl+shift": "Ctrl + Shift", "alt+shift": "Alt + Shift", "none": "None"}


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

    # Monitor Cursor
    cursorEnabled = ConfigItem("MonitorCursor", "Enabled", False, BoolValidator())

    # Smooth Scroll
    smoothEnabled = ConfigItem("SmoothScroll", "Enabled", False, BoolValidator())
    smoothAnimation = ConfigItem("SmoothScroll", "Animation", True, BoolValidator())
    smoothDuration = OptionsConfigItem("SmoothScroll", "AnimationTime", "normal", OptionsValidator(list(DURATIONS)))
    smoothDistance = RangeConfigItem("SmoothScroll", "Distance", 10, RangeValidator(5, 30))  # tenths
    smoothInertia = ConfigItem("SmoothScroll", "Inertia", True, BoolValidator())
    smoothGlide = OptionsConfigItem("SmoothScroll", "Glide", "medium", OptionsValidator(list(GLIDES)))
    smoothMomentum = RangeConfigItem("SmoothScroll", "InertiaMultiplier", 10, RangeValidator(5, 30))  # tenths
    smoothBrake = ConfigItem("SmoothScroll", "ReverseStopsGlide", True, BoolValidator())
    bypassKey = OptionsConfigItem("SmoothScroll", "BypassKey", "alt", OptionsValidator(list(BYPASS_TEXTS)))
    smoothBounce = ConfigItem("SmoothScroll", "Bounce", False, BoolValidator())  # experimental

    @classmethod
    def featureItems(cls) -> list:
        """The on/off switch of every feature."""
        return [cls.horizontalEnabled, cls.cursorEnabled, cls.smoothEnabled]

    @classmethod
    def hookItems(cls) -> list:
        """Every setting the mouse hook depends on."""
        return [*cls.featureItems(), cls.trigger, cls.toggleMode, cls.horizontalReverse, cls.horizontalSpeed,
                cls.disableInFullscreen, cls.smoothAnimation, cls.smoothDuration, cls.smoothDistance,
                cls.smoothInertia, cls.smoothMomentum, cls.smoothGlide, cls.smoothBrake, cls.bypassKey, cls.smoothBounce]


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
        skip_fullscreen=cfg.disableInFullscreen.value,
    )


def smooth_settings():
    """None when Smooth Scroll is off or would do nothing (no animation, 1.0x distance, no bounce)."""
    animate, distance, bounce = cfg.smoothAnimation.value, cfg.smoothDistance.value / 10, cfg.smoothBounce.value
    if not cfg.smoothEnabled.value or (not animate and distance == 1.0 and not bounce):
        return None
    return SmoothSettings(
        animate=animate,
        duration=DURATIONS[cfg.smoothDuration.value],
        distance=distance,
        inertia=animate and cfg.smoothInertia.value,  # inertia continues the animation
        glide=GLIDES[cfg.smoothGlide.value],
        momentum=cfg.smoothMomentum.value / 10,
        brake=cfg.smoothBrake.value,
        bounce=bounce,
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
