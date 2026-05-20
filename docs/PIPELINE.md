# 完整运行链

本文档说明本仓库从原始镜像到可测试镜像的最小可执行流程。

仓库只保存脚本、字库种子和可编辑文本，不保存原始游戏数据，也不保存重打包后的镜像。

## 1. 数据边界

提交到 Git 的内容：

- 构建脚本和校验脚本。
- `Tansaku-he.build.xml` 打包模板。
- `seed/font/font.db`。
- `seed/font/KFONT.CDB.{0,1,2,3,5,7}.{txt,lst}`。
- `source/translated/` 下的可编辑译文。
- `baselines/v2/` 下的基线快照。
- `mkpsxiso` / `dumpsxiso` 以及随包许可证文档。

不提交的本地产物：

- `work/`
- `output/`
- `*.bin`
- `*.cue`
- `*.iso`
- `*.img`
- `*.chd`
- `__pycache__/`
- `*.pyc`

## 2. 环境要求

最低要求：

- Linux 或 WSL。
- `bash`。
- `python3`。
- `sha256sum`。
- `tools/mkpsxiso-2.20-Linux/bin/dumpsxiso`。
- `tools/mkpsxiso-2.20-Linux/bin/mkpsxiso`。

可选字形重绘依赖：

```bash
python3 -m pip install pillow
```

## 3. 工作目录模型

```text
work/file0
  原始镜像解包底稿。作为干净源目录，不直接打包。

work/dst0
  实际回写和打包目录。每次构建前都会从 work/file0 重置。

source/translated
  人工编辑译文目录。

baselines/v2
  随包基线译文和 cn.raw 快照。

seed/font
  字体数据库和章节字表种子。

output
  最终输出的 cue/bin 和 sha256。
```

## 4. 一键流程

在仓库根目录执行：

```bash
bash scripts/01_extract_from_disc.sh "/path/to/Twilight Syndrome - Tansaku-hen (Japan).cue"
bash scripts/02_prepare_cnraw.sh
bash scripts/03_build_iso.sh Tansaku-he_custom
```

输出：

```text
output/Tansaku-he_custom.bin
output/Tansaku-he_custom.cue
output/Tansaku-he_custom.sha256.txt
```

## 5. 第一步：解包并提取文本

```bash
bash scripts/01_extract_from_disc.sh "/path/to/Twilight Syndrome - Tansaku-hen (Japan).cue"
```

脚本会执行：

1. 删除旧的 `work/file0` 和 `work/dst0`。
2. 使用 `dumpsxiso` 解包原始镜像。
3. 把解包结果写入 `work/file0`。
4. 复制 `work/file0` 到 `work/dst0`。
5. 复制 `seed/font/*` 到 `work/file0/DAT/FONT/`。
6. 对六组脚本执行 `linkdec`。
7. 如果 `source/translated/` 缺文件，则用提取出的 raw 文本初始化。

生成的 raw 文本：

```text
work/file0/DAT/CAP0/K0LINK.CDB.13.raw.txt
work/file0/DAT/CAP1/K1LINK.CDB.20.raw.txt
work/file0/DAT/CAP2/K2LINK.CDB.19.raw.txt
work/file0/DAT/CAP3/K3LINK.CDB.0.raw.txt
work/file0/DAT/CAP4/W4LINK.CDB.0.raw.txt
work/file0/DAT/CAPX/WXLINK.CDB.0.raw.txt
```

同时会在相同目录生成结构化脚本文件，供后续 `merge` 使用。

## 6. 第二步：编辑译文

编辑：

```text
source/translated/K0LINK.CDB.13.txt
source/translated/K1LINK.CDB.20.txt
source/translated/K2LINK.CDB.19.txt
source/translated/K3LINK.CDB.0.txt
source/translated/W4LINK.CDB.0.txt
source/translated/WXLINK.CDB.0.txt
```

规则：

- 行数不能变。
- 控制符不能丢。
- 角色名前缀结构要有效。
- 每个显示段不要超过文本框可容纳宽度。
- 新增字符如果不在 `font.db` 中，需要先补字或重建字库。

常见控制符：

```text
<BEGIN>
<HEAD,n>
<RET>
<PRESS,n>
<NEXT>
<END>
<SEL,n>
<COL,n>
<CASE,n>
<CEND,n>
```

## 7. 第三步：生成构建用 `cn.raw`

```bash
bash scripts/02_prepare_cnraw.sh
```

脚本会执行：

1. `check_speaker_line_counts.py`
2. `prepare_cn_raw_strict.py --write`
3. 把严格对齐后的 `*.cn.raw.txt` 写入 `work/file0/DAT/...`

生成文件：

