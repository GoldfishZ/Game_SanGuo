"""Promote a resumable PPO checkpoint and its self-play pool into tracked assets."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.rl import actions
from src.rl.models.actor_critic_v3 import MODEL_SCHEMA
from src.rl.observation import OBSERVATION_SCHEMA, OBSERVATION_SIZE
from src.rl.training.checkpoint import CheckpointManager


DEFAULT_RUN = ROOT / "artifacts" / "rl" / "multi_roster_v1"
DEFAULT_DESTINATION = ROOT / "assets" / "models" / "training" / "multi_roster_v1"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    shutil.copy2(source, temporary)
    os.replace(temporary, destination)


def validate_checkpoint(path, *, require_optimizer=False):
    import torch

    state = torch.load(path, map_location="cpu", weights_only=False)
    CheckpointManager.validate_schema(
        state,
        observation_schema=OBSERVATION_SCHEMA,
        observation_size=OBSERVATION_SIZE,
        action_size=actions.ACTION_SIZE,
        model_schema=MODEL_SCHEMA,
    )
    if require_optimizer and not state.get("optimizer"):
        raise ValueError(f"checkpoint 缺少优化器状态，不能用于续训: {path}")
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    args = parser.parse_args()

    run = args.run.resolve()
    destination = args.destination.resolve()
    checkpoint_source = run / "checkpoints" / "ppo_latest.pt"
    pool_source = run / "self_play"
    pool_metadata_source = pool_source / "pool.json"
    if not checkpoint_source.is_file() or not pool_metadata_source.is_file():
        raise FileNotFoundError("训练 checkpoint 或 self-play/pool.json 不存在")

    checkpoint = validate_checkpoint(checkpoint_source, require_optimizer=True)
    pool_entries = json.loads(pool_metadata_source.read_text(encoding="utf-8"))
    promoted_pool = []
    for entry in pool_entries:
        source = pool_source / entry["file"]
        if not source.is_file():
            raise FileNotFoundError(f"历史池文件不存在: {source}")
        history = validate_checkpoint(source)
        if int(history.get("update", entry["update"])) != int(entry["update"]):
            raise ValueError(f"历史池 update 不一致: {source}")
        output = destination / "self_play" / source.name
        atomic_copy(source, output)
        promoted_pool.append({
            **entry,
            "sha256": sha256(output),
            "bytes": output.stat().st_size,
        })

    checkpoint_output = destination / "checkpoints" / "ppo_latest.pt"
    atomic_copy(checkpoint_source, checkpoint_output)
    pool_metadata_output = destination / "self_play" / "pool.json"
    pool_metadata_output.write_text(
        json.dumps(pool_entries, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "schema": "sanguo-resumable-training-seed-v1",
        "training_entry": "tools/rl/train_ppo_v3.py",
        "config": "tools/rl/configs/ppo_selfplay_v3_multi_roster_long.yaml",
        "checkpoint": {
            "file": "checkpoints/ppo_latest.pt",
            "update": checkpoint.get("update"),
            "sha256": sha256(checkpoint_output),
            "bytes": checkpoint_output.stat().st_size,
            "observation_schema": checkpoint.get("observation_schema"),
            "observation_size": checkpoint.get("observation_size"),
            "action_size": checkpoint.get("action_size"),
            "model_schema": checkpoint.get("model_schema"),
            "has_optimizer": bool(checkpoint.get("optimizer")),
        },
        "self_play": {
            "metadata_file": "self_play/pool.json",
            "entries": promoted_pool,
        },
    }
    (destination / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "destination": str(destination),
        "checkpoint_update": checkpoint.get("update"),
        "self_play_models": len(promoted_pool),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
