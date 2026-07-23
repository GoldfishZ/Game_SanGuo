"""Train PvE draft/formation value models from episode telemetry."""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np
import torch

from src.rl.prebattle import (
    GENERAL_IDS, PREBATTLE_SCHEMA, build_models, encode_draft, encode_formation,
)


def load_yaml_defaults(path):
    if not path:
        return {}
    import yaml
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"预战训练配置不存在: {config_path}")
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("预战训练 YAML 顶层必须是键值映射")
    return {str(key).replace("-", "_"): value for key, value in data.items()}


def parse_args():
    bootstrap = argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument("--config", default="tools/rl/configs/prebattle_pve.yaml")
    known, _ = bootstrap.parse_known_args()
    yaml_defaults = load_yaml_defaults(known.config)
    parser = argparse.ArgumentParser(parents=[bootstrap])
    parser.add_argument("--episodes", default="artifacts/rl/round_v3/runs/selfplay-v3-round-01/episodes.jsonl")
    parser.add_argument("--output", default="artifacts/rl/pve/prebattle_value.pt")
    parser.add_argument("--min-update", type=int, default=200)
    parser.add_argument("--validation-update", type=int, default=501)
    parser.add_argument("--max-train", type=int, default=160000)
    parser.add_argument("--max-validation", type=int, default=40000)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=1024)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--seed", type=int, default=20260723)
    valid_keys = {action.dest for action in parser._actions}
    unknown_keys = sorted(set(yaml_defaults) - valid_keys)
    if unknown_keys:
        parser.error(f"YAML 包含未知参数: {', '.join(unknown_keys)}")
    parser.set_defaults(**yaml_defaults)
    args = parser.parse_args()
    if args.validation_update <= args.min_update:
        parser.error("validation_update 必须大于 min_update")
    if args.max_train <= 0 or args.max_validation <= 0:
        parser.error("max_train 和 max_validation 必须为正整数")
    return args


def _valid_formation(roster, formation):
    if len(roster) != len(formation) or not roster:
        return False
    ids = {int(item["general_id"]) for item in formation}
    cells = {(int(item["row"]), int(item["col"])) for item in formation}
    return ids == {int(value) for value in roster} and len(cells) == len(formation) and all(
        0 <= row < 3 and 0 <= col < 4 for row, col in cells
    )


def _reservoir_add(items, value, limit, seen, rng):
    if len(items) < limit:
        items.append(value)
    else:
        index = rng.randrange(seen)
        if index < limit:
            items[index] = value


def load_records(path, args):
    rng = random.Random(args.seed)
    train, validation = [], []
    seen_train = seen_validation = skipped_formation = 0
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            update = int(item.get("update", 0))
            if update < args.min_update:
                continue
            outcome = item.get("outcome")
            if outcome not in ("win", "loss", "draw"):
                continue
            target = 1.0 if outcome == "win" else (0.0 if outcome == "loss" else 0.5)
            roster_self, roster_enemy = item.get("roster_self") or [], item.get("roster_enemy") or []
            form_self, form_enemy = item.get("formation_self") or [], item.get("formation_enemy") or []
            complete = _valid_formation(roster_self, form_self) and _valid_formation(roster_enemy, form_enemy)
            if not complete:
                skipped_formation += 1
            record = (roster_self, roster_enemy, form_self, form_enemy, target, complete)
            if update >= args.validation_update:
                seen_validation += 1
                _reservoir_add(validation, record, args.max_validation, seen_validation, rng)
            else:
                seen_train += 1
                _reservoir_add(train, record, args.max_train, seen_train, rng)
            if line_number % 100000 == 0:
                print(f"读取 {line_number} 行，训练候选 {seen_train}，验证候选 {seen_validation}", flush=True)
    return train, validation, skipped_formation


def make_arrays(records, formation=False):
    features, targets = [], []
    for roster_self, roster_enemy, form_self, form_enemy, target, complete in records:
        if formation and not complete:
            continue
        encoder = encode_formation if formation else encode_draft
        args = (roster_self, roster_enemy, form_self, form_enemy) if formation else (roster_self, roster_enemy)
        features.append(encoder(*args))
        targets.append(target)
    return np.asarray(features, dtype=np.float32), np.asarray(targets, dtype=np.float32)


