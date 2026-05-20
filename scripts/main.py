#!/usr/bin/env python3
import configparser
import sys

from ini import Ini


def load_ini(path: str) -> Ini:
    conf = configparser.ConfigParser()
    conf.read(path, encoding="utf-8")
    return Ini(conf["project"])


def main(argv):
    if len(argv) != 3:
        raise SystemExit("usage: python3 main.py <fontdec|linkdec|dumpsz|merge|build|patch|test> <ini>")

    cmd = argv[1]
    ini = load_ini(argv[2])

    if cmd == "fontdec":
        from fontdec import fontdec

        fontdec(ini)
    elif cmd == "linkdec":
        from fontlib import FontLib
        from linkdec import linkdec

        linkdec(ini, FontLib(ini))
    elif cmd == "dumpsz":
        from fontlib import FontLib, dumpsz

        dumpsz(ini, FontLib(ini))
    elif cmd == "merge":
        from merge import merge

        merge(ini)
    elif cmd == "build":
        from build import build
        from fontlib import FontLib

        build(ini, FontLib(ini))
    elif cmd == "patch":
        from patch import patch

        patch(ini)
    elif cmd == "test":
        from fontlib import FontLib

        fontlib = FontLib(ini)
        for c in "ユカリチサトミシマ":
            print(fontlib.getr(c))
    else:
        raise SystemExit(f"unknown command: {cmd}")


if __name__ == "__main__":
    main(sys.argv)
