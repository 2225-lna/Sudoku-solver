
import argparse
import csv
import multiprocessing as mp
import queue
import statistics
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PUZZLES = ROOT / "puzzles" / "puzzles.csv"
RESULTS = ROOT / "results"

RAW_FIELDS = [
    "puzzle_id", "difficulty", "algorithm", "run",
    "time_seconds", "node_count", "status"
]

SUMMARY_FIELDS = [
    "puzzle_id", "difficulty", "algorithm", "runs_successful",
    "runs_total", "mean_seconds", "median_seconds",
    "node_count", "status"
]


def parse_grid(text):
    text = text.strip().replace(".", "0")

    if len(text) != 81 or not all(c in "0123456789" for c in text):
        raise ValueError("Puzzle grid must be 81 digits, with 0 for empty cells")

    return [
        [int(text[9 * r + c]) for c in range(9)]
        for r in range(9)
    ]


def child_run(method, grid, output):
    try:
        if method == "Basic":
            from solver_basic import solve_basic as solve
        else:
            from solver_mrv import solve_mrv as solve

        before = time.perf_counter()
        solution, nodes = solve(grid)
        elapsed = time.perf_counter() - before

        output.put((elapsed, nodes, solution is not None, "OK"))

    except Exception as exc:
        output.put((None, None, False, f"ERROR: {exc}"))


def run_one(method, grid, timeout):
    context = mp.get_context("spawn")
    output = context.Queue()
    proc = context.Process(target=child_run, args=(method, grid, output))

    proc.start()
    proc.join(timeout)

    if proc.is_alive():
        proc.terminate()
        proc.join()
        output.close()
        output.join_thread()
        return None, None, "TIMEOUT"

    try:
        elapsed, nodes, solved, state = output.get(timeout=1.5)
    except queue.Empty:
        elapsed, nodes, solved, state = (
            None, None, False, f"WORKER_EXIT_{proc.exitcode}"
        )

    output.close()
    output.join_thread()

    if state != "OK":
        return elapsed, nodes, state

    return elapsed, nodes, "SOLVED" if solved else "NO_SOLUTION"


def save_csv(path, fields, records):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def create_charts(summaries):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("Charts not created: run python -m pip install matplotlib")
        return

    from collections import defaultdict

    chart_settings = [
        ("median_seconds", "Median solve time (seconds)", "runtime.png"),
        ("node_count", "Recursive search nodes", "nodes.png")
    ]

    for field, ylabel, name in chart_settings:
        buckets = defaultdict(lambda: {"Basic": [], "MRV": []})

        for record in summaries:
            if record["status"] == "SOLVED" and record[field] != "":
                buckets[record["difficulty"]][record["algorithm"]].append(
                    float(record[field])
                )

        categories = [
            c for c in ("Easy", "Medium", "Hard", "Very Hard")
            if c in buckets
        ]

        if not categories:
            continue

        labels = []
        basics = []
        mrvs = []

        for cat in categories:
            labels.append(cat)

            basics.append(
                statistics.median(buckets[cat]["Basic"])
                if buckets[cat]["Basic"] else float("nan")
            )

            mrvs.append(
                statistics.median(buckets[cat]["MRV"])
                if buckets[cat]["MRV"] else float("nan")
            )

        fig, ax = plt.subplots(figsize=(8.5, 5))
        x = list(range(len(labels)))

        ax.bar([i - 0.19 for i in x], basics, 0.38, label="Basic")
        ax.bar([i + 0.19 for i in x], mrvs, 0.38, label="MRV")

        ax.set_xticks(x, labels)
        ax.set_ylabel(ylabel)
        ax.set_title("Sudoku solver comparison by clue-count category")
        ax.set_yscale("log")
        ax.legend()
        ax.grid(axis="y", alpha=0.2)

        fig.tight_layout()
        fig.savefig(RESULTS / name, dpi=150)
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark Basic and MRV Sudoku solvers"
    )

    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument(
        "--timeout",
        type=float,
        default=3.0,
        help="Maximum wall-clock seconds per attempt"
    )
    parser.add_argument("--puzzles", type=Path, default=PUZZLES)

    args = parser.parse_args()

    if args.repeats < 1 or args.timeout <= 0:
        parser.error("Repeats and timeout must be positive")

    with args.puzzles.open(newline="", encoding="utf-8-sig") as file:
        items = list(csv.DictReader(file))

    if not items:
        raise ValueError("No puzzles found")

    RESULTS.mkdir(exist_ok=True)

    raw = []
    summaries = []

    for item in items:
        grid = parse_grid(item["grid"])

        for method in ("Basic", "MRV"):
            measurements = []
            nodes_seen = set()
            statuses = []

            for iteration in range(1, args.repeats + 1):
                seconds, nodes, status = run_one(method, grid, args.timeout)
                statuses.append(status)

                if status == "SOLVED":
                    measurements.append(seconds)
                    nodes_seen.add(nodes)

                raw.append({
                    "puzzle_id": item["id"],
                    "difficulty": item["difficulty"],
                    "algorithm": method,
                    "run": iteration,
                    "time_seconds": seconds if seconds is not None else "",
                    "node_count": nodes if nodes is not None else "",
                    "status": status
                })

            finished = (
                all(s == "SOLVED" for s in statuses)
                and len(nodes_seen) == 1
            )

            summary = {
                "puzzle_id": item["id"],
                "difficulty": item["difficulty"],
                "algorithm": method,
                "runs_successful": len(measurements),
                "runs_total": args.repeats,
                "mean_seconds": (
                    statistics.mean(measurements) if measurements else ""
                ),
                "median_seconds": (
                    statistics.median(measurements) if measurements else ""
                ),
                "node_count": (
                    next(iter(nodes_seen)) if len(nodes_seen) == 1 else ""
                ),
                "status": (
                    "SOLVED" if finished
                    else "/".join(sorted(set(statuses)))
                )
            }

            summaries.append(summary)

            print(
                f"{item['id']:16} {method:5} "
                f"{summary['status']:14} "
                f"nodes={summary['node_count']}"
            )

    save_csv(RESULTS / "raw_runs.csv", RAW_FIELDS, raw)
    save_csv(RESULTS / "summary.csv", SUMMARY_FIELDS, summaries)

    create_charts(summaries)

    print("\nResults saved in:", RESULTS)


if __name__ == "__main__":
    mp.freeze_support()
    main()
