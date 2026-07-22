"""训练标量的控制台、CSV 与 TensorBoard 输出。"""
from __future__ import annotations

import csv
from dataclasses import asdict, is_dataclass
import json
from pathlib import Path
from time import strftime


class TrainLogger:
    def __init__(self, root="artifacts/rl/runs", run_name=None, config=None):
        name = run_name or f"ppo-{strftime('%Y%m%d-%H%M%S')}"
        self.path = Path(root) / name
        self.path.mkdir(parents=True, exist_ok=True)
        self.csv_file = (self.path / "metrics.csv").open("w", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self.csv_file, fieldnames=("step", "tag", "value"))
        self.writer.writeheader()
        self.episodes_file = (self.path / "episodes.jsonl").open("a", encoding="utf-8")
        self.summary_writer = None
        try:
            from torch.utils.tensorboard import SummaryWriter
            self.summary_writer = SummaryWriter(str(self.path))
        except (ImportError, ModuleNotFoundError):
            pass
        if config is not None:
            (self.path / "resolved_config.json").write_text(
                json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    def log(self, step, metrics, prefix=None):
        flattened = {}
        for key, value in metrics.items():
            tag = f"{prefix}/{key}" if prefix else key
            if isinstance(value, (int, float)):
                flattened[tag] = float(value)
                if self.summary_writer:
                    self.summary_writer.add_scalar(tag, value, step)
        for tag, value in flattened.items():
            self.writer.writerow({"step": step, "tag": tag, "value": value})
        self.csv_file.flush()
        print({"update": step, **{key: round(value, 5) for key, value in flattened.items()}}, flush=True)

    def log_episodes(self, step, summaries):
        for summary in summaries:
            payload = asdict(summary) if is_dataclass(summary) else dict(summary)
            payload["update"] = step
            self.episodes_file.write(json.dumps(payload, ensure_ascii=False) + "\n")
        if summaries:
            self.episodes_file.flush()

    def close(self):
        if self.summary_writer:
            self.summary_writer.close()
        self.episodes_file.close()
        self.csv_file.close()
