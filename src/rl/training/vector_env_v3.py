"""v3 同步采样：结构化模型、战术奖励、重复阵容与分层对手。"""
from __future__ import annotations

import multiprocessing as mp
import random

import numpy as np

from src.rl.training.vector_env import (
    EpisodeSummary, RolloutFragment, _classify_outcome, _drain_combat_events,
    _snapshot_formation, _snapshot_team,
)


def _physical_rosters(env):
    return (
        [general.general_id for general in env.controller.player1.team.generals],
        [general.general_id for general in env.controller.player2.team.generals],
    )


def _set_opponent(env, payload, opponent_model):
    from src.rl.opponents import HeuristicOpponent, ModelOpponent, RandomOpponent

    kind = (payload or {}).get("kind", "heuristic")
    opponent_id = (payload or {}).get("id", kind)
    if kind == "model":
        opponent_model.load_state_dict(payload["model"])
        opponent_model.eval()
        env.opponent = ModelOpponent(
            opponent_model, device="cpu", deterministic=False,
            opponent_id=opponent_id,
        )
    elif kind == "random":
        env.opponent = RandomOpponent()
    else:
        env.opponent = HeuristicOpponent()
    return opponent_id


def _worker_main(command_queue, result_queue, worker_id, stage, env_config,
                 roster_repeat_episodes, mirror_ratio):
    import torch
    from src.rl.env_v3 import SanguoEnv
    from src.rl.models.actor_critic_v3 import ActorCritic
    from src.rl.observation import OBSERVATION_SIZE

    env = SanguoEnv(**env_config)
    model = ActorCritic(OBSERVATION_SIZE, env.action_size).cpu()
    opponent_model = ActorCritic(OBSERVATION_SIZE, env.action_size).cpu()
    while True:
        command = command_queue.get()
        if command is None:
            return
        weights, steps, seed, opponent_payload = command
        torch.manual_seed(seed + worker_id)
        model.load_state_dict(weights)
        model.eval()
        opponent_id = _set_opponent(env, opponent_payload, opponent_model)
        sampler_rng = random.Random(seed + worker_id * 170003)

        def new_group(episode_seed):
            mirror = sampler_rng.random() < mirror_ratio
            observation, info = env.reset(episode_seed, mirror=mirror)
            return observation, info, _physical_rosters(env), 1

        observation, info, repeated_rosters, roster_uses = new_group(seed)
        episode_seed = seed
        roster_self = [general.general_id for general in env.learning_team.generals]
        roster_enemy = [general.general_id for general in env.enemy_team.generals]
        formation_self = _snapshot_formation(env.learning_team)
        formation_enemy = _snapshot_formation(env.enemy_team)
        data = {key: [] for key in (
            "observations", "masks", "actions", "log_probs", "rewards",
            "values", "dones", "no_progresses",
        )}
        summaries = []
        episode_reward = 0.0
        episode_steps = 0
        no_progress_count = 0
        action_counts = {"skill": 0, "attack": 0, "end": 0}
        damage_by_general_id = {}
        skill_usage = {}
        synergy_events = []

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
            for key, value_item in (
                ("observations", observation), ("masks", info["action_mask"]),
                ("actions", action), ("log_probs", log_prob), ("rewards", reward),
                ("values", float(value.item())), ("dones", done),
            ):
                data[key].append(value_item)
            episode_reward += reward
            episode_steps += 1
            if next_info.get("no_progress"):
                no_progress_count += 1
            data["no_progresses"].append(bool(next_info.get("no_progress")))
            result = next_info.get("result") or {}
            source_id = result.get("attacker_id", result.get("caster_id"))
            if result.get("success") and source_id is not None:
                damage_by_general_id[source_id] = damage_by_general_id.get(source_id, 0.0) + result.get("damage", 0.0)
            if result.get("success") and result.get("caster_id") is not None:
                caster_id = result["caster_id"]
                skill_usage[caster_id] = skill_usage.get(caster_id, 0) + 1
            synergy_events.extend(_drain_combat_events(env))
            observation, info = next_observation, next_info

            if done:
                outcome, winner_name, timeout = _classify_outcome(env.battle_system, env.learning_team)
                summaries.append(EpisodeSummary(
                    outcome=outcome, winner_name=winner_name, timeout=timeout,
                    turns=env.battle_system.turn_count, steps=episode_steps,
                    episode_reward=episode_reward, no_progress_count=no_progress_count,
                    action_counts=dict(action_counts),
                    damage_by_general_id=dict(damage_by_general_id),
                    learning_team_name=env.learning_team.team_name,
                    enemy_team_name=env.enemy_team.team_name,
                    learning_generals=_snapshot_team(env.learning_team),
                    enemy_generals=_snapshot_team(env.enemy_team),
                    opponent_id=opponent_id, seed=episode_seed,
                    roster_self=roster_self, roster_enemy=roster_enemy,
                    formation_self=formation_self, formation_enemy=formation_enemy,
                    skill_usage_by_general_id=dict(skill_usage),
                    synergy_events=list(synergy_events),
                ))
                episode_reward = 0.0
                episode_steps = 0
                no_progress_count = 0
                action_counts = {"skill": 0, "attack": 0, "end": 0}
                damage_by_general_id = {}
                skill_usage = {}
                synergy_events = []
                episode_seed = seed + len(data["actions"]) + worker_id * 100000
                if roster_uses < roster_repeat_episodes:
                    observation, info = env.reset(episode_seed, rosters=repeated_rosters)
                    roster_uses += 1
                else:
                    observation, info, repeated_rosters, roster_uses = new_group(episode_seed)
                roster_self = [general.general_id for general in env.learning_team.generals]
                roster_enemy = [general.general_id for general in env.enemy_team.generals]
                formation_self = _snapshot_formation(env.learning_team)
                formation_enemy = _snapshot_formation(env.enemy_team)

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
            bootstrap_value=float(bootstrap.item()), episode_summaries=summaries,
            no_progresses=np.asarray(data["no_progresses"], dtype=np.bool_),
        ))


class SyncRolloutCoordinator:
    def __init__(self, workers, stage, env_config=None, *, roster_repeat_episodes=4,
                 mirror_ratio=0.1):
        self.workers = workers
        self.context = mp.get_context("spawn")
        self.command_queues = [self.context.Queue(maxsize=1) for _ in range(workers)]
        self.result_queue = self.context.Queue(maxsize=workers)
        self.processes = [self.context.Process(
            target=_worker_main,
            args=(queue, self.result_queue, index, stage, env_config or {},
                  max(1, int(roster_repeat_episodes)), float(mirror_ratio)),
            daemon=True,
        ) for index, queue in enumerate(self.command_queues)]
        for process in self.processes:
            process.start()

    def collect(self, model, rollout_steps, seed, opponent_payloads=None):
        weights = {key: value.detach().cpu() for key, value in model.state_dict().items()}
        base, extra = divmod(rollout_steps, self.workers)
        for index, queue in enumerate(self.command_queues):
            payload = opponent_payloads[index] if opponent_payloads else {"id": "heuristic", "kind": "heuristic"}
            queue.put((weights, base + int(index < extra), seed + index * 1000000, payload))
        return [self.result_queue.get() for _ in self.processes]

    def close(self):
        for queue in self.command_queues:
            queue.put(None)
        for process in self.processes:
            process.join(timeout=10)
            if process.is_alive():
                process.terminate()
