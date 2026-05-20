#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_NAME="${1:-Tansaku-he_custom}"
OUT_BIN="$ROOT/output/${OUT_NAME}.bin"
OUT_CUE="$ROOT/output/${OUT_NAME}.cue"

mkdir -p "$ROOT/output"

echo "[1/6] 用 file0 重置 dst0"
rm -rf "$ROOT/work/dst0"
mkdir -p "$ROOT/work/dst0"
cp -a "$ROOT/work/file0/." "$ROOT/work/dst0/"

echo "[2/6] 六章 patch/merge/build"
(
  cd "$ROOT/scripts"
  python3 main.py patch cap0.work.ini
  python3 main.py merge cap0.work.ini
  python3 main.py build cap0.work.ini
  python3 main.py patch cap1.work.ini
  python3 main.py merge cap1.work.ini
  python3 main.py build cap1.work.ini
  python3 main.py patch cap2.work.ini
  python3 main.py merge cap2.work.ini
  python3 main.py build cap2.work.ini
  python3 main.py patch cap3.work.ini
  python3 main.py merge cap3.work.ini
  python3 main.py build cap3.work.ini
  python3 main.py patch cap4.work.ini
  python3 main.py merge cap4.work.ini
  python3 main.py build cap4.work.ini
  python3 main.py patch capX.work.ini
  python3 main.py merge capX.work.ini
  python3 main.py build capX.work.ini
)

echo "[3/6] 回写 link/font 分段"
(
  cd "$ROOT/scripts"
  python3 cdb.py ../work/dst0/DAT/CAP0/K0LINK.CDB 13
  python3 cdb.py ../work/dst0/DAT/FONT/KFONT.CDB 0
  python3 cdb.py ../work/dst0/DAT/CAP1/K1LINK.CDB 20
  python3 cdb.py ../work/dst0/DAT/CAP1/K1LINK.CDB 18
  python3 cdb.py ../work/dst0/DAT/FONT/KFONT.CDB 3
  python3 cdb.py ../work/dst0/DAT/CAP2/K2LINK.CDB 19
  python3 cdb.py ../work/dst0/DAT/CAP2/K2LINK.CDB 7
  python3 cdb.py ../work/dst0/DAT/FONT/KFONT.CDB 1
  python3 cdb.py ../work/dst0/DAT/CAP3/K3LINK.CDB 0
  python3 cdb.py ../work/dst0/DAT/CAP3/K3LINK.CDB 1
  python3 cdb.py ../work/dst0/DAT/FONT/KFONT.CDB 5
  python3 cdb.py ../work/dst0/DAT/CAP4/W4LINK.CDB 0
  python3 cdb.py ../work/dst0/DAT/CAP4/W4LINK.CDB 1
  python3 cdb.py ../work/dst0/DAT/FONT/KFONT.CDB 2
  python3 cdb.py ../work/dst0/DAT/CAPX/WXLINK.CDB 0
  python3 cdb.py ../work/dst0/DAT/FONT/KFONT.CDB 7
)

echo "[4/6] 回写一致性检查"
python3 "$ROOT/scripts/verify_writeback_consistency.py" --root "$ROOT" --scripts-dir scripts

echo "[5/6] cmd2 标志检查"
(
  cd "$ROOT/scripts"
  python3 check_cmd2_flags.py --root .. --scripts-dir scripts
)

echo "[6/6] 打包 ISO"
"$ROOT/tools/mkpsxiso-2.20-Linux/bin/mkpsxiso" \
  -y \
  -o "$OUT_BIN" \
  -c "$OUT_CUE" \
  "$ROOT/Tansaku-he.build.xml"

sha256sum "$OUT_BIN" "$OUT_CUE" | tee "$ROOT/output/${OUT_NAME}.sha256.txt"

echo
echo "完成："
echo "BIN: $OUT_BIN"
echo "CUE: $OUT_CUE"
echo "SHA256: $ROOT/output/${OUT_NAME}.sha256.txt"
