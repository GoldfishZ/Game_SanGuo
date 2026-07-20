"""离线强化学习环境的基本契约测试。"""
import random

import numpy as np

from src.rl.env import SanguoEnv


def _trajectory(seed, action_seed):
    env = SanguoEnv()
    observation, _ = env.reset(seed)
    rng = random.Random(action_seed)
    result = []
    done = False
    while not done and len(result) < 500:
        action = rng.choice(env.legal_actions())
        observation, reward, done, info = env.step(action)
        result.append((action, round(reward, 6), env.battle_system.turn_count, tuple(observation[:5])))
    return result, done


def test_rl_environment_reset_and_mask():
    env = SanguoEnv()
    observation, info = env.reset(20260720)
    assert observation.dtype == np.float32
    assert observation.shape[0] > 100
    assert len(info["action_mask"]) == env.action_size
    assert env.legal_actions()
    assert all(info["action_mask"][action] == 0 for action in env.legal_actions())


def test_rl_environment_rejects_masked_action_without_mutation():
    env = SanguoEnv()
    observation, _ = env.reset(11)
    before = observation.copy()
    invalid = next(index for index, value in enumerate(env.action_mask()) if value)
    try:
        env.step(invalid)
        assert False, "非法动作必须抛出 ValueError"
    except ValueError:
        pass
    assert np.array_equal(before, env.observation())


def test_rl_environment_is_reproducible_for_seed_and_actions():
    first, first_done = _trajectory(31, 99)
    second, second_done = _trajectory(31, 99)
    assert first_done and second_done
    assert first == second
