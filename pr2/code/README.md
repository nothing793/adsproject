# pr2 代码说明

本目录实现最小优先队列支持的 Dijkstra，并比较二叉堆与 Fibonacci 堆。全部核心代码为 C99，中文注释说明主要不变量与边界处理，不依赖 STL 或第三方算法库。

## 文件与职责

| 文件 | 职责 |
| --- | --- |
| `graph.c/.h` | 严格解析 DIMACS `p sp`/`a` 记录，构造 CSR，管理图内存 |
| `binary_heap.c/.h` | 带 `position` 句柄映射的二叉最小堆 |
| `fibonacci_heap.c/.h` | 数组句柄、循环链表、按度合并、切割、级联切割 |
| `dijkstra.c/.h` | 统一松弛、终止条件、前驱与操作统计 |
| `main.c` | 单对查询，输出最短距离和一条路径 |
| `benchmark.c` | 至少 1000 对固定种子查询，两种堆分别计时并逐对核对 |
| `plot_results.py` | 用 Python 标准库从 CSV 生成 SVG 规模曲线 |
| `Makefile` | GCC 构建、C 测试及清理入口 |
| `tests/test.c` | 堆结构审计、级联切割、解析边界、独立 Floyd 对拍 |
| `tests/run_tests.py` | 零告警构建、C 测试、CLI 与基准复现回归 |
| `tests/README.md` | 测试目的和运行限制 |

## 数据结构、变量与接口

| 结构 / 变量 | 含义与使用约束 |
| --- | --- |
| `Graph.vertices/arcs` | 顶点数 / 有向弧数；顶点数必须为 `1..INT_MAX` |
| `Graph.offset/target/weight` | CSR 连续数组；顶点 `u` 的出弧区间为 `[offset[u], offset[u+1])` |
| `BinaryHeap.items/position` | 堆下标到顶点及反向映射；不在堆内的位置为 `-1` |
| `FibonacciNode` | `parent/child/left/right/degree` 描述森林；`mark` 表示非根已丢失一个孩子，`active` 表示在堆内 |
| `FibonacciHeap.minimum` | 最小根的顶点编号；空堆为 `-1` |
| `Search.distance/previous/settled` | 当前距离、前驱顶点、是否已定型；初始化分别为 `DIST_INF/-1/0` |
| `Search.stats` | 本次查询的定型顶点数、扫描弧数、首次插入数和 decrease-key 次数 |
| `DIST_INF` | `UINT64_MAX`，仅用于不可达，不是有限距离 |

- `graph_load(graph, path, error, error_size)`：读取图，成功返回 1；失败返回 0 并清理部分分配。不能对尚未释放的已加载对象再次调用。
- `graph_free(graph)`：释放图并置零。
- `search_init(search, n, kind)` / `search_free(search)`：分配 / 释放工作区，仅分配被选中的一种堆；不对同一已初始化对象重复初始化。
- `dijkstra(graph, search, source, target)`：编号为 **0 起始**；`target=-1` 完整单源，否则在目标出堆时停止。此时仅保证目标及已定型节点的距离是最终值，不可把其他候选距离当作最终结果。返回 0 表示参数不合法。工作区可顺序复用，不可被多线程同时使用。
- `binary_update` / `fibonacci_update`：用于新插入或 decrease-key。调用者先更新共享 `distance`；已入堆节点的键只能减小，不能随意增加。节点编号须在容量内，键数组必须比堆活得更久。
- `binary_pop` / `fibonacci_pop`：返回并删除最小顶点；空堆返回 `-1`。
- 两种堆均按 `(distance, vertex)` 排序，避免同距节点导致探索顺序差异。堆不允许重复句柄；Dijkstra 不再插入已定型顶点。

堆接口面向内部算法，容量和编号等前置条件由 Dijkstra 保证。文件和 CLI 输入在进入这些接口前校验。字符串记录缓冲区为 1024 字节，过长行会拒绝；允许空行、注释、CRLF 和无末尾换行的短记录。

## 编译和运行

在本目录执行：

```sh
gcc -std=c99 -O2 -Wall -Wextra -Wpedantic main.c graph.c binary_heap.c fibonacci_heap.c dijkstra.c -o shortest_path
gcc -std=c99 -O2 -Wall -Wextra -Wpedantic benchmark.c graph.c binary_heap.c fibonacci_heap.c dijkstra.c -o benchmark
gcc -std=c99 -O2 -Wall -Wextra -Wpedantic -I. tests/test.c graph.c binary_heap.c fibonacci_heap.c dijkstra.c -o test_runner
./test_runner
./shortest_path /path/to/graph.gr fibonacci 1 5
./benchmark /path/to/graph.gr 1000 20261013 result.csv
python tests/run_tests.py --output /path/to/local-validation
```

Windows 使用对应的 `.\shortest_path.exe`、`.\benchmark.exe`、`.\test_runner.exe`；Linux 有 Make 时也可执行 `make` / `make test`。测试不得定义 `NDEBUG`。Python 脚本只用标准库；不需要安装额外包。

CLI 的顶点编号为 **1 起始**。例如测试脚本的合成图，查询 `1 5` 输出：

```text
distance=8
path=1 -> 3 -> 2 -> 4 -> 5
```

不可达输出 `distance=INF` 与 `path=unreachable`；源点等于终点返回距离 0。CLI 只输出一条最短路径。

## 功能完成情况

| 题目要求 | 当前状态 |
| --- | --- |
| 至少两种堆，必须含 Fibonacci 堆 | 已完成二叉堆与 Fibonacci 堆 |
| 基于堆的 Dijkstra，充分注释 | 已完成，共用流程与中文注释 |
| 性能测试程序，至少 1000 对查询 | 已完成，拒绝少于 1000；固定种子与逐对校验 |
| 真实 USA 路网评测 | 已实测 NY、BAY、COL，每份 1000 对 |
| 时间表、规模曲线与分析 | 已同步项目 README 与 Markdown 报告 |
| 只提供道路数据下载链接 | 已遵守；不打包 USA 数据 |

未实现 / 不支持：负权图、直接读取 gzip、路径启发式加速（A* 等）、额外堆类型、全部等长最短路径枚举。它们不是本题必需功能。报告待评审，尚未生成定稿 PDF。

## 测试和计时边界

`benchmark` 使用 xorshift64* 及拒绝采样生成顶点；相同图、查询数、非零种子产生相同查询。起终点不同，查询对可重复，不可达查询计入统计。每种堆各预热一次；奇偶查询交替运行顺序。CSV 在全部距离核对通过后写出。

`clock()` 测量累计 tick，CSV 记录 `clock_ticks_per_second`。本机为 1000 tick/s，小图单次耗时可能低于分辨率，因此小图仅用于正确性验证。计时包含 O(V) 状态重置和搜索，排除文件读取、初次分配、预热、随机数生成和输出。两种堆工作区同时存在，比较的不是峰值内存。每份路网目前只测一轮，没有置信区间。

标准库 `calloc/free` 用于分配和释放，`fgets/sscanf` 用于有界文本读取和解析，`clock` 用于计时。图构建线性扫描输入和弧数组，未调用第三方排序或图算法；独立测试的 Floyd 为 O(V³)。
