import hashlib
import json

from src.paths import PVE_MODELS_DIR
from src.rl.pve import (
    DEFAULT_BATTLE_MODEL,
    DEFAULT_PREBATTLE_MODEL,
    PVEController,
)


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def test_tracked_pve_bundle_is_complete_and_matches_manifest():
    manifest_path = PVE_MODELS_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert DEFAULT_BATTLE_MODEL == PVE_MODELS_DIR / "battle_policy.pt"
    assert DEFAULT_PREBATTLE_MODEL == PVE_MODELS_DIR / "prebattle_value.pt"
    assert manifest["schema"] == "sanguo-pve-model-bundle-v1"
    assert DEFAULT_BATTLE_MODEL.is_file()
    assert DEFAULT_PREBATTLE_MODEL.is_file()
    assert file_sha256(DEFAULT_BATTLE_MODEL) == manifest["battle"]["sha256"]
    assert file_sha256(DEFAULT_PREBATTLE_MODEL) == manifest["prebattle"]["sha256"]


def test_tracked_pve_bundle_loads_with_current_code_schema():
    controller = PVEController(
        battle_checkpoint=DEFAULT_BATTLE_MODEL,
        prebattle_checkpoint=DEFAULT_PREBATTLE_MODEL,
        device="cpu",
    ).load()

    assert controller.load_errors == []
    assert controller.battle_model is not None
    assert controller.prebattle.available
