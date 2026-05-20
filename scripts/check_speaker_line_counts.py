#!/usr/bin/env python3
import argparse
import pathlib
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, List, Tuple


PAIR_MAP: Dict[str, str] = {
    "K0LINK.CDB.13.txt": "work/file0/DAT/CAP0/K0LINK.CDB.13.raw.txt",
    "K1LINK.CDB.20.txt": "work/file0/DAT/CAP1/K1LINK.CDB.20.raw.txt",
    "K2LINK.CDB.19.txt": "work/file0/DAT/CAP2/K2LINK.CDB.19.raw.txt",
    "K3LINK.CDB.0.txt": "work/file0/DAT/CAP3/K3LINK.CDB.0.raw.txt",
    "W4LINK.CDB.0.txt": "work/file0/DAT/CAP4/W4LINK.CDB.0.raw.txt",
    "WXLINK.CDB.0.txt": "work/file0/DAT/CAPX/WXLINK.CDB.0.raw.txt",
}

DEFAULT_NAME_MAP: Dict[str, str] = {
    "ユカリ": "由佳里",
    "ミカ": "美嘉",
    "チサト": "千里",
    "ミホ": "美穗",
    "キミカ": "希美香",
    "先生": "老师",
    "母親": "母亲",
    "チサトの母": "千里的母亲",
    "駅員": "站员",
    "駅員A": "站员A",
    "駅員B": "站员B",
    "通行人": "路人",
    "老人": "老人",
    "北村": "北村",
    "奥野": "奥野",
    "鹿野": "鹿野",
    "3人": "三人",
    "三人": "三人",
    "際田": "际田",
    "際田先生": "际田老师",
    "謎の男": "谜之男",
    "川上": "川上",
    "スダ": "须田",
    "ミシマ": "三岛",
    "ユカリ·チサト": "由佳里·千里",
}


HEAD_RE = re.compile(r"<HEAD,\d+>")
NAME_COLON_RE = re.compile(r"([\u4e00-\u9fffぁ-ゖァ-ヺA-Za-z]{1,12})[:：;；]")


@dataclass
class HeadEvent:
    line_no: int
    idx_in_line: int
    name: str
    valid: bool
    detail: str


def nearest_colon(s: str, start: int) -> int:
    idxs = [s.find(":", start), s.find("：", start), s.find(";", start), s.find("；", start)]
    idxs = [x for x in idxs if x != -1]
    if not idxs:
        return -1
    return min(idxs)


def normalize_name(name: str) -> str:
    return name.replace("⍽", "").strip()


def extract_head_events(line: str, line_no: int) -> List[HeadEvent]:
    out: List[HeadEvent] = []
    for idx, m in enumerate(HEAD_RE.finditer(line), start=1):
        colon = nearest_colon(line, m.end())
        next_ctrl = line.find("<", m.end())
        if colon == -1 or (next_ctrl != -1 and next_ctrl < colon):
            out.append(
                HeadEvent(
                    line_no=line_no,
                    idx_in_line=idx,
                    name="",
                    valid=False,
                    detail="HEAD 后未找到合法 '名字:'",
                )
            )
            continue
        raw_name = line[m.end() : colon]
        nm = normalize_name(raw_name)
        if not nm:
            out.append(
                HeadEvent(
                    line_no=line_no,
                    idx_in_line=idx,
                    name="",
                    valid=False,
                    detail="HEAD 名字为空",
                )
            )
            continue
        out.append(
            HeadEvent(
                line_no=line_no,
                idx_in_line=idx,
                name=nm,
                valid=True,
                detail="",
            )
        )
    return out


def is_attached_to_head_prefix(line: str, pos: int) -> bool:
    prefix = line[:pos]
    m = re.search(r"<HEAD,\d+>$", prefix)
    return m is not None


