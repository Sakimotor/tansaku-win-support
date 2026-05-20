# Twilight Syndrome Tansaku-hen 翻译工具链执行手册

本文档说明如何用本仓库从合法自备的《黄昏症候群 探索篇》原版镜像开始，完成：

1. 原盘解包
2. 字体与字表种子准备
3. 文本提取
4. 翻译文本编辑
5. 构建用 `cn.raw` 生成
6. 字形库和章节字库重建
7. 文本与字体回写
8. EXE patch
9. 全盘镜像重新打包
10. 本地测试与推送前检查

这不是游戏数据仓库。公开仓库只保存脚本、配置、基线译文、字库种子和文档；原始镜像、解包后的游戏文件、BIOS、模拟器、构建输出、日志都不应提交。

## 1. 重要概念

### 原盘文件

用户自己准备的原版 PS1 镜像：

```text
origin_iso/Twilight Syndrome - Tansaku-hen (Japan).cue
origin_iso/Twilight Syndrome - Tansaku-hen (Japan).bin
```

这些文件不能提交。

仓库脚本不强制使用 `origin_iso/` 目录；只要把 `.cue` 路径传给 `scripts/01_extract_from_disc.sh` 即可。

### `work/file0`

`dumpsxiso` 解包出来的干净游戏文件树：

```text
work/file0/
```

里面有：

```text
CAP0.EXE
CAP1.EXE
CAP2.EXE
CAP3.EXE
CAP4.EXE
CAPX.EXE
DAT/FONT/KFONT.CDB
DAT/CAP0/K0LINK.CDB
DAT/CAP1/K1LINK.CDB
DAT/CAP2/K2LINK.CDB
DAT/CAP3/K3LINK.CDB
DAT/CAP4/W4LINK.CDB
DAT/CAPX/WXLINK.CDB
```

`work/file0` 来自原盘，不能提交。

### `work/dst0`

实际构建和回写目录：

```text
work/dst0/
```

每次执行 `scripts/03_build_iso.sh` 时，脚本都会先用 `work/file0` 重置 `work/dst0`，然后把 patch 后的 EXE、脚本 CDB、字体 CDB 写入这里。

`work/dst0` 不能提交。

### XML 打包模板

重新打包使用：

```text
Tansaku-he.build.xml
```

它描述输出镜像的目录结构、文件顺序、XA/STR 类型等。模板中的 `source=` 指向 `work/dst0`，所以打包前必须先完成构建回写。

### ini 配置

每个 `scripts/cap*.work.ini` 描述一个章节的 EXE、文本 CDB、字体 CDB 和表地址。

示例：

```ini
srcdir = ../work/file0
dstdir = ../work/dst0
exe = CAP2.EXE
link = DAT/CAP2/K2LINK.CDB
font = DAT/FONT/KFONT.CDB
fontid = 1
linkid = 19,13,7
fonttbl = 0x8008C820
linktbl = 0x80093D70
```

含义：

- `srcdir`: 原始解包目录。
- `dstdir`: 构建输出目录。
- `exe`: 当前章节 EXE。
- `link`: 当前章节文本 CDB。
- `font`: 字体 CDB。
- `fontid`: `KFONT.CDB` 中的字体 entry。
- `linkid`: 文本 CDB 中需要构建/回写的 entry。三段写法表示该 CDB 使用两个文本 entry，并有章节分隔点。
- `fonttbl`: EXE 中字体表地址。
- `linktbl`: EXE 中文本表地址。

### CDB

游戏使用的容器文件。脚本用 [scripts/cdb.py](scripts/cdb.py) 读写 entry。

本项目主要处理：

```text
DAT/FONT/KFONT.CDB
DAT/CAP0/K0LINK.CDB
DAT/CAP1/K1LINK.CDB
DAT/CAP2/K2LINK.CDB
DAT/CAP3/K3LINK.CDB
DAT/CAP4/W4LINK.CDB
DAT/CAPX/WXLINK.CDB
```

