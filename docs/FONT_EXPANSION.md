# 扩容字库完整文档

## 1. 文档目的

本文档用于说明本项目的“扩容字库”机制，包括：

- 最终可用版本实际采用的字库方案
- `font.db -> build -> KFONT.CDB -> EXE 字表` 的完整数据流
- 字库扩容到底是“原址覆盖”还是“重建回写”
- 项目如何判断“还能扩多少”以及“什么叫安全”
- 复现与排错时应重点查看哪些脚本和日志

本文档基于当前仓库源码与现存构建产物整理，重点以当前可用基线 `v2` 为准。


## 2. 结论先行

### 2.1 当前 `v2` 的真实来源

当前仓库中的可玩基线 `Twilight_Syndrome_CN_v2.bin`，并不是早期那个真正的 `v2`。

它实际上是后期 `v39_colonfix_20260214_042615` 改名后的基线包：

- `Twilight_Syndrome_CN_v2.sha256.txt` 中的 `bin` 哈希与 `work/sha256_v39_colonfix_20260214_042615.txt` 完全一致
- `baselines/v2_strong_baseline_20260214/meta/baseline_manifest.json` 中保留的日志链也明确指向 `v39_colonfix_20260214_042615`

因此，分析“最后可用版本的字库扩容方案”，本质上就是分析 `v39_colonfix` 这条链。

### 2.2 最终采用的字库方案

最终可用版采用的是一套 **基于 `font.db` 的离线重绘 + 章节字库重建 + EXE 字表重写** 的方案，而不是运行时动态加载 TTF，也不是简单的原址覆盖旧字模。

核心特征如下：

1. 从六个章节对应的 `KFONT.CDB.*.cn.txt` 中收集实际需要的字符集合。
2. 使用系统字体将目标 CJK 字符重绘为 16x16 点阵，写回 `font.db`。
3. 在构建阶段根据 `font.db` 重新生成每章使用的字体二进制。
4. 将新字体块写回 `KFONT.CDB` 对应分段，同时重写 EXE 内的字体索引表。
5. 最终允许总字数扩展到每章 `fontcnt * 2` 以内，并同时受 `fontmax` 字节上限约束。

对 `v39/v2` 而言，实际采用的是：

- 字体：`simhei.ttf`
- 字号：`15`
- 策略：覆盖重绘目标 CJK（`override_existing_cjk=True`）
- 非 CJK 缺字：不额外补绘（`include_missing_non_cjk=False`）


## 3. 总体架构

整个字库系统可以拆成 4 层：

1. **字形数据库层**：`font.db`
2. **章节字体描述层**：`KFONT.CDB.<fontid>.txt / .sz / .lst / .bin`
3. **镜像资源层**：`DAT/FONT/KFONT.CDB`
4. **执行映射层**：各章 `CAP*.EXE` 内的字体表 `fonttbl`

它们的职责分别是：

- `font.db`：保存“字符 -> 点阵 + 宽度”的主字典
- `*.txt`：该章字表顺序
- `*.sz`：每个字符的 advance/宽度
- `*.lst`：字体块内的位移映射
- `KFONT.CDB`：最终写回镜像的字库资源容器
- `CAP*.EXE` 中的 `fonttbl`：运行时的“索引 -> 偏移/宽度”表


## 4. 关键脚本与职责

### 4.1 `scripts/expand_font_db_simplified.py`

职责：

- 统计当前六章译文实际需要的字符
- 用 TTF/TTC 重绘缺字或覆盖现有 CJK 字形
- 直接更新 `font.db`

这是“扩容字形生产”的入口。

### 4.2 `scripts/build.py`

职责：

- 从 `font.db` 取出本章需要的字形
- 重新打包为章节字体二进制
- 重建字符索引到新偏移的映射
- 重写 EXE 中的 `fonttbl`
- 生成对应 link bin

这是“把字形变成真正可运行字库”的入口。

### 4.3 `scripts/cdb.py`

职责：

- 将构建产物写回 `KFONT.CDB` / `KxLINK.CDB`
- 当某个分段变大时，自动平移其后的分段并修正头部索引

这说明最终并不是“必须原址等长覆盖”，而是允许同一 CDB 内部做分段扩展。

### 4.4 `scripts/fontlib.py`

职责：

- 从原始 `KFONT.CDB.<id>.lst/.txt` 和 EXE 的字体表中恢复现有字符布局
- 为 `build.py` 提供旧字表的占位/保留信息

### 4.5 `scripts/verify_writeback_consistency.py`

职责：

- 检查 build 生成的 `*.bin` 是否真的按预期写回到了目标 `CDB` 分段中

