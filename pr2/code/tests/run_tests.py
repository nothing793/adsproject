"""仅使用 Python 标准库：零告警构建、C 对拍、命令行与基准复现测试。

本脚本的功能：
  1. 用 -Werror 构建 shortest_path、benchmark、test_runner 三个入口，确保无编译告警；
  2. 运行 C 测试（堆不变量、解析边界、Floyd–Warshall 独立对拍）；
  3. 用合成小图做 CLI 回归：已知路径、同点、不可达、非法堆名与越界编号；
  4. 核对 benchmark 的输入约束（少于 1000 对查询、零种子必须被拒绝）；
  5. 用同一种子跑两次基准，比较除计时字段外的全部 CSV 内容以验证可复现性。

所有构建产物、合成输入与日志都写入 --output 指定的目录，源码目录保持干净。
"""
import argparse
import csv
from pathlib import Path
import shutil
import subprocess
import sys

# 源码根目录（本文件位于 code/tests/ 下），以及所有入口共用的源文件列表。
SOURCE = Path(__file__).resolve().parents[1]
COMMON = ["graph.c", "binary_heap.c", "fibonacci_heap.c", "dijkstra.c"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="构建、日志与测试材料目录")
    parser.add_argument("--cc", default="gcc", help="GCC 可执行文件")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    # 在输出目录放一份说明，便于把该目录整体打包进 testresult/。
    (output / "README.md").write_text(
        "# 自动测试材料\n\n包含可执行文件、合成输入、测试日志与基准 CSV；不包含 USA 原始数据。\n",
        encoding="utf-8",
    )
    compiler = shutil.which(args.cc)
    if not compiler:
        raise SystemExit(f"找不到编译器：{args.cc}")
    log = []

    def run(command, success=True):
        """执行一条命令；success=False 表示"预期失败"，退出状态必须非 0。
        全部命令与输出都会追加进 validation.log，便于事后复核。"""
        command = list(map(str, command))
        result = subprocess.run(command, cwd=output, text=True, capture_output=True)
        log.extend(["$ " + " ".join(command), result.stdout, result.stderr])
        if (result.returncode == 0) != success:
            raise RuntimeError(f"退出状态异常 {result.returncode}: {command}\n{result.stdout}\n{result.stderr}")
        return result.stdout

    try:
        run([compiler, "--version"])
        # 三个入口都用 -Werror 构建：任何告警都会让测试直接失败。测试程序不得
        # 定义 NDEBUG，因为断言同时承担验证职责。
        for name, source in [("shortest_path", "main.c"), ("benchmark", "benchmark.c"), ("test_runner", "tests/test.c")]:
            run([compiler, "-std=c99", "-O2", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-I", SOURCE,
                 SOURCE / source, *[SOURCE / item for item in COMMON], "-o", output / (name + ".exe")])
        # C 测试：堆不变量、解析边界与独立 Floyd 对拍。
        print(run([output / "test_runner.exe"]).strip())
        # 合成图：含重边、零权自环与不可达顶点；期望的最短路为 1 -> 3 -> 2 -> 4 -> 5，距离 8。
        fixture = output / "sample.gr"
        fixture.write_text("c 合成测试图，不是 USA 数据\np sp 6 9\na 1 2 10\na 1 3 2\na 3 2 1\na 2 4 4\na 3 4 20\na 4 5 1\na 5 1 8\na 3 3 0\na 1 3 9\n", encoding="utf-8")
        query = output / "shortest_path.exe"
        for heap in ["binary", "fibonacci"]:
            answer = run([query, fixture, heap, "1", "5"])
            assert "distance=8\n" in answer and "path=1 -> 3 -> 2 -> 4 -> 5\n" in answer
            assert "distance=INF" in run([query, fixture, heap, "1", "6"])
            assert "distance=0\npath=3\n" in run([query, fixture, heap, "3", "3"])
            run([query, fixture, heap, "0", "1"], success=False)
        # 非法堆名、负号编号与不存在的文件都必须以非零状态退出。
        run([query, fixture, "invalid", "1", "5"], success=False)
        run([query, fixture, "binary", "-1", "5"], success=False)
        run([query, output / "missing.gr", "binary", "1", "5"], success=False)
        benchmark = output / "benchmark.exe"
        # 题目要求至少 1000 对查询，且种子必须非零：两种情况都要被拒绝。
        run([benchmark, fixture, "999", "20261013", output / "rejected.csv"], success=False)
        run([benchmark, fixture, "1000", "0", output / "rejected.csv"], success=False)
        # 同一种子跑两次：除计时字段外，CSV 的每一列都必须完全一致。
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
        # 无论成败都落盘日志，失败时可直接查看失败命令与输出。
        (output / "validation.log").write_text("\n".join(log), encoding="utf-8")


if __name__ == "__main__":
    main()
