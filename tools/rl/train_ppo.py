"""可观测、有限预算的本地 PPO 训练入口。"""
from __future__ import annotations

import argparse
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np

from src.rl.env import SanguoEnv
from src.rl import actions as action_codec
from src.rl.evaluation.strength import GeneralStrengthTracker
from src.rl.models.actor_critic import ActorCritic, MODEL_SCHEMA
from src.rl.observation import OBSERVATION_SCHEMA, OBSERVATION_SIZE
from src.rl.opponents import HeuristicOpponent, RandomOpponent
from src.rl.training.checkpoint import CheckpointManager
from src.rl.training.early_stop import ConvergenceTracker
from src.rl.training.evaluation import evaluate
from src.rl.training.gae import compute_gae
from src.rl.training.logging import TrainLogger
from src.rl.training.ppo import ppo_update
from src.rl.training.runtime import detect_runtime
from src.rl.training.self_play import HistoricalPolicyPool
from src.rl.training.vector_env import SyncRolloutCoordinator


def batch_from_fragments(fragments, gamma=0.99, gae_lambda=0.95):
    """分别计算截断 fragment 的 GAE，再拼接为 learner batch。"""
    merged = {key: [] for key in ("observations", "masks", "actions", "log_probs", "advantages", "returns")}
    for fragment in fragments:
        advantages, returns = compute_gae(
            fragment.rewards, fragment.values, fragment.dones, fragment.bootstrap_value,
            gamma=gamma, gae_lambda=gae_lambda,
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
    action_ids = np.concatenate([fragment.actions for fragment in fragments])
    action_counts = {
        "end": int(np.count_nonzero(action_ids < action_codec.SKILL_BASE)),
        "skill": int(np.count_nonzero(
            (action_ids >= action_codec.SKILL_BASE) & (action_ids < action_codec.ATTACK_BASE)
        )),
        "attack": int(np.count_nonzero(action_ids >= action_codec.ATTACK_BASE)),
    }
    reported_no_progress = sum(
        int(np.count_nonzero(fragment.no_progresses))
        if fragment.no_progresses is not None else 0
        for fragment in fragments
    )
    if not any(fragment.no_progresses is not None for fragment in fragments):
        reported_no_progress = sum(summary.no_progress_count for summary in summaries)
    if tracker:
        for summary in summaries:
            tracker.record_episode_from_summary(summary)
    denominator = max(1, episodes)
    size_metrics = {
        "mean_learning_roster_size": sum(len(item.roster_self) for item in summaries) / denominator,
        "mean_enemy_roster_size": sum(len(item.roster_enemy) for item in summaries) / denominator,
    }
    size_groups = {}
    for summary in summaries:
        matchup = f"{len(summary.roster_self)}v{len(summary.roster_enemy)}"
        group = size_groups.setdefault(matchup, {"episodes": 0, "wins": 0})
        group["episodes"] += 1
        group["wins"] += int(summary.outcome == "win")
    for matchup, group in size_groups.items():
        size_metrics[f"roster_{matchup}_episodes"] = group["episodes"]
        size_metrics[f"roster_{matchup}_win_rate"] = group["wins"] / group["episodes"]
    current = [summary for summary in summaries if summary.opponent_id == "current"]
    historical = [summary for summary in summaries if summary.opponent_id.startswith("history-")]
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
        "no_progress_rate": reported_no_progress / max(1, total_steps),
        "current_opponent_ratio": len(current) / denominator,
        "historical_opponent_ratio": len(historical) / denominator,
        "vs_current_win_rate": sum(item.outcome == "win" for item in current) / max(1, len(current)),
        "vs_history_win_rate": sum(item.outcome == "win" for item in historical) / max(1, len(historical)),
        **{f"action_{kind}_ratio": count / max(1, total_steps) for kind, count in action_counts.items()},
        **size_metrics,
    }


def linear_schedule(initial, final, progress):
    """线性退火，并确保超出 horizon 后保持最终值。"""
    return initial + (final - initial) * min(1.0, max(0.0, progress))




def make_opponent(stage):
    return RandomOpponent() if stage == "random" else HeuristicOpponent()


def load_yaml_defaults(path):
    if not path:
        return {}
    import yaml
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"训练配置不存在: {config_path}")
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("训练 YAML 顶层必须是键值映射")
    return {str(key).replace("-", "_"): value for key, value in data.items()}


