# 报告生成工具

`build_report.py` 读取验证目录中的 `summary.json`、`cases.csv` 和样例输出，生成 Markdown 报告、布局图与运行时间图，再调用排版工具导出 HTML 和 PDF。图表不使用模拟测量值。

```bash
python documentation/assets/build_report.py --validation path/to/validation-20261020
```

运行目录为 `pr3/`。图表依赖 Python 3 和 Pillow，`--font` 可指定图表中文字体，默认 `C:/Windows/Fonts/msyh.ttc`。PDF 正文、标题、表格和图注统一采用微软雅黑字族，正文与数学公式颜色均为 `#202020`。独立公式约 11.5 pt，正文约 11 pt；代码采用同色关键词字重高亮。

| 文件 | 功能 |
| --- | --- |
| `build_report.py` | 读取实测记录，生成报告内容和图表 |
| `math_layout.py` | 使用带下标的统一数学记号，给出 LaTeX 约束和复杂度推导 |
| `render_pdf.py` | 将报告使用的 Markdown 子集转换为排版页面 |
| `render_report.cjs` | 调用 Edge、MathJax 与 highlight.js，校验公式和高亮后导出 PDF |

PDF 导出还需要 Node.js、Playwright 和 Edge。`PLAYWRIGHT_MODULE` 可指定已有 Playwright 模块路径，`NODE_EXE` 可指定 Node 可执行文件，`REPORT_PROXY` 可指定代理。排版时从官方 CDN 加载固定版本 MathJax 3.2.2 与 highlight.js 11.12.0；完成后保存已排版 HTML 并移除加载脚本，日后阅读 HTML/PDF 不需要联网。

图表、字体和排版库不参与 C 求解或正确性判定。Pillow 图像缓冲区随像素数量线性增长；公式矢量字形和高亮标记的数量随文档内容增长。加载方式参考 [MathJax 官方文档](https://docs.mathjax.org/en/v3.1/web/configuration.html) 和 [highlight.js 官方 CDN 说明](https://github.com/highlightjs/highlight.js/blob/main/README.CDN.md)。

`render_pdf.py` 支持本报告使用的标题、段落、表格、代码、图片及 LaTeX 公式等 Markdown 子集，可单独重新导出：

```bash
python documentation/assets/render_pdf.py documentation/report.md documentation/report.pdf
```

行内公式使用 `$...$`，独立公式使用单独成行的 `$$`，推导对齐使用 `aligned`。C、Python 风格伪代码和 Bash 示例分别指定代码块语言。导出前检查公式错误、横向溢出及 C 关键字高亮；输出图片不含网页页脚，PDF 页脚仅显示页码。
