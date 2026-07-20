"""训练与评估共用的策略适配器。"""
from __future__ import annotations

import numpy as np


class RandomPolicy:
    def select_action(self, observation, action_mask, rng):
        legal = np.flatnonzero(np.asarray(action_mask) == 0)
        return int(rng.choice(legal))


class TorchPolicy:
    def __init__(self, model, device="cpu", deterministic=True):
        self.model = model
        self.device = device
        self.deterministic = deterministic

    def select_action(self, observation, action_mask, rng=None):
        import torch
        with torch.no_grad():
            obs = torch.as_tensor(observation, dtype=torch.float32, device=self.device).unsqueeze(0)
            mask = torch.as_tensor(action_mask, dtype=torch.bool, device=self.device).unsqueeze(0)
            logits, _ = self.model(obs, mask)
            if self.deterministic:
                return int(logits.argmax(dim=-1).item())
            return int(torch.distributions.Categorical(logits=logits).sample().item())