### 字表与字形库

字体相关文件：

```text
KFONT.CDB.<fontid>.txt      # 字符表，20 字一行
KFONT.CDB.<fontid>.lst      # 字形偏移表
font.db                     # 构建用字形库
```

本精简仓库公开保留：

```text
seed/font/font.db
seed/font/KFONT.CDB.0.txt
seed/font/KFONT.CDB.0.lst
seed/font/KFONT.CDB.1.txt
seed/font/KFONT.CDB.1.lst
seed/font/KFONT.CDB.2.txt
seed/font/KFONT.CDB.2.lst
seed/font/KFONT.CDB.3.txt
seed/font/KFONT.CDB.3.lst
seed/font/KFONT.CDB.5.txt
seed/font/KFONT.CDB.5.lst
seed/font/KFONT.CDB.7.txt
seed/font/KFONT.CDB.7.lst
```

这些是当前基线可构建所需的字体种子。完整字形提取、重绘和扩容机制见 [docs/FONT_EXPANSION.md](docs/FONT_EXPANSION.md)。

### 文本文件

当前链路使用旧式 raw/cn.raw 合并流程：

```text
*.txt          # linkdec 导出的结构化脚本 JSON
*.raw.txt      # linkdec 导出的原始可读文本
*.cn.raw.txt   # 翻译后、控制符严格对齐的构建输入
*.cn.txt       # merge 生成的构建用结构化脚本 JSON
```

推荐人工编辑入口是：

```text
source/translated/*.txt
```

不要直接手改 `work/file0/DAT/.../*.txt` 里的脚本 JSON，除非你明确知道控制码结构。

## 2. 环境准备

### Python

推荐 Python 3.11+。

```bash
python3 --version
```

当前精简链路默认不需要 Pillow，因为已经随包提供 `seed/font/font.db`。

如果要重新绘制或扩容字形，需要：

```bash
python3 -m pip install pillow
```

### mkpsxiso

仓库内已经包含：

```text
tools/mkpsxiso-2.20-Linux/bin/dumpsxiso
tools/mkpsxiso-2.20-Linux/bin/mkpsxiso
```

用途：

- `dumpsxiso`: 从原始 cue/bin 解包光盘文件树。
- `mkpsxiso`: 根据 `Tansaku-he.build.xml` 重新打包 cue/bin。

### 中文或目标语言字体

随包基线不需要本地字体。

如果你新增大量未覆盖字符，需要从完整工程补入字形重绘脚本，并指定 TTF/TTC 字体，例如：

```text
/mnt/c/Windows/Fonts/simhei.ttf
/mnt/c/Windows/Fonts/simsun.ttc
/mnt/c/Windows/Fonts/msyh.ttc
```

## 3. 目录约定

推荐本地目录：

```text
origin_iso/                         # 本地原版镜像，不提交
work/file0/                         # 原盘解包目录，不提交
work/dst0/                          # 构建回写目录，不提交
work/file0/original_dump.xml        # dumpsxiso 生成的 XML，不提交
output/                             # 输出镜像，不提交
baselines/v2/                       # 随包基线，可提交
seed/font/                          # 字体种子，可提交
source/translated/                  # 可编辑译文，可提交
scripts/                            # 可提交脚本
docs/                               # 可提交文档
```

`.gitignore` 已忽略主要本地产物：

```text
work/
output/
*.bin
*.cue
*.iso
*.img
*.chd
*.pyc
__pycache__/
```

## 4. 从原盘解包

输入：

```text
origin_iso/Twilight Syndrome - Tansaku-hen (Japan).cue
origin_iso/Twilight Syndrome - Tansaku-hen (Japan).bin
```

命令：

```bash
bash scripts/01_extract_from_disc.sh \
  "origin_iso/Twilight Syndrome - Tansaku-hen (Japan).cue"
```

