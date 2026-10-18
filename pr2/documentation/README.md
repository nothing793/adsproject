# pr2 报告与图表

- [report.md](report.md)：四章 Markdown 报告，包含问题描述、数据结构与伪代码、实测结果、复杂度与讨论。
- [runtime.svg](runtime.svg)：从三份实际 benchmark CSV 生成的运行时间与顶点规模曲线。
- [assets/](assets/README.md)：生成报告图表的脚本（`plot_results.py`），按仓库公约放在此处而非 `code/`。
- [report.pdf](report.pdf):由report.md转为的报告。

原始 CSV、自动化测试日志和必要的合成输入收录于 `../testresult/validation-20261013.zip`（该压缩包只含 `testresult/` 内的测试材料，不再打包代码与报告）；不包含 USA 道路原始数据。
