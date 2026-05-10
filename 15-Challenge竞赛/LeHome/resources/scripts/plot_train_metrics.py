#!/usr/bin/env python3
import argparse
import csv
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


LINE_RE = re.compile(
    r"step:(?P<step>\d+)\s+smpl:(?P<smpl>[0-9.+-eEKM]+)\s+ep:(?P<ep>\d+)\s+epch:(?P<epch>[0-9.]+)\s+"
    r"loss:(?P<loss>[0-9.+-eE]+)\s+grdn:(?P<grdn>[0-9.+-eE]+)\s+lr:(?P<lr>[0-9.+-eE]+)\s+"
    r"updt_s:(?P<updt_s>[0-9.+-eE]+)\s+data_s:(?P<data_s>[0-9.+-eE]+)"
)


def parse_compact_number(value: str) -> int:
    value = value.strip().upper()
    if value.endswith("K"):
        return int(float(value[:-1]) * 1_000)
    if value.endswith("M"):
        return int(float(value[:-1]) * 1_000_000)
    return int(float(value))


def parse_rows(log_file: Path) -> list[dict]:
    rows = []
    for line in log_file.read_text(errors="ignore").splitlines():
        match = LINE_RE.search(line)
        if not match:
            continue
        data = match.groupdict()
        rows.append(
            {
                "step": int(data["step"]),
                "smpl": parse_compact_number(data["smpl"]),
                "ep": int(data["ep"]),
                "epch": float(data["epch"]),
                "loss": float(data["loss"]),
                "grdn": float(data["grdn"]),
                "lr": float(data["lr"]),
                "updt_s": float(data["updt_s"]),
                "data_s": float(data["data_s"]),
            }
        )
    return rows


def save_csv(rows: list[dict], csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "step",
                "smpl",
                "ep",
                "epch",
                "loss",
                "grdn",
                "lr",
                "updt_s",
                "data_s",
                "step_per_sec",
            ],
        )
        writer.writeheader()
        for row in rows:
            merged = dict(row)
            merged["step_per_sec"] = (
                1.0 / row["updt_s"] if row["updt_s"] > 0 else 0.0
            )
            writer.writerow(merged)


def save_summary(rows: list[dict], json_path: Path) -> None:
    summary = {"num_rows": len(rows)}
    if rows:
        summary.update(
            {
                "first_step": rows[0]["step"],
                "last_step": rows[-1]["step"],
                "loss_first": rows[0]["loss"],
                "loss_last": rows[-1]["loss"],
                "loss_min": min(r["loss"] for r in rows),
                "loss_max": max(r["loss"] for r in rows),
                "grad_norm_max": max(r["grdn"] for r in rows),
                "grad_norm_min": min(r["grdn"] for r in rows),
                "lr_last": rows[-1]["lr"],
                "avg_update_seconds": sum(r["updt_s"] for r in rows) / len(rows),
                "avg_data_seconds": sum(r["data_s"] for r in rows) / len(rows),
            }
        )
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))


def save_plot(rows: list[dict], plot_path: Path, title: str) -> None:
    if not rows:
        return
    steps = [r["step"] for r in rows]
    loss = [r["loss"] for r in rows]
    grad_norm = [r["grdn"] for r in rows]
    lr = [r["lr"] for r in rows]
    update_s = [r["updt_s"] for r in rows]
    data_s = [r["data_s"] for r in rows]

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(2, 2, figsize=(15, 9.5))
    fig.patch.set_facecolor("#f6f3ee")
    fig.suptitle(title, fontsize=18, fontweight="bold", y=0.98)

    colors = {
        "loss": "#d1495b",
        "grad": "#00798c",
        "lr": "#edae49",
        "update": "#30638e",
        "data": "#7f5539",
    }

    for ax in axes.flat:
        ax.set_facecolor("#fffdf8")
        for spine in ax.spines.values():
            spine.set_alpha(0.25)
        ax.tick_params(labelsize=10)
        ax.grid(alpha=0.22, linewidth=0.8)

    axes[0, 0].plot(steps, loss, color=colors["loss"], linewidth=2.4)
    axes[0, 0].set_title("Training Loss", fontsize=13, fontweight="bold")
    axes[0, 0].set_xlabel("Step")
    axes[0, 0].set_ylabel("Loss")

    axes[0, 1].plot(steps, grad_norm, color=colors["grad"], linewidth=2.4)
    axes[0, 1].set_title("Gradient Norm", fontsize=13, fontweight="bold")
    axes[0, 1].set_xlabel("Step")
    axes[0, 1].set_ylabel("Grad Norm")

    axes[1, 0].plot(steps, lr, color=colors["lr"], linewidth=2.4)
    axes[1, 0].set_title("Learning Rate", fontsize=13, fontweight="bold")
    axes[1, 0].set_xlabel("Step")
    axes[1, 0].set_ylabel("LR")
    axes[1, 0].yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y:.1e}"))

    axes[1, 1].plot(steps, update_s, label="Update", color=colors["update"], linewidth=2.2)
    axes[1, 1].plot(steps, data_s, label="Data", color=colors["data"], linewidth=2.2)
    axes[1, 1].set_title("Step Timing", fontsize=13, fontweight="bold")
    axes[1, 1].set_xlabel("Step")
    axes[1, 1].set_ylabel("Seconds")
    axes[1, 1].legend(frameon=False, fontsize=10, loc="upper right")

    fig.tight_layout(rect=[0, 0, 1, 0.96])
    plot_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(plot_path, dpi=160)


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse LeRobot train log and plot metrics.")
    parser.add_argument("--log_file", required=True, help="Path to train.log")
    parser.add_argument(
        "--out_dir",
        required=True,
        help="Directory to store CSV, JSON summary and PNG plot",
    )
    parser.add_argument("--title", default="LeHome Training Metrics")
    args = parser.parse_args()

    log_file = Path(args.log_file).resolve()
    out_dir = Path(args.out_dir).resolve()
    rows = parse_rows(log_file)

    save_csv(rows, out_dir / "train_metrics.csv")
    save_summary(rows, out_dir / "train_metrics_summary.json")
    save_plot(rows, out_dir / "train_metrics.png", args.title)

    print(f"Parsed rows: {len(rows)}")
    print(f"Output dir : {out_dir}")


if __name__ == "__main__":
    main()