def metrics(logits, targets):
    probabilities = torch.sigmoid(logits).detach().cpu().numpy()
    labels = targets.detach().cpu().numpy()
    hard = labels >= 0.5
    accuracy = float(((probabilities >= 0.5) == hard).mean())
    brier = float(np.mean((probabilities - labels) ** 2))
    clipped = np.clip(probabilities, 1e-6, 1 - 1e-6)
    log_loss = float(np.mean(-(labels * np.log(clipped) + (1 - labels) * np.log(1 - clipped))))
    binary = labels > 0.5
    positives, negatives = int(binary.sum()), int((~binary).sum())
    if positives and negatives:
        order = np.argsort(probabilities)
        ranks = np.empty_like(order, dtype=np.float64)
        ranks[order] = np.arange(1, len(order) + 1)
        auc = float((ranks[binary].sum() - positives * (positives + 1) / 2) / (positives * negatives))
    else:
        auc = 0.5
    return {"accuracy": accuracy, "brier": brier, "log_loss": log_loss, "auc": auc}


def train_model(model, train_x, train_y, val_x, val_y, args, device, name):
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1e-4)
    loss_fn = torch.nn.BCEWithLogitsLoss()
    train_x = torch.from_numpy(train_x)
    train_y = torch.from_numpy(train_y)
    val_x = torch.from_numpy(val_x)
    val_y = torch.from_numpy(val_y)
    generator = torch.Generator().manual_seed(args.seed)
    for epoch in range(1, args.epochs + 1):
        permutation = torch.randperm(len(train_x), generator=generator)
        model.train()
        total = 0.0
        for start in range(0, len(permutation), args.batch_size):
            index = permutation[start:start + args.batch_size]
            x = train_x[index].to(device)
            y = train_y[index].to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = loss_fn(model(x), y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total += float(loss.item()) * len(index)
        print(f"{name} epoch {epoch}/{args.epochs} loss={total/len(train_x):.5f}", flush=True)
    model.eval()
    outputs = []
    with torch.no_grad():
        for start in range(0, len(val_x), args.batch_size):
            outputs.append(model(val_x[start:start + args.batch_size].to(device)).cpu())
    result = metrics(torch.cat(outputs), val_y)
    result["train_samples"] = len(train_x)
    result["validation_samples"] = len(val_x)
    return result


def main():
    args = parse_args()
    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)
    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else args.device
    if device == "auto": device = "cpu"
    train, validation, skipped = load_records(args.episodes, args)
    if not train or not validation:
        raise RuntimeError("没有足够的训练/验证 episode，请检查 update 切分")
    draft_train_x, draft_train_y = make_arrays(train)
    draft_val_x, draft_val_y = make_arrays(validation)
    form_train_x, form_train_y = make_arrays(train, formation=True)
    form_val_x, form_val_y = make_arrays(validation, formation=True)
    draft_model, formation_model = build_models()
    draft_metrics = train_model(draft_model, draft_train_x, draft_train_y, draft_val_x, draft_val_y, args, device, "draft")
    formation_metrics = train_model(formation_model, form_train_x, form_train_y, form_val_x, form_val_y, args, device, "formation")
    metadata = {
        "episodes": str(args.episodes), "min_update": args.min_update,
        "validation_update": args.validation_update, "seed": args.seed,
        "skipped_incomplete_formations": skipped,
        "draft_metrics": draft_metrics, "formation_metrics": formation_metrics,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "schema": PREBATTLE_SCHEMA, "general_ids": GENERAL_IDS,
        "draft_model": {k: v.detach().cpu() for k, v in draft_model.state_dict().items()},
        "formation_model": {k: v.detach().cpu() for k, v in formation_model.state_dict().items()},
        "metadata": metadata,
    }, output)
    print(json.dumps({"output": str(output), **metadata}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