def selfplay_payloads(model, pool, worker_count, rng, current_ratio):
    current_state = {key: value.detach().cpu() for key, value in model.state_dict().items()}
    payloads = []
    for _ in range(worker_count):
        entry = None if rng.random() < current_ratio else pool.sample(rng)
        if entry is None:
            payloads.append({"id": "current", "model": current_state})
        else:
            state = pool.load(entry, device="cpu")
            CheckpointManager.validate_schema(
                state,
                observation_schema=OBSERVATION_SCHEMA,
                observation_size=OBSERVATION_SIZE,
                action_size=SanguoEnv.action_size,
                model_schema=MODEL_SCHEMA,
            )
            payloads.append({"id": entry["id"], "model": state["model"]})
    return payloads


def collect_rollout(env, model, device, rollout_steps, seed_base, tracker,
                    gamma=0.99, gae_lambda=0.95):
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
        source_id = result.get("attacker_id", result.get("caster_id"))
        if source_id is not None:
            damage[source_id] = damage.get(source_id, 0.0) + result.get("damage", 0.0)
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
    advantages, returns = compute_gae(
        trajectory["rewards"], trajectory["values"], trajectory["dones"],
        float(bootstrap.item()), gamma=gamma, gae_lambda=gae_lambda,
    )
    batch = {key: np.asarray(value) for key, value in trajectory.items() if key not in ("rewards", "values", "dones")}
    batch.update({"advantages": advantages, "returns": returns})
    rollout = {"episodes": episodes, "win_rate": wins / max(1, episodes), "loss_rate": losses / max(1, episodes), "draw_rate": draws / max(1, episodes), **{f"action_{key}_ratio": value / rollout_steps for key, value in actions.items()}}
    return batch, rollout