这是“写回是否正确”的权威校验脚本。

### 4.6 `scripts/check_cmd2_flags.py`

职责：

- 检查构建后的 link 数据里 `xC1/xCD` 之类的关键控制标志是否与源 JSON 一致

这是“字库扩容是否连带破坏脚本控制流”的回归校验。


## 5. `font.db` 是什么

`font.db` 是一个使用 `pickle` 存储的字典库。其核心结构是：

- `字符 -> (点阵字节, 宽度)`
- `md5(点阵字节) -> 字符`
- `PAL -> 调色板`

其中：

- 点阵固定按 `16x16` 组织
- 实际存储时每字占 `8 * 16 = 128` 字节原始点阵数据
- 每个像素仅使用 `0/4/6` 三种编码值：
  - `0`：字身
  - `4`：背景
  - `6`：描边/黑边


## 6. 扩容流程详解

### 6.1 第一步：收集目标字符集合

`expand_font_db_simplified.py` 默认读取这 6 个文件：

- `work/file0/DAT/FONT/KFONT.CDB.0.cn.txt`
- `work/file0/DAT/FONT/KFONT.CDB.1.cn.txt`
- `work/file0/DAT/FONT/KFONT.CDB.2.cn.txt`
- `work/file0/DAT/FONT/KFONT.CDB.3.cn.txt`
- `work/file0/DAT/FONT/KFONT.CDB.5.cn.txt`
- `work/file0/DAT/FONT/KFONT.CDB.7.cn.txt`

也就是说，扩容目标不是“理论上所有中文字符”，而是“当前译文实际会用到的字符集合”。

这一步得到：

- `required_chars`
- `required_cjk`
- `missing_cjk`
- `missing_non_cjk`

最终 `v39/v2` 的日志显示：

- `required_chars=1892`
- `required_cjk=1782`
- `missing_all=0`

说明在那一阶段，字库中的目标字符已经基本齐全，主要工作是“统一重绘现有 CJK”。

### 6.2 第二步：重绘字形

扩容脚本会：

1. 选择系统字体
2. 在 16x16 画布上计算 bbox
3. 居中绘制字符
4. 按阈值转成项目使用的三值点阵
5. 计算 advance 宽度
6. 写回 `font.db`

最终可用版对应的字形日志为：

- `override_existing_cjk=True`
- `include_missing_non_cjk=False`
- `use_font=/mnt/c/Windows/Fonts/simhei.ttf`
- `size=15`
- `added=1782`

这代表它不是只补缺字，而是对目标 CJK 集合做统一重绘。

### 6.3 第三步：构建章节字体块

`build.py` 会读取：

- `font.db`
- 当前章节 `KFONT.CDB.<id>.cn.txt`
- 原始 `lst/txt` 与 EXE 字表信息

然后生成新的章节字体块：

1. 先写入调色板
2. 逐字从 `font.db` 取出点阵与宽度
3. 必要时对点阵做 `enc2()` 压缩编码
4. 记录每个字符的新 `(offset, size)`
5. 生成新的 `rmap`（字符 -> 新索引）

### 6.4 第四步：重建 EXE 字表

构建完成后，`build.py` 会把新的字体表写回 `CAP*.EXE`。

这里写的不是旧表的局部补丁，而是新的：

- 偏移
- 宽度
- 链接段表

也就是说，最终运行时使用的“字符索引 -> 偏移/宽度”关系，是 build 阶段重新生成的。

### 6.5 第五步：回写到 `KFONT.CDB`

最后用 `cdb.py` 把生成好的 `*.bin` 写回 `DAT/FONT/KFONT.CDB` 对应分段。

这一步具有两个关键特征：

1. **不是必须等长覆盖**
2. **允许分段扩张并平移后续分段**

如果新分段长度 `n` 大于旧长度 `on`：

- 先读出后续数据
- 写入新数据
- 追加后续数据
- 修正 CDB 头部中所有后续分段的位置

所以最终的真实行为是：

- `font.db` 阶段：可以视为“原地改字典”
- `KFONT.CDB` 阶段：是“重建分段并回写”，不是死板的原址逐字节覆盖


## 7. 它到底是不是“原址重写”

### 7.1 `font.db` 层面

是“原文件整体重写”。

脚本会在内存里更新 `db[ch] = (b, adv)`，最后用 `wb` 整体覆盖写回 `font.db`。

### 7.2 `KFONT.CDB` 层面

不是“原字模地址不动的原址覆盖”。

真实行为是：

- 重新生成整段字体 bin
- 重新计算本段字符在字体块中的偏移
- 将整段写回 `KFONT.CDB`
- 若长度变化，则移动后续分段并修正头部

