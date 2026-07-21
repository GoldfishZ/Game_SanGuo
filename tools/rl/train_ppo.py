"""可观测、有限预算的本地 PPO 训练入口。"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np

from src.rl.env import SanguoEnv
from src.rl.evaluation.strength import GeneralStrengthTracker
from src.rl.models.actor_critic import ActorCritic
from src.rl.observation import OBSERVATION_SIZE
from src.rl.opponents import HeuristicOpponent, RandomOpponent
from src.rl.training.checkpoint import CheckpointManager
from src.rl.training.early_stop import ConvergenceTracker
from src.rl.training.evaluation import evaluate
from src.rl.training.gae import compute_gae
from src.rl.training.logging import TrainLogger
from src.rl.training.ppo import ppo_update
from src.rl.training.runtime import detect_runtime
from src.rl.training.vector_env import SyncRolloutCoordinator


def batch_from_fragments(fragments):
    """分别计算截断 fragment 的 GAE，再拼接为 learner batch。"""
    merged = {key: [] for key in ("observations", "masks", "actions", "log_probs", "advantages", "returns")}
    for fragment in fragments:
        advantages, returns = compute_gae(
            fragment.rewards, fragment.values, fragment.dones, fragment.bootstrap_value,
        )
        for key in ("observations", "masks", "actions", "log_probs"):
            merged[key].append(getattr(fragment, key))
        merged["advantages"].append(advantages)
        merged["returns"].append(returns)
    return {key: np.concatenate(values) for key, values in merged.items()}


def rollout_metrics_from_fragments(fragments, tracker=None):
    """汇总 worker 的已完成 episode；截断 episode 只参与 GAE，不进入胜负统计。"""
    summaries = [summary for fragment in fragments for summary in fragment.episode_summaries]
    total_steps = sum(len(fragment.actions) for fragment in fragments)
    episodes = len(summaries)
    wins = sum(summary.outcome == "win" for summary in summaries)
    losses = sum(summary.outcome == "loss" for summary in summaries)
    draws = sum(summary.outcome == "draw" for summary in summaries)
    action_counts = {
        kind: sum(summary.action_counts.get(kind, 0) for summary in summaries)
        for kind in ("skill", "attack", "end")
    }
    if tracker:
        for summary in summaries:
            tracker.record_episode_from_summary(summary)
    denominator = max(1, episodes)
    return {
        "episodes": episodes,
        "worker_count": len(fragments),
        "win_rate": wins / denominator,
        "loss_rate": losses / denominator,
        "draw_rate": draws / denominator,
        "timeout_rate": sum(summary.timeout for summary in summaries) / denominator,
        "mean_turns": sum(summary.turns for summary in summaries) / denominator,
        "mean_episode_steps": sum(summary.steps for summary in summaries) / denominator,
        "mean_episode_reward": sum(summary.episode_reward for summary in summaries) / denominator,
        "no_progress_rate": sum(summary.no_progress_count for summary in summaries) / max(1, total_steps),
        **{f"action_{kind}_ratio": count / max(1, total_steps) for kind, count in action_counts.items()},
    }


def linear_schedule(initial, final, progress):
    """线性退火，并确保超出 horizon 后保持最终值。"""
    return initial + (final - initial) * min(1.0, max(0.0, progress))




def make_opponent(stage):
    return RandomOpponent() if stage == "random" else HeuristicOpponent()


def collect_rollout(env, model, device, rollout_steps, seed_base, tracker):
    observation, info = env.reset(seed_base)
    trajectory = {key: [] for key in ("observations", "masks", "actions", "log_probs", "rewards", "values", "dones")}
    episode_reward = episode_steps = 0
    episodes = wins = losses = draws = 0
    actions = {"skill": 0, "attack": 0, "end": 0}
    damage = {}
    for index in range(rollout_steps):
        import torch
        obs_tensor = torch.as_tensor(observation, dtype=torch.float32, device=device).unsqueeze(0)
        mask_tensor = torch.as_tensor(info["action_mask"], dtype=torch.bool, device=device).unsqueeze(0)
        with torch.no_grad():
            logits, value = model(obs_tensor, mask_tensor)
            distribution = torch.distributions.Categorical(logits=logits)
            action = int(distribution.sample().item())
            log_prob = float(distribution.log_prob(torch.tensor(action, device=device)).item())
        decoded = env.decode_action(action)
        if decoded.kind.startswith("skill"):
            actions["skill"] += 1
        elif decoded.kind == "attack":
            actions["attack"] += 1
        else:
            actions["end"] += 1
        next_observation, reward, done, next_info = env.step(action)
        trajectory["observations"].append(observation)
        trajectory["masks"].append(info["action_mask"])
        trajectory["actions"].append(action)
        trajectory["log_probs"].append(log_prob)
        trajectory["rewards"].append(reward)
        trajectory["values"].append(float(value.item()))
        trajectory["dones"].append(done)
        episode_reward += reward
        episode_steps += 1
        result = next_info.get("result") or {}
        if result.get("attacker_id") is not None:
            damage[result["attacker_id"]] = damage.get(result["attacker_id"], 0.0) + result.get("damage", 0.0)
        observation, info = next_observation, next_info
        if done:
            episodes += 1
            winner = env.battle_system._determine_winner()
            if env.battle_system.turn_count >= env.battle_system.max_turns:
                draws += 1
            elif winner == env.learning_team.team_name:
                wins += 1
            else:
                losses += 1
            tracker.record_episode(env.learning_team, env.enemy_team, winner, damage)
            observation, info = env.reset(seed_base + index + 1)
            episode_reward = episode_steps = 0
            damage = {}
    import torch
    with torch.no_grad():
        obs_tensor = torch.as_tensor(observation, dtype=torch.float32, device=device).unsqueeze(0)
        mask_tensor = torch.as_tensor(info["action_mask"], dtype=torch.bool, device=device).unsqueeze(0)
        _, bootstrap = model(obs_tensor, mask_tensor)
    advantages, returns = compute_gae(trajectory["rewards"], trajectory["values"], trajectory["dones"], float(bootstrap.item()))
    batch = {key: np.asarray(value) for key, value in trajectory.items() if key not in ("rewards", "values", "dones")}
    batch.update({"advantages": advantages, "returns": returns})
    rollout = {"episodes": episodes, "win_rate": wins / max(1, episodes), "loss_rate": losses / max(1, episodes), "draw_rate": draws / max(1, episodes), **{f"action_{key}_ratio": value / rollout_steps for key, value in actions.items()}}
    return batch, rollout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("random", "heuristic"), default="random")
    parser.add_argument("--seed", type=int, default=20260720)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--num-workers", default="auto", help="当前版本记录建议值；多 worker coordinator 后续启用")
    parser.add_argument("--rollout-steps", default="auto")
    parser.add_argument("--minibatch-size", default="auto")
    parser.add_argument("--max-updates", type=int, default=5000, help="学习率/探索系数退火周期；不是停止上限，0 表示不退火")
    parser.add_argument("--max-wallclock-minutes", type=float, default=0, help="可选硬保险；0 表示不限制")
    parser.add_argument("--eval-every", type=int, default=20)
    parser.add_argument("--eval-episodes", type=int, default=64)
    parser.add_argument("--eval-max-steps", type=int, default=4096)
    parser.add_argument("--eval-max-seconds", type=float, default=300)
    parser.add_argument("--checkpoint-every", type=int, default=20)
    parser.add_argument("--keep-last", type=int, default=5)
    parser.add_argument("--target-winrate", type=float, default=0.85)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--min-delta", type=float, default=0.01)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--learning-rate-final", type=float, default=1e-4)
    parser.add_argument("--entropy-coef", type=float, default=0.05)
    parser.add_argument("--entropy-coef-final", type=float, default=0.01)
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--target-kl", type=float, default=0.015)
    parser.add_argument("--run-name")
    parser.add_argument("--resume")
    args = parser.parse_args()
    import torch

    profile = detect_runtime(args.device, args.num_workers, args.rollout_steps, args.minibatch_size)
    torch.manual_seed(args.seed)
    model = ActorCritic(OBSERVATION_SIZE, SanguoEnv.action_size).to(profile.device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)
    manager = CheckpointManager(keep_last=args.keep_last)
    start_update = 0
    if args.resume:
        state = manager.load(args.resume, profile.device)
        model.load_state_dict(state["model"])
        optimizer.load_state_dict(state["optimizer"])
        start_update = state.get("update", 0)
    config = vars(args) | {"runtime": profile.to_dict()}
    logger = TrainLogger(run_name=args.run_name, config=config)
    tracker = GeneralStrengthTracker()
    convergence = ConvergenceTracker(args.min_delta)
    if args.resume:
        convergence.best_win_rate = state.get("best_win_rate", float("-inf"))
        convergence.best_quality_score = state.get("best_quality_score", convergence.best_win_rate)
    final_lr = args.learning_rate_final if args.learning_rate_final is not None else args.learning_rate
    final_entropy = args.entropy_coef_final if args.entropy_coef_final is not None else args.entropy_coef
    env = SanguoEnv(make_opponent(args.stage))
    coordinator = SyncRolloutCoordinator(profile.num_workers, args.stage) if profile.num_workers > 1 else None
    started = time.monotonic()
    try:
        update = start_update
        while True:
            update += 1
            if coordinator:
                fragments = coordinator.collect(model, profile.rollout_steps, args.seed + update * 100000)
                batch = batch_from_fragments(fragments)
                rollout = rollout_metrics_from_fragments(fragments, tracker=tracker)
            else:
                batch, rollout = collect_rollout(env, model, profile.device, profile.rollout_steps, args.seed + update * 100000, tracker)
            elapsed = time.monotonic() - started
            progress = 0.0 if args.max_updates <= 0 else min(1.0, update / args.max_updates)
            scheduled_lr = linear_schedule(args.learning_rate, final_lr, progress)
            scheduled_entropy = linear_schedule(args.entropy_coef, final_entropy, progress)
            for group in optimizer.param_groups:
                group["lr"] = scheduled_lr
            metrics = ppo_update(
                model, optimizer, batch, epochs=args.epochs,
                minibatch_size=profile.minibatch_size, target_kl=args.target_kl,
                entropy_coef=scheduled_entropy, device=profile.device,
            )
            metrics["entropy_coefficient"] = scheduled_entropy
            metrics.update({"rollout_steps": profile.rollout_steps, "fps": profile.rollout_steps / max(elapsed, 1e-6), "wallclock_minutes": elapsed / 60})
            logger.log(update, metrics, "train")
            logger.log(update, rollout, "rollout")
            for name, stat in tracker.snapshot().items():
                logger.log(update, stat, f"general/{name}")
            logger.log(update, tracker.balance_metrics(), "balance")
            should_checkpoint = update % args.checkpoint_every == 0
            is_best = False
            stop_reason = None
            if update % args.eval_every == 0:
                validation = evaluate(
                    model, profile.device, HeuristicOpponent(),
                    episodes=args.eval_episodes,
                    max_steps_per_episode=args.eval_max_steps,
                    max_seconds=args.eval_max_seconds,
                )
                logger.log(update, {key: value for key, value in validation.items() if isinstance(value, (int, float))}, "eval/heuristic")
                logger.log(update, validation["balance"], "eval_balance")
                is_best, quality_score = convergence.update(
                    validation["win_rate"], validation["timeout_rate"],
                )
                logger.log(update, {"quality_score": quality_score, "best_quality_score": convergence.best_quality_score}, "eval/heuristic")
                stop_reason = None
            state = {
                "model": model.state_dict(), "optimizer": optimizer.state_dict(),
                "update": update, "config": config,
                "best_win_rate": convergence.best_win_rate,
                "best_quality_score": convergence.best_quality_score,
            }
            if should_checkpoint or is_best:
                manager.save(state, update, is_best=is_best)
            if args.max_wallclock_minutes and elapsed >= args.max_wallclock_minutes * 60:
                manager.save(state, update)
                print("训练停止：max_wallclock_minutes")
                break
    except KeyboardInterrupt:
        manager.save({"model": model.state_dict(), "optimizer": optimizer.state_dict(), "config": config}, start_update)
        print("训练已中断，已保存 latest checkpoint")
    finally:
        if coordinator:
            coordinator.close()
        logger.close()


if __name__ == "__main__":
    main()
