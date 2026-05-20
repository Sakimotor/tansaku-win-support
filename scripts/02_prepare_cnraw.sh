#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "[1/2] 说话人/行数检查"
python3 "$ROOT/scripts/check_speaker_line_counts.py" --root "$ROOT" --strict-map

echo "[2/2] 生成 cn.raw"
python3 "$ROOT/scripts/prepare_cn_raw_strict.py" --root "$ROOT" --write

cat <<'EOF'

完成。
如需强制把每段可见字符裁到 20 字，可手动运行：
python3 scripts/fix_cnraw_overflow.py --root . --write

注意：该命令会直接删字符，默认不建议自动执行。
下一步: bash scripts/03_build_iso.sh 你的输出名
EOF