### 7.3 `EXE` 层面

也不是局部不动。

`fonttbl` 会被整体重写成新的偏移/宽度表，因此索引到物理字模位置的关系已经被重新定义。

### 7.4 一句话说明

这个项目的扩容方案不是“固定地址覆写旧字模”，而是：

**离线重绘字形 -> 重新构建章节字库 -> 重写 EXE 映射表 -> 回写 CDB 分段**。


## 8. 为什么它叫“扩容”

项目中的“扩容”主要体现在两点：

### 8.1 索引容量扩容

在 `build.py` 中，存在明确断言：

- `len(flst) > fontcnt`
- `len(flst) <= fontcnt * 2`

这说明：

- 新字表长度必须大于原始 `fontcnt`
- 但最大不能超过 `fontcnt` 的 2 倍

因此该项目的扩容模型可以概括为：

**每章字库允许在原有字表基础上扩到双倍索引容量。**

### 8.2 CDB 分段容量扩容

`cdb.py` 允许写回时增大分段长度，并自动平移后续分段。

这意味着字库不仅逻辑上能多放字，物理上对应的 `KFONT.CDB` 分段也允许变大。


## 9. 怎么判断“最多能扩多少”

这是项目里最容易误解的地方。

结论是：**不能只看字数，也不能只看字节数，必须两者同时满足。**

### 9.1 第一重限制：索引数量上限

每章配置文件都有：

- `fontcnt`：原始字体表基数

例如：

- `cap0`: 548
- `cap1`: 870
- `cap2`: 865
- `cap3`: 783
- `cap4`: 857
- `capX`: 566

由于 `build.py` 要求 `len(flst) <= fontcnt * 2`，理论索引上限分别是：

- `cap0`: 1096
- `cap1`: 1740
- `cap2`: 1730
- `cap3`: 1566
- `cap4`: 1714
- `capX`: 1132

### 9.2 第二重限制：字节大小上限

每章配置文件还有：

- `fontmax`

当前工作配置里各章都是：

- `fontmax = 93696`

`build.py` 在打包新字体块后会检查：

- `bin.tell() <= maxsz`

也就是说：

- 即使字数没超
- 只要打包后字体块字节数超过 `fontmax`
- 仍然判定不安全、直接失败

### 9.3 为什么不能只算“还剩多少字”

因为每个字：

- 形状不同
- 压缩率不同
- 宽度不同
- 是否进入优先区不同

所以真实可扩张空间必须以 build 实测结果为准。

安全的表达方式应是：

`可继续增加字符数 = min(索引余量, 字节余量折算后的可容纳数量)`

而字节余量只有在实际 build 后才能知道。


## 10. 什么才叫“安全”

在这个项目里，“安全”至少要同时满足 4 件事：

1. **字数不超上限**：`len(flst) <= fontcnt * 2`
2. **字节不超上限**：`bin.tell() <= fontmax`
3. **写回一致**：`verify_writeback_consistency.py` 通过
4. **脚本控制流不回归**：`check_cmd2_flags.py` 通过

### 10.1 运行安全还包含优先字符策略

`build.py` 会统计 XA 文本里出现频率高的字符，并优先把它们放进前半段索引区。

这一步的目的不是提升容量，而是降低：

- 章节切换异常
- XA/插图相关黑屏
- 低频字符挤占关键索引区导致的稳定性问题

### 10.2 `safe_remap` 不是最终方案核心

源码里有 `make_safe_rmap()` 兜底逻辑，可以把超出 `fontcnt` 的字符映射到问号或中点等回退字。

但最终可用版 `v39/v2` 的重建日志显示：

- `safe_remap_disabled`

这说明最终方案不是依赖“超限字符回退占位字”来保命，而是实际构建出的扩容字表本身已可稳定运行。


## 11. 最终可用版的实际参数

### 11.1 字形重绘参数

从 `v39` 相关日志可见，最终可用版的字库参数为：

- `required_chars=1892`
- `required_cjk=1782`
- `missing_all=0`
- `target_cjk=1782`
- `override_existing_cjk=True`
- `include_missing_non_cjk=False`
- `use_font=/mnt/c/Windows/Fonts/simhei.ttf`
- `size=15`

这意味着：

- 采用黑体风格的统一 15px 字形
- 以“覆盖统一 CJK”为主，不是单纯补缺字

### 11.2 最终 build 的实际字数

最终可用版重建日志中，各章 build 的 `flst` 长度如下：

- `cap0`: 693
- `cap1`: 1141
- `cap2`: 1136
- `cap3`: 1010
- `cap4`: 1103
- `capX`: 731

