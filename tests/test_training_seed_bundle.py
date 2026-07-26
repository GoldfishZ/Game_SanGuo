import hashlib
import json

import torch

from src.paths import PROJECT_ROOT
from tools.rl.promote_training_seed import validate_checkpoint


TRAINING_SEED = PROJECT_ROOT / "assets" / "models" / "training" / "multi_roster_v1"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def test_tracked_training_seed_is_resumable_and_complete():
    manifest = json.loads(
        (TRAINING_SEED / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["schema"] == "sanguo-resumable-training-seed-v1"
    checkpoint_meta = manifest["checkpoint"]
    checkpoint_path = TRAINING_SEED / checkpoint_meta["file"]
    checkpoint = validate_checkpoint(checkpoint_path, require_optimizer=True)
    assert checkpoint["update"] == 4906
    assert checkpoint_meta["has_optimizer"] is True
    assert sha256(checkpoint_path) == checkpoint_meta["sha256"]

    pool = json.loads(
        (TRAINING_SEED / manifest["self_play"]["metadata_file"]).read_text(
            encoding="utf-8"
        )
    )
    assert len(pool) == len(manifest["self_play"]["entries"]) == 32
    assert {item["file"] for item in pool} == {
        item["file"] for item in manifest["self_play"]["entries"]
    }
    for entry in manifest["self_play"]["entries"]:
        path = TRAINING_SEED / "self_play" / entry["file"]
        assert path.is_file()
        assert sha256(path) == entry["sha256"]


def test_tracked_resume_checkpoint_loads_model_and_optimizer_state():
    manifest = json.loads(
        (TRAINING_SEED / "manifest.json").read_text(encoding="utf-8")
    )
    state = torch.load(
        TRAINING_SEED / manifest["checkpoint"]["file"],
        map_location="cpu",
        weights_only=False,
    )
    assert state["model"]
    assert state["optimizer"]["state"]
    assert state["optimizer"]["param_groups"]
