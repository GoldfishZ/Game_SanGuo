"""带评分元数据的冻结历史策略池。"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path


class HistoricalPolicyPool:
    def __init__(self, directory="artifacts/rl/self_play", *, max_size=24,
                 top_k=8, temperature=0.25):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.metadata_path = self.directory / "pool.json"
        self.max_size = max(1, int(max_size))
        self.top_k = max(1, int(top_k))
        self.temperature = max(1e-6, float(temperature))
        self.entries = self._load_metadata()

    def _load_metadata(self):
        if not self.metadata_path.exists():
            return []
        data = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        return [item for item in data if (self.directory / item["file"]).exists()]

    def _save_metadata(self):
        temporary = self.metadata_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(self.entries, ensure_ascii=False, indent=2), encoding="utf-8",
        )
        os.replace(temporary, self.metadata_path)

    @staticmethod
    def _cpu_state_dict(model_state):
        return {key: value.detach().cpu() for key, value in model_state.items()}

    def add(self, model_state, *, update, score, observation_schema,
            observation_size, action_size, model_schema):
        import torch
        policy_id = f"history-{int(update):06d}"
        filename = f"{policy_id}.pt"
        path = self.directory / filename
        temporary = path.with_suffix(".tmp")
        torch.save({
            "model": self._cpu_state_dict(model_state),
            "update": int(update),
            "score": float(score),
            "observation_schema": observation_schema,
            "observation_size": int(observation_size),
            "action_size": int(action_size),
            "model_schema": model_schema,
        }, temporary)
        os.replace(temporary, path)
        self.entries = [item for item in self.entries if item["id"] != policy_id]
        self.entries.append({
            "id": policy_id, "file": filename,
            "update": int(update), "score": float(score),
        })
        self.entries.sort(key=lambda item: (item["score"], item["update"]), reverse=True)
        removed = self.entries[self.max_size:]
        self.entries = self.entries[:self.max_size]
        for item in removed:
            old_path = self.directory / item["file"]
            if old_path.exists():
                old_path.unlink()
        self._save_metadata()
        return policy_id

    def sample(self, rng):
        """从最高分 top-k 中按 softmax(score / temperature) 加权采样。"""
        if not self.entries:
            return None
        candidates = self.entries[:self.top_k]
        maximum = max(item["score"] for item in candidates)
        weights = [
            math.exp((item["score"] - maximum) / self.temperature)
            for item in candidates
        ]
        item = rng.choices(candidates, weights=weights, k=1)[0]
        return dict(item)

    def load(self, entry, device="cpu"):
        import torch
        return torch.load(self.directory / entry["file"], map_location=device)

    def metrics(self):
        if not self.entries:
            return {"pool_size": 0, "best_score": 0.0, "mean_score": 0.0}
        return {
            "pool_size": len(self.entries),
            "best_score": max(item["score"] for item in self.entries),
            "mean_score": sum(item["score"] for item in self.entries) / len(self.entries),
        }
