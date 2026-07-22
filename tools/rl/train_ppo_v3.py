"""PPO v3 入口；与仍在运行的 v2 训练进程和 checkpoint 完全隔离。"""
from __future__ import annotations

from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.rl import train_ppo as base
from src.rl.env_v3 import SanguoEnv as V3Env
from src.rl.models.actor_critic_v3 import ActorCritic, MODEL_SCHEMA
from src.rl.observation import OBSERVATION_SCHEMA, OBSERVATION_SIZE
from src.rl.training.evaluation_v3 import evaluate as evaluate_v3
from src.rl.training.ppo_v3 import ppo_update
from src.rl.training.vector_env_v3 import SyncRolloutCoordinator as V3Coordinator


V3_DEFAULTS = {
    "reward_fence_delta": 0.10,
    "reward_shield_delta": 0.02,
    "reward_effect_delta": 0.01,
    "selfplay_heuristic_ratio": 0.20,
    "selfplay_random_ratio": 0.10,
    "roster_repeat_episodes": 4,
    "mirror_ratio": 0.15,
    "eval_mirror_episodes": 128,
}
settings = dict(V3_DEFAULTS)
_base_yaml_loader = base.load_yaml_defaults
_base_rollout_metrics = base.rollout_metrics_from_fragments


def load_yaml_defaults(path):
    values = _base_yaml_loader(path)
    for key in V3_DEFAULTS:
        if key in values:
            settings[key] = values.pop(key)
    return values


def _reward_config(config):
    merged = dict(config or {})
    merged.update({
        "fence_delta": float(settings["reward_fence_delta"]),
        "shield_delta": float(settings["reward_shield_delta"]),
        "effect_delta": float(settings["reward_effect_delta"]),
    })
    return merged


class SanguoEnv(V3Env):
    def __init__(self, opponent=None, **kwargs):
        kwargs["reward_config"] = _reward_config(kwargs.get("reward_config"))
        super().__init__(opponent, **kwargs)


class SyncRolloutCoordinator(V3Coordinator):
    def __init__(self, workers, stage, env_config=None):
        env_config = dict(env_config or {})
        env_config["reward_config"] = _reward_config(env_config.get("reward_config"))
        super().__init__(
            workers, stage, env_config,
            roster_repeat_episodes=int(settings["roster_repeat_episodes"]),
            mirror_ratio=float(settings["mirror_ratio"]),
        )


def _stratified_counts(worker_count, ratios):
    raw = {key: worker_count * value for key, value in ratios.items()}
    counts = {key: int(value) for key, value in raw.items()}
    remaining = worker_count - sum(counts.values())
    order = sorted(ratios, key=lambda key: (raw[key] - counts[key], ratios[key]), reverse=True)
    for key in order[:remaining]:
        counts[key] += 1
    return counts


def selfplay_payloads(model, pool, worker_count, rng, current_ratio):
    heuristic_ratio = float(settings["selfplay_heuristic_ratio"])
    random_ratio = float(settings["selfplay_random_ratio"])
    history_ratio = 1.0 - float(current_ratio) - heuristic_ratio - random_ratio
    if min(float(current_ratio), heuristic_ratio, random_ratio, history_ratio) < 0:
        raise ValueError("self-play 的 current/history/heuristic/random 比例之和必须为 1")
    ratios = {
        "current": float(current_ratio), "history": history_ratio,
        "heuristic": heuristic_ratio, "random": random_ratio,
    }
    if not pool.entries:
        ratios["current"] += ratios["history"]
        ratios["history"] = 0.0
    counts = _stratified_counts(worker_count, ratios)
    current_state = {key: value.detach().cpu() for key, value in model.state_dict().items()}
    payloads = []
    payloads.extend({"id": "current", "kind": "model", "model": current_state} for _ in range(counts["current"]))
    for _ in range(counts["history"]):
        entry = pool.sample(rng)
        state = pool.load(entry, device="cpu")
        base.CheckpointManager.validate_schema(
            state, observation_schema=OBSERVATION_SCHEMA,
            observation_size=OBSERVATION_SIZE, action_size=SanguoEnv.action_size,
            model_schema=MODEL_SCHEMA,
        )
        payloads.append({"id": entry["id"], "kind": "model", "model": state["model"]})
    payloads.extend({"id": "heuristic", "kind": "heuristic"} for _ in range(counts["heuristic"]))
    payloads.extend({"id": "random", "kind": "random"} for _ in range(counts["random"]))
    rng.shuffle(payloads)
    return payloads


def rollout_metrics_from_fragments(fragments, tracker=None):
    metrics = _base_rollout_metrics(fragments, tracker=tracker)
    summaries = [summary for fragment in fragments for summary in fragment.episode_summaries]
    denominator = max(1, len(summaries))
    for opponent_id in ("heuristic", "random"):
        selected = [summary for summary in summaries if summary.opponent_id == opponent_id]
        metrics[f"{opponent_id}_opponent_ratio"] = len(selected) / denominator
        metrics[f"vs_{opponent_id}_win_rate"] = sum(item.outcome == "win" for item in selected) / max(1, len(selected))
    return metrics


def evaluate(model, device, opponent, **kwargs):
    kwargs["env_config"] = dict(kwargs.get("env_config") or {})
    kwargs["env_config"]["reward_config"] = _reward_config(kwargs["env_config"].get("reward_config"))
    primary = evaluate_v3(model, device, opponent, **kwargs)
    mirror_episodes = int(settings["eval_mirror_episodes"])
    if mirror_episodes > 0:
        mirror_kwargs = dict(kwargs)
        mirror_kwargs["episodes"] = mirror_episodes
        mirror_kwargs["seed_base"] = int(kwargs.get("seed_base", 20260800)) + 500000
        mirror_kwargs["reset_options"] = {"mirror": True}
        mirror = evaluate_v3(model, device, opponent, **mirror_kwargs)
        for key, value in mirror.items():
            if isinstance(value, (int, float)):
                primary[f"mirror_{key}"] = value
    return primary


def main():
    base.ActorCritic = ActorCritic
    base.MODEL_SCHEMA = MODEL_SCHEMA
    base.SanguoEnv = SanguoEnv
    base.SyncRolloutCoordinator = SyncRolloutCoordinator
    base.ppo_update = ppo_update
    base.load_yaml_defaults = load_yaml_defaults
    base.selfplay_payloads = selfplay_payloads
    base.rollout_metrics_from_fragments = rollout_metrics_from_fragments
    base.evaluate = evaluate
    base.main()


if __name__ == "__main__":
    main()
