"""支持固定/镜像阵容的 v3 策略评估。"""
from __future__ import annotations

import time

from src.rl.env_v3 import SanguoEnv
from src.rl.evaluation.strength import GeneralStrengthTracker
from src.rl.policy import TorchPolicy


def evaluate(model, device, opponent, *, episodes=64, seed_base=20260800,
             max_steps_per_episode=4096, max_seconds=300, policy=None,
             env_config=None, reset_options=None):
    policy = policy or TorchPolicy(model, device=device, deterministic=True)
    tracker = GeneralStrengthTracker()
    wins = losses = draws = timeouts = 0
    turns, steps = [], []
    size_groups = {}
    deadline = time.monotonic() + max_seconds
    reset_options = dict(reset_options or {})

    for offset in range(episodes):
        if time.monotonic() >= deadline:
            timeouts += episodes - offset
            draws += episodes - offset
            break
        env = SanguoEnv(opponent, **(env_config or {}))
        observation, info = env.reset(seed_base + offset, **reset_options)
        done = False
        count = 0
        damage = {}
        while not done and count < max_steps_per_episode and time.monotonic() < deadline:
            action = policy.select_action(observation, info["action_mask"], env.rng)
            observation, _, done, info = env.step(action)
            result = info.get("result") or {}
            source_id = result.get("attacker_id", result.get("caster_id"))
            if result.get("success") and source_id is not None:
                damage[source_id] = damage.get(source_id, 0.0) + result.get("damage", 0.0)
            count += 1
        timed_out = not done
        won = False
        if timed_out:
            timeouts += 1
            draws += 1
            tracker.record_episode(env.learning_team, env.enemy_team, "", damage)
        else:
            winner = env.battle_system._determine_winner()
            if env.battle_system.turn_count >= env.battle_system.max_turns:
                draws += 1
            elif winner == env.learning_team.team_name:
                wins += 1
                won = True
            else:
                losses += 1
            tracker.record_episode(env.learning_team, env.enemy_team, winner, damage)
        matchup = f"{len(env.learning_team.generals)}v{len(env.enemy_team.generals)}"
        group = size_groups.setdefault(matchup, {"episodes": 0, "wins": 0, "timeouts": 0})
        group["episodes"] += 1
        group["wins"] += int(won)
        group["timeouts"] += int(timed_out)
        turns.append(env.battle_system.turn_count)
        steps.append(count)
    completed = len(steps)
    return {
        "win_rate": wins / episodes,
        "loss_rate": losses / episodes,
        "draw_rate": draws / episodes,
        "timeout_rate": timeouts / episodes,
        "mean_turns": sum(turns) / max(1, completed),
        "mean_steps": sum(steps) / max(1, completed),
        "evaluated_episodes": completed,
        "general": tracker.snapshot(),
        "balance": tracker.balance_metrics(),
        "roster_size_matrix": {
            matchup: {
                "episodes": group["episodes"],
                "win_rate": group["wins"] / group["episodes"],
                "timeout_rate": group["timeouts"] / group["episodes"],
            }
            for matchup, group in size_groups.items()
        },
    }
