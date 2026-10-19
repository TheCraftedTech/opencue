# Baut OpenCue mit PyInstaller (Ordner-Build) und auf Wunsch den Installer.
#   powershell -File packaging\build.ps1              Release-Build ohne Konsole  -> dist\OpenCue\
#   powershell -File packaging\build.ps1 -Console     Test-Build MIT Konsole (Fehlermeldungen sichtbar)
#   powershell -File packaging\build.ps1 -Installer   zusaetzlich den Inno-Setup-Installer -> dist\installer\OpenCue-Setup-v<Version>.exe
#   -SkipLicenses  Lizenztexte nicht neu sammeln (packaging\third_party bleibt wie es ist)
# Voraussetzungen: Python 3.13 mit venv und requirements.txt, dazu packagingequirements-build.txt; fuer -Installer Inno Setup 6.
param(
    [switch]$Console,
    [switch]$Installer,
    [switch]$SkipLicenses
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$py = Join-Path $root "venv\Scripts\python.exe"

function Step($text) { Write-Host "`n== $text" -ForegroundColor Cyan }

if (-not (Test-Path $py)) { throw "venv fehlt: $py  (python -m venv venv; venv\Scripts\pip install -r requirements.txt)" }
& $py -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) { throw "PyInstaller fehlt im venv:  venv\Scripts\pip install -r packaging\requirements-build.txt" }
if (-not (Test-Path "ffmpeg\ffmpeg.exe")) { throw "ffmpeg\ffmpeg.exe fehlt (siehe ffmpeg\README.md)" }
if (-not (Test-Path "packaging\OpenCue.ico")) { throw "packaging\OpenCue.ico fehlt:  venv\Scripts\python.exe packaging\make_icon.py" }

Step "Version"
& $py packaging\make_version_info.py
if ($LASTEXITCODE -ne 0) { throw "make_version_info.py fehlgeschlagen" }

if (-not $SkipLicenses) {
    Step "Lizenztexte sammeln"
    & $py packaging\collect_licenses.py
    if ($LASTEXITCODE -ne 0) { throw "collect_licenses.py fehlgeschlagen" }
}

Step ("PyInstaller" + $(if ($Console) { " (mit Konsole)" } else { "" }))
$env:OPENCUE_CONSOLE = $(if ($Console) { "1" } else { "0" })
& $py -m PyInstaller packaging\OpenCue.spec --noconfirm --clean --distpath dist --workpath build
if ($LASTEXITCODE -ne 0) { throw "PyInstaller fehlgeschlagen" }
Write-Host "`nFertig: dist\OpenCue\OpenCue.exe" -ForegroundColor Green

if ($Installer) {
    Step "Installer (Inno Setup)"
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
    )
    $iscc = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $iscc) { throw "Inno Setup 6 nicht gefunden (https://jrsoftware.org/isinfo.php)" }
    & $iscc packaging\OpenCue.iss
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup fehlgeschlagen" }
    Write-Host "`nInstaller: dist\installer\" -ForegroundColor Green
}
