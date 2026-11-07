"""Win32 bindings (ctypes) for the mouse hook, input injection and full-screen detection."""
import ctypes
import os
from ctypes import wintypes

from .cursor import Rect

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
dwmapi = ctypes.WinDLL("dwmapi")

LRESULT = wintypes.LPARAM
ULONG_PTR = ctypes.c_size_t

WH_MOUSE_LL = 14
HC_ACTION = 0
WM_QUIT = 0x0012
WM_TIMER = 0x0113
WM_APP = 0x8000
WM_MOUSEMOVE = 0x0200
WM_MOUSEWHEEL = 0x020A
WM_XBUTTONDOWN = 0x020B
WM_XBUTTONUP = 0x020C
PM_NOREMOVE = 0x0000

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_SHIFT, VK_CONTROL, VK_MENU, VK_LWIN, VK_RWIN = 0x10, 0x11, 0x12, 0x5B, 0x5C
VK_MASK = 0xE8  # unassigned: tapping it while Alt/Win is held keeps a menu from opening on release
GA_PARENT, GA_ROOT = 1, 2
WS_VSCROLL = 0x00200000
SB_VERT = 1
SIF_RANGE, SIF_PAGE, SIF_POS = 0x1, 0x2, 0x4
SWP_NOSIZE, SWP_NOZORDER, SWP_NOACTIVATE, SWP_NOOWNERZORDER, SWP_ASYNCWINDOWPOS = 0x1, 0x4, 0x10, 0x200, 0x4000
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TOKEN_QUERY = 0x0008
TOKEN_INTEGRITY_LEVEL = 25
CREATE_WAITABLE_TIMER_HIGH_RESOLUTION = 0x2
TIMER_ALL_ACCESS = 0x1F0003
WAIT_TIMEOUT = 0x102
MOUSEEVENTF_XDOWN = 0x0080
MOUSEEVENTF_XUP = 0x0100
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x1000

ASFW_ANY = 0xFFFFFFFF
REG_NOTIFY_CHANGE_LAST_SET = 0x4
INFINITE = 0xFFFFFFFF
WAIT_OBJECT_0 = 0
MONITOR_DEFAULTTONEAREST = 2
GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_CAPTION = 0x00C00000
WS_EX_TOOLWINDOW = 0x00000080
GW_OWNER = 4
DWMWA_CLOAKED = 14

# Tags every event we inject (dwExtraInfo) so our own hook lets it through. Keep the value:
# Horizontal Scroll used the same tag, so an old copy and Mouse Plus ignore each other's events.
MAGIC = 0x48534352


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("pt", wintypes.POINT),
                ("mouseData", wintypes.DWORD),
                ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ULONG_PTR)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG),
                ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ULONG_PTR)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD),
                ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ULONG_PTR)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD),
                ("wParamL", wintypes.WORD),
                ("wParamH", wintypes.WORD)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


class SCROLLINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT),
                ("fMask", wintypes.UINT),
                ("nMin", ctypes.c_int),
                ("nMax", ctypes.c_int),
                ("nPage", wintypes.UINT),
                ("nPos", ctypes.c_int),
                ("nTrackPos", ctypes.c_int)]


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD),
                ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT),
                ("dwFlags", wintypes.DWORD)]


HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
MONITORENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
                                     ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def _fn(dll, name, restype, *argtypes):
    f = getattr(dll, name)
    f.restype = restype
    f.argtypes = argtypes
    return f


SetWindowsHookExW = _fn(user32, "SetWindowsHookExW", wintypes.HHOOK,
                        ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD)
