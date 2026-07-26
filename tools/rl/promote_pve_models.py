"""Validate and promote selected training checkpoints into tracked PvE assets."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.paths import PVE_MODELS_DIR
from src.rl import actions
from src.rl.models.actor_critic_v3 import MODEL_SCHEMA
from src.rl.observation import OBSERVATION_SCHEMA, OBSERVATION_SIZE
from src.rl.prebattle import GENERAL_IDS, PREBATTLE_SCHEMA
from src.rl.pve import BATTLE_MISTAKE_RATES, BATTLE_TEMPERATURES
from src.rl.training.checkpoint import CheckpointManager


DIFFICULTIES = ("easy", "normal", "hard")
DEFAULT_SOURCES = {
    difficulty: {
        "battle": ROOT / "artifacts" / "rl" / "pve_tiers" / "frozen" / f"battle_{difficulty}.pt",
        "prebattle": ROOT / "artifacts" / "rl" / "pve_tiers" / "prebattle" / f"prebattle_{difficulty}.pt",
    }
    for difficulty in DIFFICULTIES
}


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    for difficulty in DIFFICULTIES:
        parser.add_argument(
            f"--{difficulty}-battle", type=Path,
            default=DEFAULT_SOURCES[difficulty]["battle"],
        )
        parser.add_argument(
            f"--{difficulty}-prebattle", type=Path,
            default=DEFAULT_SOURCES[difficulty]["prebattle"],
        )
    parser.add_argument("--destination", type=Path, default=PVE_MODELS_DIR)
    return parser.parse_args()


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(battle_path, prebattle_path):
    import torch

    battle = torch.load(battle_path, map_location="cpu", weights_only=False)
    CheckpointManager.validate_schema(
        battle,
        observation_schema=OBSERVATION_SCHEMA,
        observation_size=OBSERVATION_SIZE,
        action_size=actions.ACTION_SIZE,
        model_schema=MODEL_SCHEMA,
    )
    prebattle = torch.load(prebattle_path, map_location="cpu", weights_only=False)
    if prebattle.get("schema") != PREBATTLE_SCHEMA:
        raise ValueError(f"不兼容的预战模型 schema: {prebattle.get('schema')}")
    if tuple(prebattle.get("general_ids", ())) != GENERAL_IDS:
        raise ValueError("预战模型的武将注册表与当前游戏不一致")
    return battle, prebattle


def promote(source, destination):
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    shutil.copy2(source, temporary)
    os.replace(temporary, destination)


def relative_or_absolute(path):
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def main():
    args = parse_args()
    destination = args.destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": "sanguo-pve-model-bundle-v2",
        "promoted_at": datetime.now(timezone.utc).isoformat(),
        "default_difficulty": "normal",
        "difficulties": {},
    }
    for difficulty in DIFFICULTIES:
        battle_path = getattr(args, f"{difficulty}_battle").resolve()
        prebattle_path = getattr(args, f"{difficulty}_prebattle").resolve()
        if not battle_path.is_file() or not prebattle_path.is_file():
            raise FileNotFoundError(f"{difficulty} 档战斗模型或预战模型不存在，不能发布")
        battle, prebattle = validate(battle_path, prebattle_path)
        battle_output = destination / f"battle_policy_{difficulty}.pt"
        prebattle_output = destination / f"prebattle_value_{difficulty}.pt"
        promote(battle_path, battle_output)
        promote(prebattle_path, prebattle_output)
        manifest["difficulties"][difficulty] = {
            "runtime_policy": {
                "temperature": BATTLE_TEMPERATURES[difficulty],
                "legal_exploration_rate": BATTLE_MISTAKE_RATES[difficulty],
            },
            "battle": {
                "file": battle_output.name,
                "source": relative_or_absolute(battle_path),
                "sha256": sha256(battle_output),
                "bytes": battle_output.stat().st_size,
                "update": battle.get("update"),
                "observation_schema": battle.get("observation_schema"),
                "model_schema": battle.get("model_schema"),
            },
            "prebattle": {
                "file": prebattle_output.name,
                "source": relative_or_absolute(prebattle_path),
                "sha256": sha256(prebattle_output),
                "bytes": prebattle_output.stat().st_size,
                "schema": prebattle.get("schema"),
                "metadata": prebattle.get("metadata", {}),
            },
        }
    (destination / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
