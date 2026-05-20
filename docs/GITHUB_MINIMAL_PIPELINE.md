# GitHub 最小可执行运行链

本文档用于说明本仓库的最小可执行汉化链路。仓库不包含原始游戏镜像、解包后的游戏文件或重打包镜像；使用者需要自行准备合法拥有的原始日版 `.cue/.bin`。

## 1. 仓库内容

```text
.
├── README.md
├── Tansaku-he.build.xml
├── scripts/
│   ├── 01_extract_from_disc.sh
│   ├── 02_prepare_cnraw.sh
│   ├── 03_build_iso.sh
│   ├── 04_restore_v2_baseline.sh
│   ├── main.py
│   ├── build.py
│   ├── cdb.py
│   ├── fontlib.py
│   ├── fontdb.py
│   ├── ini.py
│   ├── linkdec.py
│   ├── merge.py
│   ├── patch.py
│   ├── init_translated_from_raw.py
│   ├── prepare_cn_raw_strict.py
│   ├── fix_cnraw_overflow.py
│   ├── check_speaker_line_counts.py
│   ├── verify_writeback_consistency.py
│   ├── check_cmd2_flags.py
│   ├── rle.py
│   └── cap*.work.ini
├── seed/font/
│   ├── font.db
│   └── KFONT.CDB.{0,1,2,3,5,7}.{txt,lst}
├── source/translated/
│   └── 六个可编辑译文 txt
└── tools/mkpsxiso-2.20-Linux/bin/
    ├── dumpsxiso
    └── mkpsxiso
```

不应提交：

```text
work/
output/
*.bin
*.cue
*.iso
*.img
*.chd
*.rar
*.zip
__pycache__/
```

## 2. 运行环境

- Linux 或 WSL
- `bash`
- `python3`
- `sha256sum`
- `dumpsxiso`
- `mkpsxiso`

主链路默认不需要 Pillow，因为 `seed/font/` 已经包含可构建的 `font.db` 和字表种子。只有重新制作或统一重绘字形时才需要安装：

```bash
python3 -m pip install pillow
```

## 3. 一键主流程

以下命令均在仓库根目录执行。

### 3.1 从原始镜像解包

```bash
bash scripts/01_extract_from_disc.sh "/path/to/Twilight Syndrome - Tansaku-hen (Japan).cue"
```

这一步会：

1. 用 `dumpsxiso` 解包到 `work/file0`
2. 复制 `work/file0` 到 `work/dst0`
3. 把 `seed/font/` 写入 `work/file0/DAT/FONT/`
4. 对六章执行 `python3 main.py linkdec cap*.work.ini`
5. 生成原始脚本文本 `*.raw.txt`
6. 如果 `source/translated/` 缺文件，则用 raw 文本初始化可编辑译文

### 3.2 翻译文本

编辑这些文件：

```text
source/translated/K0LINK.CDB.13.txt
source/translated/K1LINK.CDB.20.txt
source/translated/K2LINK.CDB.19.txt
source/translated/K3LINK.CDB.0.txt
source/translated/W4LINK.CDB.0.txt
source/translated/WXLINK.CDB.0.txt
```

约束：

- 行数必须与对应 `*.raw.txt` 一致
- 控制符必须保留，例如 `<BEGIN>`、`<HEAD,3>`、`<RET>`、`<NEXT>`、`<END>`
- 每个显示段建议不超过 20 个可见字符
- 人名后的冒号建议统一使用半角 `:`

### 3.3 生成构建用 `cn.raw`

```bash
bash scripts/02_prepare_cnraw.sh
```

这一步会：

1. `check_speaker_line_counts.py` 检查说话人和行数
2. `prepare_cn_raw_strict.py --write` 把译文套回原始控制符骨架
3. 在 `work/file0/DAT/...` 下生成 `*.cn.raw.txt`

可选裁剪命令：

```bash
python3 scripts/fix_cnraw_overflow.py --root . --write
```

该命令会直接删减超长字符，默认不建议自动执行。

### 3.4 回写文本、字库并打包

```bash
bash scripts/03_build_iso.sh Tansaku-he_custom
```

这一步会：

1. 用 `work/file0` 重置 `work/dst0`
2. 对六章依次执行 `patch -> merge -> build`
3. 生成新的章节脚本 bin 和字体 bin
4. 用 `cdb.py` 回写 `DAT/CAP*/K*LINK.CDB` 和 `DAT/FONT/KFONT.CDB`
5. 执行 `verify_writeback_consistency.py` 和 `check_cmd2_flags.py`
6. 用 `mkpsxiso` 根据 `Tansaku-he.build.xml` 重新打包

输出文件：

```text
output/Tansaku-he_custom.bin
output/Tansaku-he_custom.cue
output/Tansaku-he_custom.sha256.txt
```

