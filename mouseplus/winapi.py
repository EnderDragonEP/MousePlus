"""Win32 bindings (ctypes) for the mouse hook, input injection and full-screen detection."""
import ctypes
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)

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
WS_CAPTION = 0x00C00000

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


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD),
                ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT),
                ("dwFlags", wintypes.DWORD)]


HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)


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


def _mouse_input(flags: int, data: int = 0) -> INPUT:
    inp = INPUT(type=INPUT_MOUSE)
    inp.mi = MOUSEINPUT(0, 0, data & 0xFFFFFFFF, flags, 0, MAGIC)
    return inp


def send_hwheel(delta: int):
    """Inject a horizontal wheel event at the cursor (positive = scroll right)."""
    inp = _mouse_input(MOUSEEVENTF_HWHEEL, delta)
    SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def send_xclick(button: int):
    """Inject a full click (down + up) of XBUTTON1 (Back) or XBUTTON2 (Forward)."""
    inputs = (INPUT * 2)(_mouse_input(MOUSEEVENTF_XDOWN, button),
                         _mouse_input(MOUSEEVENTF_XUP, button))
    SendInput(2, inputs, ctypes.sizeof(INPUT))


_SHELL_CLASSES = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"}


def foreground_is_fullscreen() -> bool:
    """True when the foreground window covers its whole monitor (games, F11, videos)."""
    hwnd = GetForegroundWindow()
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
