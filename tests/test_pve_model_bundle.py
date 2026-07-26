import hashlib
import json

from src.paths import PVE_MODELS_DIR
from src.rl.pve import (
    BATTLE_MISTAKE_RATES,
    BATTLE_TEMPERATURES,
    DEFAULT_BATTLE_MODEL,
    DEFAULT_BATTLE_MODELS,
    DEFAULT_PREBATTLE_MODEL,
    DEFAULT_PREBATTLE_MODELS,
    PVE_DIFFICULTIES,
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

    assert DEFAULT_BATTLE_MODEL == PVE_MODELS_DIR / "battle_policy_normal.pt"
    assert DEFAULT_PREBATTLE_MODEL == PVE_MODELS_DIR / "prebattle_value_normal.pt"
    assert manifest["schema"] == "sanguo-pve-model-bundle-v2"
    assert manifest["default_difficulty"] == "normal"
    for difficulty in PVE_DIFFICULTIES:
        battle = DEFAULT_BATTLE_MODELS[difficulty]
        prebattle = DEFAULT_PREBATTLE_MODELS[difficulty]
        assert battle.is_file()
        assert prebattle.is_file()
        assert file_sha256(battle) == manifest["difficulties"][difficulty]["battle"]["sha256"]
        assert file_sha256(prebattle) == manifest["difficulties"][difficulty]["prebattle"]["sha256"]
        assert manifest["difficulties"][difficulty]["runtime_policy"] == {
            "temperature": BATTLE_TEMPERATURES[difficulty],
            "legal_exploration_rate": BATTLE_MISTAKE_RATES[difficulty],
        }


def test_tracked_pve_bundle_loads_with_current_code_schema():
    for difficulty in PVE_DIFFICULTIES:
        controller = PVEController(difficulty=difficulty, device="cpu").load()
        assert controller.load_errors == []
        assert controller.battle_model is not None
        assert controller.prebattle.available


def test_difficulty_profiles_have_increasing_battle_precision():
    assert BATTLE_TEMPERATURES == {"easy": 1.35, "normal": None, "hard": None}
    assert BATTLE_MISTAKE_RATES == {"easy": 0.0, "normal": 0.30, "hard": 0.0}
