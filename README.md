# Tansaku-he 精简生成链

这个包只保留“解包 -> 提取文本 -> 编辑译文 -> 生成 `cn.raw` -> 回写 -> 打包 ISO”的关键链路。

目标是：

- 别人拿到后能直接跑
- 不把整个 30 多 GB 工程一起打包
- 保留当前稳定的 `v1/v2` 文本基线

## 包内包含

- `scripts/`
  核心构建脚本、校验脚本、一键 shell
- `tools/mkpsxiso-2.20-Linux/bin/`
  `dumpsxiso`、`mkpsxiso`
- `seed/font/`
  已提取好的 `font.db` 和 `KFONT.CDB.{0,1,2,3,5,7}.{txt,lst}`
- `source/translated/`
  预置 `v2` 基线译文，可直接编辑
- `baselines/v2/`
  `v2` 的 `translated` 和 `cnraw`，用于一键回退
- `Tansaku-he.build.xml`
  打包模板

## 没有包含什么

- 原始日版镜像
- 完整 `work/file0` / `work/dst0` 解包结果
- 字体重绘链、LLM 清洗链、历史版本快照

这样包体会保持很小，但仍能从原始镜像开始完整走通主流程。

## 运行环境

- Linux / WSL
- `bash`
- `python3`

这个精简包默认不依赖 `Pillow`，因为首次初始化直接使用已提取好的字体种子，不再强制跑 `fontdec`。

## 推荐流程

### 1. 从原始镜像解包并提取文本

```bash
bash scripts/01_extract_from_disc.sh "/path/to/Twilight Syndrome - Tansaku-hen (Japan).cue"
```

这一步会：

1. 用 `dumpsxiso` 解包到 `work/file0`
2. 复制一份干净底稿到 `work/dst0`
3. 写入 `seed/font` 里的字体元数据
4. 对六章执行 `linkdec`
5. 在 `work/file0/DAT/...` 下生成：
   - `*.txt`
   - `*.raw.txt`
6. 如果 `source/translated` 缺文件，则用 raw 文本初始化

### 2. 编辑译文

直接改：

- `source/translated/K0LINK.CDB.13.txt`
- `source/translated/K1LINK.CDB.20.txt`
- `source/translated/K2LINK.CDB.19.txt`
- `source/translated/K3LINK.CDB.0.txt`
- `source/translated/W4LINK.CDB.0.txt`
- `source/translated/WXLINK.CDB.0.txt`

包里预置的是 `v2` 基线译文，所以即使不改，也可以直接构建一次验证环境。

### 3. 生成构建用 `cn.raw`

```bash
bash scripts/02_prepare_cnraw.sh
```

这一步会：

1. 检查说话人/行数
2. 把 `source/translated` 严格套回 raw 控制符骨架
3. 生成 `work/file0/DAT/.../*.cn.raw.txt`

注意：

- `scripts/fix_cnraw_overflow.py --write` 是可选的
- 它会直接删字符，不建议默认自动执行

### 4. 打包 ISO

```bash
bash scripts/03_build_iso.sh Tansaku-he_custom_v1text
```

这一步会：

1. 用 `work/file0` 重新覆盖 `work/dst0`
2. 对六章依次执行 `patch -> merge -> build`
3. 用 `cdb.py` 回写 `KxLINK.CDB` 和 `KFONT.CDB`
4. 跑：
   - `verify_writeback_consistency.py`
   - `check_cmd2_flags.py`
5. 用 `mkpsxiso` 输出到 `output/`

最终产物：

- `output/Tansaku-he_custom_v1text.bin`
- `output/Tansaku-he_custom_v1text.cue`
- `output/Tansaku-he_custom_v1text.sha256.txt`

## 一键回退到 v2 文本

```bash
bash scripts/04_restore_v2_baseline.sh
```

作用：

- 恢复 `source/translated` 到 `v2`
- 如果已经完成解包，也同步恢复六个 `cn.raw`

## 目录说明

- `work/file0`
  原始解包底稿，不直接打包
- `work/dst0`
  每次构建前由 `file0` 重置，实际写回目标
- `source/translated`
  人工编辑区
- `output`
  最终镜像输出目录

## 已知约束

- 这是当前项目的“主链精简包”，不是全量研发仓库
- 默认针对《トワイライトシンドローム 探索編》当前这套目录/表地址/六章配置
- 若要继续做字体扩容、字模重绘、LLM 批量修文，请回到原仓库
