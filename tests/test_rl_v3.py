import math
import random

import numpy as np
import pytest
import torch

from src.rl import actions
from src.rl.models.actor_critic_v3 import ActorCritic, MODEL_SCHEMA
from src.rl.observation import OBSERVATION_SIZE
from src.rl.reward_v3 import RewardHandler
from src.rl.training.ppo_v3 import ppo_update
from src.rl.training.self_play import HistoricalPolicyPool
from tools.rl import train_ppo_v3


class Fence:
    def __init__(self, active=True):
        self.is_active = active


class General:
    def __init__(self, hp=10, fence=None):
        self.current_hp = hp
        self.buffs = []
        self.debuffs = []
        self.fence = fence

    def get_passive_skill(self, name):
        return self.fence if name == "防栅" else None


class Team:
    def __init__(self, name, generals):
        self.team_name = name
        self.generals = generals

    def get_alive_generals(self):
        return [general for general in self.generals if general.current_hp > 0]


def test_structured_actor_masks_illegal_actions_and_uses_v3_schema():
    model = ActorCritic(OBSERVATION_SIZE, actions.ACTION_SIZE)
    observations = torch.zeros((2, OBSERVATION_SIZE))
    mask = torch.ones((2, actions.ACTION_SIZE), dtype=torch.bool)
    mask[:, actions.END_SKILL] = False
    logits, values = model(observations, mask)
    assert MODEL_SCHEMA.endswith("v3")
    assert logits.shape == (2, actions.ACTION_SIZE)
    assert values.shape == (2,)
    assert torch.all(logits[:, actions.END_SKILL] > -1e8)
    assert torch.all(logits[:, actions.END_ATTACK] < -1e8)


def test_end_actions_receive_neither_success_reward_nor_no_progress_penalty():
    learning = Team("learning", [General()])
    enemy = Team("enemy", [General()])
    reward = RewardHandler()
    reward.reset(learning, enemy)
    value = reward.step(
        learning, enemy, action_success=True, action_kind="end_skill",
    )
    assert value == 0.0
    assert not reward.last_no_progress
    assert reward.last_components["action"] == 0.0


def test_breaking_enemy_fence_has_explicit_positive_reward():
    learning = Team("learning", [General()])
    enemy_fence = Fence(True)
    enemy = Team("enemy", [General(fence=enemy_fence)])
    reward = RewardHandler({"action_success": 0.0})
    reward.reset(learning, enemy)
    enemy_fence.is_active = False
    value = reward.step(
        learning, enemy, action_success=True, action_kind="attack",
    )
    assert value == pytest.approx(reward.config["fence_delta"])
    assert reward.last_components["fence"] > 0


class TinyActorCritic(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.actor = torch.nn.Linear(3, 2)
        self.critic = torch.nn.Linear(3, 1)

    def forward(self, observations, masks=None):
        logits = self.actor(observations)
        if masks is not None:
            logits = logits.masked_fill(masks, -1e9)
        return logits, self.critic(observations).squeeze(-1)


def test_ppo_v3_completes_epochs_when_epoch_mean_kl_is_safe():
    torch.manual_seed(7)
    model = TinyActorCritic()
    observations = torch.randn(8, 3)
    masks = torch.zeros((8, 2), dtype=torch.bool)
    with torch.no_grad():
        logits, _ = model(observations, masks)
        distribution = torch.distributions.Categorical(logits=logits)
        actions_taken = distribution.sample()
        old_log_probs = distribution.log_prob(actions_taken)
    batch = {
        "observations": observations.numpy(), "masks": masks.numpy(),
        "actions": actions_taken.numpy(), "log_probs": old_log_probs.numpy(),
        "returns": np.zeros(8, dtype=np.float32),
        "advantages": np.linspace(-1, 1, 8, dtype=np.float32),
    }
    optimizer = torch.optim.Adam(model.parameters(), lr=0.0)
    metrics = ppo_update(
        model, optimizer, batch, epochs=3, minibatch_size=4, target_kl=0.01,
    )
    assert metrics["epochs_completed"] == 3
    assert metrics["minibatches_completed"] == 6
    assert metrics["minibatch_fraction"] == 1.0
    assert metrics["early_stop_kl"] == 0.0


def test_v3_selfplay_uses_stratified_anchor_payloads(tmp_path):
    train_ppo_v3.settings.update(train_ppo_v3.V3_DEFAULTS)
    pool = HistoricalPolicyPool(tmp_path)
    model = torch.nn.Linear(2, 2)
    payloads = train_ppo_v3.selfplay_payloads(
        model, pool, worker_count=6, rng=random.Random(9), current_ratio=0.4,
    )
    ids = [payload["id"] for payload in payloads]
    assert len(ids) == 6
    assert ids.count("heuristic") == 1
    assert ids.count("random") == 1
    assert ids.count("current") == 4  # 历史池为空时回退到最新模型。