脚本实际执行：

1. 清理旧的 `work/file0` 和 `work/dst0`。
2. 用 `dumpsxiso` 解包原盘到 `work/file0`。
3. 复制一份干净底稿到 `work/dst0`。
4. 把 `seed/font` 中的字体种子写入 `work/file0/DAT/FONT/`。
5. 对六章执行 `linkdec`。
6. 如果 `source/translated` 缺文件，则从 `*.raw.txt` 初始化。

检查：

```bash
test -f work/file0/CAP0.EXE
test -f work/file0/DAT/FONT/KFONT.CDB
test -f work/file0/DAT/CAP0/K0LINK.CDB
test -f work/file0/DAT/CAPX/WXLINK.CDB
```

常见错误：

- `dumpsxiso: No such file`: 工具路径不对或没有执行权限。
- 找不到 `.bin`: `.cue` 里的 `FILE` 行和实际文件名不一致。
- 解包后缺 `license_data.dat`: 重新用随包脚本解包，确认 `dumpsxiso -s` 正常生成 XML 和 license 文件。

## 5. 章节配置概览

| 章节 | 配置 | EXE | 文本 CDB | linkid | fontid |
| --- | --- | --- | --- | --- | --- |
| cap0 | `scripts/cap0.work.ini` | `CAP0.EXE` | `DAT/CAP0/K0LINK.CDB` | `13` | `0` |
| cap1 | `scripts/cap1.work.ini` | `CAP1.EXE` | `DAT/CAP1/K1LINK.CDB` | `20,3,18` | `3` |
| cap2 | `scripts/cap2.work.ini` | `CAP2.EXE` | `DAT/CAP2/K2LINK.CDB` | `19,13,7` | `1` |
| cap3 | `scripts/cap3.work.ini` | `CAP3.EXE` | `DAT/CAP3/K3LINK.CDB` | `0,3,1` | `5` |
| cap4 | `scripts/cap4.work.ini` | `CAP4.EXE` | `DAT/CAP4/W4LINK.CDB` | `0,2,1` | `2` |
| capX | `scripts/capX.work.ini` | `CAPX.EXE` | `DAT/CAPX/WXLINK.CDB` | `0` | `7` |

## 6. 字体和字表准备

精简仓库已经带有可构建的字体种子：

```text
seed/font/font.db
seed/font/KFONT.CDB.*.txt
seed/font/KFONT.CDB.*.lst
```

`scripts/01_extract_from_disc.sh` 会自动复制：

```bash
cp -f seed/font/* work/file0/DAT/FONT/
```

因此正常使用时不需要再执行 `fontdec` 或 `fontdb.py update`。

如果你要从零重新提取字体，需要回到完整研发工程，使用：

```bash
python3 scripts/main.py fontdec <cap*.ini>
python3 scripts/main.py dumpsz <cap*.ini>
python3 scripts/fontdb.py update <KFONT.CDB.fontid>
python3 scripts/fontdb.py pal <KFONT.CDB>
```

当前公开精简仓库只保留主链路，不默认携带完整字形重绘工具。详细机制见 [docs/FONT_EXPANSION.md](docs/FONT_EXPANSION.md)。

## 7. 提取文本

解包脚本会自动执行文本提取。手动等价命令：

```bash
cd scripts
python3 main.py linkdec cap0.work.ini
python3 main.py linkdec cap1.work.ini
python3 main.py linkdec cap2.work.ini
python3 main.py linkdec cap3.work.ini
python3 main.py linkdec cap4.work.ini
python3 main.py linkdec capX.work.ini
cd ..
```

输出在 CDB 旁边，例如：

