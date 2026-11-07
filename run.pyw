"""Double-click to run Mouse Plus from source, without building the exe.

Uses the project's .venv (create it once with the commands in README.md).
"""
import subprocess
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"


def fail(text: str):
    import ctypes

    ctypes.windll.user32.MessageBoxW(None, text, "Mouse Plus", 0x10)  # MB_ICONERROR
    sys.exit(1)


if Path(sys.prefix).resolve() != VENV.resolve():
    # Started by the system Python, which doesn't have PyQt6: relaunch with the project's venv.
    pythonw = VENV / "Scripts" / "pythonw.exe"
    if not pythonw.exists():
        fail("The .venv folder is missing. Create it once from the project folder with:\n\n"
             "python -m venv .venv\n"
             ".venv\\Scripts\\python -m pip install -r requirements.txt")
    subprocess.Popen([str(pythonw), __file__, *sys.argv[1:]], cwd=ROOT)
    sys.exit()

sys.path.insert(0, str(ROOT))
try:
    import main
except Exception:
    fail("Mouse Plus couldn't start:\n\n" + traceback.format_exc())
sys.exit(main.main())
