"""带合法动作掩码的紧凑 MLP actor-critic。"""
from __future__ import annotations

import torch
from torch import nn


class ActorCritic(nn.Module):
    def __init__(self, observation_size: int, action_size: int, hidden_size: int = 256):
        super().__init__()
        self.body = nn.Sequential(
            nn.Linear(observation_size, hidden_size), nn.Tanh(),
            nn.Linear(hidden_size, hidden_size), nn.Tanh(),
        )
        self.actor = nn.Linear(hidden_size, action_size)
        self.critic = nn.Linear(hidden_size, 1)

    def forward(self, observations, action_masks=None):
        features = self.body(observations)
        logits = self.actor(features)
        if action_masks is not None:
            logits = logits.masked_fill(action_masks.bool(), -1e9)
        return logits, self.critic(features).squeeze(-1)