```text
work/file0/DAT/CAP0/K0LINK.CDB.13.txt
work/file0/DAT/CAP0/K0LINK.CDB.13.raw.txt
work/file0/DAT/CAP1/K1LINK.CDB.20.txt
work/file0/DAT/CAP1/K1LINK.CDB.20.raw.txt
work/file0/DAT/CAP2/K2LINK.CDB.19.txt
work/file0/DAT/CAP2/K2LINK.CDB.19.raw.txt
work/file0/DAT/CAP3/K3LINK.CDB.0.txt
work/file0/DAT/CAP3/K3LINK.CDB.0.raw.txt
work/file0/DAT/CAP4/W4LINK.CDB.0.txt
work/file0/DAT/CAP4/W4LINK.CDB.0.raw.txt
work/file0/DAT/CAPX/WXLINK.CDB.0.txt
work/file0/DAT/CAPX/WXLINK.CDB.0.raw.txt
```

含义：

- `*.txt`: 结构化脚本 JSON，包含控制命令和文本段。
- `*.raw.txt`: 可读文本导出，用作译文行数和控制符骨架基准。

常见错误：

- 文本全是占位符或乱码：字体种子没有复制到 `DAT/FONT/`，或 `fontid` 不匹配。
- `assert` 失败：原盘版本或 CDB entry 与当前配置不匹配。

## 8. 翻译文本

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

- 行数必须与对应 `*.raw.txt` 一致。
- 保留所有控制符。
- 不要删除 `⍽` 这类占位符，除非你确认后续脚本会处理。
- 角色名后的冒号建议统一为半角 `:`。
- 每个显示段建议控制在 20 个可见字符以内。
- 当前基线是中文，但工具链本身可以用于其他语言；前提是字库和宽度限制能满足目标语言。

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

## 9. 生成构建用 `cn.raw`

命令：

```bash
bash scripts/02_prepare_cnraw.sh
```

脚本会：

1. 运行说话人/行数检查。
2. 把 `source/translated` 严格套回 raw 控制符骨架。
3. 生成 `work/file0/DAT/.../*.cn.raw.txt`。

输出：

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

注意：这个命令会直接删字符，不建议默认自动执行。更推荐人工调整译文。

## 10. 文本、字体和 EXE 回写

命令：

```bash
bash scripts/03_build_iso.sh Tansaku-he_custom
```

脚本做的事：

1. 用 `work/file0` 重新覆盖 `work/dst0`。
2. 对六章依次执行：
   - `python3 main.py patch <ini>`
   - `python3 main.py merge <ini>`
   - `python3 main.py build <ini>`
3. 生成章节文本 bin 和字体 bin。
4. 用 `cdb.py` 回写 `KxLINK.CDB` 和 `KFONT.CDB` 对应分段。
5. 运行 `verify_writeback_consistency.py`。
6. 运行 `check_cmd2_flags.py`。
7. 用 `mkpsxiso` 打包输出镜像。

其中：

- `patch`: 修改 `CAP*.EXE` 的字库读取逻辑和表格式。
- `merge`: 校验 raw/cn.raw 控制符一致性，并生成构建用 `*.cn.txt`。
- `build`: 根据 `font.db`、章节字表和脚本 JSON 生成新 bin，并改写 EXE 表。
- `cdb.py`: 把生成的 bin 写回 CDB entry。

## 11. 手动回写命令

如果不使用一键脚本，构建阶段可以手动执行：

```bash
cd scripts
for ini in cap0.work.ini cap1.work.ini cap2.work.ini cap3.work.ini cap4.work.ini capX.work.ini; do
  python3 main.py patch "$ini"
  python3 main.py merge "$ini"
  python3 main.py build "$ini"
done
cd ..
```

CDB 回写：

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

校验：

```bash
python3 scripts/verify_writeback_consistency.py --root . --scripts-dir scripts

cd scripts
python3 check_cmd2_flags.py --root .. --scripts-dir scripts
cd ..
```

## 12. 打包

一键脚本已经包含打包步骤：

```bash
bash scripts/03_build_iso.sh Tansaku-he_custom
```

输出：

