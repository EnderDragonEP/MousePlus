# PyInstaller spec: one small windowed MousePlus.exe.  Build with .\build.ps1
import re
from pathlib import Path, PurePath

from PyInstaller.utils.win32.versioninfo import (FixedFileInfo, StringFileInfo, StringStruct, StringTable,
                                                 VarFileInfo, VarStruct, VSVersionInfo)

# Version and author live in one place: mouseplus/__init__.py
_INIT = (Path(SPECPATH) / "mouseplus" / "__init__.py").read_text()
VERSION = re.search(r'__version__ = "([^"]+)"', _INIT).group(1)
AUTHOR = re.search(r'__author__ = "([^"]+)"', _INIT).group(1)
VERSION_TUPLE = tuple(int(n) for n in (VERSION.split(".") + ["0"] * 4)[:4])

# Shown in the exe's Properties > Details tab (FileDescription is also the name Task Manager shows).
VERSION_INFO = VSVersionInfo(
    ffi=FixedFileInfo(filevers=VERSION_TUPLE, prodvers=VERSION_TUPLE),
    kids=[
        StringFileInfo([StringTable("040904B0", [
            StringStruct("FileDescription", "Mouse Plus"),
            StringStruct("ProductName", "Mouse Plus"),
            StringStruct("FileVersion", VERSION),
            StringStruct("ProductVersion", VERSION),
            StringStruct("InternalName", "MousePlus"),
            StringStruct("OriginalFilename", "MousePlus.exe"),
            StringStruct("CompanyName", AUTHOR),  # shown as "Publisher" in Task Manager's Startup apps
            StringStruct("LegalCopyright", f"Copyright (C) 2026 {AUTHOR}. Licensed under GPL-3.0."),
            StringStruct("Comments", "Horizontal scrolling, proportional cursor movement between monitors and scroll inertia."),
        ])]),
        VarFileInfo([VarStruct("Translation", [1033, 1200])]),  # US English, Unicode
    ],
)

EXCLUDES = [
    # large packages that might be installed but are never used
    "numpy", "PIL", "scipy", "colorthief", "tkinter",
    # optional parts of the UI libraries
    "qfluentwidgets.multimedia", "qframelesswindow.webengine",
    "PyQt6.QtMultimedia", "PyQt6.QtMultimediaWidgets", "PyQt6.QtWebEngineCore", "PyQt6.QtWebEngineWidgets",
    "PyQt6.QtQuick", "PyQt6.QtQml", "PyQt6.QtPdf", "PyQt6.QtOpenGL", "PyQt6.QtOpenGLWidgets",
    # pywin32's MFC UI and COM code generator (pulled in via win32com, never used)
    "win32ui", "pywin", "win32com.client.makepy",
    # Python's OpenSSL modules: networking goes through Qt; hashlib falls back to built-in hashes
    "ssl", "_ssl", "_hashlib",
]

# Qt files a widgets-only English app never loads.
# The update check uses HTTPS through Windows' own TLS (qschannelbackend), so the OpenSSL backend can go,
# and with it the OpenSSL DLLs PyInstaller's Qt hook collects from PATH (Git for Windows has them, for one).
DROP_FILES = {"opengl32sw.dll", "d3dcompiler_47.dll", "qt6pdf.dll", "qopensslbackend.dll", "qcertonlybackend.dll",
              "libcrypto-3-x64.dll", "libssl-3-x64.dll", "libcrypto-3.dll", "libssl-3.dll"}
DROP_PLUGIN_DIRS = {"networkinformation"}
DROP_IMAGE_PLUGINS = {"qgif", "qjpeg", "qtiff", "qwebp", "qicns", "qtga", "qwbmp", "qpdf"}


def keep(entry):
    dest = PurePath(entry[0])
    if dest.name.lower() in DROP_FILES or "translations" in dest.parts:
        return False
    if dest.parent.name in DROP_PLUGIN_DIRS:
        return False
    return not (dest.parent.name == "imageformats" and dest.stem.lower() in DROP_IMAGE_PLUGINS)


a = Analysis(["main.py"], excludes=EXCLUDES)
a.binaries = [b for b in a.binaries if keep(b)]
a.datas = [d for d in a.datas if keep(d)]
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="MousePlus",
    console=False,
    icon="build/app.ico",
    version=VERSION_INFO,
    upx=False,
)
