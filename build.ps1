# Builds dist\MousePlus.exe inside a project-local virtual environment,
# so unrelated packages from the global Python never end up in the exe.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path .venv)) {
    python -m venv .venv
    if ($LASTEXITCODE) { throw "Could not create the virtual environment" }
}
$py = ".\.venv\Scripts\python.exe"

& $py -m pip install --disable-pip-version-check -q -r requirements.txt pyinstaller
if ($LASTEXITCODE) { throw "pip install failed" }

& $py -m mouseplus.icons build\app.ico
if ($LASTEXITCODE) { throw "Icon generation failed" }

& $py -m PyInstaller --noconfirm --clean MousePlus.spec
if ($LASTEXITCODE) { throw "PyInstaller failed" }

$exe = Get-Item dist\MousePlus.exe
"Built {0} ({1:N1} MB)" -f $exe.FullName, ($exe.Length / 1MB)
