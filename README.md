# Mouse Plus

![Banner](.asset/banner.png)

A small Windows tray app that gets more out of your mouse: scroll sideways with Back/Forward + wheel, move the cursor between monitors of different sizes without getting stuck, and scroll as smoothly as a touchpad.
Formerly called **Horizontal Scroll**: on first launch your settings and "Start with Windows" move over automatically.
The settings window follows the Fluent Design System: Mica background, light/dark mode and your accent color.

## Features

Each feature has its own tab and on/off switch. Monitor Cursor and Smooth Scroll start off; turn them on in their tabs.

### Horizontal Scroll

- 🖱️ **Hold to scroll sideways** – Hold Mouse Back or Forward and roll the wheel.
- 👆 **Clicks still work** – A quick click without scrolling still goes back or forward as usual.
- 🔒 **Toggle mode** – Click once to lock horizontal scrolling on, click again to turn it off.
- 🎛️ **Make it yours** – Pick the trigger button, scroll speed (0.5×–3.0×) and scroll direction.

### Monitor Cursor

- 🖥️ **Proportional crossing** – Leaving a monitor halfway down lands the cursor halfway down the next one, instead of at the same pixel row.
- 🚧 **No dead zones** – The cursor crosses anywhere along a shared edge, even where monitors only partly overlap.
- 🧭 **Any layout** – Side by side or stacked, mixed sizes and scaling, and monitors added or rearranged while it runs. It also works while dragging windows or files.
- 🗺️ **See it in action** – The Cursor tab draws your monitors to scale and shades the edges that connect. A dot follows your cursor, so you can watch where it lands.

### Smooth Scroll

- 🧈 **Smooth steps** – Each wheel notch scrolls in small steps instead of one jump. Pick the animation time and scroll distance.
- 🛝 **Inertia** – A fast flick keeps scrolling and slows down gradually. Set how strongly it glides (0.5×–3.0×) and how slowly it stops. A click, Back/Forward or the bypass key stop it at once. Turning the wheel back stops it too, and by default that notch only stops the glide instead of scrolling back (a setting). Optionally, a glide carries on in the next app when the cursor moves there.
- ⌨️ **Bypass key** – Hold Alt (or the key you pick) for normal notched scrolling and your apps' own Alt + wheel shortcuts. Ctrl + wheel (zoom) always passes through untouched.
- 🖼️ **Apps that scroll normally** – Smooth Scroll stays out of the apps on a list: apps that react to every wheel step, like image viewers that would otherwise flip through dozens of images per notch. XnView, IrfanView, FastStone, ImageGlass and other common viewers are on it already; add more from the Smooth tab.
- 🧪 **Overscroll bounce** – Experimental and off by default: the window springs back a little at the end of a page (see the limitations).

### Everywhere

- 🎮 **Game friendly** – Every feature steps aside in full-screen games, videos and F11 browsers.
- ⏸️ **Quick tray menu** – Right-click the tray icon to pause every feature at once, turn single features on or off, or download an update once one is out.
- 🚀 **Start with Windows** – An optional toggle, so it's always ready.
- 📌 **Lives in the tray** – Closing the window keeps it running.
- 🎨 **Feels like a native app** – Fluent Design with Mica, light/dark mode and your accent color, updated live.
- 🔔 **Update check** – On startup, Mouse Plus asks GitHub whether a new version is out and lets you know with a notification, or a message in the window if it's open. You can turn this off, or check any time, in the General tab.

## Limitations

- **Admin windows:** the features don't act over windows of apps running as administrator unless Mouse Plus also runs as administrator. Windows blocks this; the wheel simply scrolls normally there.
- **Horizontal Scroll:** apps without horizontal-scroll support won't scroll sideways. If mouse software (for example Logitech Options+) remaps Back/Forward to keystrokes, the app never sees the buttons. In hold mode, Back/Forward fires on button release, a moment later than usual.
- **Monitor Cursor:** while it's on, Mouse Plus decides every crossing itself, so Windows 11's "Ease cursor movement between displays" no longer applies at shared edges.
- **Smooth Scroll:** the few apps that ignore wheel steps smaller than a notch (some older apps and games) won't scroll smoothly. Apps that act on every wheel step, however small, jump much too far: add them to the apps that scroll normally (common image viewers are there already). Windows sends the wheel to the window under the cursor, so by default inertia stops when the cursor moves to another window. With "Carry the glide to other apps" on, it scrolls the new window instead, but still stops at apps on the list, the taskbar, full-screen apps and admin windows.
- **Overscroll bounce:** Windows can't tell other programs when an app hits the end of a page, so the bounce only works in apps with classic Windows scrollbars (like Notepad++), and never moves maximized windows. A snapped window may lose its snap layout after a bounce.
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
The old `%APPDATA%\HorizontalScroll` folder is left untouched after the move; you can delete it.

To try a build without touching your real settings or autostart entry, start it with `APPDATA` pointing at a scratch folder and `MOUSEPLUS_RUN_KEY` at a scratch registry key (for example `Software\MousePlusTest\Run`).

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
main.py                  entry point: single instance, migration, wires config, hook and UI
mouseplus/hook.py        the one low-level mouse hook (all features) + output thread (SendInput, animation)
mouseplus/router.py      which feature handles a wheel event (pure, unit-tested)
mouseplus/horizontal.py  Horizontal Scroll: trigger, click replay and toggle decisions (pure, unit-tested)
mouseplus/cursor.py      Monitor Cursor: proportional mapping between monitors (pure, unit-tested)
mouseplus/smooth.py      Smooth Scroll: easing and inertia (pure, unit-tested)
mouseplus/bounce.py      experimental overscroll bounce: edge test and spring (pure, unit-tested)
mouseplus/winapi.py      ctypes bindings: input injection, monitors, windows, timers, full-screen check
mouseplus/config.py      settings (qfluentwidgets QConfig) and the Run-key autostart
mouseplus/migrate.py     one-time move of settings and autostart from Horizontal Scroll
mouseplus/accent.py      Windows accent shades + watcher for accent changes
mouseplus/window.py      Fluent settings window, one tab per feature
mouseplus/monitormap.py  monitor layout drawing on the Cursor tab, with a live cursor dot
mouseplus/applist.py     the Smooth tab's list of apps that scroll normally, and the picker that adds one
mouseplus/tray.py        tray icon and menu
mouseplus/osd.py         toggle-mode on/off pill
mouseplus/icons.py       icons drawn in code + .ico writer for the build
tools/banner.py          draws the README banner (.asset/banner.png) from the app icon
```

## Disclaimer

This software is provided "as is", without warranty of any kind. Use it at your own risk; the author is not responsible for any damage or data loss resulting from its use.

Mouse Plus (formerly Horizontal Scroll) started as a personal project. It is not affiliated with or endorsed by Microsoft.

Claude Code was used in the development of this software.

## License

[GPL-3.0](LICENSE) © 2026 Ender Yang. Dependency information is in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
