<!-- markdownlint-configure-file { "MD024": { "siblings_only": true } } -->
# Changelog

All notable changes to Mouse Plus (formerly Horizontal Scroll) are listed here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the versions follow [Semantic Versioning](https://semver.org/).

## [2.0.2] - 2026-11-11

### Changed

- **Overscroll bounce** works without Inertia: with Inertia off and the bounce on, each notch scrolls as usual and the window still springs back at the end of a page.

## [2.0.1] - 2026-11-10

### Added

- **Flick contrast** on the Inertia tab (Off, Low, Medium or High): hard flicks glide disproportionately farther than gentle ones. Flicks up to about 40 notches a second glide just as before. It starts at Low; Off is the 2.0.0 behavior.

### Changed

- **Scroll Inertia works with Horizontal Scroll:** a fast flick while holding Back or Forward glides on sideways too, whenever Scroll Inertia is on. The "Sideways too" switch is gone.

### Fixed

- Flicking again during a glide felt weaker than the first flick, even at the same speed. Each flick now scrolls as fast as the first one, and its glide starts at least as fast.

## [2.0.0] - 2026-11-08

Horizontal Scroll is now **Mouse Plus**. Besides scrolling sideways, it can move your cursor between monitors of different sizes without getting stuck, and keep scrolling after a fast flick, like a free-spinning wheel. Each feature has its own tab and on/off switch; the new ones start off.

### Added

- **Monitor Cursor**
  - Leaving a monitor halfway down lands the cursor halfway down the next one, even when the monitors are different sizes.
  - No more dead zones where monitors only partly line up. It works while dragging windows and files, with side-by-side or stacked layouts, mixed sizes and scaling, and monitors added or rearranged while it runs.
  - Pen, touch and remote-control cursor moves go exactly where they point, and games that lock the cursor are left alone.
  - The Cursor tab shows a live map of your monitors, with a dot that follows your cursor.
- **Scroll Inertia**
  - **Inertia:** a fast flick keeps scrolling and slows down gradually, while a single notch scrolls one notch at once, as usual. The glide sends whole notches, as a real wheel does, so apps handle it like normal scrolling. Choose how many quick notches make a flick (2–6), how strongly it glides (0.5×–3.0×) and how it slows down.
  - **Free spin:** a glide that coasts like a free-spinning wheel. A hard flick keeps going for seconds and hundreds of lines, and each further notch spins it faster.
  - Turning the wheel back stops a glide, by default without scrolling back. Optionally, a glide carries on into the next app your cursor moves to.
  - Back/Forward + wheel glides on sideways after a flick too.
  - **Bypass key:** hold Alt (or a key you choose) to scroll without inertia and to use your apps' own Alt + wheel shortcuts. Ctrl + wheel (zoom) is never touched.
  - **Apps that scroll normally:** Scroll Inertia stays out of apps where a glide gets in the way, like image viewers. XnView, IrfanView, FastStone, ImageGlass and other common viewers are on the list already, and you can add any open app or program.
  - **Overscroll bounce:** experimental and off by default.
- **Tray menu:** a switch for each feature, and "Download version X.Y.Z" once an update is out.
- **Update check on startup:** a notification, or a message in the settings window if it's open. You can turn it off in General.
- **Changelog** and **Licenses** links in Settings → General → About.
- A new app icon with a "+" badge.

### Changed

- Renamed from Horizontal Scroll to Mouse Plus. On first launch, your settings and "Start with Windows" move over automatically, and Mouse Plus reminds you to quit Horizontal Scroll if it's still running.
- The settings window has a tab for each feature (Horizontal, Cursor and Inertia) plus General.
- "Disable in full-screen apps" now covers every feature.
- The tray menu's header shows the state and the version, and Pause pauses every feature at once.

### Removed

- The tray menu's "Switch to toggle mode" item. Toggle mode is still in Settings → Horizontal.

**Upgrading from Horizontal Scroll:** quit it from its tray icon, then run `MousePlus.exe`. After the first run, you can delete `HorizontalScroll.exe` and the `%APPDATA%\HorizontalScroll` folder.

## [1.0.2] - 2026-10-05

### Changed

- The tray menu opens with a status header that says what the app is doing and how to use it right now. Its items are Pause/Resume, Switch to hold/toggle mode, Check for updates and Quit (formerly Exit).

### Fixed

- The update check understands release tags written like "v.1.0.1".

## [1.0.1] - 2026-10-05

### Changed

- The About card shows the version with a "View source" link next to it, instead of a copyright line.

## [1.0.0] - 2026-10-04

The first release, as Horizontal Scroll.

### Added

- Hold Mouse Back or Forward and roll the wheel to scroll sideways. A quick click still goes back or forward as usual.
- Toggle mode: click once to lock horizontal scrolling on, click again to turn it off.
- Choose the trigger button, the scroll speed (0.5×–3.0×) and the scroll direction.
- It turns off automatically in full-screen games, videos and F11 browsers.
- Start with Windows, and a tray icon that keeps it running when the window is closed.
- A Fluent Design settings window with Mica, light/dark mode and your Windows accent color, updated live.
- An About section with "View source" and "Check for updates".

[2.0.2]: https://github.com/EnderDragonEP/MousePlus/compare/v2.0.1...v2.0.2
[2.0.1]: https://github.com/EnderDragonEP/MousePlus/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/EnderDragonEP/MousePlus/compare/v1.0.2...v2.0.0
[1.0.2]: https://github.com/EnderDragonEP/MousePlus/compare/v.1.0.1...v1.0.2
[1.0.1]: https://github.com/EnderDragonEP/MousePlus/compare/v1.0.0...v.1.0.1
[1.0.0]: https://github.com/EnderDragonEP/MousePlus/releases/tag/v1.0.0
