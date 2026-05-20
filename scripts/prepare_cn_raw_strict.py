#!/usr/bin/env python3
import argparse
import pathlib
import re
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple


PAIR_MAP: Dict[str, str] = {
    "K0LINK.CDB.13.txt": "work/file0/DAT/CAP0/K0LINK.CDB.13.raw.txt",
    "K1LINK.CDB.20.txt": "work/file0/DAT/CAP1/K1LINK.CDB.20.raw.txt",
    "K2LINK.CDB.19.txt": "work/file0/DAT/CAP2/K2LINK.CDB.19.raw.txt",
    "K3LINK.CDB.0.txt": "work/file0/DAT/CAP3/K3LINK.CDB.0.raw.txt",
    "W4LINK.CDB.0.txt": "work/file0/DAT/CAP4/W4LINK.CDB.0.raw.txt",
    "WXLINK.CDB.0.txt": "work/file0/DAT/CAPX/WXLINK.CDB.0.raw.txt",
}


TOKEN_RE = re.compile(r"(<[^>]+>|⍽)")


@dataclass
class FileStat:
    name: str
    lines: int = 0
    changed_lines: int = 0


def split_tokens(s: str) -> List[str]:
    return [x for x in TOKEN_RE.split(s) if x != ""]


def is_ctrl_or_slot(tok: str) -> bool:
    return tok == "⍽" or (tok.startswith("<") and tok.endswith(">"))


def transplant_to_raw_skeleton(raw_line: str, tr_line: str) -> str:
    raw_tokens = split_tokens(raw_line)
    tr_tokens = split_tokens(tr_line)
    tr_texts = [t for t in tr_tokens if not is_ctrl_or_slot(t)]
    raw_text_pos = [i for i, t in enumerate(raw_tokens) if not is_ctrl_or_slot(t)]

    if not raw_text_pos:
        return "".join(raw_tokens)

    assigned: List[str] = []
    ti = 0
    for _ in raw_text_pos:
        if ti < len(tr_texts):
            assigned.append(tr_texts[ti])
            ti += 1
        else:
            assigned.append("")
    if ti < len(tr_texts):
        assigned[-1] += "".join(tr_texts[ti:])

    out = list(raw_tokens)
    for pos, txt in zip(raw_text_pos, assigned):
        out[pos] = txt
    return "".join(out)


def split_name_and_rest(s: str) -> tuple[str, str]:
    i1 = s.find(":")
    i2 = s.find("：")
    idx = -1
    if i1 == -1:
        idx = i2
    elif i2 == -1:
        idx = i1
    else:
        idx = min(i1, i2)
    if idx == -1:
        return "", s
    return s[:idx], s[idx + 1 :]


def preserve_head_name_from_raw(raw_line: str, line: str) -> str:
    rt = split_tokens(raw_line)
    ct = split_tokens(line)
    if len(rt) != len(ct):
        return line
    for i, tok in enumerate(rt):
        if not tok.startswith("<HEAD,") or not tok.endswith(">"):
            continue
        if i + 1 >= len(rt):
            continue
        if is_ctrl_or_slot(rt[i + 1]) or is_ctrl_or_slot(ct[i + 1]):
            continue
        raw_name, _ = split_name_and_rest(rt[i + 1])
        if not raw_name:
            continue
        cur_seg = ct[i + 1]
        c1 = cur_seg.find(":")
        c2 = cur_seg.find("：")
        cidx = -1
        if c1 == -1:
            cidx = c2
        elif c2 == -1:
            cidx = c1
        else:
            cidx = min(c1, c2)

        use_raw = False
        cur_rest = cur_seg
        if cidx == -1:
            use_raw = True
        else:
            next_ctrl = cur_seg.find("<")
            if next_ctrl != -1 and next_ctrl < cidx:
                use_raw = True
            else:
                cur_name = cur_seg[:cidx]
                cur_rest = cur_seg[cidx + 1 :]
                if len(cur_name) <= 0 or len(cur_name) > 7:
                    use_raw = True
                else:
                    # 名字有效，仅统一分隔符为 ':'
                    ct[i + 1] = cur_name + ":" + cur_rest

        if use_raw:
            ct[i + 1] = raw_name + ":" + cur_rest
    return "".join(ct)


def strict_ctrl_tokens(s: str) -> List[str]:
    return TOKEN_RE.findall(s)


def load_lines(p: pathlib.Path) -> Tuple[List[str], bool]:
    txt = p.read_text(encoding="utf-8")
    return txt.splitlines(), txt.endswith("\n")


def write_lines(p: pathlib.Path, lines: Sequence[str], trailing_nl: bool) -> None:
    out = "\n".join(lines)
    if trailing_nl:
        out += "\n"
    p.write_text(out, encoding="utf-8")


def process_one(root: pathlib.Path, translated_dir: pathlib.Path, name: str, raw_rel: str, write: bool) -> FileStat:
    tr_path = translated_dir / name
    raw_path = root / raw_rel
    if raw_path.name.endswith(".raw.txt"):
        cn_raw_name = raw_path.name.replace(".raw.txt", ".cn.raw.txt")
    else:
        cn_raw_name = raw_path.name + ".cn.raw.txt"
    cn_raw_path = raw_path.with_name(cn_raw_name)

    tr_lines, tr_nl = load_lines(tr_path)
    raw_lines, _ = load_lines(raw_path)
    if len(tr_lines) != len(raw_lines):
        raise RuntimeError(f"{name}: line_count mismatch tr={len(tr_lines)} raw={len(raw_lines)}")

    out: List[str] = []
    changed = 0
    for tr, raw in zip(tr_lines, raw_lines):
        nl = transplant_to_raw_skeleton(raw, tr)
        nl = preserve_head_name_from_raw(raw, nl)
        if nl != tr:
            changed += 1
        if strict_ctrl_tokens(nl) != strict_ctrl_tokens(raw):
            raise RuntimeError(f"{name}: strict token mismatch after transplant")
        out.append(nl)

    if write:
        write_lines(cn_raw_path, out, tr_nl)
    return FileStat(name=name, lines=len(out), changed_lines=changed)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Prepare strict cn.raw text with raw control/placeholder skeleton.")
    p.add_argument("--root", default=".", help="project root")
    p.add_argument("--translated-dir", default="source/translated", help="translated dir")
    p.add_argument("--write", action="store_true", help="write to *.cn.raw.txt")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    root = pathlib.Path(args.root).resolve()
    tdir = (root / args.translated_dir).resolve()
    mode = "WRITE" if args.write else "DRY-RUN"
    print(f"mode={mode}")
    total_changed = 0
    total_lines = 0
    for name, raw_rel in PAIR_MAP.items():
        st = process_one(root, tdir, name, raw_rel, write=args.write)
        total_changed += st.changed_lines
        total_lines += st.lines
        print(f"{st.name}: lines={st.lines}, changed_lines={st.changed_lines}")
    print(f"TOTAL lines={total_lines}, changed_lines={total_changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
