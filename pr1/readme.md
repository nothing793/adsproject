# ADS PR1：Roll Your Own Mini Search Engine（迷你搜索引擎）

作者：陈昱年，宋诗雨，王宇轩
第四组。
陈昊老师。

本目录是课程 project 1 的提交内容：对 MIT 莎士比亚全集建立带词干化的位置倒排索引，并提供独立的查询程序与阈值实验。
算法细节、测试过程与 Bonus 分析见 [documentation.md](documentation.md)；程序接口、文件格式与运行参数见 [code/README.md](code/README.md)。

## 1. 题目要求

1. **Part 1 词频与停用词**：统计语料词频，给出「interesting / noisy」的划分依据。
2. **Part 2 倒排索引**：建立带词干化、去除停用词的位置倒排索引。
3. **Part 3 查询程序**：在索引之上实现查询并返回命中文档 ID；除单词查询外支持多词 AND 与连续短语。
4. **Part 4 查询阈值**：测试阈值如何影响查询结果。
5. **Bonus**：讨论 500,000 个文件 / 400,000,000 个不同词条件下的可行性。

判据：停用词按文档频率 `df / N > θ` 划分（默认 θ = 0.5）；查询阈值同样为 `df / N > τ`。两处条件都是严格大于，相等时不触发。停用词的位置不写入索引，因此包含停用词的精确短语无法检索。

## 2. 目录结构

```
pr1/
├── readme.md              本文件：题面、结构、编译与运行
├── documentation.md       实验报告（Chapter 1 问题描述、Chapter 2 数据结构与算法、Chapter 3 测试与结果分析、Chapter 4 复杂度、结果讨论与 Bonus、Chapter 5 复现与提交文件）
├── test_data.zip          测试与实验材料：语料、结果表、原始日志、源码修复记录与 8 张实验截图
└── code/
    ├── index_gen.c        两遍扫描：词频统计、停用词表、二进制索引
    ├── query.c            单词 / AND / 短语查询与查询阈值
    ├── index.h            内存索引、文档表与 index.bin 读写
    ├── stem.c / stem.h    Porter 词干化（来源与许可见 LICENSE-stmr.txt）
    ├── test.txt           文件输入示例
    └── tests/             全集对照、边界回归与 Bonus 实验脚本
```

## 3. 语料与统计口径

- 语料：MIT 网站目录的 42 个条目（37 部戏剧 + 5 个诗歌集合），154 首十四行诗合并为一篇；每个输入文件 = 一篇文档，doc_id 按命令行给出的文件顺序从 0 分配。
- 分词：取 ASCII 字母 / 数字连续段并转小写；撇号、连字符是分隔符（`don't` 分为 `don` 和 `t`）；位置按完整 token 序列编号，起始为 0，删除停用词后仍保留原编号。
- 全集规模：**956,647 个 token / 23,871 种原词形 / 14,986 个词干**。
- θ = 0.5 时：停用词 1,780 条，索引 663,434 B，保留 131,136 个位置（13.71%）。

## 4. 编译与运行

先把 `test_data.zip` 解压到 `pr1` 目录（解压后得到 `data/`、`results/`、`evidence/`），再编译：

```powershell
gcc -std=c99 -O2 -Wall -Wextra -Wpedantic code/index_gen.c code/stem.c -lm -o code/index_gen.exe
gcc -std=c99 -O2 -Wall -Wextra -Wpedantic code/query.c code/stem.c -lm -o code/query.exe
$corpus = Get-ChildItem data/shakespeare/corpus/*.txt | Sort-Object Name
Set-Location code
./index_gen.exe --theta=0.5 $corpus.FullName
./query.exe hamlet
./query.exe antonio bassanio
./query.exe 'et tu brute'
./query.exe --tau=0.1 caesar
./query.exe
Get-Content output.txt
```

Linux / macOS 使用同样的 gcc 命令生成 `index_gen` 与 `query`，语料路径按实际位置传入；命令行多个参数表示 AND，单参数内的多个 token 表示连续短语。查询从当前目录读取 `index.bin`，结果写入 `output.txt`。

## 5. 测试与复现

完整测试入口为 `code/tests/run_lab.ps1`，也可依次运行：

```powershell
python code/tests/run_extended.py      # 语料构建、独立对拍、查询与边界回归
python code/tests/review_regression.py # 补充回归（标点归一化、阈值边界、异常索引等）
python code/tests/run_bonus.py         # Bonus 压力实验与外存原型
```

已完成的验证：全集测试 **78 项通过 / 0 项失败**，补充回归 **36 项通过 / 0 项失败**；重复构建与 load→save 往返的索引逐字节一致，θ = 0.5 的 SHA-256 为
`0e80dc9ee4c5b369966e36c07e94a49b40333a82ce1d90c47d8a86bd09348d69`。
8 张实验截图位于解压后的 `evidence/screenshots/`，图中数据来自已保存的运行日志。

## 6. 已知限制

- 当前 C 实现不能直接支持题目给出的完整 Bonus 规模：内存词典与全量加载、位置插入的 O(tf²) 代价、巨型 `argv` 以及 Windows `long` 文件偏移都是约束；独立 SQLite 外存原型只做了方向性验证，未实跑 500,000 个实体文件与 400,000,000 个不同词。
- 不支持增量更新：语料变化需要整份重建索引。
- `index.bin` v1 没有校验和，结构自洽的字节改动不一定能被发现。
