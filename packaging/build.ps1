# Baut OpenCue: PyInstaller-Ordner (dist\OpenCue\) und auf Wunsch den Installer (dist\installer\OpenCue-Setup-v<Version>.exe) - lokal und in GitHub Actions derselbe Weg.
#
#   powershell -File packaging\build.ps1                    Release-Build ohne Konsole  -> dist\OpenCue\
#   powershell -File packaging\build.ps1 -Installer         zusaetzlich der Inno-Setup-Installer + SHA256SUMS.txt
#   powershell -File packaging\build.ps1 -Console           Test-Build MIT Konsole (Fehlermeldungen sichtbar)
#   -SkipLicenses     Lizenztexte nicht neu sammeln (packaging\third_party bleibt wie es ist)
#   -Python <pfad>    anderer Python-Interpreter statt venv\Scripts\python.exe (z. B. in CI: der von setup-python)
#   -MaxInstallerMB   Obergrenze fuer die Installer-Groesse (Standard 100); ueberschritten = Fehler. 0 = nicht pruefen.
#   -InstallerOnly    nur den Installer neu bauen (dist\OpenCue muss schon da sein; z. B. nach einer Textaenderung in OpenCue.iss)
#
# Der Build bricht bei jedem Fehler mit Exit-Code 1 ab. Nach dem PyInstaller-Lauf wird das Ergebnis geprueft: Exe + eingebettetes Manifest,
# keine unerwuenschten Pakete (PyAV, hf_xet, das mitgelieferte Sprachmodell), Version stimmt mit app\version.py. Der Installer-Name enthaelt die Version.
# Voraussetzungen: Python 3.13 mit requirements.txt + packaging\requirements-build.txt, ffmpeg\ffmpeg.exe (siehe ffmpeg\README.md); fuer -Installer Inno Setup 6
# (winget install JRSoftware.InnoSetup  /  choco install innosetup).
param(
    [switch]$Console,
    [switch]$Installer,
    [switch]$SkipLicenses,
    [switch]$InstallerOnly,
    [string]$Python = "",
    [int]$MaxInstallerMB = 100
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
# Entwicklung: die venv liegt im Projektordner ueber dem App-Ordner (eine Ebene hoeher); in CI / im oeffentlichen Repository gibt es sie nicht (dort -Python <pfad>)
$py = if ($Python) { $Python } elseif (Test-Path (Join-Path $root "venv\Scripts\python.exe")) { Join-Path $root "venv\Scripts\python.exe" } else { Join-Path (Split-Path -Parent $root) "venv\Scripts\python.exe" }
$started = Get-Date

function Step($text) { Write-Host "`n== $text" -ForegroundColor Cyan }
function Fail($text) { Write-Host "`nFEHLER: $text" -ForegroundColor Red; exit 1 }
function Run($what, [scriptblock]$cmd) {
    & $cmd
    if ($LASTEXITCODE -ne 0) { Fail "$what fehlgeschlagen (Exit-Code $LASTEXITCODE)" }
}

try {
    if ($InstallerOnly) { $Installer = $true }

    # --- Voraussetzungen -----------------------------------------------------------------------------------------------
    if (-not (Test-Path $py)) { Fail "Python fehlt: $py  (python -m venv venv; venv\Scripts\pip install -r requirements.txt  oder -Python <pfad>)" }
    if (-not (Test-Path "packaging\OpenCue.ico")) { Fail "packaging\OpenCue.ico fehlt:  python packaging\make_icon.py" }
    if (-not $InstallerOnly) {
        & $py -c "import PyInstaller" 2>$null
        if ($LASTEXITCODE -ne 0) { Fail "PyInstaller fehlt:  pip install -r packaging\requirements-build.txt" }
        if (-not (Test-Path "ffmpeg\ffmpeg.exe")) { Fail "ffmpeg\ffmpeg.exe fehlt (siehe ffmpeg\README.md)" }
    }

    Step "Version"
    Run "make_version_info.py" { & $py packaging\make_version_info.py }
    $version = (& $py -c "import sys; sys.path.insert(0, '.'); from app.version import APP_VERSION; print(APP_VERSION)").Trim()
    if (-not $version) { Fail "Version nicht lesbar (app\version.py)" }
    Write-Host "OpenCue $version"

    Step "Installer-Texte (sechs Sprachen)"
    Run "make_installer_messages.py" { & $py packaging\make_installer_messages.py }

    if (-not $InstallerOnly) {
        if (-not $SkipLicenses) {
            Step "Lizenztexte sammeln"
            Run "collect_licenses.py" { & $py packaging\collect_licenses.py }
        }

        Step ("PyInstaller" + $(if ($Console) { " (mit Konsole)" } else { "" }))
        $env:OPENCUE_CONSOLE = $(if ($Console) { "1" } else { "0" })
        Run "PyInstaller" { & $py -m PyInstaller packaging\OpenCue.spec --noconfirm --clean --distpath dist --workpath build }

        # --- Ergebnis pruefen ---------------------------------------------------------------------------------------------
        Step "Ergebnis pruefen"
        $exe = "dist\OpenCue\OpenCue.exe"
        if (-not (Test-Path $exe)) { Fail "$exe fehlt" }
        $internal = "dist\OpenCue\_internal"
        foreach ($unwanted in @("av", "av.libs", "hf_xet", "defaults\voice")) {
            if (Test-Path (Join-Path $internal $unwanted)) { Fail "unerwuenscht im Paket: $unwanted (haelt den Installer gross; siehe packaging\OpenCue.spec)" }
        }
        foreach ($required in @("ffmpeg\ffmpeg.exe", "static", "defaults", "templates")) {
            if (-not (Test-Path (Join-Path $internal $required))) { Fail "fehlt im Paket: $required" }
        }
        $manifest = & $py -c "from PyInstaller.utils.win32.winmanifest import read_manifest_from_executable as r; m = r(r'$exe'); print('ok' if m and b'asInvoker' in m else 'fehlt')"
        if ($manifest -ne "ok") { Fail "Manifest (asInvoker) ist nicht in OpenCue.exe eingebettet" }
        $info = (Get-Item $exe).VersionInfo
        if ($info.ProductVersion -notlike "$version*" -and $info.FileVersion -notlike "$version*") { Fail "Versionsinfo der Exe ($($info.FileVersion)) passt nicht zu $version" }
        $mb = [math]::Round(((Get-ChildItem "dist\OpenCue" -Recurse -File | Measure-Object Length -Sum).Sum) / 1MB, 1)
        Write-Host "OK: Exe, Manifest, Version $version, keine unerwuenschten Pakete; Ordner $mb MB"
        Write-Host "`nFertig: dist\OpenCue\OpenCue.exe" -ForegroundColor Green
    } elseif (-not (Test-Path "dist\OpenCue\OpenCue.exe")) {
        Fail "dist\OpenCue\OpenCue.exe fehlt (-InstallerOnly braucht einen vorhandenen Build)"
    }

    # --- Installer ---------------------------------------------------------------------------------------------------------
    if ($Installer) {
        Step "Installer (Inno Setup)"
        $candidates = @(
            (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
            (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
            (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
        )
        $iscc = $candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
        if (-not $iscc) {
            $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
            if ($cmd) { $iscc = $cmd.Source }
        }
        if (-not $iscc) { Fail "Inno Setup 6 nicht gefunden (winget install JRSoftware.InnoSetup)" }
        if (Test-Path "dist\installer") { Get-ChildItem "dist\installer" -File | Remove-Item -Force }       # keine alten Fassungen liegen lassen
        Run "Inno Setup" { & $iscc /Q packaging\OpenCue.iss }
        $setup = Get-ChildItem "dist\installer\OpenCue-Setup-v*.exe" | Select-Object -First 1
        if (-not $setup) { Fail "Installer wurde nicht erzeugt" }
        $setupMB = [math]::Round($setup.Length / 1MB, 1)
        $hash = (Get-FileHash $setup.FullName -Algorithm SHA256).Hash
        "$hash *$($setup.Name)" | Set-Content -Path "dist\installer\SHA256SUMS.txt" -Encoding ascii
        Write-Host "Installer: $($setup.Name)  $setupMB MB"
        Write-Host "SHA-256:   $hash"
        if ($MaxInstallerMB -gt 0 -and $setupMB -gt $MaxInstallerMB) { Fail "Installer ist $setupMB MB gross (Grenze $MaxInstallerMB MB)" }
        Write-Host "`nInstaller: dist\installer\" -ForegroundColor Green
    }
    Write-Host ("`nBuild fertig in {0:N0} s" -f ((Get-Date) - $started).TotalSeconds) -ForegroundColor Green
}
catch {
    Fail $_.Exception.Message
}
