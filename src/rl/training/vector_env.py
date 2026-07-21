"""Windows spawn-safe synchronous CPU rollout workers for on-policy PPO."""
from __future__ import annotations

from dataclasses import dataclass
import multiprocessing as mp

import numpy as np


@dataclass
class GeneralRecord:
    """终局武将快照，可安全通过 multiprocessing Queue 回传。"""
    general_id: int
    name: str
    hp_fraction: float
    survived: bool


@dataclass
class EpisodeSummary:
    """一个完成 episode 的训练指标与武将归因数据。"""
    outcome: str
    winner_name: str
    timeout: bool
    turns: int
    steps: int
    episode_reward: float
    no_progress_count: int
    action_counts: dict
    damage_by_general_id: dict
    learning_team_name: str
    enemy_team_name: str
    learning_generals: list
    enemy_generals: list


@dataclass
class RolloutFragment:
    observations: np.ndarray
    masks: np.ndarray
    actions: np.ndarray
    log_probs: np.ndarray
    rewards: np.ndarray
    values: np.ndarray
    dones: np.ndarray
    bootstrap_value: float
    episode_summaries: list


def _snapshot_team(team):
    return [
        GeneralRecord(
            general_id=general.general_id,
            name=general.name,
            hp_fraction=general.current_hp / max(1, general.max_hp),
            survived=bool(general.is_alive),
        )
        for general in team.generals
    ]


def _classify_outcome(battle_system, learning_team):
    """与单进程 rollout/evaluation 一致地将终局状态分类。"""
    timeout = battle_system.turn_count >= battle_system.max_turns
    winner = battle_system._determine_winner()
    if timeout:
        return "draw", winner, True
    if winner == learning_team.team_name:
        return "win", winner, False
    return "loss", winner, False


def _make_opponent(stage):
    from src.rl.opponents import HeuristicOpponent, RandomOpponent
    return RandomOpponent() if stage == "random" else HeuristicOpponent()


def _worker_main(command_queue, result_queue, worker_id, stage):
    """Top-level target: required by Windows multiprocessing spawn."""
    import torch
    from src.rl.env import SanguoEnv
    from src.rl.models.actor_critic import ActorCritic
    from src.rl.observation import OBSERVATION_SIZE

    env = SanguoEnv(_make_opponent(stage))
    model = ActorCritic(OBSERVATION_SIZE, env.action_size).cpu()
    while True:
        command = command_queue.get()
        if command is None:
            return
        weights, steps, seed = command
        model.load_state_dict(weights)
        model.eval()
        observation, info = env.reset(seed)
        data = {key: [] for key in ("observations", "masks", "actions", "log_probs", "rewards", "values", "dones")}
        summaries = []
        episode_reward = 0.0
        episode_steps = 0
        no_progress_count = 0
        action_counts = {"skill": 0, "attack": 0, "end": 0}
        damage_by_general_id = {}
        for _ in range(steps):
            obs = torch.as_tensor(observation, dtype=torch.float32).unsqueeze(0)
            mask = torch.as_tensor(info["action_mask"], dtype=torch.bool).unsqueeze(0)
            with torch.no_grad():
                logits, value = model(obs, mask)
                dist = torch.distributions.Categorical(logits=logits)
                action = int(dist.sample().item())
                log_prob = float(dist.log_prob(torch.tensor(action)).item())
            decoded = env.decode_action(action)
            if decoded.kind.startswith("skill"):
                action_counts["skill"] += 1
            elif decoded.kind == "attack":
                action_counts["attack"] += 1
            else:
                action_counts["end"] += 1
            next_observation, reward, done, next_info = env.step(action)
            for key, value_item in (("observations", observation), ("masks", info["action_mask"]), ("actions", action), ("log_probs", log_prob), ("rewards", reward), ("values", float(value.item())), ("dones", done)):
                data[key].append(value_item)
            episode_reward += reward
            episode_steps += 1
            if next_info.get("no_progress"):
                no_progress_count += 1
            result = next_info.get("result") or {}
            if result.get("success") and result.get("attacker_id") is not None:
                general_id = result["attacker_id"]
                damage_by_general_id[general_id] = damage_by_general_id.get(general_id, 0.0) + result.get("damage", 0.0)
            observation, info = next_observation, next_info
            if done:
                outcome, winner_name, timeout = _classify_outcome(env.battle_system, env.learning_team)
                summaries.append(EpisodeSummary(
                    outcome=outcome,
                    winner_name=winner_name,
                    timeout=timeout,
                    turns=env.battle_system.turn_count,
                    steps=episode_steps,
                    episode_reward=episode_reward,
                    no_progress_count=no_progress_count,
                    action_counts=dict(action_counts),
                    damage_by_general_id=dict(damage_by_general_id),
                    learning_team_name=env.learning_team.team_name,
                    enemy_team_name=env.enemy_team.team_name,
                    learning_generals=_snapshot_team(env.learning_team),
                    enemy_generals=_snapshot_team(env.enemy_team),
                ))
                episode_reward = 0.0
                episode_steps = 0
                no_progress_count = 0
                action_counts = {"skill": 0, "attack": 0, "end": 0}
                damage_by_general_id = {}
                observation, info = env.reset(seed + len(data["actions"]) + worker_id * 100000)
        with torch.no_grad():
            obs = torch.as_tensor(observation, dtype=torch.float32).unsqueeze(0)
            mask = torch.as_tensor(info["action_mask"], dtype=torch.bool).unsqueeze(0)
            _, bootstrap = model(obs, mask)
        result_queue.put(RolloutFragment(
            observations=np.asarray(data["observations"], dtype=np.float32),
            masks=np.asarray(data["masks"], dtype=np.bool_),
            actions=np.asarray(data["actions"], dtype=np.int64),
            log_probs=np.asarray(data["log_probs"], dtype=np.float32),
            rewards=np.asarray(data["rewards"], dtype=np.float32),
            values=np.asarray(data["values"], dtype=np.float32),
            dones=np.asarray(data["dones"], dtype=np.bool_),
            bootstrap_value=float(bootstrap.item()),
            episode_summaries=summaries,
        ))


class SyncRolloutCoordinator:
    """Synchronous learner-worker barrier. Workers sample only; learner updates GPU model."""
    def __init__(self, workers, stage):
        self.workers = workers
        self.context = mp.get_context("spawn")
        self.command_queues = [self.context.Queue(maxsize=1) for _ in range(workers)]
        self.result_queue = self.context.Queue(maxsize=workers)
        self.processes = [self.context.Process(target=_worker_main, args=(queue, self.result_queue, index, stage), daemon=True) for index, queue in enumerate(self.command_queues)]
        for process in self.processes:
            process.start()

    def collect(self, model, rollout_steps, seed):
        import torch
        weights = {key: value.detach().cpu() for key, value in model.state_dict().items()}
        base, extra = divmod(rollout_steps, self.workers)
        for index, queue in enumerate(self.command_queues):
            queue.put((weights, base + int(index < extra), seed + index * 1000000))
        fragments = [self.result_queue.get() for _ in self.processes]
        return fragments

    def close(self):
        for queue in self.command_queues:
            queue.put(None)
        for process in self.processes:
            process.join(timeout=10)
            if process.is_alive():
                process.terminate()
