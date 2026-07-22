"""评估随机或已训练策略对战离线基线。"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.rl.env import SanguoEnv
from src.rl.opponents import HeuristicOpponent, RandomOpponent
from src.rl.policy import RandomPolicy, TorchPolicy
from src.rl.observation import OBSERVATION_SCHEMA, OBSERVATION_SIZE
from src.rl.training.checkpoint import CheckpointManager


def load_policy(checkpoint, device):
    if not checkpoint:
        return RandomPolicy()
    try:
        import torch
    except ImportError as error:
        raise SystemExit("加载 checkpoint 需要 PyTorch：pip install torch") from error
    from src.rl.models.actor_critic import ActorCritic, MODEL_SCHEMA
    state = torch.load(checkpoint, map_location=device)
    CheckpointManager.validate_schema(
        state, observation_schema=OBSERVATION_SCHEMA,
        observation_size=OBSERVATION_SIZE, action_size=SanguoEnv.action_size,
        model_schema=MODEL_SCHEMA,
    )
    model = ActorCritic(OBSERVATION_SIZE, SanguoEnv.action_size)
    model.load_state_dict(state["model"])
    model.eval()
    return TorchPolicy(model, device=device)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint")
    parser.add_argument("--opponent", choices=("random", "heuristic"), default="random")
    parser.add_argument("--episodes", type=int, default=50)
    parser.add_argument("--seed-base", type=int, default=20260720)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    opponent = RandomOpponent() if args.opponent == "random" else HeuristicOpponent()
    policy = load_policy(args.checkpoint, args.device)
    wins = losses = draws = 0
    turns = []
    for offset in range(args.episodes):
        env = SanguoEnv(opponent)
        observation, info = env.reset(args.seed_base + offset)
        done = False
        while not done:
            action = policy.select_action(observation, info["action_mask"], env.rng)
            observation, _, done, info = env.step(action)
        outcome = env.rules.outcome()
        if outcome.timeout:
            draws += 1
        elif outcome.winner == env.learning_team.team_name:
            wins += 1
        else:
            losses += 1
        turns.append(env.battle_system.turn_count)
    print({"episodes": args.episodes, "wins": wins, "losses": losses, "draws": draws, "mean_turns": round(sum(turns) / len(turns), 2)})


if __name__ == "__main__":
    main()
