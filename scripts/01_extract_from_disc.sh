#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DISC_PATH="${1:-}"

if [[ -z "$DISC_PATH" ]]; then
  echo "用法: bash scripts/01_extract_from_disc.sh /path/to/game.cue"
  exit 1
fi

DISC_PATH="$(realpath "$DISC_PATH")"
if [[ ! -f "$DISC_PATH" ]]; then
  echo "找不到镜像: $DISC_PATH"
  exit 1
fi

echo "[1/5] 清理旧工作目录"
rm -rf "$ROOT/work/file0" "$ROOT/work/dst0"
mkdir -p "$ROOT/work/file0" "$ROOT/work/dst0"

echo "[2/5] dumpsxiso 解包"
"$ROOT/tools/mkpsxiso-2.20-Linux/bin/dumpsxiso" \
  -x "$ROOT/work/file0" \
  -s "$ROOT/work/file0/original_dump.xml" \
  "$DISC_PATH"

echo "[3/5] 初始化 dst0"
cp -a "$ROOT/work/file0/." "$ROOT/work/dst0/"

echo "[4/5] 写入字体种子"
cp -f "$ROOT/seed/font/"* "$ROOT/work/file0/DAT/FONT/"

echo "[5/5] 提取六章脚本文本"
(
  cd "$ROOT/scripts"
  python3 main.py linkdec cap0.work.ini
  python3 main.py linkdec cap1.work.ini
  python3 main.py linkdec cap2.work.ini
  python3 main.py linkdec cap3.work.ini
  python3 main.py linkdec cap4.work.ini
  python3 main.py linkdec capX.work.ini
)

python3 "$ROOT/scripts/init_translated_from_raw.py" --root "$ROOT"

echo
echo "完成。"
echo "原始提取目录: $ROOT/work/file0"
echo "可编辑译文目录: $ROOT/source/translated"
echo "下一步: bash scripts/02_prepare_cnraw.sh"