与理论双倍上限相比，索引上仍有余量：

- `cap0`: 1096 - 693 = 403
- `cap1`: 1740 - 1141 = 599
- `cap2`: 1730 - 1136 = 594
- `cap3`: 1566 - 1010 = 556
- `cap4`: 1714 - 1103 = 611
- `capX`: 1132 - 731 = 401

但这只是“索引余量”，不是最终可继续新增的绝对安全字数；还要叠加 `fontmax` 的字节限制。


## 12. 版本演进脉络

字库方案并不是一步到位，而是经历了多次探索。

### 12.1 早期阶段

- `v18`: 开始统一 CJK 扩容字形
- `v19`: 放大到 `size=13`
- `v20`: 放大到 `size=15`
- `v21`: 切到 `simsun`

### 12.2 样式探索阶段

- `v24`: 试过汉字黑边/内描边
- `v26` / `v27` / `v28`: 试过不同 shadow/全字表覆盖策略

### 12.3 收敛阶段

- `v34`: 单包稳定线
- `v35`: 冒号/姓名修正
- `v39`: `size15 gapfix` 系列收敛
- `v39_colonfix`: 成为当前 `v2` 基线的真实来源

### 12.4 后续高编号版本

`v41` / `v42` / `v43` 看起来版本号更高，但它们是后续样式/间距/姓名宽度微调链，不代表当前仓库定义的“可玩基线”。

当前基线仍是：

- `v2_strong_baseline_20260214`
- 实质对应 `v39_colonfix_20260214_042615`


## 13. 复现推荐流程

若要基于当前链路重新做字库扩容，建议流程如下：

### 13.1 准备阶段

1. 恢复到当前可用基线
2. 确认六章 `translated` / `cnraw` 已对齐
3. 确认 `font.db` 与 `work/file0/DAT/FONT/` 内容一致

### 13.2 字形重绘

运行扩容脚本重绘 `font.db`。

对当前最终链路，应优先保持以下原则：

- 使用 `simhei.ttf`
- `font-size=15`
- 覆盖目标 CJK
- 先 dry run 再 write

### 13.3 六章构建

对 `cap0/cap1/cap2/cap3/cap4/capX` 依次执行：

- `patch`
- `merge`
- `build`

入口脚本为 `scripts/main.py`。

### 13.4 回写与打包

1. 将生成的 `*.bin` 写回 `KFONT.CDB` / `KxLINK.CDB`
2. 执行一致性校验
3. 执行 `cmd2` 标志校验
4. 重建 ISO


## 14. 复现时最该看的日志

### 14.1 字形生成日志

- `work/expand_font_db_*.txt`

重点看：

- `required_chars`
- `required_cjk`
- `missing_all`
- `target_cjk`
- `use_font`
- `size`
- `added`

### 14.2 构建日志

- `rebuild_*.log`

重点看：

- 每章 `safe_remap_disabled` / `safe_remap`
- 每章打印出的 `len(flst)`

### 14.3 一致性日志

- `work/consistency_*.txt`

重点看：

- `TOTAL=16 BAD=0`

### 14.4 控制流校验日志

- `work/check_cmd2_flags_*.txt`

重点看：

- `TOTAL_MISMATCHES=0`


## 15. 常见误解

### 15.1 “扩容就是直接把旧字模原址覆盖”

错误。

真实过程是：

- 先在 `font.db` 改字形
- 再重建章节字库
- 再重写 EXE 表
- 再写回 CDB

### 15.2 “只要 `fontcnt * 2` 没满就一定安全”

错误。

还要同时满足：

- `fontmax` 没爆
- `verify_writeback_consistency.py` 通过
- `check_cmd2_flags.py` 通过

### 15.3 “版本号越高一定越是最终稳定版”

不一定。

当前仓库的可用基线是改名后的 `v2`，它实际来自 `v39_colonfix`，而不是编号最高的 `v43`。


## 16. 最终结论

本项目最后可用版的扩容字库方案，可以概括为：

**基于 `font.db` 的离线重绘式扩容，使用 `SimHei 15px` 统一覆盖目标 CJK，构建阶段按章节重建 `KFONT.CDB` 分段并重写 EXE 字表，最终在“索引数量不超过 `fontcnt * 2` 且字体块字节数不超过 `fontmax`”的条件下实现稳定运行。**

它不是单纯补几个缺字，也不是固定地址硬改字模，而是一条完整的：

**字形数据库更新 -> 字库重建 -> 指针重写 -> CDB 回写 -> 一致性校验 -> ISO 打包**

的工程化扩容链路。
