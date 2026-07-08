"""Fail CI if benchmark quality drops too far from the committed baseline."""
import argparse
import json
import sys
from pathlib import Path


def _load(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", default="eval/baseline/benchmark.json")
    parser.add_argument("--current", default="eval/results/benchmark.json")
    parser.add_argument("--max-drop", type=float, default=0.05)
    args = parser.parse_args()

    baseline = _load(Path(args.baseline))
    current = _load(Path(args.current))
    k = baseline["k"]
    metric = f"ndcg_at_{k}"

    failures: list[str] = []
    for mode, expected in baseline["modes"].items():
        observed = current["modes"].get(mode)
        if observed is None:
            failures.append(f"{mode}: missing from current benchmark")
            continue

        floor = expected[metric] * (1.0 - args.max_drop)
        if observed[metric] < floor:
            failures.append(
                f"{mode}: {metric} {observed[metric]:.4f} < "
                f"{floor:.4f} baseline floor"
            )

    if failures:
        print("Benchmark regression detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(
        f"Benchmark regression check passed: {metric} stayed within "
        f"{args.max_drop:.0%} of baseline for all modes."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