CallNextHookEx = _fn(user32, "CallNextHookEx", LRESULT,
                     wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
UnhookWindowsHookEx = _fn(user32, "UnhookWindowsHookEx", wintypes.BOOL, wintypes.HHOOK)
GetMessageW = _fn(user32, "GetMessageW", wintypes.BOOL,
                  ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT)
PeekMessageW = _fn(user32, "PeekMessageW", wintypes.BOOL, ctypes.POINTER(wintypes.MSG),
                   wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT)
PostThreadMessageW = _fn(user32, "PostThreadMessageW", wintypes.BOOL,
                         wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
SetTimer = _fn(user32, "SetTimer", ULONG_PTR, wintypes.HWND, ULONG_PTR, wintypes.UINT, ctypes.c_void_p)
KillTimer = _fn(user32, "KillTimer", wintypes.BOOL, wintypes.HWND, ULONG_PTR)
SendInput = _fn(user32, "SendInput", wintypes.UINT, wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
GetForegroundWindow = _fn(user32, "GetForegroundWindow", wintypes.HWND)
GetWindowRect = _fn(user32, "GetWindowRect", wintypes.BOOL, wintypes.HWND, ctypes.POINTER(wintypes.RECT))
GetClassNameW = _fn(user32, "GetClassNameW", ctypes.c_int, wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
MonitorFromWindow = _fn(user32, "MonitorFromWindow", wintypes.HMONITOR, wintypes.HWND, wintypes.DWORD)
GetMonitorInfoW = _fn(user32, "GetMonitorInfoW", wintypes.BOOL, wintypes.HMONITOR, ctypes.POINTER(MONITORINFO))
IsZoomed = _fn(user32, "IsZoomed", wintypes.BOOL, wintypes.HWND)
GetWindowLongW = _fn(user32, "GetWindowLongW", wintypes.LONG, wintypes.HWND, ctypes.c_int)
AllowSetForegroundWindow = _fn(user32, "AllowSetForegroundWindow", wintypes.BOOL, wintypes.DWORD)
SetCursorPos = _fn(user32, "SetCursorPos", wintypes.BOOL, ctypes.c_int, ctypes.c_int)
GetCursorPos = _fn(user32, "GetCursorPos", wintypes.BOOL, ctypes.POINTER(wintypes.POINT))
EnumDisplayMonitors = _fn(user32, "EnumDisplayMonitors", wintypes.BOOL,
                          wintypes.HDC, ctypes.POINTER(wintypes.RECT), MONITORENUMPROC, wintypes.LPARAM)
GetCurrentThreadId = _fn(kernel32, "GetCurrentThreadId", wintypes.DWORD)
GetModuleHandleW = _fn(kernel32, "GetModuleHandleW", wintypes.HMODULE, wintypes.LPCWSTR)
SetCurrentProcessExplicitAppUserModelID = _fn(shell32, "SetCurrentProcessExplicitAppUserModelID",
                                              ctypes.c_long, wintypes.LPCWSTR)
RegNotifyChangeKeyValue = _fn(advapi32, "RegNotifyChangeKeyValue", wintypes.LONG,
                              wintypes.HKEY, wintypes.BOOL, wintypes.DWORD, wintypes.HANDLE, wintypes.BOOL)
CreateEventW = _fn(kernel32, "CreateEventW", wintypes.HANDLE,
                   ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR)
SetEvent = _fn(kernel32, "SetEvent", wintypes.BOOL, wintypes.HANDLE)
CloseHandle = _fn(kernel32, "CloseHandle", wintypes.BOOL, wintypes.HANDLE)
WaitForMultipleObjects = _fn(kernel32, "WaitForMultipleObjects", wintypes.DWORD,
                             wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE), wintypes.BOOL, wintypes.DWORD)
GetAsyncKeyState = _fn(user32, "GetAsyncKeyState", ctypes.c_short, ctypes.c_int)
WindowFromPoint = _fn(user32, "WindowFromPoint", wintypes.HWND, wintypes.POINT)
GetAncestor = _fn(user32, "GetAncestor", wintypes.HWND, wintypes.HWND, wintypes.UINT)
GetWindowThreadProcessId = _fn(user32, "GetWindowThreadProcessId", wintypes.DWORD,
                               wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
OpenProcess = _fn(kernel32, "OpenProcess", wintypes.HANDLE, wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
GetCurrentProcess = _fn(kernel32, "GetCurrentProcess", wintypes.HANDLE)
OpenProcessToken = _fn(advapi32, "OpenProcessToken", wintypes.BOOL,
                       wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE))
GetTokenInformation = _fn(advapi32, "GetTokenInformation", wintypes.BOOL, wintypes.HANDLE, ctypes.c_int,
                          ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD))
GetSidSubAuthorityCount = _fn(advapi32, "GetSidSubAuthorityCount", ctypes.POINTER(ctypes.c_ubyte), ctypes.c_void_p)
GetSidSubAuthority = _fn(advapi32, "GetSidSubAuthority", ctypes.POINTER(wintypes.DWORD),
                         ctypes.c_void_p, wintypes.DWORD)
CreateWaitableTimerExW = _fn(kernel32, "CreateWaitableTimerExW", wintypes.HANDLE,
                             ctypes.c_void_p, wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD)
SetWaitableTimer = _fn(kernel32, "SetWaitableTimer", wintypes.BOOL, wintypes.HANDLE,
                       ctypes.POINTER(ctypes.c_longlong), wintypes.LONG, ctypes.c_void_p, ctypes.c_void_p,
                       wintypes.BOOL)
CancelWaitableTimer = _fn(kernel32, "CancelWaitableTimer", wintypes.BOOL, wintypes.HANDLE)
GetScrollInfo = _fn(user32, "GetScrollInfo", wintypes.BOOL, wintypes.HWND, ctypes.c_int, ctypes.POINTER(SCROLLINFO))
IsIconic = _fn(user32, "IsIconic", wintypes.BOOL, wintypes.HWND)
IsWindowVisible = _fn(user32, "IsWindowVisible", wintypes.BOOL, wintypes.HWND)
SetWindowPos = _fn(user32, "SetWindowPos", wintypes.BOOL, wintypes.HWND, wintypes.HWND,
                   ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT)
GetDpiForWindow = _fn(user32, "GetDpiForWindow", wintypes.UINT, wintypes.HWND)
QueryFullProcessImageNameW = _fn(kernel32, "QueryFullProcessImageNameW", wintypes.BOOL, wintypes.HANDLE,
                                 wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD))
GetCurrentProcessId = _fn(kernel32, "GetCurrentProcessId", wintypes.DWORD)
EnumWindows = _fn(user32, "EnumWindows", wintypes.BOOL, WNDENUMPROC, wintypes.LPARAM)
GetWindow = _fn(user32, "GetWindow", wintypes.HWND, wintypes.HWND, wintypes.UINT)
GetWindowTextW = _fn(user32, "GetWindowTextW", ctypes.c_int, wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
GetWindowTextLengthW = _fn(user32, "GetWindowTextLengthW", ctypes.c_int, wintypes.HWND)
FindWindowExW = _fn(user32, "FindWindowExW", wintypes.HWND,
                    wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR)
DwmGetWindowAttribute = _fn(dwmapi, "DwmGetWindowAttribute", ctypes.c_long,
                            wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD)


def _mouse_input(flags: int, data: int = 0) -> INPUT:
    inp = INPUT(type=INPUT_MOUSE)
    inp.mi = MOUSEINPUT(0, 0, data & 0xFFFFFFFF, flags, 0, MAGIC)
    return inp


def send_hwheel(delta: int):
    """Inject a horizontal wheel event at the cursor (positive = scroll right)."""
    inp = _mouse_input(MOUSEEVENTF_HWHEEL, delta)
    SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def send_wheel(delta: int):
    """Inject a vertical wheel event at the cursor (positive = away from the user)."""
    inp = _mouse_input(MOUSEEVENTF_WHEEL, delta)
    SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def send_mask_key():
    """Tap an unassigned key, so releasing a held Alt/Win doesn't open a menu bar or Start."""
    inputs = (INPUT * 2)()
    for inp, flags in zip(inputs, (0, KEYEVENTF_KEYUP)):
        inp.type = INPUT_KEYBOARD
        inp.ki = KEYBDINPUT(VK_MASK, 0, flags, 0, MAGIC)
    SendInput(2, inputs, ctypes.sizeof(INPUT))


def held_modifiers() -> frozenset:
    """The modifier keys held right now: any of "alt", "ctrl", "shift", "win"."""
    down = lambda vk: GetAsyncKeyState(vk) & 0x8000
    held = set()
    if down(VK_MENU):
        held.add("alt")
    if down(VK_CONTROL):
        held.add("ctrl")
    if down(VK_SHIFT):
        held.add("shift")
    if down(VK_LWIN) or down(VK_RWIN):
        held.add("win")
    return frozenset(held)


def root_window_at(x: int, y: int):
    """The top-level window under a screen point."""
    hwnd = WindowFromPoint(wintypes.POINT(x, y))
    return GetAncestor(hwnd, GA_ROOT) if hwnd else None


def window_at(x: int, y: int):
    """The window under a screen point, child windows included. In a Store app that's the
    app's own content window, not the frame Windows draws around it."""
    return WindowFromPoint(wintypes.POINT(x, y))


def program_path(hwnd) -> str:
    """Full path of the program that owns a window; '' if it can't be read."""
    pid = wintypes.DWORD()
    GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    process = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not process:
        return ""
    try:
        size = wintypes.DWORD(1024)
        path = ctypes.create_unicode_buffer(size.value)
        return path.value if QueryFullProcessImageNameW(process, 0, path, ctypes.byref(size)) else ""
    finally:
        CloseHandle(process)


def program_name(hwnd) -> str:
    """Lowercase file name of the program that owns a window, e.g. 'xnviewmp.exe'; '' if unknown."""
    return os.path.basename(program_path(hwnd)).lower()


def open_apps() -> list:
    """(program path, window title) for each app with a window on the taskbar, front to back:
    one entry per program, this app left out."""
    apps, seen, own = [], set(), GetCurrentProcessId()
    name = ctypes.create_unicode_buffer(64)

    def collect(hwnd, _):
        if (not IsWindowVisible(hwnd) or GetWindow(hwnd, GW_OWNER)
                or GetWindowLongW(hwnd, GWL_EXSTYLE) & WS_EX_TOOLWINDOW):
            return True
        cloaked = wintypes.DWORD()  # hidden by Windows: other virtual desktops, suspended Store apps
        DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
        length = GetWindowTextLengthW(hwnd)
        GetClassNameW(hwnd, name, len(name))
        if cloaked.value or not length or name.value in ("Progman", "WorkerW"):  # the desktop
            return True
        owner = hwnd
        if name.value == "ApplicationFrameWindow":  # a Store app: the app itself is a child window
            owner = FindWindowExW(hwnd, None, "Windows.UI.Core.CoreWindow", None)
            if not owner:
                return True
        pid = wintypes.DWORD()
        GetWindowThreadProcessId(owner, ctypes.byref(pid))
        path = program_path(owner) if pid.value != own else ""
        if path and path.lower() not in seen:
            seen.add(path.lower())
            title = ctypes.create_unicode_buffer(length + 1)
            GetWindowTextW(hwnd, title, length + 1)
            apps.append((path, title.value))
        return True

    EnumWindows(WNDENUMPROC(collect), 0)
    return apps


def _integrity(process) -> int:
    """Integrity level RID of a process handle (e.g. 0x2000 medium, 0x3000 high); -1 if unknown."""
    token = wintypes.HANDLE()
    if not OpenProcessToken(process, TOKEN_QUERY, ctypes.byref(token)):
        return -1
    try:
        size = wintypes.DWORD()
        GetTokenInformation(token, TOKEN_INTEGRITY_LEVEL, None, 0, ctypes.byref(size))
        buffer = ctypes.create_string_buffer(size.value)
        if not GetTokenInformation(token, TOKEN_INTEGRITY_LEVEL, buffer, size, ctypes.byref(size)):
            return -1
        sid = ctypes.c_void_p.from_buffer(buffer).value  # TOKEN_MANDATORY_LABEL.Label.Sid
        count = GetSidSubAuthorityCount(sid).contents.value
        return GetSidSubAuthority(sid, count - 1).contents.value
    finally:
        CloseHandle(token)


_OWN_INTEGRITY = None


def window_is_elevated(hwnd) -> bool:
    """True when the window's process runs at a higher integrity level than this app
    (e.g. an app started as administrator). Windows blocks injected input there.
    A process that can't be inspected counts as elevated, so its input is left alone."""
    global _OWN_INTEGRITY
    if _OWN_INTEGRITY is None:
        _OWN_INTEGRITY = _integrity(GetCurrentProcess())
    pid = wintypes.DWORD()
    GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    process = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not process:
        return True
    try:
        level = _integrity(process)
    finally:
        CloseHandle(process)
    return level < 0 or level > _OWN_INTEGRITY


def send_xclick(button: int):
    """Inject a full click (down + up) of XBUTTON1 (Back) or XBUTTON2 (Forward)."""
    inputs = (INPUT * 2)(_mouse_input(MOUSEEVENTF_XDOWN, button),
                         _mouse_input(MOUSEEVENTF_XUP, button))
    SendInput(2, inputs, ctypes.sizeof(INPUT))


def cursor_pos() -> tuple:
    point = wintypes.POINT()
    GetCursorPos(ctypes.byref(point))
    return point.x, point.y


def monitor_rects() -> list:
    """Every monitor's rectangle in physical pixels (Qt makes the process per-monitor DPI aware)."""
    rects = []

    def collect(monitor, dc, rect, data):
        r = rect.contents
        rects.append(Rect(r.left, r.top, r.right, r.bottom))
        return True

    EnumDisplayMonitors(None, None, MONITORENUMPROC(collect), 0)
    return rects


def classic_scrollbar_at(x: int, y: int):
    """The window under a point, or its nearest parent, that has a classic vertical scrollbar,
    as (window, pos, min, max, page); None when there is none (most modern apps)."""
    hwnd = WindowFromPoint(wintypes.POINT(x, y))
    root = GetAncestor(hwnd, GA_ROOT) if hwnd else None
    while hwnd:
        if GetWindowLongW(hwnd, GWL_STYLE) & WS_VSCROLL:
            info = SCROLLINFO(cbSize=ctypes.sizeof(SCROLLINFO), fMask=SIF_RANGE | SIF_PAGE | SIF_POS)
            if GetScrollInfo(hwnd, SB_VERT, ctypes.byref(info)):
                return hwnd, info.nPos, info.nMin, info.nMax, info.nPage
        if hwnd == root:
            break
        hwnd = GetAncestor(hwnd, GA_PARENT)
    return None


def bounceable(root):
    """(x, y, scale) of a top-level window that may be nudged, or None: it must be visible
    and not minimized, maximized, full screen or elevated."""
    if not root or not IsWindowVisible(root) or IsIconic(root) or IsZoomed(root):
        return None
    if is_fullscreen(root) or window_is_elevated(root):
        return None
    rect = wintypes.RECT()
    if not GetWindowRect(root, ctypes.byref(rect)):
        return None
    return rect.left, rect.top, (GetDpiForWindow(root) or 96) / 96


def window_position(hwnd):
    rect = wintypes.RECT()
    return (rect.left, rect.top) if GetWindowRect(hwnd, ctypes.byref(rect)) else None


def move_window(hwnd, x: int, y: int):
    """Move without resizing, activating or changing the z-order."""
    SetWindowPos(hwnd, None, x, y, 0, 0,
                 SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_NOOWNERZORDER | SWP_ASYNCWINDOWPOS)


_SHELL_CLASSES = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"}


def foreground_is_fullscreen() -> bool:
    """True when the foreground window covers its whole monitor (games, F11, videos)."""
    return is_fullscreen(GetForegroundWindow())


def is_fullscreen(hwnd) -> bool:
    """True when the window covers its whole monitor (games, F11, videos)."""
    if not hwnd:
        return False
    name = ctypes.create_unicode_buffer(64)
    GetClassNameW(hwnd, name, 64)
    if name.value in _SHELL_CLASSES:  # desktop and taskbar
        return False
    rect = wintypes.RECT()
    info = MONITORINFO(cbSize=ctypes.sizeof(MONITORINFO))
    if not GetWindowRect(hwnd, ctypes.byref(rect)):
        return False
    if not GetMonitorInfoW(MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST), ctypes.byref(info)):
        return False
    mon = info.rcMonitor
    if rect.left > mon.left or rect.top > mon.top or rect.right < mon.right or rect.bottom < mon.bottom:
        return False
    # A maximized window with a title bar also covers the monitor when the
    # taskbar auto-hides; that is not full screen.
    has_caption = (GetWindowLongW(hwnd, GWL_STYLE) & WS_CAPTION) == WS_CAPTION
    return not (IsZoomed(hwnd) and has_caption)
