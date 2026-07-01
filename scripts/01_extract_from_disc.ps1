$ErrorActionPreference = "Stop"

$ROOT = Split-Path $PSScriptRoot -Parent
$DISC_PATH = $args[0]

if ([string]::IsNullOrWhiteSpace($DISC_PATH)) {
    Write-Host "Usage: .\01_extract_from_disc.ps1 path\to\game.cue"
    exit 1
}

$DISC_PATH = (Resolve-Path $DISC_PATH).Path

if (!(Test-Path $DISC_PATH)) {
    Write-Host "Disc image not found: $DISC_PATH"
    exit 1
}

Write-Host "[1/5] Cleaning work directory"

Remove-Item "$ROOT\work\file0" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$ROOT\work\dst0" -Recurse -Force -ErrorAction SilentlyContinue

New-Item -ItemType Directory "$ROOT\work\file0" -Force | Out-Null
New-Item -ItemType Directory "$ROOT\work\dst0" -Force | Out-Null

Write-Host "[2/5] Extracting disc"

& "$ROOT\tools\mkpsxiso-2.20-Windows\bin\dumpsxiso.exe" `
    -x "$ROOT\work\file0" `
    -s "$ROOT\work\file0\original_dump.xml" `
    "$DISC_PATH"

Write-Host "[3/5] Initializing dst0"

Copy-Item "$ROOT\work\file0\*" "$ROOT\work\dst0" -Recurse -Force

Write-Host "[4/5] Copying font seed"

Copy-Item "$ROOT\seed\font\*" "$ROOT\work\file0\DAT\FONT" -Force

Write-Host "[5/5] Extracting chapter scripts"

Push-Location "$ROOT\scripts"

py main.py linkdec cap0.work.ini
py main.py linkdec cap1.work.ini
py main.py linkdec cap2.work.ini
py main.py linkdec cap3.work.ini
py main.py linkdec cap4.work.ini
py main.py linkdec capX.work.ini

Pop-Location

py "$ROOT\scripts\init_translated_from_raw.py" --root "$ROOT"

Write-Host ""
Write-Host "Done."
Write-Host "Raw extraction: $ROOT\work\file0"
Write-Host "Translation directory: $ROOT\source\translated"
Write-Host "Next: .\02_prepare_cnraw.ps1"