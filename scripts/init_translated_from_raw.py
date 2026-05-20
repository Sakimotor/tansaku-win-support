#!/usr/bin/env python3
import argparse
import pathlib


PAIR_MAP = {
    "K0LINK.CDB.13.txt": "work/file0/DAT/CAP0/K0LINK.CDB.13.raw.txt",
    "K1LINK.CDB.20.txt": "work/file0/DAT/CAP1/K1LINK.CDB.20.raw.txt",
    "K2LINK.CDB.19.txt": "work/file0/DAT/CAP2/K2LINK.CDB.19.raw.txt",
    "K3LINK.CDB.0.txt": "work/file0/DAT/CAP3/K3LINK.CDB.0.raw.txt",
    "W4LINK.CDB.0.txt": "work/file0/DAT/CAP4/W4LINK.CDB.0.raw.txt",
    "WXLINK.CDB.0.txt": "work/file0/DAT/CAPX/WXLINK.CDB.0.raw.txt",
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Initialize source/translated from extracted raw texts.")
    ap.add_argument("--root", default=".", help="project root")
    ap.add_argument("--force", action="store_true", help="overwrite existing translated files")
    args = ap.parse_args()

    root = pathlib.Path(args.root).resolve()
    tdir = root / "source" / "translated"
    tdir.mkdir(parents=True, exist_ok=True)

    copied = 0
    skipped = 0
    for name, raw_rel in PAIR_MAP.items():
        src = root / raw_rel
        dst = tdir / name
        if not src.exists():
            raise SystemExit(f"missing raw file: {src}")
        if dst.exists() and not args.force:
            skipped += 1
            continue
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        copied += 1

    print(f"copied={copied} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
