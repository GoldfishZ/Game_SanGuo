"""Observation v2 的共享阵位、结构化动作 Actor-Critic v3。"""
from __future__ import annotations

import math

import torch
from torch import nn

from src.rl import actions
from src.rl.actions import GRID_SIZE
from src.rl.observation import GENERAL_FEATURES, GLOBAL_FEATURES, OBSERVATION_SIZE

MODEL_SCHEMA = "sanguo-structured-action-actor-critic-v3"


def _action_descriptors():
    """将固定动作 ID 映射为可共享的结构化字段。"""
    type_ids, actor_slots, target_slots, area_slots, guess_ids = [], [], [], [], []
    type_map = {"end_skill": 0, "end_attack": 1, "skill_target": 2, "skill_area": 3, "attack": 4}
    guess_map = {None: 0, "奇": 1, "偶": 2}
    padding_slot = GRID_SIZE
    for action_id in range(actions.ACTION_SIZE):
        action = actions.decode(action_id)
        type_ids.append(type_map[action.kind])
        actor_slots.append(action.actor_slot if action.actor_slot >= 0 else padding_slot)
        target_slots.append(action.target_slot if action.target_slot >= 0 else padding_slot)
        area_slots.append(action.row * 4 + action.col if action.kind == "skill_area" else padding_slot)
        guess_ids.append(guess_map.get(action.guess, 0))
    return tuple(torch.tensor(values, dtype=torch.long) for values in (
        type_ids, actor_slots, target_slots, area_slots, guess_ids,
    ))


class ActorCritic(nn.Module):
    """共享阵位编码，并按 actor/target/type 组合计算每个动作的分数。"""

    def __init__(self, observation_size: int, action_size: int,
                 hidden_size: int = 256, slot_hidden_size: int = 64,
                 action_slot_size: int = 32, action_hidden_size: int = 64):
        super().__init__()
        if observation_size != OBSERVATION_SIZE:
            raise ValueError(f"ActorCritic v3 需要 observation_size={OBSERVATION_SIZE}，实际为 {observation_size}")
        if action_size != actions.ACTION_SIZE:
            raise ValueError(f"ActorCritic v3 需要 action_size={actions.ACTION_SIZE}，实际为 {action_size}")
        self.slot_count = GRID_SIZE * 2
        self.action_size = action_size
        self.slot_encoder = nn.Sequential(
            nn.Linear(GENERAL_FEATURES, slot_hidden_size), nn.Tanh(),
            nn.Linear(slot_hidden_size, slot_hidden_size), nn.Tanh(),
        )
        trunk_input = GLOBAL_FEATURES + self.slot_count * slot_hidden_size
        self.body = nn.Sequential(
            nn.Linear(trunk_input, hidden_size), nn.Tanh(),
            nn.Linear(hidden_size, hidden_size), nn.Tanh(),
        )
        self.action_slot_projection = nn.Linear(slot_hidden_size, action_slot_size)
        self.action_type_embedding = nn.Embedding(5, 16)
        self.area_embedding = nn.Embedding(GRID_SIZE + 1, 12, padding_idx=GRID_SIZE)
        self.guess_embedding = nn.Embedding(3, 8)
        descriptor_size = action_slot_size * 3 + 16 + 12 + 8
        self.action_encoder = nn.Sequential(
            nn.Linear(descriptor_size, action_hidden_size), nn.Tanh(),
            nn.Linear(action_hidden_size, action_hidden_size), nn.Tanh(),
        )
        self.action_query = nn.Linear(hidden_size, action_hidden_size)
        self.type_bias = nn.Linear(hidden_size, 5)
        self.critic = nn.Linear(hidden_size, 1)

        for name, tensor in zip(
            ("action_type_ids", "action_actor_slots", "action_target_slots", "action_area_slots", "action_guess_ids"),
            _action_descriptors(),
        ):
            self.register_buffer(name, tensor, persistent=False)

    @staticmethod
    def _gather_slots(slots, indices):
        expanded = indices.view(1, -1, 1).expand(slots.shape[0], -1, slots.shape[-1])
        return slots.gather(1, expanded)

    def forward(self, observations, action_masks=None):
        global_state = observations[:, :GLOBAL_FEATURES]
        raw_slots = observations[:, GLOBAL_FEATURES:].reshape(-1, self.slot_count, GENERAL_FEATURES)
        encoded_slots = self.slot_encoder(raw_slots)
        features = self.body(torch.cat((global_state, encoded_slots.flatten(start_dim=1)), dim=-1))

        projected = self.action_slot_projection(encoded_slots)
        padding = projected.new_zeros((projected.shape[0], 1, projected.shape[-1]))
        self_slots = torch.cat((projected[:, :GRID_SIZE], padding), dim=1)
        enemy_slots = torch.cat((projected[:, GRID_SIZE:], padding), dim=1)
        actor = self._gather_slots(self_slots, self.action_actor_slots)
        self_target = self._gather_slots(self_slots, self.action_target_slots)
        enemy_target = self._gather_slots(enemy_slots, self.action_target_slots)

        batch = observations.shape[0]
        action_types = self.action_type_embedding(self.action_type_ids).unsqueeze(0).expand(batch, -1, -1)
        areas = self.area_embedding(self.action_area_slots).unsqueeze(0).expand(batch, -1, -1)
        guesses = self.guess_embedding(self.action_guess_ids).unsqueeze(0).expand(batch, -1, -1)
        action_keys = self.action_encoder(torch.cat(
            (actor, self_target, enemy_target, action_types, areas, guesses), dim=-1,
        ))
        query = self.action_query(features).unsqueeze(1)
        logits = (action_keys * query).sum(dim=-1) / math.sqrt(action_keys.shape[-1])
        logits = logits + self.type_bias(features).gather(
            1, self.action_type_ids.view(1, -1).expand(batch, -1),
        )
        if action_masks is not None:
            logits = logits.masked_fill(action_masks.bool(), -1e9)
        return logits, self.critic(features).squeeze(-1)