def main():
    bootstrap = argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument("--config", default="tools/rl/configs/ppo_default.yaml")
    known, _ = bootstrap.parse_known_args()
    yaml_defaults = load_yaml_defaults(known.config)
    parser = argparse.ArgumentParser(parents=[bootstrap])
    parser.add_argument("--stage", choices=("random", "heuristic", "selfplay"), default="random")
    parser.add_argument("--seed", type=int, default=20260720)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--num-workers", default="auto", help="同步 rollout worker 数；auto 按 CPU/GPU 配置选择")
    parser.add_argument("--rollout-steps", default="auto")
    parser.add_argument("--minibatch-size", default="auto")
    parser.add_argument("--max-updates", type=int, default=5000, help="训练 update 硬上限；0 表示不限制")
    parser.add_argument("--schedule-updates", type=int, default=5000, help="学习率/探索系数退火周期；0 表示不退火")
    parser.add_argument("--max-wallclock-minutes", type=float, default=0, help="可选硬保险；0 表示不限制")
    parser.add_argument("--eval-every", type=int, default=20)
    parser.add_argument("--eval-episodes", type=int, default=64)
    parser.add_argument("--eval-max-steps", type=int, default=4096)
    parser.add_argument("--eval-max-seconds", type=float, default=300)
    parser.add_argument("--checkpoint-every", type=int, default=20)
    parser.add_argument("--keep-last", type=int, default=5)
    parser.add_argument("--min-delta", type=float, default=0.01)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--learning-rate-final", type=float, default=1e-4)
    parser.add_argument("--entropy-coef", type=float, default=0.05)
    parser.add_argument("--entropy-coef-final", type=float, default=0.01)
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--target-kl", type=float, default=0.015)
    parser.add_argument("--gamma", type=float, default=0.99)
    parser.add_argument("--gae-lambda", type=float, default=0.95)
    parser.add_argument("--clip-ratio", type=float, default=0.2)
    parser.add_argument("--value-coef", type=float, default=0.5)
    parser.add_argument("--grad-clip", type=float, default=0.5)
    parser.add_argument("--team-size", type=int, default=3,
                        help="固定阵容人数；0 表示按费用规则启用多阵容采样")
    parser.add_argument("--min-team-size", type=int, default=1)
    parser.add_argument("--max-team-size", type=int, default=8)
    parser.add_argument("--team-size-power", type=float, default=0.0,
                        help="多阵容采样权重 size**power；正值提高大阵容频率")
    parser.add_argument("--roster-candidate-samples", type=int, default=256)
    parser.add_argument("--roster-cost-bias", type=float, default=0.75,
                        help="0=全候选均匀，1=优先接近费用上限")
    parser.add_argument("--cost-limit", type=float, default=8.0)
    parser.add_argument("--max-turns", type=int, default=200)
    parser.add_argument("--reward-hp-delta", type=float, default=0.05)
    parser.add_argument("--reward-kill", type=float, default=0.15)
    parser.add_argument("--reward-action-success", type=float, default=0.01)
    parser.add_argument("--reward-no-progress", type=float, default=-0.02)
    parser.add_argument("--reward-win", type=float, default=1.0)
    parser.add_argument("--reward-lose", type=float, default=-1.0)
    parser.add_argument("--reward-draw", type=float, default=0.0)
    parser.add_argument("--run-name")
    parser.add_argument("--resume")
    parser.add_argument("--artifact-root", default="artifacts/rl")
    parser.add_argument("--selfplay-current-ratio", type=float, default=0.5)
    parser.add_argument("--selfplay-pool-size", type=int, default=24)
    parser.add_argument("--selfplay-top-k", type=int, default=8)
    parser.add_argument("--selfplay-temperature", type=float, default=0.25)
    parser.add_argument("--selfplay-snapshot-every", type=int, default=20)
    valid_keys = {action.dest for action in parser._actions}
    unknown_keys = sorted(set(yaml_defaults) - valid_keys)
    if unknown_keys:
        parser.error(f"YAML 包含未知参数: {', '.join(unknown_keys)}")
    parser.set_defaults(**yaml_defaults)
    args = parser.parse_args()
    if not 0.0 <= args.selfplay_current_ratio <= 1.0:
        parser.error("selfplay_current_ratio 必须在 0 到 1 之间")
    if args.eval_every <= 0 or args.checkpoint_every <= 0:
        parser.error("eval_every 和 checkpoint_every 必须为正整数")
    if args.team_size < 0:
        parser.error("team_size 不能为负数；使用 0 启用多阵容采样")
    if not 1 <= args.min_team_size <= args.max_team_size <= 12:
        parser.error("多阵容人数范围必须满足 1 <= min_team_size <= max_team_size <= 12")
    if args.roster_candidate_samples <= 0:
        parser.error("roster_candidate_samples 必须为正整数")
    if not 0.0 <= args.roster_cost_bias <= 1.0:
        parser.error("roster_cost_bias 必须在 0 到 1 之间")
    import torch

    profile = detect_runtime(args.device, args.num_workers, args.rollout_steps, args.minibatch_size)
    torch.manual_seed(args.seed)
    model = ActorCritic(OBSERVATION_SIZE, SanguoEnv.action_size).to(profile.device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)
    artifact_root = Path(args.artifact_root)
    manager = CheckpointManager(artifact_root / "checkpoints", keep_last=args.keep_last)
    start_update = 0
    if args.resume:
        state = manager.load(args.resume, profile.device)
        manager.validate_schema(
            state,
            observation_schema=OBSERVATION_SCHEMA,
            observation_size=OBSERVATION_SIZE,
            action_size=SanguoEnv.action_size,
            model_schema=MODEL_SCHEMA,
        )
        model.load_state_dict(state["model"])
        optimizer.load_state_dict(state["optimizer"])
        start_update = state.get("update", 0)
    config = vars(args) | {"runtime": profile.to_dict()}
    logger = TrainLogger(root=artifact_root / "runs", run_name=args.run_name, config=config)
    tracker = GeneralStrengthTracker()
    convergence = ConvergenceTracker(args.min_delta)
    if args.resume:
        convergence.best_win_rate = state.get("best_win_rate", float("-inf"))
        convergence.best_quality_score = state.get("best_quality_score", convergence.best_win_rate)
    final_lr = args.learning_rate_final if args.learning_rate_final is not None else args.learning_rate
    final_entropy = args.entropy_coef_final if args.entropy_coef_final is not None else args.entropy_coef
    reward_config = {
        "hp_delta": args.reward_hp_delta, "kill": args.reward_kill,
        "skill_success": args.reward_action_success,
        "no_progress": args.reward_no_progress,
        "win": args.reward_win, "lose": args.reward_lose, "draw": args.reward_draw,
    }
    env_config = {
        "team_size": args.team_size,
        "min_team_size": args.min_team_size,
        "max_team_size": args.max_team_size,
        "team_size_power": args.team_size_power,
        "roster_candidate_samples": args.roster_candidate_samples,
        "roster_cost_bias": args.roster_cost_bias,
        "cost_limit": args.cost_limit,
        "max_turns": args.max_turns, "reward_config": reward_config,
    }
    env = SanguoEnv(make_opponent(args.stage), **env_config)
    coordinator = SyncRolloutCoordinator(profile.num_workers, args.stage, env_config) if profile.num_workers > 1 or args.stage == "selfplay" else None
    selfplay_pool = None
    selfplay_rng = random.Random(args.seed + 9000000)
    if args.stage == "selfplay":
        selfplay_pool = HistoricalPolicyPool(
            directory=artifact_root / "self_play",
            max_size=args.selfplay_pool_size,
            top_k=args.selfplay_top_k,
            temperature=args.selfplay_temperature,
        )
    started = time.monotonic()
    last_state = None
    try:
        update = start_update
        while args.max_updates <= 0 or update < args.max_updates:
            update += 1
            update_started = time.monotonic()
            summaries = []
            if coordinator:
                payloads = None
                if selfplay_pool:
                    payloads = selfplay_payloads(
                        model, selfplay_pool, profile.num_workers,
                        selfplay_rng, args.selfplay_current_ratio,
                    )
                fragments = coordinator.collect(
                    model, profile.rollout_steps, args.seed + update * 100000,
                    opponent_payloads=payloads,
                )
                batch = batch_from_fragments(fragments, args.gamma, args.gae_lambda)
                summaries = [summary for fragment in fragments for summary in fragment.episode_summaries]
                rollout = rollout_metrics_from_fragments(fragments, tracker=tracker)
            else:
                batch, rollout = collect_rollout(
                    env, model, profile.device, profile.rollout_steps,
                    args.seed + update * 100000, tracker,
                    gamma=args.gamma, gae_lambda=args.gae_lambda,
                )
            elapsed = time.monotonic() - started
            progress = 0.0 if args.schedule_updates <= 0 else min(1.0, update / args.schedule_updates)
            scheduled_lr = linear_schedule(args.learning_rate, final_lr, progress)
            scheduled_entropy = linear_schedule(args.entropy_coef, final_entropy, progress)
            for group in optimizer.param_groups:
                group["lr"] = scheduled_lr
            metrics = ppo_update(
                model, optimizer, batch, epochs=args.epochs,
                minibatch_size=profile.minibatch_size, target_kl=args.target_kl,
                entropy_coef=scheduled_entropy, device=profile.device,
                clip_ratio=args.clip_ratio, value_coef=args.value_coef,
                grad_clip=args.grad_clip,
            )
            metrics["entropy_coefficient"] = scheduled_entropy
            update_elapsed = time.monotonic() - update_started
            metrics.update({"rollout_steps": profile.rollout_steps, "fps": profile.rollout_steps / max(update_elapsed, 1e-6), "wallclock_minutes": elapsed / 60})
            logger.log(update, metrics, "train")
            logger.log(update, rollout, "rollout")
            logger.log_episodes(update, summaries)
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
                    env_config=env_config,
                )
                logger.log(update, {key: value for key, value in validation.items() if isinstance(value, (int, float))}, "eval/heuristic")
                logger.log(update, validation["balance"], "eval_balance")
                for matchup, size_metrics in validation.get("roster_size_matrix", {}).items():
                    logger.log(update, size_metrics, f"eval/roster_size/{matchup}")
                is_best, quality_score = convergence.update(
                    validation["win_rate"], validation["timeout_rate"],
                )
                logger.log(update, {"quality_score": quality_score, "best_quality_score": convergence.best_quality_score}, "eval/heuristic")
                if selfplay_pool and update % args.selfplay_snapshot_every == 0:
                    selfplay_pool.add(
                        model.state_dict(), update=update, score=quality_score,
                        observation_schema=OBSERVATION_SCHEMA,
                        observation_size=OBSERVATION_SIZE,
                        action_size=SanguoEnv.action_size,
                        model_schema=MODEL_SCHEMA,
                    )
                    logger.log(update, selfplay_pool.metrics(), "selfplay")
                stop_reason = None
            state = {
                "model": model.state_dict(), "optimizer": optimizer.state_dict(),
                "update": update, "config": config,
                "best_win_rate": convergence.best_win_rate,
                "best_quality_score": convergence.best_quality_score,
                "observation_schema": OBSERVATION_SCHEMA,
                "observation_size": OBSERVATION_SIZE,
                "action_size": SanguoEnv.action_size,
                "model_schema": MODEL_SCHEMA,
            }
            last_state = state
            if should_checkpoint or is_best:
                manager.save(state, update, is_best=is_best)
            if args.max_wallclock_minutes and elapsed >= args.max_wallclock_minutes * 60:
                manager.save(state, update)
                print("训练停止：max_wallclock_minutes")
                break
            if args.max_updates > 0 and update >= args.max_updates:
                manager.save(state, update)
                print("训练停止：max_updates")
                break
    except KeyboardInterrupt:
        if last_state is None:
            last_state = {
                "model": model.state_dict(), "optimizer": optimizer.state_dict(),
                "update": start_update, "config": config,
                "best_win_rate": convergence.best_win_rate,
                "best_quality_score": convergence.best_quality_score,
                "observation_schema": OBSERVATION_SCHEMA,
                "observation_size": OBSERVATION_SIZE,
                "action_size": SanguoEnv.action_size,
                "model_schema": MODEL_SCHEMA,
            }
        manager.save(last_state, last_state["update"])
        print("训练已中断，已保存 latest checkpoint")
    finally:
        if coordinator:
            coordinator.close()
        logger.close()


if __name__ == "__main__":
    main()
