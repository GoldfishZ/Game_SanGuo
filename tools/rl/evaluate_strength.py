"""生成 checkpoint 在随机实战或受控镜像条件下的武将强度报告。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import torch

from src.game_data.generals_data import GENERALS_DATA
from src.rl.env import SanguoEnv
from src.rl.evaluation.strength import GeneralStrengthTracker
from src.rl.models.actor_critic import ActorCritic
from src.rl.observation import OBSERVATION_SIZE
from src.rl.opponents import HeuristicOpponent
from src.rl.policy import TorchPolicy


def play(env, policy, seed, *, mirror=False):
    observation, info = env.reset(seed, mirror=mirror)
    done = False
    damage = {}
    while not done:
        action = policy.select_action(observation, info["action_mask"], env.rng)
        observation, _, done, info = env.step(action)
        result = info.get("result") or {}
        if result.get("attacker_id") is not None:
            damage[result["attacker_id"]] = damage.get(result["attacker_id"], 0.0) + result.get("damage", 0.0)
    return env.learning_team, env.enemy_team, env.battle_system._determine_winner(), damage


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--mode", choices=("practical", "mirror"), default="practical")
    parser.add_argument("--episodes", type=int, default=500)
    parser.add_argument("--seed-base", type=int, default=20260900)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--out", default="artifacts/rl/character_strength/strength.json")
    args = parser.parse_args()
    state = torch.load(args.checkpoint, map_location=args.device)
    model = ActorCritic(OBSERVATION_SIZE, SanguoEnv.action_size).to(args.device)
    model.load_state_dict(state["model"])
    model.eval()
    policy = TorchPolicy(model, args.device, deterministic=True)
    tracker = GeneralStrengthTracker()
    for offset in range(args.episodes):
        env = SanguoEnv(HeuristicOpponent())
        learning, enemy, winner, damage = play(env, policy, args.seed_base + offset, mirror=args.mode == "mirror")
        tracker.record_episode(learning, enemy, winner, damage)
    report = {"mode": args.mode, "episodes": args.episodes, "general": tracker.snapshot(), "balance": tracker.balance_metrics()}
    output = ROOT / args.out
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["balance"], ensure_ascii=False, indent=2))
    for name, stat in list(report["general"].items())[:10]:
        print(f"{name}: strength={stat['practical_strength']:+.3f}, samples={stat['appearances']}")


if __name__ == "__main__":
    main()
