"""从 benchmark CSV 生成报告用的 SVG 运行时间-规模曲线（仅用 Python 标准库）。

本脚本用于生成 documentation 中的图表，按仓库公约存放在 documentation/assets/ 下，
而不是放在 code/ 中：code/ 只保留 C 实现的源码。

用法：
    python documentation/assets/plot_results.py NY.csv BAY.csv COL.csv --output documentation/runtime.svg

输入为 code/benchmark 写出的 CSV（每份数据必须同时含 binary 与 fibonacci 两行，
且查询数不少于 1000）；输出为不依赖第三方库、可直接在浏览器查看的 SVG。
"""
import argparse
import csv
from html import escape
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    # 两种堆各自收集 (顶点数, 平均毫秒, 数据集名) 坐标点。
    groups = {"binary": [], "fibonacci": []}
    for path in args.csv:
        with path.open(encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        # 每份 CSV 必须恰好是两种堆各一行，否则说明输入不是完整的基准结果。
        if len(rows) != 2 or {r["heap"] for r in rows} != set(groups):
            raise SystemExit(f"CSV 必须各含一行 binary 和 fibonacci：{path}")
        for row in rows:
            if int(row["queries"]) < 1000:
                raise SystemExit("每组评测至少需要 1000 对查询")
            groups[row["heap"]].append((int(row["vertices"]), float(row["mean_ms"]), path.stem))
    points = [point for group in groups.values() for point in group]
    # 坐标范围：横轴按最大顶点数留 12% 余量，纵轴留 20% 余量（全零时退化为 1）。
    xmax = max(p[0] for p in points) * 1.12
    ymax = max(p[1] for p in points) * 1.2 or 1.0
    left, top, width, height = 100, 80, 680, 380
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="920" height="590" viewBox="0 0 920 590">',
           '<rect width="920" height="590" fill="white"/>',
           '<g font-family="Arial, sans-serif" fill="#182636">',
           '<text x="100" y="35" font-size="23">Dijkstra on DIMACS USA road networks</text>',
           '<text x="100" y="58" font-size="13">Same seeded queries; lower is faster; one run per dataset</text>']
    # 5 等分网格线：纵轴标注毫秒，横轴标注顶点数（单位 k）。
    for i in range(6):
        x = left + width * i / 5
        y = top + height - height * i / 5
        svg.extend([
            f'<path d="M {left} {y} H {left + width}" stroke="#e0e5eb"/>',
            f'<text x="{left - 12}" y="{y + 5}" text-anchor="end" font-size="13">{ymax * i / 5:.1f}</text>',
            f'<text x="{x}" y="{top + height + 24}" text-anchor="middle" font-size="13">{xmax * i / 5000:.0f}k</text>',
        ])
    svg.extend([f'<path d="M {left} {top} V {top + height} H {left + width}" fill="none" stroke="#182636"/>',
                '<text x="440" y="510" text-anchor="middle">Vertices</text>',
                '<text transform="translate(28 275) rotate(-90)" text-anchor="middle">Mean time per query (ms)</text>'])
    # 每条曲线按顶点数排序后连成折线，并在每个数据点旁标注数据集名与耗时。
    for index, (heap, color) in enumerate([("binary", "#1769b0"), ("fibonacci", "#c65320")]):
        ordered = sorted(groups[heap])
        coordinates = [(left + n / xmax * width, top + height - ms / ymax * height, name, ms) for n, ms, name in ordered]
        svg.append(f'<polyline points="{" ".join(f"{x:.2f},{y:.2f}" for x,y,_,_ in coordinates)}" fill="none" stroke="{color}" stroke-width="3"/>')
        for x, y, name, ms in coordinates:
            svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" fill="{color}"/>')
            svg.append(f'<text x="{x + 9:.2f}" y="{y - 9:.2f}" fill="{color}" font-size="12">{escape(name)} {ms:.2f}</text>')
        svg.append(f'<text x="{150 + index * 220}" y="548" fill="{color}" font-size="16">{heap}</text>')
    # 图注说明计时口径，避免读者把曲线当成受控的渐近实验。
    svg.extend(['<text x="100" y="576" font-size="12">Graph loading, allocation, warm-up and CSV writing excluded; query reset included.</text>', '</g></svg>'])
    args.output.write_text("\n".join(svg), encoding="utf-8")


if __name__ == "__main__":
    main()