```text
output/Tansaku-he_custom.bin
output/Tansaku-he_custom.cue
output/Tansaku-he_custom.sha256.txt
```

手动打包：

```bash
mkdir -p output
tools/mkpsxiso-2.20-Linux/bin/mkpsxiso \
  -y \
  -o output/Tansaku-he_custom.bin \
  -c output/Tansaku-he_custom.cue \
  Tansaku-he.build.xml

sha256sum output/Tansaku-he_custom.bin output/Tansaku-he_custom.cue \
  > output/Tansaku-he_custom.sha256.txt
```

注意：

- `Tansaku-he.build.xml` 指向 `work/dst0`。
- 如果只改了 `work/file0` 而没有执行构建回写，打包不会包含你的改动。
- 输出镜像不要提交。

## 13. 恢复随包基线

命令：

```bash
bash scripts/04_restore_v2_baseline.sh
```

作用：

1. 把 `baselines/v2/translated/*.txt` 复制回 `source/translated/`。
2. 如果已经解包，也把 `baselines/v2/cnraw/*.cn.raw.txt` 复制回 `work/file0/DAT/...`。

## 14. 测试

用模拟器加载输出 `.cue`。

最少检查：

1. 能启动。
2. 能进入各章节。
3. 字体显示正常。
4. 没有大量 `□`、`⍽`、空白字。
5. 对话能翻页。
6. 选项能选择。
7. 等待、音效、语音没有明显错位。
8. 章节切换、关键跳转和结尾不死机。

测试产物不要提交：

```text
output/
work/
*.bin
*.cue
*.mcd
pcsx-redux-*/
```

## 15. 推送 GitHub 前检查

确认没有把镜像、解包文件、缓存或二进制产物加入 Git：

```bash
git diff --cached --name-only | rg -i '\.(bin|cue|iso|img|rom|dll|exe|zip|png|jpg|pyc)$|(^|/)work/|(^|/)output/|origin_iso|pcsx'
```

期望没有输出。

检查敏感 token：

```bash
git diff --cached --name-only | xargs -r rg -n 'g[h]p_' || true
git diff --cached --name-only | xargs -r rg -n 'github_[p]at_' || true
```

检查 Python 语法：

```bash
python3 -m compileall -q scripts
```

查看提交范围：

```bash
git status --short
git diff --cached --stat
```

## 16. 推荐最小复现路径

从零开始最稳的验证路径：

```bash
# 1. 解包并提取文本
bash scripts/01_extract_from_disc.sh \
  "origin_iso/Twilight Syndrome - Tansaku-hen (Japan).cue"

# 2. 编辑 source/translated/*.txt

# 3. 生成 cn.raw
bash scripts/02_prepare_cnraw.sh

# 4. 构建、回写、校验并打包
bash scripts/03_build_iso.sh Tansaku-he_custom
```

成功后检查：

```text
output/Tansaku-he_custom.bin
output/Tansaku-he_custom.cue
output/Tansaku-he_custom.sha256.txt
```

## 17. 工具链关系图

```text
合法自备 cue/bin
  |
  | dumpsxiso
  v
work/file0 + original_dump.xml
  |
  | seed/font 写入 DAT/FONT
  v
KFONT.CDB.<id>.txt/lst + font.db
  |
  | linkdec
  v
*.txt + *.raw.txt
  |
  | 编辑 source/translated/*.txt
  v
译文文本
  |
  | prepare_cn_raw_strict.py
  v
*.cn.raw.txt
  |
  | merge.py
  v
*.cn.txt
  |
  | build.py + patch.py
  v
新字体 bin + 新文本 bin + patched EXE
  |
  | cdb.py
  v
work/dst0/DAT/... CDB
  |
  | verify_writeback_consistency.py + check_cmd2_flags.py
  v
已校验 dst0
  |
  | mkpsxiso
  v
output/*.cue + output/*.bin
```
