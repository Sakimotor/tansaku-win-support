#!/usr/bin/env python3
import argparse
import pathlib
import re
from dataclasses import dataclass
from typing import List, Tuple


HEAD_RE = re.compile(r"<HEAD,(\d+)>")
COL_RE = re.compile(r"<COL,(\d+)>")
TOKEN_RE = re.compile(r"(<[^>]+>|⍽)")

TARGETS = [
    "work/file0/DAT/CAP0/K0LINK.CDB.13.cn.raw.txt",
    "work/file0/DAT/CAP1/K1LINK.CDB.20.cn.raw.txt",
    "work/file0/DAT/CAP2/K2LINK.CDB.19.cn.raw.txt",
    "work/file0/DAT/CAP3/K3LINK.CDB.0.cn.raw.txt",
    "work/file0/DAT/CAP4/W4LINK.CDB.0.cn.raw.txt",
    "work/file0/DAT/CAPX/WXLINK.CDB.0.cn.raw.txt",
]


@dataclass
class FileStat:
    path: pathlib.Path
    lines: int = 0
    changed: int = 0
    dropped_chars: int = 0


def fix_line(line: str, limit: int) -> Tuple[str, int]:
    parts = [x for x in TOKEN_RE.split(line) if x != ""]
    head_len = 0
    col = 0
    dropped = 0
    out: List[str] = []

    for part in parts:
        if not part:
            continue
        if part == "⍽":
            out.append(part)
            if col < limit:
                col += 1
            continue

        if part.startswith("<") and part.endswith(">"):
            out.append(part)
            if part.startswith("<HEAD,"):
                m = HEAD_RE.match(part)
                if m:
                    head_len = int(m.group(1))
                continue
            if part.startswith("<COL,"):
                m = COL_RE.match(part)
                if m:
                    col = int(m.group(1))
                continue
            if part == "<RET>":
                col = head_len
                continue
            if part in ("<NEXT>", "<END>", "<BEGIN>"):
                if part in ("<NEXT>", "<BEGIN>"):
                    head_len = 0
                col = 0
                continue
            continue

        keep_chars: List[str] = []
        for ch in part:
            if col < limit:
                keep_chars.append(ch)
                col += 1
            else:
                dropped += 1
        out.append("".join(keep_chars))

    return "".join(out), dropped


def process_file(path: pathlib.Path, limit: int, write: bool) -> FileStat:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    trailing_nl = text.endswith("\n")

    out_lines: List[str] = []
    changed = 0
    dropped_total = 0

    for line in lines:
        fixed, dropped = fix_line(line, limit)
        if fixed != line:
            changed += 1
        dropped_total += dropped
        out_lines.append(fixed)

    if write and changed > 0:
        out = "\n".join(out_lines)
        if trailing_nl:
            out += "\n"
        path.write_text(out, encoding="utf-8")

    return FileStat(path=path, lines=len(lines), changed=changed, dropped_chars=dropped_total)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Trim overflow chars in cn.raw text while preserving controls.")
    p.add_argument("--root", default=".", help="project root")
    p.add_argument("--limit", type=int, default=20, help="max visible chars per segment")
    p.add_argument("--write", action="store_true", help="write changes")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    root = pathlib.Path(args.root).resolve()
    mode = "WRITE" if args.write else "DRY-RUN"
    print(f"mode={mode} limit={args.limit}")

    total_lines = 0
    total_changed = 0
    total_dropped = 0

    for rel in TARGETS:
        path = (root / rel).resolve()
        st = process_file(path, args.limit, args.write)
        total_lines += st.lines
        total_changed += st.changed
        total_dropped += st.dropped_chars
        print(f"{path}: lines={st.lines} changed={st.changed} dropped_chars={st.dropped_chars}")

    print(f"TOTAL lines={total_lines} changed={total_changed} dropped_chars={total_dropped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
