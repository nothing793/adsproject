# ADS PR1：迷你搜索引擎

当前仓库基线：nothing793/adsproject，commit `5d36a46145236b406eb37643db4e5cefcb351f3a`。

已补充题目指定网站的全集语料、真实正确性与 θ/τ 测试、Bonus 规模实验、修复回归和 8 张过程截图。全集为 **42 文档 / 956,647 tokens / 14,986 词干**；最终 **78 PASS / 0 FAIL**。

- [完整实验报告](documentation.md)：Chapter 1 问题、Chapter 2 方法、Chapter 3 测试与 Bonus。
- [实验记录与报告素材](实验记录与报告素材.md)：命令、结果、分析和截图引用。
- [8 张截图的说明](evidence/截图说明.md)；[浏览器展示页索引](evidence/index.html)。PNG 是实际浏览器截图，展示页由原始日志生成。
- [源码修改差异](evidence/source_changes.patch)：短语词序、合法空文档加载、test.txt AND 语义、Windows 索引替换。
- [全集清单](data/shakespeare/documents.csv)、[来源与校验和](data/shakespeare/manifest.json)。

## 编译与运行

```powershell
gcc -std=c99 -O2 -Wall -Wextra -Wpedantic -o code/index_gen.exe code/index_gen.c code/stem.c -lm
gcc -std=c99 -O2 -Wall -Wextra -Wpedantic -o code/query.exe code/query.c code/stem.c -lm
Set-Location code
$corpus = Get-ChildItem ../data/shakespeare/corpus/*.txt | Sort-Object Name
./index_gen.exe --theta=0.5 $corpus.FullName
./query.exe 'et tu brute'
./query.exe antonio bassanio
./query.exe --tau=0.1 caesar
./query.exe # 读取已附 test.txt；普通多词行是 AND，phrase: 行为短语
Get-Content output.txt
```

Linux / macOS 使用同样 gcc 命令生成 index_gen / query，然后 `./index_gen corpus/*.txt`（传入正确相对路径）。输入文件顺序决定 doc_id；本次清单按文件名排序。

## 一键复现实验

Python 3 + gcc，无第三方 Python 包依赖。PowerShell：

```powershell
./run_lab.ps1 -PythonExe '你的Python路径/python.exe'
# 已有索引时，可复用索引并重新对拍、重启查询
./run_lab.ps1 -PythonExe '你的Python路径/python.exe' -ReuseIndexes
```

也可直接运行 `python code/tests/run_extended.py`、`python code/tests/run_bonus.py`、`python code/tests/make_lab_report.py`。首次全集建索引需要数分钟；原始 stdout/stderr、参数、cwd、退出码和测量保存在 results/logs。

`python code/tests/sweep.py` 展示最近一次校验通过的阈值表；`--rebuild` 重新构建并校验。旧合成语料测试保留作补充，不再代表真实全集结果。

## Bonus 的验证范围

原 C 后端与独立外存原型均实测至 **50 万逻辑 doc_id / 100 万不同词干**。未创建 50 万实体文件，未实跑 4 亿不同词。当前 C 后端不能直接支持完整 Bonus 规模：内存词典、二次方位置插入、全量加载、巨型 argv 与 Windows long 偏移限制均需改造。独立 SQLite 原型验证固定页缓存的外存方向，不能据此宣称完整 Bonus 规模已通过。

临时大型索引、数据库、exe、token dump 不纳入 Git；测量、真实语料、截图和生成脚本纳入 Git。源代码版本与初始参考仓库相等性见 evidence/repository_baseline.json。
