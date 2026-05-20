#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import pathlib
import shutil
import subprocess
import sys


TARGET_FILES = [
    "K0LINK.CDB.13.txt",
    "K1LINK.CDB.20.txt",
    "K2LINK.CDB.19.txt",
    "K3LINK.CDB.0.txt",
    "W4LINK.CDB.0.txt",
    "WXLINK.CDB.0.txt",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Create rollback snapshot for translated text files.")
    p.add_argument("--root", default=".", help="project root")
    p.add_argument("--label", default="manual", help="snapshot label")
    p.add_argument(
        "--translated-dir",
        default="source/translated",
        help="translated directory relative to root",
    )
    p.add_argument(
        "--snapshots-dir",
        default="snapshots",
        help="snapshots directory relative to root",
    )
    p.add_argument(
        "--with-lint",
        action="store_true",
        help="run scripts/lint_i18n.py and save report in snapshot",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    root = pathlib.Path(args.root).resolve()
    translated_dir = (root / args.translated_dir).resolve()
    snapshots_dir = (root / args.snapshots_dir).resolve()

    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in args.label.strip())
    if not safe_label:
        safe_label = "manual"
    snapshot_dir = snapshots_dir / f"{ts}_{safe_label}"
    payload_dir = snapshot_dir / "payload"
    payload_dir.mkdir(parents=True, exist_ok=False)

    copied = []
    for name in TARGET_FILES:
        src = translated_dir / name
        if not src.exists():
            continue
        dst = payload_dir / name
        shutil.copy2(src, dst)
        copied.append(name)

    lint_report_rel = None
    if args.with_lint:
        lint_path = snapshot_dir / "lint_report.txt"
        cmd = [sys.executable, str(root / "scripts/lint_i18n.py"), "--max-lines", "8"]
        result = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        lint_path.write_text(result.stdout + result.stderr, encoding="utf-8")
        lint_report_rel = str(lint_path.relative_to(root))

    meta = {
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "label": args.label,
        "files": copied,
        "lint_report": lint_report_rel,
    }
    (snapshot_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(str(snapshot_dir.relative_to(root)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
