# Mouse Plus

![Banner](.asset/banner.png)

A small Windows tray app that adds to your mouse: hold **Mouse Back** or **Mouse Forward** and roll the wheel to scroll sideways.
Formerly called Horizontal Scroll; settings and autostart move over automatically.
The settings window follows the Fluent Design System: Mica background, light/dark mode and your accent color.

## Features

- 🖱️ **Hold to scroll sideways** – Hold Mouse Back or Forward and roll the wheel.
- 👆 **Clicks still work** – A quick click without scrolling still goes back or forward as usual.
- 🔒 **Toggle mode** – Click once to lock horizontal scrolling on, click again to turn it off.
- 🎮 **Game friendly** – Turn off automatically in full-screen games, videos and F11 browsers.
- 🎛️ **Make it yours** – Pick the trigger button, scroll speed (0.5×–3.0×) and scroll direction.
- 🚀 **Start with Windows** – An optional toggle, so it's always ready.
- 📌 **Lives in the tray** – Closing the window keeps it running. Right-click the tray icon to pause it or exit.
- 🎨 **Feels like Native App** – Fluent Design with Mica, light/dark mode and your accent color, updated live.
- 🔔 **Update check** – See if a new version is out, right from the About section.

## Limitations

- It doesn't work over windows of apps running as administrator unless Mouse Plus also runs as administrator. Windows blocks this.
- Apps without horizontal-scroll support won't scroll sideways.
- If mouse software (for example Logitech Options+) remaps Back/Forward to keystrokes, the app never sees the buttons.
- In hold mode, Back/Forward fires on button release, a moment later than usual.
- Single-file PyInstaller exes are sometimes flagged by antivirus heuristics. If that happens, build a one-folder version instead by moving `a.binaries`/`a.datas` into a `COLLECT` step in the spec.

## Run

- **Exe:** download `MousePlus.exe` from the [Releases](../../releases) page, or build it yourself (see below). It's a single file, and Python isn't needed. Start it with `--tray` to start hidden.
- **From source:**

  ```powershell
  python -m venv .venv
  .\.venv\Scripts\python -m pip install -r requirements.txt
  .\.venv\Scripts\pythonw main.py
  ```

  After that, you can also just double-click `run.pyw` to test your changes without building the exe.

Settings are saved to `%APPDATA%\MousePlus\config.json`, and errors are logged to `error.log` in the same folder.

## Build the exe

```powershell
powershell -ExecutionPolicy Bypass -File build.ps1
```

The script creates `.venv`, installs the requirements plus PyInstaller, and writes `dist\MousePlus.exe` (about 24 MB).

## Tests

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -v
```

## Layout

```text
main.py                entry point: single instance, wires config, hook and UI
mouseplus/horizontal.py  horizontal scroll and toggle decisions (pure, unit-tested)
mouseplus/hook.py      low-level mouse hook thread + SendInput injector thread
mouseplus/winapi.py    ctypes bindings, input injection, full-screen detection
mouseplus/config.py    settings (qfluentwidgets QConfig) and the Run-key autostart
mouseplus/migrate.py   one-time move of settings and autostart from Horizontal Scroll
mouseplus/accent.py    Windows accent shades + watcher for accent changes
mouseplus/window.py    Fluent settings window, one tab per feature
mouseplus/tray.py      tray icon and menu
mouseplus/osd.py       toggle-mode on/off pill
mouseplus/icons.py     icons drawn in code + .ico writer for the build
```

## Disclaimer

This software is provided "as is", without warranty of any kind. Use it at your own risk; the author is not responsible for any damage or data loss resulting from its use.

Mouse Plus (formerly Horizontal Scroll) started as a personal project. It is not affiliated with or endorsed by Microsoft.

Claude Code was used in the development of this software.

## License

[GPL-3.0](LICENSE) © 2026 Ender Yang. Dependency information is in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