def collect_stray_name_prefixes(
    line: str,
    line_no: int,
    known_names: set,
) -> List[str]:
    bad: List[str] = []
    for m in NAME_COLON_RE.finditer(line):
        nm = normalize_name(m.group(1))
        if nm not in known_names:
            continue
        # 复合名字“由佳里·千里:”中的后半段不算串位
        if m.start() > 0 and line[m.start() - 1] in ("·", "・"):
            continue
        if is_attached_to_head_prefix(line, m.start()):
            continue
        bad.append(f"L{line_no} pos{m.start()+1} '{nm}:' 非 HEAD 前缀")
    return bad


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="检查六个文本中角色发言句数是否稳定，并检测粘连型'角色名:'串位",
    )
    p.add_argument("--root", default=".", help="项目根目录")
    p.add_argument("--translated-dir", default="source/translated", help="译文目录")
    p.add_argument(
        "--report",
        default="work/check_speaker_line_counts_report.txt",
        help="报告输出路径",
    )
    p.add_argument("--max-samples", type=int, default=80, help="每文件最多输出样例条数")
    p.add_argument(
        "--strict-map",
        action="store_true",
        help="严格使用 DEFAULT_NAME_MAP 做句数/说话人校验（推荐）",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    root = pathlib.Path(args.root).resolve()
    translated_dir = (root / args.translated_dir).resolve()
    report_path = (root / args.report).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)

    report: List[str] = []
    total_files = 0
    total_head_invalid = 0
    total_head_count_mismatch = 0
    total_mapping_mismatch = 0
    total_expected_mismatch = 0
    total_stray_prefix = 0

    for src_name, raw_rel in PAIR_MAP.items():
        src = translated_dir / src_name
        raw = root / raw_rel
        report.append(f"== {src_name} ==")
        total_files += 1

        if not src.exists():
            report.append(f"[ERROR] missing translated: {src}")
            report.append("")
            continue
        if not raw.exists():
            report.append(f"[ERROR] missing raw: {raw}")
            report.append("")
            continue

        src_lines = src.read_text(encoding="utf-8").splitlines()
        raw_lines = raw.read_text(encoding="utf-8").splitlines()
        if len(src_lines) != len(raw_lines):
            report.append(
                f"[ERROR] line_count mismatch translated={len(src_lines)} raw={len(raw_lines)}"
            )
            report.append("")
            continue

        raw_events: List[HeadEvent] = []
        src_events: List[HeadEvent] = []
        head_count_mismatch_lines: List[str] = []
        invalid_head_lines: List[str] = []

        for ln, (rl, sl) in enumerate(zip(raw_lines, src_lines), start=1):
            revents = extract_head_events(rl, ln)
            sevents = extract_head_events(sl, ln)
            raw_events.extend(revents)
            src_events.extend(sevents)
            if len(revents) != len(sevents):
                head_count_mismatch_lines.append(
                    f"L{ln} HEAD 数量不同 raw={len(revents)} tr={len(sevents)}"
                )
            for i_ev, ev in enumerate(sevents):
                # raw 同位置本来就不是合法“名字:”时，视为脚本结构特例，不记问题
                raw_same = revents[i_ev] if i_ev < len(revents) else None
                if not ev.valid and (raw_same is None or raw_same.valid):
                    invalid_head_lines.append(f"L{ev.line_no}#{ev.idx_in_line} {ev.detail}")

        raw_valid = [e for e in raw_events if e.valid]
        src_valid = [e for e in src_events if e.valid]
        pair_n = min(len(raw_valid), len(src_valid))

        mapping_counter: Dict[str, Counter] = defaultdict(Counter)
        raw_count = Counter()
        expected_count = Counter()
        actual_by_raw_count = defaultdict(Counter)
        for i in range(pair_n):
            rn = raw_valid[i].name
            sn = src_valid[i].name
            mapping_counter[rn][sn] += 1
            raw_count[rn] += 1
            actual_by_raw_count[rn][sn] += 1

        dominant_map: Dict[str, str] = {}
        for rn, c in mapping_counter.items():
            dominant_map[rn] = c.most_common(1)[0][0]

        expected_map: Dict[str, str] = {}
        for rn in mapping_counter.keys():
            if args.strict_map and rn in DEFAULT_NAME_MAP:
                expected_map[rn] = DEFAULT_NAME_MAP[rn]
            else:
                # 优先默认映射；没有时回退到数据驱动映射
                expected_map[rn] = DEFAULT_NAME_MAP.get(rn, dominant_map[rn])
            expected_count[rn] = raw_count[rn]

        mapping_mismatch_samples: List[str] = []
        expected_mismatch_samples: List[str] = []
        for i in range(pair_n):
            rn = raw_valid[i].name
            sn = src_valid[i].name
            if rn not in dominant_map:
                continue
            if sn != dominant_map[rn]:
                mapping_mismatch_samples.append(
                    f"L{src_valid[i].line_no}#{src_valid[i].idx_in_line} raw='{rn}' tr='{sn}' 期望='{dominant_map[rn]}'"
                )
            exp = expected_map[rn]
            if sn != exp:
                expected_mismatch_samples.append(
                    f"L{src_valid[i].line_no}#{src_valid[i].idx_in_line} raw='{rn}' tr='{sn}' 期望(映射)='{exp}'"
                )

        known_names = set([e.name for e in src_valid] + list(expected_map.values()) + list(DEFAULT_NAME_MAP.keys()))
        stray_samples: List[str] = []
        for ln, sl in enumerate(src_lines, start=1):
            stray_samples.extend(collect_stray_name_prefixes(sl, ln, known_names))

        head_invalid_cnt = len(invalid_head_lines)
        head_count_mismatch_cnt = len(head_count_mismatch_lines)
        mapping_mismatch_cnt = len(mapping_mismatch_samples)
        expected_mismatch_cnt = len(expected_mismatch_samples)
        stray_cnt = len(stray_samples)

        total_head_invalid += head_invalid_cnt
        total_head_count_mismatch += head_count_mismatch_cnt
        total_mapping_mismatch += mapping_mismatch_cnt
        total_expected_mismatch += expected_mismatch_cnt
        total_stray_prefix += stray_cnt

        report.append(f"line_count: {len(src_lines)}")
        report.append(f"head_total_raw: {len(raw_events)}")
        report.append(f"head_total_tr: {len(src_events)}")
        report.append(f"head_invalid_tr: {head_invalid_cnt}")
        report.append(f"head_count_mismatch_lines: {head_count_mismatch_cnt}")
        report.append(f"speaker_mapping_mismatch: {mapping_mismatch_cnt}")
        report.append(f"speaker_expected_mismatch: {expected_mismatch_cnt}")
        report.append(f"stray_name_prefix: {stray_cnt}")

        report.append("raw_speaker_counts(固定基数):")
        for rn, cnt in raw_count.most_common():
            exp = expected_map.get(rn, "?")
            top_actual = actual_by_raw_count[rn].most_common(3)
            top_s = ", ".join([f"{k}:{v}" for k, v in top_actual])
            report.append(f"  - {rn}: {cnt} 期望='{exp}' 实际TOP=[{top_s}]")

        if head_count_mismatch_lines:
            report.append("samples_head_count_mismatch:")
            for s in head_count_mismatch_lines[: args.max_samples]:
                report.append(f"  - {s}")

        if invalid_head_lines:
            report.append("samples_head_invalid:")
            for s in invalid_head_lines[: args.max_samples]:
                report.append(f"  - {s}")

        if mapping_mismatch_samples:
            report.append("samples_mapping_mismatch:")
            for s in mapping_mismatch_samples[: args.max_samples]:
                report.append(f"  - {s}")

        if expected_mismatch_samples:
            report.append("samples_expected_mismatch:")
            for s in expected_mismatch_samples[: args.max_samples]:
                report.append(f"  - {s}")

        if stray_samples:
            report.append("samples_stray_name_prefix:")
            for s in stray_samples[: args.max_samples]:
                report.append(f"  - {s}")

        report.append("")

    report.append("== TOTAL ==")
    report.append(f"files: {total_files}")
    report.append(f"head_invalid_tr: {total_head_invalid}")
    report.append(f"head_count_mismatch_lines: {total_head_count_mismatch}")
    report.append(f"speaker_mapping_mismatch: {total_mapping_mismatch}")
    report.append(f"speaker_expected_mismatch: {total_expected_mismatch}")
    report.append(f"stray_name_prefix: {total_stray_prefix}")
    report.append(f"report: {report_path}")

    text = "\n".join(report) + "\n"
    report_path.write_text(text, encoding="utf-8")
    print(text, end="")

    if (
        total_head_invalid
        or total_head_count_mismatch
        or total_mapping_mismatch
        or total_expected_mismatch
        or total_stray_prefix
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
