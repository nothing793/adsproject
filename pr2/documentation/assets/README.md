# 报告图表生成工具

本目录存放生成 `documentation/` 内图表所用的脚本或工具（按仓库公约，这类工具不放进 `code/`）。

- `plot_results.py`：读取 `code/benchmark` 输出的 CSV，用 Python 标准库生成 `../runtime.svg` 规模曲线。每个 CSV 必须同时包含 `binary` 与 `fibonacci` 两行，且查询数不少于 1000。

用法（在 `pr2/` 目录执行）：

```sh
python documentation/assets/plot_results.py NY.csv BAY.csv COL.csv --output documentation/runtime.svg
```

本脚本不依赖第三方包；输入 CSV 由实测产生，不在本目录保存。
