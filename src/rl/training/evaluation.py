"""固定 seed 的策略评估。"""
from __future__ import annotations

from src.rl.env import SanguoEnv
from src.rl.evaluation.strength import GeneralStrengthTracker
from src.rl.policy import TorchPolicy


def evaluate(model, device, opponent, *, episodes=64, seed_base=20260800):
    policy = TorchPolicy(model, device=device, deterministic=True)
    tracker = GeneralStrengthTracker()
    wins = losses = draws = 0
    turns = []
    steps = []
    for offset in range(episodes):
        env = SanguoEnv(opponent)
        observation, info = env.reset(seed_base + offset)
        done = False
        count = 0
        damage = {}
        while not done:
            action = policy.select_action(observation, info["action_mask"], env.rng)
            observation, _, done, info = env.step(action)
            result = info.get("result") or {}
            if result.get("success") and result.get("attacker_id") is not None:
                damage[result["attacker_id"]] = damage.get(result["attacker_id"], 0.0) + result.get("damage", 0.0)
            count += 1
        winner = env.battle_system._determine_winner()
        if env.battle_system.turn_count >= env.battle_system.max_turns:
            draws += 1
        elif winner == env.learning_team.team_name:
            wins += 1
        else:
            losses += 1
        tracker.record_episode(env.learning_team, env.enemy_team, winner, damage)
        turns.append(env.battle_system.turn_count)
        steps.append(count)
    return {
        "win_rate": wins / episodes,
        "loss_rate": losses / episodes,
        "draw_rate": draws / episodes,
        "mean_turns": sum(turns) / episodes,
        "mean_steps": sum(steps) / episodes,
        "general": tracker.snapshot(),
        "balance": tracker.balance_metrics(),
    }
