$ErrorActionPreference = "Stop"

$ROOT = Split-Path $PSScriptRoot -Parent

if ($args.Count -gt 0) {
    $OUT_NAME = $args[0]
}
else {
    $OUT_NAME = "Tansaku-he_custom"
}

$OUT_BIN = "$ROOT\output\$OUT_NAME.bin"
$OUT_CUE = "$ROOT\output\$OUT_NAME.cue"

New-Item "$ROOT\output" -ItemType Directory -Force | Out-Null

Write-Host "[1/6] Resetting dst0"

Remove-Item "$ROOT\work\dst0" -Recurse -Force -ErrorAction SilentlyContinue
New-Item "$ROOT\work\dst0" -ItemType Directory -Force | Out-Null
Copy-Item "$ROOT\work\file0\*" "$ROOT\work\dst0" -Recurse -Force

Write-Host "[2/6] Patch / Merge / Build"

Push-Location "$ROOT\scripts"

foreach ($cap in "cap0","cap1","cap2","cap3","cap4","capX") {
    py main.py patch "$cap.work.ini"
    py main.py merge "$cap.work.ini"
    py main.py build "$cap.work.ini"
}

Write-Host "[3/6] Writing link/font sections"

py cdb.py ../work/dst0/DAT/CAP0/K0LINK.CDB 13
py cdb.py ../work/dst0/DAT/FONT/KFONT.CDB 0
py cdb.py ../work/dst0/DAT/CAP1/K1LINK.CDB 20
py cdb.py ../work/dst0/DAT/CAP1/K1LINK.CDB 18
py cdb.py ../work/dst0/DAT/FONT/KFONT.CDB 3
py cdb.py ../work/dst0/DAT/CAP2/K2LINK.CDB 19
py cdb.py ../work/dst0/DAT/CAP2/K2LINK.CDB 7
py cdb.py ../work/dst0/DAT/FONT/KFONT.CDB 1
py cdb.py ../work/dst0/DAT/CAP3/K3LINK.CDB 0
py cdb.py ../work/dst0/DAT/CAP3/K3LINK.CDB 1
py cdb.py ../work/dst0/DAT/FONT/KFONT.CDB 5
py cdb.py ../work/dst0/DAT/CAP4/W4LINK.CDB 0
py cdb.py ../work/dst0/DAT/CAP4/W4LINK.CDB 1
py cdb.py ../work/dst0/DAT/FONT/KFONT.CDB 2
py cdb.py ../work/dst0/DAT/CAPX/WXLINK.CDB 0
py cdb.py ../work/dst0/DAT/FONT/KFONT.CDB 7

Pop-Location

Write-Host "[4/6] Writeback consistency"

py "$ROOT\scripts\verify_writeback_consistency.py" `
    --root "$ROOT" `
    --scripts-dir scripts

Write-Host "[5/6] CMD2 flag check"

Push-Location "$ROOT\scripts"

py check_cmd2_flags.py `
    --root .. `
    --scripts-dir scripts

Pop-Location

Write-Host "[6/6] Building ISO"

& "$ROOT\tools\mkpsxiso-2.20-Windows\bin\mkpsxiso.exe" `
    -y `
    -o "$OUT_BIN" `
    -c "$OUT_CUE" `
    "$ROOT\Tansaku-he.build.xml"

$shaFile = "$ROOT\output\$OUT_NAME.sha256.txt"

@(
    Get-FileHash $OUT_BIN -Algorithm SHA256
    Get-FileHash $OUT_CUE -Algorithm SHA256
) | ForEach-Object {
    "$($_.Hash.ToLower())  $($_.Path)"
} | Tee-Object -FilePath $shaFile

Write-Host ""
Write-Host "Done:"
Write-Host "BIN: $OUT_BIN"
Write-Host "CUE: $OUT_CUE"
Write-Host "SHA256: $shaFile"