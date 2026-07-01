$ErrorActionPreference = "Stop"

$ROOT = Split-Path $PSScriptRoot -Parent

Write-Host "[1/2] Speaker/line count check"

py "$ROOT\scripts\check_speaker_line_counts.py" `
    --root "$ROOT" `
    --strict-map

Write-Host "[2/2] Generating cn.raw"

py "$ROOT\scripts\prepare_cn_raw_strict.py" `
    --root "$ROOT" `
    --write

Write-Host ""
Write-Host "Done."
Write-Host ""
Write-Host "If you want to force every visible line to 20 characters:"
Write-Host "py scripts\fix_cnraw_overflow.py --root . --write"
Write-Host ""
Write-Host "Warning: this removes characters automatically."
Write-Host "Next: .\03_build_iso.ps1 YourOutputName"