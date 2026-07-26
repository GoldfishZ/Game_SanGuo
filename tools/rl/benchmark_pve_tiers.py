"""Benchmark the deployed PvE difficulty tiers on identical battle seeds."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import torch

from src.rl.opponents import HeuristicOpponent
from src.rl.pve import PVEController, PVE_DIFFICULTIES
from src.rl.training.evaluation_v3 import evaluate


class DeployedPVEPolicy:
    """Adapter that evaluates the exact action rule used by the Web controller."""

    def __init__(self, controller):
        self.controller = controller

    def select_action(self, observation, action_mask, rng=None):
        action = self.controller.choose_battle_action(observation, action_mask)
        if action is None:
            raise RuntimeError(
                f"{self.controller.difficulty} 战斗模型不可用: "
                + "; ".join(self.controller.load_errors)
            )
        return action


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=500)
    parser.add_argument("--seed-base", type=int, default=2026072500)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--max-seconds-per-tier", type=int, default=1800)
    parser.add_argument(
        "--tiers", nargs="+", choices=PVE_DIFFICULTIES, default=list(PVE_DIFFICULTIES),
    )
    parser.add_argument(
        "--normal-temperature", type=float,
        help="用于校准普通档；省略时评测正式部署设置",
    )
    parser.add_argument(
        "--normal-mistake-rate", type=float,
        help="用于校准普通档；省略时评测正式部署设置",
    )
    parser.add_argument(
        "--out", default="artifacts/rl/pve_tiers/benchmark/deployed_tiers.json",
    )
    args = parser.parse_args()

    reports = {}
    for index, difficulty in enumerate(args.tiers):
        # Keep the easy tier's stochastic policy reproducible across benchmark runs.
        torch.manual_seed(args.seed_base + index)
        controller = PVEController(
            difficulty=difficulty,
            device=args.device,
            battle_temperature=(
                args.normal_temperature
                if difficulty == "normal" and args.normal_temperature is not None
                else None
            ),
            mistake_rate=(
                args.normal_mistake_rate
                if difficulty == "normal" and args.normal_mistake_rate is not None
                else None
            ),
        )
        report = evaluate(
            controller.load().battle_model,
            args.device,
            HeuristicOpponent(),
            episodes=args.episodes,
            seed_base=args.seed_base,
            max_seconds=args.max_seconds_per_tier,
            policy=DeployedPVEPolicy(controller),
        )
        reports[difficulty] = report
        print(
            difficulty,
            {
                key: report[key]
                for key in (
                    "win_rate", "loss_rate", "draw_rate", "timeout_rate",
                    "mean_turns", "evaluated_episodes",
                )
            },
            flush=True,
        )

    output = ROOT / args.out
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "schema": "sanguo-pve-tier-benchmark-v1",
                "episodes": args.episodes,
                "seed_base": args.seed_base,
                "opponent": "heuristic",
                "tiers": reports,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"报告已写入: {output}")


if __name__ == "__main__":
    main()
