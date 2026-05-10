#!/usr/bin/env python3
import argparse
import csv
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt


def load_rows(csv_file: Path) -> list[dict]:
    rows = []
    with csv_file.open() as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                {
                    "timestamp": datetime.strptime(row["timestamp"].strip(), "%Y/%m/%d %H:%M:%S.%f"),
                    "utilization_gpu": float(row["utilization_gpu"]),
                    "memory_used_mb": float(row["memory_used_mb"]),
                    "memory_total_mb": float(row["memory_total_mb"]),
                    "temperature_gpu": float(row["temperature_gpu"]),
                    "power_draw_w": float(row["power_draw_w"]),
                }
            )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot sampled GPU metrics.")
    parser.add_argument("--csv_file", required=True)
    parser.add_argument("--out_png", required=True)
    parser.add_argument("--title", default="GPU Training Monitor")
    args = parser.parse_args()

    rows = load_rows(Path(args.csv_file))
    if not rows:
        raise SystemExit("No GPU metric rows found.")

    x = list(range(len(rows)))
    util = [row["utilization_gpu"] for row in rows]
    mem_used = [row["memory_used_mb"] / 1024 for row in rows]
    mem_total = rows[0]["memory_total_mb"] / 1024
    temp = [row["temperature_gpu"] for row in rows]
    power = [row["power_draw_w"] for row in rows]

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(2, 2, figsize=(15, 9.5))
    fig.patch.set_facecolor("#f6f3ee")
    fig.suptitle(args.title, fontsize=18, fontweight="bold", y=0.98)

    for ax in axes.flat:
        ax.set_facecolor("#fffdf8")
        ax.grid(alpha=0.22, linewidth=0.8)

    axes[0, 0].plot(x, util, color="#006d77", linewidth=2.4)
    axes[0, 0].fill_between(x, util, color="#83c5be", alpha=0.25)
    axes[0, 0].set_title("GPU Utilization", fontsize=13, fontweight="bold")
    axes[0, 0].set_ylabel("Percent")
    axes[0, 0].set_ylim(0, 105)

    axes[0, 1].plot(x, mem_used, color="#d1495b", linewidth=2.4)
    axes[0, 1].axhline(mem_total, color="#6c757d", linestyle="--", linewidth=1.2, label="Total")
    axes[0, 1].set_title("GPU Memory", fontsize=13, fontweight="bold")
    axes[0, 1].set_ylabel("GiB")
    axes[0, 1].legend(frameon=False)

    axes[1, 0].plot(x, temp, color="#ff7d00", linewidth=2.4)
    axes[1, 0].set_title("Temperature", fontsize=13, fontweight="bold")
    axes[1, 0].set_ylabel("C")

    axes[1, 1].plot(x, power, color="#3a86ff", linewidth=2.4)
    axes[1, 1].set_title("Power Draw", fontsize=13, fontweight="bold")
    axes[1, 1].set_ylabel("W")

    for ax in axes[1]:
        ax.set_xlabel("Sample")
    for ax in axes[0]:
        ax.set_xlabel("Sample")

    out_png = Path(args.out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(out_png, dpi=160)


if __name__ == "__main__":
    main()
