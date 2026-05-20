from copyreg import pickle
from ini import Ini
from fontlib import FontLib
from merge import mark
import os
import pickle
from fontdb import read20
import io
from rle import (enc, dec, enc_safe)
import json
from linkdec import asm
import struct
import re
from collections import Counter

def enc2(b: bytes):
	for x in b:
		lx = x & 0xf
		hx = x >> 4
		if lx not in [0, 4, 6] or hx not in [0, 4, 6]:
			return b

	ret = io.BytesIO()
	# magic number
	ret.write(b'\x1E')
	assert len(b) == 16*8
	for i in range(0, len(b), 2):
		lx0, hx0 = b[i] & 0xf, b[i] >> 4
		lx1, hx1 = b[i+1] & 0xf, b[i+1] >> 4

		ret.write(bytes([
			(lx0 >> 1) | (hx0 << 1) | (lx1 << 3) | (hx1 << 5)
		]))
	return ret.getvalue()

def mkfont(db, ftbl, fcnt, lib: FontLib, fbin, maxsz, z, priority_chars=None):
	cs = read20(ftbl)

	# 先准备 bin
	bin = io.BytesIO()
	bin.write(enc(db['PAL']))

	mpos = {}
	for c in cs:
		b, sz = db[c]
		assert sz > 0, c
		mpos[c] = (bin.tell(), sz)
		if z:
			b = enc2(b)
		bin.write(enc(b))

	assert bin.tell() <= maxsz, bin.tell()

	with open(fbin, "wb") as f:
		f.write(bin.getvalue())

	# idx -> off, sz, 字
	lst = []
	# 字体反查
	rmap = {}

	mm = {}
	mmr = set()
	for i in range(fcnt):
		c = lib.get(i)
		if c in mark:
			mm[i] = c
			mmr.add(c)

	# 优先把插图/XA相关文本字符放入前 fcnt 段，降低章节切换黑屏风险
	prio = set(priority_chars or [])
	nonmark = [c for c in cs if c not in mmr]
	order = [c for c in nonmark if c in prio] + [c for c in nonmark if c not in prio]
	assert len(order) == len(nonmark)

	i = 0
	oi = 0
	while oi < len(order):
		c = None
		if i in mm:
			c = mm[i]
		else:
			c = order[oi]
			oi += 1
		assert c is not None

		lst.append(mpos[c])
		rmap[c] = i
		i += 1

	assert i == len(cs)

	return lst, rmap


def make_safe_rmap(rmap, fcnt):
	# 兜底：脚本文本尽量只用 < fontcnt 的索引，避免未覆盖路径触发异常
	fb_candidates = ["？", "·", "。", "、", " "]
	fb_idx = None
	for c in fb_candidates:
		if c in rmap and rmap[c] < fcnt:
			fb_idx = rmap[c]
			break
	if fb_idx is None:
		for c, idx in rmap.items():
			if idx < fcnt:
				fb_idx = idx
				break
	assert fb_idx is not None

	out = dict(rmap)
	remap = {}
	for c, idx in rmap.items():
		if c in mark:
			continue
		if idx >= fcnt:
			out[c] = fb_idx
			remap[c] = idx
	return out, remap


_CTRL_RE = re.compile(r'<[^>]+>')


def collect_priority_chars(flink):
	with open(flink, "rt", encoding="utf-8") as f:
		link = json.load(f)

	cnt_xa = Counter()
	cnt_all = Counter()
	for sec in link:
		has_xa = any(v[0] == "XA" for v in sec[1:])
		for v in sec[1:]:
			if v[0] != "TEXT":
				continue
			txt = _CTRL_RE.sub("", v[1]).replace("⍽", "")
			if not txt:
				continue
			cnt_all.update(txt)
			if has_xa:
				cnt_xa.update(txt)

	# 仅优先 XA 文本字符；其余字符保持原顺序
	return [c for c, _ in cnt_xa.most_common()]

def mklink(lst, rmap, flink, dstlinks, linksep, linkcnt):
	with open(flink, "rt", encoding='utf-8') as f:
		link = json.load(f)
	assert len(link) == linkcnt
	use_safe_rle = os.environ.get("TS_RLE_SAFE", "0") == "1"
	enc_link = enc_safe if use_safe_rle else enc

	bins = [io.BytesIO(), io.BytesIO()]
	# code, secid, pp, func
	lst = []

	for v in link:
		secid, codeH, codeL, func, _ = v[0]
		if isinstance(func, str):
			func = int(func, 16)
		pp = 0xFFFFFFFF
		if len(v) > 1:
			dataid = 0
			if linksep is not None and secid >= linksep:
				dataid = 1
			bin = bins[dataid]
			pp = bin.tell()

			tmp = io.BytesIO()
			asm(rmap, tmp, v[1:])

			encb = enc_link(tmp.getvalue())
			assert dec(encb)[0] == tmp.getvalue()
			bin.write(encb)

		lst.append(((codeH<<4)|codeL, secid, pp, func))

	for i, dst in enumerate(dstlinks):
		with open(dst, "wb") as f:
			f.write(bins[i].getvalue())
	return lst

def patchexe(flst, llst, ini: Ini):
	# 写码表
	with open(ini.dstexe, "rb+") as f:
		f.seek(ini.fonttbl - ini.base)

		for off, sz in flst:
			assert off <= 0xffffff
			# f.write(struct.pack("<2I", ini.fontbuf+off, sz))
			# 采用压缩法
			f.write(struct.pack("<I", (off << 8) | sz))

		f.seek(ini.linktbl - ini.base)

		for code, secid, pp, func in llst:
			if pp != 0xFFFFFFFF:
				pp += ini.linkbuf
			f.write(struct.pack("<2BH2I", code, secid, 0, pp, func))

def build(ini: Ini, lib: FontLib):
	fontdb = os.path.join(os.path.dirname(ini.font), 'font.db')
	with open(fontdb, "rb") as f:
		db = pickle.load(f)

	fontname = "{}.{}".format(ini.font, ini.fontid)
	ftbl = fontname + ".cn.txt"
	fbin = "{}.{}.bin".format(ini.dstfont, ini.fontid)

	linkname = "{}.{}".format(ini.link, ini.linkid()[0][0])
	flink = linkname + ".cn.txt"
	dstlinks = ["{}.{}.bin".format(ini.dstlink, id) for id in ini.linkid()[0]]

	priority_chars = collect_priority_chars(flink)

	# 生成 字库 lst bin sz
	flst, rmap = mkfont(db, ftbl, ini.fontcnt, lib, fbin, ini.fontmax, ini.fontzip, priority_chars=priority_chars)
	use_safe_rmap = os.environ.get("TS_SAFE_RMAP", "0") == "1"
	if use_safe_rmap:
		rmap, remap = make_safe_rmap(rmap, ini.fontcnt)
		if remap:
			print("safe_remap", len(remap))
	else:
		print("safe_remap_disabled")
	print(len(flst), hex(len(flst)*8), len(flst)<=ini.fontcnt)
	assert len(flst) > ini.fontcnt and len(flst) <= ini.fontcnt * 2

	llst = mklink(flst, rmap, flink, dstlinks, ini.linkid()[1], ini.linkcnt)
	if os.path.exists(ini.dstexe):
		patchexe(flst, llst, ini)
