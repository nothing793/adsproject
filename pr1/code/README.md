# 程序说明

本目录实现词频统计、停用词识别、位置倒排索引和查询处理。算法与实验分析见 `../documentation.md`。

## 文件

| 文件 | 功能 |
| --- | --- |
| `index_gen.c` | 两遍扫描，统计词频、生成停用词表及二进制索引 |
| `query.c` | 单词、AND、连续短语查询及查询阈值 |
| `index.h` | 内存索引、文档表和二进制读写 |
| `stem.c`、`stem.h` | Porter 词干化；来源及许可见 `LICENSE-stmr.txt` |
| `test.txt` | 文件输入示例 |
| `tests/` | 全集对照、边界回归及 Bonus 实验脚本 |

## 编译与运行

从 `pr1` 目录将 `test_data.zip` 解压到当前目录，再执行：

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

`index_gen` 为每个输入文件分配一个文档 ID，顺序由参数决定。`-` 表示标准输入；`--count-only` 仅统计词频并生成 `stoplist.txt`。查询从当前目录读取 `index.bin`，结果写入 `output.txt`。

查询与语料按字母、数字连续段分词。多个命令行参数表示 AND；一个参数内的多个 token 表示连续短语。`test.txt` 的普通行表示 AND，`phrase:` 行表示短语。最多 32 个单元，每个短语最多 16 个词。

θ 控制建索引时的停用词过滤，τ 控制查询时的结果列表展示。两者的条件均为 `df/N > threshold`，相等时不触发。默认 θ=0.5；默认不设置 τ。被删除停用词的位置不保存在索引中。

文件格式使用 64 B 头部、升序文档表、升序词典和差分位置段。各段必须连续；加载器验证计数、顺序、范围及文档引用。实现采用全量内存索引，当前位置插入为 O(tf²)，Windows long 文件偏移约束及规模实验见报告第 4 章。

完整测试入口与依赖见 `tests/README.md`。
