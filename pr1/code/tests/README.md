# pr1 测试目录

## 当前实验入口

Python 3 + gcc，无第三方 Python 包依赖：

```powershell
python run_extended.py               # 全集构建、独立对拍、查询/边界/修复回归
python run_extended.py --reuse-indexes # 复用索引，重编译并重新验证内容与查询
python run_bonus.py                  # 原 C 后端压力与独立 SQLite 外存原型
python sweep.py                     # 展示最近一次已验证的 θ/τ 文档数表
python sweep.py --rebuild            # 重新构建与验证再展示
python make_lab_report.py            # 从日志生成报告素材和截图展示页
```

最终全集检查 78 PASS / 0 FAIL；压力测试最高 50 万逻辑 doc_id / 100 万不同词干。它们不等同于 50 万实体文件、4 亿不同词端到端测试。原始数据在 `../../results/`，8 张浏览器截图在 `../../evidence/screenshots/`；浏览器截图生成需要已有 Playwright 和 Edge，运行 `capture_evidence.cjs`（可设置 PLAYWRIGHT_MODULE）。

`prepare_shakespeare.py` 从官方 MIT 镜像提取语料；实际清单与 HTML 已附。`lab_support.py` 保存每次完整命令、stdout/stderr、退出码、墙钟时间和 Windows 峰值 working set。`bonus_probe.c` 调用原 C 内存后端；`bonus_disk_demo.py` 为独立外存演示，不兼容原 index.bin。

以下内容保留原合成语料测试说明，其中 21 项及 /tmp 工作路径为历史记录。

本目录是 pr1 迷你搜索引擎的测试与实验脚本，对应的正文说明见
[`../README.md`](../README.md) 第 12 节。

**这里没有构建产物**：所有编译和执行都在临时工作目录里进行（默认 `/tmp/pr1-test`，
可以用 `run_tests.sh <工作目录>` 换），不会污染 `code/`。

## 文件

| 文件 | 用途 |
| --- | --- |
| `run_tests.sh` | 端到端测试入口：编译（零告警）→ 生成语料 → 切词（`index_gen --dump-tokens`）→ 建索引 → 各项校验，逐项打印 PASS/FAIL（当前 21 项全过） |
| `gen_corpus.py` | 确定性合成语料生成器（没下载莎士比亚全集前用它跑通整条流水线）。功能词比例可调，保证一定会出现"跨文档高频词"这类停用词 |
| `stem_list.c` | 词干命令行工具：从 stdin 读词、逐行输出词干。只给 `brute_check.py` 用（Python 侧没有 Porter 实现） |
| `pick_term.py` | 从 `file.txt` 里挑一个词干并打印它的 df / N（可按 df/N 区间、最高频、最稀有），供 `sweep.py` 与阈值测试动态选词 |
| `brute_check.py` | 独立校验：用另一份实现解析 `index.bin`，与从 `file.txt` 暴力统计的结果逐词条对比（含 df / tf / 位置链、是否剔除了停用词）；另外可以暴力枚举短语出现位置，用来对拍短语查询 |
| `roundtrip.c` | 读 `index.bin` → 用 `index_save()` 再写一份，供 `cmp` 验证"加载再落盘逐字节相同"（编译时链 `../stem.c`，索引实现在 `../index.h`） |
| `sweep.py` | 第 4 问的阈值实验：θ ∈ {0.3,0.4,0.5,0.6} × τ ∈ {0.1,0.2,0.3,0.4}，打印 Markdown 表格（stoplist 大小、平均结果集大小、被阈值拦下的比例） |

## 用法

```bash
sh run_tests.sh                      # 全套测试，默认工作目录 /tmp/pr1-test
python3 sweep.py /tmp/pr1-test       # 阈值敏感性实验（先用 run_tests.sh 准备好工作目录）
```

`run_tests.sh` 依赖 `python3`、`gcc`、`tr`、`diff`、`cmp`。语料是合成的：
换成真实的莎士比亚全集，只要把命令行里的语料换成莎士比亚的文本即可，
其余步骤（θ / τ 实验、对拍）完全一样。
