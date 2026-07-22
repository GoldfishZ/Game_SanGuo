import random

import pytest
import torch

from src.rl.training.checkpoint import CheckpointManager
from src.rl.training.self_play import HistoricalPolicyPool
from tools.rl.train_ppo import load_yaml_defaults


def test_history_pool_keeps_best_and_samples_top_k(tmp_path):
    pool = HistoricalPolicyPool(tmp_path, max_size=3, top_k=2, temperature=0.1)
    for update, score in enumerate((0.1, 0.8, 0.4, 0.9), start=1):
        pool.add(
            {"weight": torch.tensor([float(update)])},
            update=update, score=score,
            observation_schema="test-v2", observation_size=12, action_size=7,
            model_schema="test-model-v2",
        )
    assert len(pool.entries) == 3
    assert [item["score"] for item in pool.entries] == [0.9, 0.8, 0.4]
    sampled = {pool.sample(random.Random(seed))["score"] for seed in range(20)}
    assert sampled <= {0.9, 0.8}


def test_checkpoint_schema_rejects_legacy_state():
    with pytest.raises(ValueError, match="schema"):
        CheckpointManager.validate_schema(
            {"model": {}},
            observation_schema="v2", observation_size=10, action_size=4,
            model_schema="model-v2",
        )


def test_yaml_loader_normalizes_cli_style_keys(tmp_path):
    path = tmp_path / "train.yaml"
    path.write_text("max-updates: 3\nstage: selfplay\n", encoding="utf-8")
    assert load_yaml_defaults(path) == {"max_updates": 3, "stage": "selfplay"}