## 4. 手工命令链

### 4.1 解包游戏

```bash
mkdir -p work/file0 work/dst0
tools/mkpsxiso-2.20-Linux/bin/dumpsxiso \
  -x work/file0 \
  -s work/file0/original_dump.xml \
  "/path/to/original.cue"
cp -a work/file0/. work/dst0/
cp -f seed/font/* work/file0/DAT/FONT/
```

### 4.2 提取文本

```bash
cd scripts
python3 main.py linkdec cap0.work.ini
python3 main.py linkdec cap1.work.ini
python3 main.py linkdec cap2.work.ini
python3 main.py linkdec cap3.work.ini
python3 main.py linkdec cap4.work.ini
python3 main.py linkdec capX.work.ini
cd ..
python3 scripts/init_translated_from_raw.py --root .
```

### 4.3 准备译文 raw

```bash
python3 scripts/check_speaker_line_counts.py --root . --strict-map
python3 scripts/prepare_cn_raw_strict.py --root . --write
```

### 4.4 合并和构建

```bash
cd scripts
for ini in cap0.work.ini cap1.work.ini cap2.work.ini cap3.work.ini cap4.work.ini capX.work.ini; do
  python3 main.py patch "$ini"
  python3 main.py merge "$ini"
  python3 main.py build "$ini"
done
cd ..
```

### 4.5 回写 CDB

```bash
cd scripts
python3 cdb.py ../work/dst0/DAT/CAP0/K0LINK.CDB 13
python3 cdb.py ../work/dst0/DAT/FONT/KFONT.CDB 0
python3 cdb.py ../work/dst0/DAT/CAP1/K1LINK.CDB 20
python3 cdb.py ../work/dst0/DAT/CAP1/K1LINK.CDB 18
python3 cdb.py ../work/dst0/DAT/FONT/KFONT.CDB 3
python3 cdb.py ../work/dst0/DAT/CAP2/K2LINK.CDB 19
python3 cdb.py ../work/dst0/DAT/CAP2/K2LINK.CDB 7
python3 cdb.py ../work/dst0/DAT/FONT/KFONT.CDB 1
python3 cdb.py ../work/dst0/DAT/CAP3/K3LINK.CDB 0
python3 cdb.py ../work/dst0/DAT/CAP3/K3LINK.CDB 1
python3 cdb.py ../work/dst0/DAT/FONT/KFONT.CDB 5
python3 cdb.py ../work/dst0/DAT/CAP4/W4LINK.CDB 0
python3 cdb.py ../work/dst0/DAT/CAP4/W4LINK.CDB 1
python3 cdb.py ../work/dst0/DAT/FONT/KFONT.CDB 2
python3 cdb.py ../work/dst0/DAT/CAPX/WXLINK.CDB 0
python3 cdb.py ../work/dst0/DAT/FONT/KFONT.CDB 7
cd ..
```

### 4.6 检查和打包

```bash
python3 scripts/verify_writeback_consistency.py --root . --scripts-dir scripts
cd scripts
python3 check_cmd2_flags.py --root .. --scripts-dir scripts
cd ..

tools/mkpsxiso-2.20-Linux/bin/mkpsxiso \
  -y \
  -o output/Tansaku-he_custom.bin \
  -c output/Tansaku-he_custom.cue \
  Tansaku-he.build.xml

sha256sum output/Tansaku-he_custom.bin output/Tansaku-he_custom.cue \
  > output/Tansaku-he_custom.sha256.txt
```

## 5. 字表和字形制作

正常翻译和打包不需要重新制作字形。如果译文新增了 seed 字库没有覆盖的字符，需要从完整工程补入：

```text
scripts/expand_font_db_simplified.py
scripts/fontdec.py
scripts/fontdb.py
scripts/mkfont.py
```

示例：

```bash
python3 scripts/expand_font_db_simplified.py \
  --root . \
  --fontdb work/file0/DAT/FONT/font.db \
  --font-path /mnt/c/Windows/Fonts/simhei.ttf \
  --font-size 15 \
  --override-existing-cjk \
  --write
```

之后再执行 `03_build_iso.sh` 即可让新字形进入最终镜像。

## 6. 最小验证标准

一次可发布构建至少应满足：

```bash
bash scripts/01_extract_from_disc.sh "/path/to/original.cue"
bash scripts/02_prepare_cnraw.sh
bash scripts/03_build_iso.sh Tansaku-he_custom
```

成功后确认：

```text
output/Tansaku-he_custom.bin
output/Tansaku-he_custom.cue
output/Tansaku-he_custom.sha256.txt
```

并且构建日志中：

```text
verify_writeback_consistency.py: BAD=0
check_cmd2_flags.py: BAD=0
```
