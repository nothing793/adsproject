# 程序目录

本目录实现 Project 3 栅栏布局恢复。采用相邻连接器候选图、精确度数与交叉互斥约束，以及自行实现的 CDCL 布尔求解器。C 程序只依赖标准库。

## 文件与接口

| 文件 | 功能及主要接口 |
| --- | --- |
| `main.c` | 单用例输入检查、按行优先输出；可选 `--stats` 将 JSON 统计写入标准错误 |
| `fence.h`、`fence.c` | `Garden` 保存输入；`fence_solve` 构造约束并恢复布局；`FenceResult` 保存四方向状态和统计 |
| `sat.h`、`sat.c` | `sat_create`、`sat_add_clause`、`sat_solve`、`sat_value`、`sat_stats`、`sat_destroy` |
| `Makefile` | C99 零告警编译，`make` 构建、`make clean` 清理 |
| `tests/` | 独立几何检查、小规模穷举和 SAT 核心对拍，见目录内说明 |

内部行列、变量编号从 0 开始，输出行列从 1 开始。四方向顺序为上、下、左、右；相反方向编号通过 `direction ^ 1` 得到。候选边编号在 `incident` 中关联端口，-1 表示该方向没有候选边。

SAT 正文字编码为 `2*variable`，负文字为 `2*variable+1`。求解实例只运行一次，添加子句时不允许重复变量或互补文字；花园编码与测试生成器均满足此前置条件。`sat_value` 只在可满足时读取。学习子句由内部冲突分析生成。

## 编译与运行

在 `pr3` 目录执行：

```bash
gcc -std=c99 -O2 -Wall -Wextra -Wpedantic code/main.c code/fence.c code/sat.c -o fence
./fence < input.txt
./fence --stats < input.txt
```

也可在本目录执行 `make`。Windows PowerShell 中将输出名改为 `fence.exe`，再运行 `Get-Content input.txt | ./fence.exe`。

每次运行只接收一个输入用例；正常结果或 `No Solution` 写入标准输出，返回 0。输入越界、缺少字段和多余数据返回 1；资源或输出错误返回 2。空花园是合法空布局，标准输出为空。`--stats` 不改变评测输出。

## 功能范围

题目要求的度数恢复、长直线栅栏、无连接器处不交叉、四路连接器、非唯一解及无解处理均已实现。题目没有要求最短总长度、全图连通或枚举所有解，程序不提供这些扩展目标。

建模为 O(nm)，求解最坏仍可能需要指数级搜索。50×50 的规模试验和限制见报告 Chapter 3、Chapter 4。当前版本保留学习子句而不定期清理，困难实例的内存可能增长；分配失败以运行错误退出，不输出虚假的 `No Solution`。

全部 `.c`、`.h` 文件具有功能说明；关键步骤的中文注释说明监视不变量、First-UIP 分析、回溯边界、方向互反和内存失败处理。
