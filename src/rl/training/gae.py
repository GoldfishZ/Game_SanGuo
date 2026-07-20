"""广义优势估计。"""
import numpy as np


def compute_gae(rewards, values, dones, bootstrap_value, gamma=0.99, gae_lambda=0.95):
    advantages = np.zeros(len(rewards), dtype=np.float32)
    last_advantage = 0.0
    next_value = bootstrap_value
    for index in range(len(rewards) - 1, -1, -1):
        non_terminal = 1.0 - float(dones[index])
        delta = rewards[index] + gamma * next_value * non_terminal - values[index]
        last_advantage = delta + gamma * gae_lambda * non_terminal * last_advantage
        advantages[index] = last_advantage
        next_value = values[index]
    return advantages, advantages + np.asarray(values, dtype=np.float32)
