# Twilight Syndrome: Tansaku-hen Translation Kit

《黄昏症候群 探索篇》（`Twilight Syndrome: Tansaku-hen`）逆向分析与多语言翻译构建工具链。

这个仓库不发布游戏镜像，也不包含原始解包数据。它保存的是一条可以复现的翻译工程链路：从合法拥有的 PlayStation 原始镜像解包资源，提取脚本文本，编辑译文，重建脚本和字库资源，再重新打包为本地测试用的 `.bin/.cue`。

## 项目定位

这个仓库包含：

- 可运行的解包、文本提取、合并、构建、回写和打包脚本。
- `source/translated/` 下的可编辑基线文本。
- 可直接构建当前基线的 `seed/font/font.db` 与章节字表种子。
- 当前稳定基线的 `translated` / `cn.raw` 快照。
- `mkpsxiso` / `dumpsxiso` 工具及其随包许可证文档。

这个仓库不包含：

- 原始游戏镜像。
- `work/` 下的完整解包结果。
- 重新打包后的 `.bin/.cue`。
- 全量历史研发目录、旧版镜像、调试备份和大型产物。

使用者需要自行准备合法拥有的原始日版镜像。

## 快速开始

在仓库根目录执行：

```bash
bash scripts/01_extract_from_disc.sh "/path/to/Twilight Syndrome - Tansaku-hen (Japan).cue"
bash scripts/02_prepare_cnraw.sh
bash scripts/03_build_iso.sh Tansaku-he_custom
```

输出文件：

```text
output/Tansaku-he_custom.bin
output/Tansaku-he_custom.cue
output/Tansaku-he_custom.sha256.txt
```

完整运行链见 [docs/PIPELINE.md](docs/PIPELINE.md)。

字库扩容机制见 [docs/FONT_EXPANSION.md](docs/FONT_EXPANSION.md)。

## 翻译入口

解包后，编辑这些文件：

```text
source/translated/K0LINK.CDB.13.txt
source/translated/K1LINK.CDB.20.txt
source/translated/K2LINK.CDB.19.txt
source/translated/K3LINK.CDB.0.txt
source/translated/W4LINK.CDB.0.txt
source/translated/WXLINK.CDB.0.txt
```

当前随仓库放入的是基线中文译文，但工具链并不限定只能做中文。只要文本控制符、行数和字库支持满足要求，也可以用于其他语言。

编辑时必须注意：

- 行数必须与提取出的 `*.raw.txt` 一致。
- 控制符必须保留，例如 `<BEGIN>`、`<HEAD,3>`、`<RET>`、`<NEXT>`、`<END>`。
- 角色名前缀结构要保持有效。
- 每个显示段需要控制长度，避免文本框溢出。
- 如果新增字符不在 `font.db` 中，需要先补字或重建字库。

## 目录结构

```text
.
├── README.md
├── Tansaku-he.build.xml
├── baselines/
│   └── v2/
│       ├── translated/
│       └── cnraw/
├── docs/
│   ├── PIPELINE.md
│   └── FONT_EXPANSION.md
├── scripts/
│   ├── 01_extract_from_disc.sh
│   ├── 02_prepare_cnraw.sh
│   ├── 03_build_iso.sh
│   ├── 04_restore_v2_baseline.sh
│   ├── main.py
│   ├── linkdec.py
│   ├── merge.py
│   ├── build.py
│   ├── patch.py
│   ├── cdb.py
│   └── cap*.work.ini
├── seed/
│   └── font/
├── source/
│   └── translated/
└── tools/
    └── mkpsxiso-2.20-Linux/
```

本地生成目录不会提交：

```text
work/
output/
```

## 构建链路概览

主链路：

```text
原始 cue/bin
  -> dumpsxiso 解包
  -> work/file0
  -> linkdec 提取脚本
  -> raw text + script JSON
  -> source/translated 编辑译文
  -> prepare_cn_raw_strict 生成 cn.raw
  -> merge 合并回脚本 JSON
  -> build 重建脚本与字库 bin
  -> cdb.py 回写 CDB 分段
  -> mkpsxiso 打包
  -> output cue/bin
```

字库链路：

```text
font.db
  -> 章节字表 KFONT.CDB.*.cn.txt
  -> 章节字体二进制 KFONT.CDB.*.bin
  -> DAT/FONT/KFONT.CDB
  -> CAP*.EXE 字表补丁
```

## 运行环境

最低要求：

- Linux 或 WSL
- `bash`
- `python3`
- `sha256sum`
- 随包 `dumpsxiso`
- 随包 `mkpsxiso`

只有重新制作或统一重绘字形时才需要 Pillow：

```bash
python3 -m pip install pillow
```

当前精简仓库默认不需要 Pillow，因为 `seed/font/` 已经包含可构建的字库种子。

## 恢复基线文本

```bash
bash scripts/04_restore_v2_baseline.sh
```

这个命令会把 `baselines/v2/translated/` 恢复到 `source/translated/`。如果已经完成解包，也会同步恢复六个 `cn.raw` 到 `work/file0`。

## 文档

- [docs/PIPELINE.md](docs/PIPELINE.md)：完整可执行运行链。
- [docs/FONT_EXPANSION.md](docs/FONT_EXPANSION.md)：扩容字库、字形重绘、EXE 字表重写和 CDB 回写机制。

## 法律说明

本仓库只用于逆向研究、翻译和保存工作流，不分发游戏镜像或原始游戏数据。请只在合法拥有原盘的前提下使用。