```text
work/file0/DAT/CAP0/K0LINK.CDB.13.cn.raw.txt
work/file0/DAT/CAP1/K1LINK.CDB.20.cn.raw.txt
work/file0/DAT/CAP2/K2LINK.CDB.19.cn.raw.txt
work/file0/DAT/CAP3/K3LINK.CDB.0.cn.raw.txt
work/file0/DAT/CAP4/W4LINK.CDB.0.cn.raw.txt
work/file0/DAT/CAPX/WXLINK.CDB.0.cn.raw.txt
```

可选裁剪：

```bash
python3 scripts/fix_cnraw_overflow.py --root . --write
```

这个命令会直接删减超长字符。建议只在人工确认后使用。

## 8. 第四步：补丁、合并、构建、回写、打包

```bash
bash scripts/03_build_iso.sh Tansaku-he_custom
```

脚本会执行：

1. 用 `work/file0` 重置 `work/dst0`。
2. 对六个章节配置执行 `patch -> merge -> build`。
3. 生成新的脚本 bin 和字体 bin。
4. 用 `cdb.py` 回写 `KxLINK.CDB` 和 `KFONT.CDB` 对应分段。
5. 执行回写一致性检查。
6. 执行 `cmd2` 控制标志检查。
7. 用 `mkpsxiso` 重新打包 cue/bin。
8. 生成 SHA-256。

## 9. 手工等价命令

### 9.1 解包

```bash
mkdir -p work/file0 work/dst0
tools/mkpsxiso-2.20-Linux/bin/dumpsxiso \
  -x work/file0 \
  -s work/file0/original_dump.xml \
  "/path/to/original.cue"

cp -a work/file0/. work/dst0/
cp -f seed/font/* work/file0/DAT/FONT/
```

### 9.2 提取脚本

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

### 9.3 准备 `cn.raw`

```bash
python3 scripts/check_speaker_line_counts.py --root . --strict-map
python3 scripts/prepare_cn_raw_strict.py --root . --write
```

### 9.4 合并和构建

```bash
cd scripts
for ini in cap0.work.ini cap1.work.ini cap2.work.ini cap3.work.ini cap4.work.ini capX.work.ini; do
  python3 main.py patch "$ini"
  python3 main.py merge "$ini"
  python3 main.py build "$ini"
done
cd ..
```

### 9.5 回写 CDB

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

### 9.6 校验和打包

```bash
python3 scripts/verify_writeback_consistency.py --root . --scripts-dir scripts

cd scripts
python3 check_cmd2_flags.py --root .. --scripts-dir scripts
cd ..

mkdir -p output
tools/mkpsxiso-2.20-Linux/bin/mkpsxiso \
  -y \
  -o output/Tansaku-he_custom.bin \
  -c output/Tansaku-he_custom.cue \
  Tansaku-he.build.xml

sha256sum output/Tansaku-he_custom.bin output/Tansaku-he_custom.cue \
  > output/Tansaku-he_custom.sha256.txt
```

## 10. 主要脚本职责

```text
scripts/main.py
  命令入口。

scripts/linkdec.py
  从 link CDB 和 EXE 表中提取脚本结构和 raw 文本。

scripts/prepare_cn_raw_strict.py
  把译文套回原始控制符骨架，生成 cn.raw。

scripts/merge.py
  校验 raw/cn.raw 控制符一致性，并生成可构建脚本 JSON。

scripts/build.py
  重建脚本 bin、章节字体 bin 和 EXE 映射表。

scripts/patch.py
  修改 CAP*.EXE 的字库读取逻辑。

scripts/cdb.py
  把生成的 bin 写回 CDB 分段，并在必要时修正 CDB 头部。

scripts/verify_writeback_consistency.py
  检查生成的 bin 是否确实写入目标 CDB。

scripts/check_cmd2_flags.py
  检查关键控制命令标志是否被构建过程破坏。
```

## 11. 字库说明

当前仓库带有可直接使用的 `seed/font/font.db`。对随包基线文本来说，不需要额外生成字体。

如果译文引入新字符，需要回到完整研发工程，或把以下可选脚本补入当前仓库：

```text
scripts/expand_font_db_simplified.py
scripts/fontdec.py
scripts/mkfont.py
```

详细机制见 [FONT_EXPANSION.md](FONT_EXPANSION.md)。

## 12. 恢复随包基线

```bash
bash scripts/04_restore_v2_baseline.sh
```

这个命令会从 `baselines/v2/translated/` 恢复 `source/translated/`。如果已经完成解包，也会把随包 `cn.raw` 快照恢复到 `work/file0`。

## 13. 发布前检查

本地发布或测试重打包镜像前，至少确认：

- `scripts/02_prepare_cnraw.sh` 成功退出。
- `scripts/03_build_iso.sh` 成功退出。
- `verify_writeback_consistency.py` 没有 BAD 项。
- `check_cmd2_flags.py` 没有 mismatch。
- 输出 cue/bin 能在模拟器中启动。
