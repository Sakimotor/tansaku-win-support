#!/usr/bin/env python3
import argparse
import configparser
import json
import pathlib
import struct
import sys
from dataclasses import dataclass
from typing import List, Tuple

from ini import Ini
from rle import dec


INI_FILES = [
    "cap0.work.ini",
    "cap1.work.ini",
    "cap2.work.ini",
    "cap3.work.ini",
    "cap4.work.ini",
    "capX.work.ini",
]


@dataclass
class CheckItem:
    ini_name: str
    section_idx: int
    secid: int
    raw_ops: List[Tuple[str, int, int]]
    json_ops: List[Tuple[str, int, int]]


def load_ini(path: pathlib.Path) -> Ini:
    conf = configparser.ConfigParser()
    conf.read(path, encoding="utf-8")
    return Ini(conf["project"])


def parse_x_ops(asm_bytes: bytes) -> List[Tuple[str, int, int]]:
    # 仅提取 xC1/xCD 的 (name, cmd2, value)
    out: List[Tuple[str, int, int]] = []
    if len(asm_bytes) < 2:
        return out

    i = 2  # skip FIRST
    final_97 = 0
    final_cc = False
    final_8b = False

    while i + 1 < len(asm_bytes):
        code, = struct.unpack("<H", asm_bytes[i : i + 2])
        i += 2

        cmd0 = code >> 14
        cmd1 = (code >> 8) & 0x3F
        cmd2 = code & 0xFF

        if code == 0xFFFF:
            # FIN 后部参数
            if final_97:
                i += final_97 * 2
            if final_cc or final_8b:
                i += 2
            break

        if cmd0 == 0:
            # text glyph
            continue

        if cmd0 == 2:
            if cmd1 in (0x17, 0x27):
                final_97 = cmd2
            elif cmd1 == 0x0B:
                final_8b = True
            continue

        if cmd0 == 3:
            if cmd1 == 0x0C:
                final_cc = True
                continue

            if cmd1 == 0x01:  # xC1
                if i + 1 >= len(asm_bytes):
                    break
                v, = struct.unpack("<H", asm_bytes[i : i + 2])
                i += 2
                out.append(("xC1", cmd2, v))
                continue

            if cmd1 == 0x0D:  # xCD
                if i + 1 >= len(asm_bytes):
                    break
                v, = struct.unpack("<H", asm_bytes[i : i + 2])
                i += 2
                out.append(("xCD", cmd2, v))
                continue

            # 其余带附加参数的指令，跳过参数以保持流同步
            if cmd1 == 0x08:  # XA
                i += 2
            elif cmd1 == 0x0E and cmd2 in (1, 3, 4):  # AWAIT with arg
                i += 2
            elif cmd1 in (0x10, 0x11, 0x12):  # ACT0
                i += 2
            elif cmd1 in (0x16, 0x17, 0x18) and cmd2 < 2:  # ACT1
                i += 2
            continue

    return out


def parse_json_x_ops(section: list) -> List[Tuple[str, int, int]]:
    out: List[Tuple[str, int, int]] = []
    for v in section[1:]:
        if v[0] not in ("xC1", "xCD"):
            continue
        if len(v) == 2:
            out.append((v[0], 0, int(v[1])))
        else:
            out.append((v[0], int(v[1]), int(v[2])))
    return out


def check_one(ini_name: str, ini: Ini, root: pathlib.Path) -> List[CheckItem]:
    # link data source: build 产物 bin（最接近最终写回内容）
    link_ids, link_sep = ini.linkid()
    link_bins = []
    for idx in link_ids:
        p = pathlib.Path(f"{ini.dstlink}.{idx}.bin")
        link_bins.append(p.read_bytes())

    # 读取 dstexe 的 link table，得到每条脚本指向位置
    rows = []
    with open(ini.dstexe, "rb") as f:
        f.seek(ini.linktbl - ini.base)
        for _ in range(ini.linkcnt):
            code, secid, ign, pp, func = struct.unpack("<2BH2I", f.read(12))
            rows.append((code, secid, pp))

    # 读取 cn json（用于比较 xC1/xCD）
    link_json = pathlib.Path(f"{ini.link}.{link_ids[0]}.cn.txt")
    sections = json.loads(link_json.read_text(encoding="utf-8"))
    if len(sections) != len(rows):
        raise RuntimeError(f"{ini_name}: section count mismatch {len(sections)} != {len(rows)}")

    mismatches: List[CheckItem] = []
    for i, (row, sec) in enumerate(zip(rows, sections)):
        _, secid, pp = row
        if pp == 0xFFFFFFFF:
            raw_ops = []
        else:
            data_id = 0
            if link_sep is not None and secid >= link_sep:
                data_id = 1
            off = pp - ini.linkbuf
            asm_bytes, _ = dec(link_bins[data_id][off:])
            raw_ops = parse_x_ops(bytes(asm_bytes))

        json_ops = parse_json_x_ops(sec)
        if raw_ops != json_ops:
            mismatches.append(
                CheckItem(
                    ini_name=ini_name,
                    section_idx=i,
                    secid=secid,
                    raw_ops=raw_ops,
                    json_ops=json_ops,
                )
            )
    return mismatches


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Check xC1/xCD cmd2 flags are preserved in cn json.")
    p.add_argument("--root", default=".", help="project root")
    p.add_argument("--scripts-dir", default="scripts", help="scripts dir")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    root = pathlib.Path(args.root).resolve()
    sdir = (root / args.scripts_dir).resolve()

    all_mismatches: List[CheckItem] = []
    for ini_name in INI_FILES:
        ini_path = sdir / ini_name
        ini = load_ini(ini_path)
        mm = check_one(ini_name, ini, root)
        all_mismatches.extend(mm)
        print(f"{ini_name}: mismatches={len(mm)}")
        for it in mm[:10]:
            print(
                f"  - sec#{it.section_idx} secid={it.secid} raw={it.raw_ops} json={it.json_ops}"
            )
        if len(mm) > 10:
            print(f"  - ... ({len(mm) - 10} more)")

    print(f"TOTAL_MISMATCHES={len(all_mismatches)}")
    return 1 if all_mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
