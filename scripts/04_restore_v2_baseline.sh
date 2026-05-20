#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "[1/2] 恢复 source/translated 到 v2 基线"
cp -f "$ROOT/baselines/v2/translated/"*.txt "$ROOT/source/translated/"

if [[ -f "$ROOT/work/file0/DAT/CAP0/K0LINK.CDB.13.raw.txt" ]]; then
  echo "[2/2] 恢复构建用 cn.raw 到 v2 基线"
  cp -f "$ROOT/baselines/v2/cnraw/K0LINK.CDB.13.cn.raw.txt" "$ROOT/work/file0/DAT/CAP0/"
  cp -f "$ROOT/baselines/v2/cnraw/K1LINK.CDB.20.cn.raw.txt" "$ROOT/work/file0/DAT/CAP1/"
  cp -f "$ROOT/baselines/v2/cnraw/K2LINK.CDB.19.cn.raw.txt" "$ROOT/work/file0/DAT/CAP2/"
  cp -f "$ROOT/baselines/v2/cnraw/K3LINK.CDB.0.cn.raw.txt" "$ROOT/work/file0/DAT/CAP3/"
  cp -f "$ROOT/baselines/v2/cnraw/W4LINK.CDB.0.cn.raw.txt" "$ROOT/work/file0/DAT/CAP4/"
  cp -f "$ROOT/baselines/v2/cnraw/WXLINK.CDB.0.cn.raw.txt" "$ROOT/work/file0/DAT/CAPX/"
else
  echo "[2/2] 尚未解包，先只恢复 source/translated"
fi

echo "完成。"
