"""离线强化学习环境的基本契约测试。"""
import random

import numpy as np

from src.rl.env import SanguoEnv
from src.game_data.generals_data import GENERALS_DATA
from src.rl.observation import (
    ATTRIBUTES,
    BUFF_TYPES,
    CAMPS,
    GENERAL_FEATURES,
    OBSERVATION_SCHEMA,
    OBSERVATION_SIZE,
    SKILL_IDS,
)


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
    assert observation.shape == (OBSERVATION_SIZE,)
    assert info["observation_schema"] == OBSERVATION_SCHEMA
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


def test_observation_v2_registry_covers_game_content():
    assert set(CAMPS) == {"魏", "蜀", "吴", "凉", "袁", "他"}
    assert "fence_rebuild" in SKILL_IDS
    assert "防栅" in ATTRIBUTES
    assert "damage_shield" in BUFF_TYPES
    assert GENERAL_FEATURES > 150


def test_observation_changes_for_fence_and_buff_runtime_state():
    env = SanguoEnv()
    env.reset(77)
    general = env.learning_team.get_alive_generals()[0]
    before = env.observation()
    general.add_buff("damage_shield", 4, 2)
    after_buff = env.observation()
    assert not np.array_equal(before, after_buff)

    fenced = next((g for g in env.learning_team.generals if g.has_passive_skill("防栅")), None)
    if fenced is not None:
        fence = fenced.get_passive_skill("防栅")
        with_fence = env.observation()
        fence.is_active = False
        assert not np.array_equal(with_fence, env.observation())


def test_variable_roster_sampling_covers_multiple_legal_team_sizes():
    env = SanguoEnv(
        team_size=0, min_team_size=1, max_team_size=8,
        team_size_power=1.0, roster_candidate_samples=128,
        roster_cost_bias=0.8, cost_limit=8.0,
    )
    sizes = set()
    for seed in range(80):
        env.rng = random.Random(seed)
        selection = env._choose_selection(GENERALS_DATA)
        sizes.add(len(selection))
        assert 1 <= len(selection) <= 8
        assert sum(float(item["cost"]) for item in selection) <= 8.0

    assert len(sizes) >= 5
    assert max(sizes) > 3


def test_fixed_team_size_sampling_remains_backward_compatible():
    env = SanguoEnv(team_size=3, cost_limit=8.0)
    env.rng = random.Random(7)
    selection = env._choose_selection(GENERALS_DATA)
    assert len(selection) == 3
    assert sum(float(item["cost"]) for item in selection) <= 8.0