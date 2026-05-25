# End-to-end installer + runtime test for Windows builds.
#
# Verifies the full distribution flow:
#   1) Silent install from dist\installer\TRPG_Converter_Pro_Setup_*.exe
#   2) Launch installed exe, confirm it stays alive for 6s (no hang/crash)
#   3) Verify timeout value in installed updater.py matches source
#   4) Confirm Start Menu shortcut exists
#   5) Silent uninstall
#   6) Confirm install dir removed, %APPDATA% preserved
#
# Run from repo root:
#   powershell -ExecutionPolicy Bypass -File scripts\e2e_installer_test.ps1
#
# Exit codes:
#   0 = all checks passed
#   1 = installer not found
#   2 = install failed
#   3 = launch failed
#   4 = mismatch between source and installed code
#   5 = start menu missing
#   6 = uninstall failed
#   7 = cleanup incomplete

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path "$PSScriptRoot\..").Path

function Write-Step($msg) {
    Write-Host "`n→ $msg" -ForegroundColor Cyan
}
function Write-Pass($msg) {
    Write-Host "  ✓ $msg" -ForegroundColor Green
}
function Write-Fail($msg) {
    Write-Host "  ✗ $msg" -ForegroundColor Red
}

# ── 1. Locate installer ─────────────────────────────────────────────
Write-Step "1. Locating installer"
$installer = Get-ChildItem "$repo\dist\installer\TRPG_Converter_Pro_Setup_*.exe" `
    -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $installer) {
    Write-Fail "No installer found in dist\installer\"
    exit 1
}
Write-Pass "Found: $($installer.Name) ($([math]::Round($installer.Length/1MB,1)) MB)"

# ── 2. Kill any running instance + uninstall previous if present ───
Write-Step "2. Cleaning previous install (if any)"
Get-Process -Name "TRPG_Converter_Pro" -ErrorAction SilentlyContinue |
    Stop-Process -Force
$prev = "$env:LOCALAPPDATA\Programs\TRPG_Converter_Pro\unins000.exe"
if (Test-Path $prev) {
    & $prev /SILENT /SUPPRESSMSGBOXES /NORESTART | Out-Null
    Start-Sleep -Seconds 2
}
Write-Pass "Pre-clean done"

# ── 3. Silent install ────────────────────────────────────────────────
Write-Step "3. Silent install"
$proc = Start-Process -FilePath $installer.FullName `
    -ArgumentList "/SILENT","/SUPPRESSMSGBOXES","/CURRENTUSER","/NORESTART" `
    -Wait -PassThru
if ($proc.ExitCode -ne 0) {
    Write-Fail "Installer exit code: $($proc.ExitCode)"
    exit 2
}
Write-Pass "Install exit 0"

$installDir = "$env:LOCALAPPDATA\Programs\TRPG_Converter_Pro"
$installedExe = "$installDir\TRPG_Converter_Pro.exe"
if (-not (Test-Path $installedExe)) {
    Write-Fail "Installed exe not found at $installedExe"
    exit 2
}
$installSize = [math]::Round((Get-ChildItem $installDir -Recurse |
    Measure-Object Length -Sum).Sum / 1MB, 1)
Write-Pass "Install dir: $installDir ($installSize MB)"

# ── 4. Source/install sync check (critical regression guard) ────────
Write-Step "4. Source/install sync check"
$srcUpdater = Get-Content "$repo\core\services\updater.py" -Raw
$instUpdater = Get-Content "$installDir\_internal\core\services\updater.py" -Raw
$srcHash = [System.BitConverter]::ToString(
    [System.Security.Cryptography.SHA256]::Create().ComputeHash(
        [System.Text.Encoding]::UTF8.GetBytes($srcUpdater)))
$instHash = [System.BitConverter]::ToString(
    [System.Security.Cryptography.SHA256]::Create().ComputeHash(
        [System.Text.Encoding]::UTF8.GetBytes($instUpdater)))
if ($srcHash -ne $instHash) {
    Write-Fail "updater.py source/install hash mismatch — stale installer!"
    Write-Host "  src:  $($srcHash.Substring(0,16))..."
    Write-Host "  inst: $($instHash.Substring(0,16))..."
    exit 4
}
Write-Pass "updater.py source/install hash match"

# Extract _TIMEOUT_SECONDS from installed code and assert sanity.
if ($instUpdater -match '_TIMEOUT_SECONDS\s*=\s*(\d+(\.\d+)?)') {
    $timeout = [double]$Matches[1]
    if ($timeout -gt 4) {
        Write-Fail "Installed _TIMEOUT_SECONDS=$timeout is too high (> 4s)"
        exit 4
    }
    Write-Pass "Installed _TIMEOUT_SECONDS=$timeout (within budget)"
}

# ── 5. Launch installed exe ─────────────────────────────────────────
Write-Step "5. Launching installed exe"
$proc = Start-Process -FilePath $installedExe -PassThru
Start-Sleep -Seconds 6
$alive = Get-Process -Id $proc.Id -ErrorAction SilentlyContinue
if (-not $alive) {
    Write-Fail "Process exited within 6s (code: $($proc.ExitCode))"
    exit 3
}
$memMB = [math]::Round($alive.WorkingSet/1MB, 1)
Write-Pass "Running pid=$($alive.Id) memMB=$memMB"
Stop-Process -Id $alive.Id -Force
Start-Sleep -Seconds 1

# ── 6. Start Menu shortcut ──────────────────────────────────────────
Write-Step "6. Start Menu shortcut"
$shortcut = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\TRPG Log Converter Pro\TRPG Log Converter Pro.lnk"
if (-not (Test-Path $shortcut)) {
    Write-Fail "Start Menu shortcut missing"
    exit 5
}
Write-Pass "Shortcut: $shortcut"

# ── 7. Settings file location (must be %APPDATA%, not install dir) ─
Write-Step "7. Settings location check"
$installSettings = "$installDir\gui_settings.json"
$appdataSettings = "$env:APPDATA\TRPG_Converter_Pro\gui_settings.json"
if (Test-Path $installSettings) {
    Write-Fail "Settings polluted install dir (should be %APPDATA%)"
    exit 4
}
if (Test-Path $appdataSettings) {
    Write-Pass "Settings at %APPDATA%\TRPG_Converter_Pro (correct)"
} else {
    Write-Host "  ⚠ Settings file not created yet (app didn't reach save point)" -ForegroundColor Yellow
}

# ── 8. Silent uninstall ─────────────────────────────────────────────
Write-Step "8. Silent uninstall"
$uninstaller = "$installDir\unins000.exe"
$proc = Start-Process -FilePath $uninstaller `
    -ArgumentList "/SILENT","/SUPPRESSMSGBOXES","/NORESTART" `
    -Wait -PassThru
if ($proc.ExitCode -ne 0) {
    Write-Fail "Uninstaller exit: $($proc.ExitCode)"
    exit 6
}
Write-Pass "Uninstall exit 0"

# ── 9. Post-uninstall verification ──────────────────────────────────
Write-Step "9. Post-uninstall cleanup verification"
if (Test-Path $installDir) {
    Write-Fail "Install dir NOT removed: $installDir"
    exit 7
}
Write-Pass "Install dir removed"

$shortcutDir = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\TRPG Log Converter Pro"
if (Test-Path $shortcutDir) {
    Write-Fail "Start Menu group NOT removed"
    exit 7
}
Write-Pass "Start Menu group removed"

if (Test-Path "$env:APPDATA\TRPG_Converter_Pro") {
    Write-Pass "User data preserved at %APPDATA% (intentional)"
}

Write-Host "`n=========================================================" -ForegroundColor Green
Write-Host "  E2E INSTALLER TEST PASSED" -ForegroundColor Green
Write-Host "=========================================================" -ForegroundColor Green
exit 0
