#!/usr/bin/env python3
import argparse
import configparser
import pathlib
from dataclasses import dataclass
from typing import List, Tuple

from cdb import CDB
from ini import Ini


INI_FILES = [
    "cap0.work.ini",
    "cap1.work.ini",
    "cap2.work.ini",
    "cap3.work.ini",
    "cap4.work.ini",
    "capX.work.ini",
]


@dataclass
class CheckResult:
    name: str
    kind: str
    idx: int
    ok: bool
    detail: str


def load_ini(path: pathlib.Path) -> Ini:
    conf = configparser.ConfigParser()
    conf.read(path, encoding="utf-8")
    return Ini(conf["project"])


def pad_sector(data: bytes) -> bytes:
    rem = len(data) % 2048
    if rem == 0:
        return data
    return data + (b"\0" * (2048 - rem))


def compare_cdb_section(cdb_path: pathlib.Path, idx: int, expected_data: bytes) -> Tuple[bool, str]:
    db = CDB(str(cdb_path))
    got = db.read(idx)
    exp = pad_sector(expected_data)
    if got == exp:
        return True, f"exact len={len(exp)}"

    # cdb.py 在 new<=old 时会保留原分段长度，多余部分填 0
    if len(got) > len(exp):
        tail = got[len(exp) :]
        if got[: len(exp)] == exp and all(b == 0 for b in tail):
            return True, f"prefix_match len={len(exp)} padded_to={len(got)}"

    if len(got) != len(exp):
        return False, f"size_mismatch got={len(got)} exp={len(exp)}"
    # same size, compare first diff
    for i, (a, b) in enumerate(zip(got, exp)):
        if a != b:
            return False, f"byte_mismatch@{i} got=0x{a:02x} exp=0x{b:02x}"
    return False, "unknown_mismatch"


def verify_one(ini: Ini) -> List[CheckResult]:
    out: List[CheckResult] = []

    # link bins -> link cdb sections
    link_ids, _ = ini.linkid()
    link_cdb = pathlib.Path(ini.dstlink)
    for idx in link_ids:
        bin_path = pathlib.Path(f"{ini.dstlink}.{idx}.bin")
        if not bin_path.exists():
            out.append(
                CheckResult(
                    name=link_cdb.name,
                    kind="link",
                    idx=idx,
                    ok=False,
                    detail=f"missing_bin:{bin_path}",
                )
            )
            continue
        ok, detail = compare_cdb_section(link_cdb, idx, bin_path.read_bytes())
        out.append(CheckResult(name=link_cdb.name, kind="link", idx=idx, ok=ok, detail=detail))

    # font bin -> font cdb section
    font_idx = ini.fontid
    font_cdb = pathlib.Path(ini.dstfont)
    font_bin = pathlib.Path(f"{ini.dstfont}.{font_idx}.bin")
    if not font_bin.exists():
        out.append(
            CheckResult(
                name=font_cdb.name,
                kind="font",
                idx=font_idx,
                ok=False,
                detail=f"missing_bin:{font_bin}",
            )
        )
    else:
        ok, detail = compare_cdb_section(font_cdb, font_idx, font_bin.read_bytes())
        out.append(CheckResult(name=font_cdb.name, kind="font", idx=font_idx, ok=ok, detail=detail))

    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Verify build bin is written back into dst0 CDB sections exactly.")
    p.add_argument("--root", default=".", help="project root")
    p.add_argument("--scripts-dir", default="scripts", help="scripts dir relative to root")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    root = pathlib.Path(args.root).resolve()
    sdir = (root / args.scripts_dir).resolve()

    results: List[CheckResult] = []
    for ini_name in INI_FILES:
        ini_path = sdir / ini_name
        ini = load_ini(ini_path)
        results.extend(verify_one(ini))

    bad = [r for r in results if not r.ok]
    for r in results:
        status = "OK" if r.ok else "NG"
        print(f"[{status}] {r.kind} {r.name} idx={r.idx} {r.detail}")
    print(f"TOTAL={len(results)} BAD={len(bad)}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
