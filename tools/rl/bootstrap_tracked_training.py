"""Copy the tracked resumable training seed into a writable artifacts run."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.rl.promote_training_seed import validate_checkpoint


SOURCE = ROOT / "assets" / "models" / "training" / "multi_roster_v1"
DEFAULT_TARGET = ROOT / "artifacts" / "rl" / "multi_roster_v1_resume"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verified_copy(source, destination, expected_sha):
    if destination.exists():
        if sha256(destination) != expected_sha:
            raise FileExistsError(
                f"目标文件已存在且内容不同，拒绝覆盖: {destination}"
            )
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    if sha256(destination) != expected_sha:
        raise RuntimeError(f"复制后哈希不一致: {destination}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    manifest = json.loads((SOURCE / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != "sanguo-resumable-training-seed-v1":
        raise ValueError("未知的训练种子 manifest schema")
    checkpoint_meta = manifest["checkpoint"]
    checkpoint_source = SOURCE / checkpoint_meta["file"]
    if sha256(checkpoint_source) != checkpoint_meta["sha256"]:
        raise ValueError("可恢复 checkpoint 哈希不一致")
    checkpoint = validate_checkpoint(checkpoint_source, require_optimizer=True)
    if int(checkpoint.get("update", -1)) != int(checkpoint_meta["update"]):
        raise ValueError("可恢复 checkpoint update 与 manifest 不一致")
    for entry in manifest["self_play"]["entries"]:
        source = SOURCE / "self_play" / entry["file"]
        if sha256(source) != entry["sha256"]:
            raise ValueError(f"历史池模型哈希不一致: {entry['file']}")

    if args.verify_only:
        print(
            f"训练种子验证通过：update {checkpoint['update']}，"
            f"{len(manifest['self_play']['entries'])} 个历史模型"
        )
        return

    target = args.target.resolve()
    checkpoint_target = target / "checkpoints" / "ppo_latest.pt"
    verified_copy(checkpoint_source, checkpoint_target, checkpoint_meta["sha256"])
    for entry in manifest["self_play"]["entries"]:
        verified_copy(
            SOURCE / "self_play" / entry["file"],
            target / "self_play" / entry["file"],
            entry["sha256"],
        )
    pool_source = SOURCE / manifest["self_play"]["metadata_file"]
    pool_target = target / "self_play" / "pool.json"
    pool_target.parent.mkdir(parents=True, exist_ok=True)
    if pool_target.exists() and pool_target.read_bytes() != pool_source.read_bytes():
        raise FileExistsError(f"目标历史池元数据不同，拒绝覆盖: {pool_target}")
    if not pool_target.exists():
        shutil.copy2(pool_source, pool_target)

    relative_target = target.relative_to(ROOT)
    relative_checkpoint = checkpoint_target.relative_to(ROOT)
    print(f"训练种子已准备到: {relative_target}")
    print("续训命令：")
    print(
        "python tools/rl/train_ppo_v3.py "
        "--config tools/rl/configs/ppo_selfplay_v3_multi_roster_long.yaml "
        f"--artifact-root {relative_target.as_posix()} "
        f"--resume {relative_checkpoint.as_posix()} "
        "--run-name multi-roster-v1-resume"
    )


if __name__ == "__main__":
    main()
