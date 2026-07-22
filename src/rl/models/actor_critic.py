"""Observation v2 的共享阵位编码 Actor-Critic。"""
from __future__ import annotations

from torch import nn
import torch

from src.rl.actions import GRID_SIZE
from src.rl.observation import GENERAL_FEATURES, GLOBAL_FEATURES, OBSERVATION_SIZE

MODEL_SCHEMA = "sanguo-shared-slot-actor-critic-v2"


class ActorCritic(nn.Module):
    """双方 24 个阵位共用一个 encoder，再保留阵位顺序进入全局 trunk。"""

    def __init__(self, observation_size: int, action_size: int,
                 hidden_size: int = 256, slot_hidden_size: int = 64):
        super().__init__()
        if observation_size != OBSERVATION_SIZE:
            raise ValueError(
                f"ActorCritic v2 需要 observation_size={OBSERVATION_SIZE}，"
                f"实际为 {observation_size}"
            )
        self.slot_count = GRID_SIZE * 2
        self.slot_encoder = nn.Sequential(
            nn.Linear(GENERAL_FEATURES, slot_hidden_size), nn.Tanh(),
            nn.Linear(slot_hidden_size, slot_hidden_size), nn.Tanh(),
        )
        trunk_input = GLOBAL_FEATURES + self.slot_count * slot_hidden_size
        self.body = nn.Sequential(
            nn.Linear(trunk_input, hidden_size), nn.Tanh(),
            nn.Linear(hidden_size, hidden_size), nn.Tanh(),
        )
        self.actor = nn.Linear(hidden_size, action_size)
        self.critic = nn.Linear(hidden_size, 1)

    def forward(self, observations, action_masks=None):
        global_state = observations[:, :GLOBAL_FEATURES]
        slots = observations[:, GLOBAL_FEATURES:].reshape(
            -1, self.slot_count, GENERAL_FEATURES,
        )
        encoded_slots = self.slot_encoder(slots).flatten(start_dim=1)
        features = self.body(torch.cat((global_state, encoded_slots), dim=-1))
        logits = self.actor(features)
        if action_masks is not None:
            logits = logits.masked_fill(action_masks.bool(), -1e9)
        return logits, self.critic(features).squeeze(-1)
