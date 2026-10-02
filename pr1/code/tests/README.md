# 测试说明

测试依赖 Python 3 和 gcc。将 `test_data.zip` 解压到 `pr1` 目录后执行：

```powershell
./code/tests/run_lab.ps1 -PythonExe 'python'
```

也可分别运行：

```powershell
python code/tests/run_extended.py
python code/tests/review_regression.py
python code/tests/run_bonus.py
python code/tests/make_lab_report.py
```

首次运行会构建五组全集索引，耗时数分钟。已有完整索引及 token dump 时，`run_extended.py --reuse-indexes` 复用索引并重新编译、解析和查询；索引缺失时仍执行构建。`run_bonus.py --reuse-indexes` 可复用原 C 后端压力索引。

| 文件 | 检查内容 |
| --- | --- |
| `run_extended.py` | 42 文档的分词、停用词、完整位置索引、查询、阈值边界及空文档，共 78 项 |
| `brute_check.py` | 独立解析二进制索引，与暴力聚合结果比较 |
| `stem_list.c` | 批量输出词干，供参考结果聚合使用 |
| `roundtrip.c` | 加载索引并重新保存，比较字节一致性 |
| `review_regression.py` | 36 项补充回归，包括 80 组固定随机种子的 AND／短语对照 |
| `range_roundtrip.c` | 使用 -ftrapv 验证 INT_MAX 位置的加载／保存边界 |
| `review_malloc_fault.c` | 64 位 Windows 下的位置节点分配失败注入，用于验证构建错误处理 |
| `run_bonus.py`、`bonus_probe.c` | 原 C 后端的逻辑文档、不同词数和高频位置链规模实验 |
| `bonus_disk_demo.py` | SQLite 外存索引原型，与原 C 文件格式独立 |
| `lab_support.py` | 保存命令、输出、退出码、墙钟时间及 Windows 峰值 working set |
| `prepare_shakespeare.py` | 从 MIT 网站公开镜像提取语料及校验清单 |
| `make_lab_report.py` | 根据测量与日志生成报告和结果展示页 |
| `capture_evidence.cjs` | 使用 Edge 重新截取八张展示页，需 Playwright |

测试结果保存在 `pr1/results/`，结果展示页与图片保存在 `pr1/evidence/`。词干算法在参考结果和 C 程序中共享，分词、聚合、二进制解析与查询枚举分别实现。

补充回归的修正前结果为 17 PASS／19 FAIL，修正后为 36 PASS／0 FAIL。固定随机测试使用种子 793。分配失败测试依赖 GNU 链接器 `--wrap=malloc` 及本次 64 位 Windows 的结构尺寸。

Bonus 最大实测为 500,000 个逻辑文档 ID 和 1,000,000 个不同词。未创建 500,000 个实体文件，未执行 400,000,000 个不同词的完整实验。

截图重建：

```powershell
node code/tests/capture_evidence.cjs
```

`PLAYWRIGHT_MODULE` 可指定 Playwright 模块路径。八张图片均由结果页重新截取。
