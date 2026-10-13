"""读取 benchmark CSV，用标准库生成可在浏览器查看的 SVG 规模曲线。"""
import argparse
import csv
from html import escape
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    groups = {"binary": [], "fibonacci": []}
    for path in args.csv:
        with path.open(encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        if len(rows) != 2 or {r["heap"] for r in rows} != set(groups):
            raise SystemExit(f"CSV 必须各含一行 binary 和 fibonacci：{path}")
        for row in rows:
            if int(row["queries"]) < 1000:
                raise SystemExit("每组评测至少需要 1000 对查询")
            groups[row["heap"]].append((int(row["vertices"]), float(row["mean_ms"]), path.stem))
    points = [point for group in groups.values() for point in group]
    xmax = max(p[0] for p in points) * 1.12
    ymax = max(p[1] for p in points) * 1.2 or 1.0
    left, top, width, height = 100, 80, 680, 380
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="920" height="590" viewBox="0 0 920 590">',
           '<rect width="920" height="590" fill="white"/>',
           '<g font-family="Arial, sans-serif" fill="#182636">',
           '<text x="100" y="35" font-size="23">Dijkstra on DIMACS USA road networks</text>',
           '<text x="100" y="58" font-size="13">Same seeded queries; lower is faster; one run per dataset</text>']
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
    for index, (heap, color) in enumerate([("binary", "#1769b0"), ("fibonacci", "#c65320")]):
        ordered = sorted(groups[heap])
        coordinates = [(left + n / xmax * width, top + height - ms / ymax * height, name, ms) for n, ms, name in ordered]
        svg.append(f'<polyline points="{" ".join(f"{x:.2f},{y:.2f}" for x,y,_,_ in coordinates)}" fill="none" stroke="{color}" stroke-width="3"/>')
        for x, y, name, ms in coordinates:
            svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" fill="{color}"/>')
            svg.append(f'<text x="{x + 9:.2f}" y="{y - 9:.2f}" fill="{color}" font-size="12">{escape(name)} {ms:.2f}</text>')
        svg.append(f'<text x="{150 + index * 220}" y="548" fill="{color}" font-size="16">{heap}</text>')
    svg.extend(['<text x="100" y="576" font-size="12">Graph loading, allocation, warm-up and CSV writing excluded; query reset included.</text>', '</g></svg>'])
    args.output.write_text("\n".join(svg), encoding="utf-8")


if __name__ == "__main__":
    main()
