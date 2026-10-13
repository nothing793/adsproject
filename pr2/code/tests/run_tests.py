"""仅使用 Python 标准库：零告警构建、C 对拍、命令行与基准复现测试。"""
import argparse
import csv
from pathlib import Path
import shutil
import subprocess
import sys

SOURCE = Path(__file__).resolve().parents[1]
COMMON = ["graph.c", "binary_heap.c", "fibonacci_heap.c", "dijkstra.c"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="构建、日志与测试材料目录")
    parser.add_argument("--cc", default="gcc", help="GCC 可执行文件")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    (output / "README.md").write_text(
        "# 自动测试材料\n\n包含可执行文件、合成输入、测试日志与基准 CSV；不包含 USA 原始数据。\n",
        encoding="utf-8",
    )
    compiler = shutil.which(args.cc)
    if not compiler:
        raise SystemExit(f"找不到编译器：{args.cc}")
    log = []

    def run(command, success=True):
        command = list(map(str, command))
        result = subprocess.run(command, cwd=output, text=True, capture_output=True)
        log.extend(["$ " + " ".join(command), result.stdout, result.stderr])
        if (result.returncode == 0) != success:
            raise RuntimeError(f"退出状态异常 {result.returncode}: {command}\n{result.stdout}\n{result.stderr}")
        return result.stdout

    try:
        run([compiler, "--version"])
        for name, source in [("shortest_path", "main.c"), ("benchmark", "benchmark.c"), ("test_runner", "tests/test.c")]:
            run([compiler, "-std=c99", "-O2", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-I", SOURCE,
                 SOURCE / source, *[SOURCE / item for item in COMMON], "-o", output / (name + ".exe")])
        print(run([output / "test_runner.exe"]).strip())
        fixture = output / "sample.gr"
        fixture.write_text("c 合成测试图，不是 USA 数据\np sp 6 9\na 1 2 10\na 1 3 2\na 3 2 1\na 2 4 4\na 3 4 20\na 4 5 1\na 5 1 8\na 3 3 0\na 1 3 9\n", encoding="utf-8")
        query = output / "shortest_path.exe"
        for heap in ["binary", "fibonacci"]:
            answer = run([query, fixture, heap, "1", "5"])
            assert "distance=8\n" in answer and "path=1 -> 3 -> 2 -> 4 -> 5\n" in answer
            assert "distance=INF" in run([query, fixture, heap, "1", "6"])
            assert "distance=0\npath=3\n" in run([query, fixture, heap, "3", "3"])
            run([query, fixture, heap, "0", "1"], success=False)
        run([query, fixture, "invalid", "1", "5"], success=False)
        run([query, fixture, "binary", "-1", "5"], success=False)
        run([query, output / "missing.gr", "binary", "1", "5"], success=False)
        benchmark = output / "benchmark.exe"
        run([benchmark, fixture, "999", "20261013", output / "rejected.csv"], success=False)
        run([benchmark, fixture, "1000", "0", output / "rejected.csv"], success=False)
        rows = []
        for repeat in range(2):
            path = output / f"benchmark_repeat_{repeat}.csv"
            run([benchmark, fixture, "1000", "20261013", path])
            with path.open(newline="") as file:
                data = list(csv.DictReader(file))
            assert len(data) == 2 and {row["heap"] for row in data} == {"binary", "fibonacci"}
            assert data[0]["checksum"] == data[1]["checksum"]
            assert all(row["queries"] == "1000" and 0 < int(row["reachable"]) < 1000 for row in data)
            rows.append([{key: value for key, value in row.items() if key not in {"total_seconds", "mean_ms"}} for row in data])
        assert rows[0] == rows[1], "同种子复现结果不一致"
        summary = "PASS CLI, benchmark >=1000, unreachable queries, deterministic seed; all builds warning-free"
        log.append(summary)
        print(summary)
    finally:
        (output / "validation.log").write_text("\n".join(log), encoding="utf-8")


if __name__ == "__main__":
    main()
