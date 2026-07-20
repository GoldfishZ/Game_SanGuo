"""Windows spawn-safe synchronous CPU rollout workers for on-policy PPO."""
from __future__ import annotations

from dataclasses import dataclass
import multiprocessing as mp

import numpy as np


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
        for _ in range(steps):
            obs = torch.as_tensor(observation, dtype=torch.float32).unsqueeze(0)
            mask = torch.as_tensor(info["action_mask"], dtype=torch.bool).unsqueeze(0)
            with torch.no_grad():
                logits, value = model(obs, mask)
                dist = torch.distributions.Categorical(logits=logits)
                action = int(dist.sample().item())
                log_prob = float(dist.log_prob(torch.tensor(action)).item())
            next_observation, reward, done, next_info = env.step(action)
            for key, value_item in (("observations", observation), ("masks", info["action_mask"]), ("actions", action), ("log_probs", log_prob), ("rewards", reward), ("values", float(value.item())), ("dones", done)):
                data[key].append(value_item)
            observation, info = next_observation, next_info
            if done:
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
