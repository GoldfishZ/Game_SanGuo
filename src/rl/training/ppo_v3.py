"""PPO v3：按完整 epoch 的平均 KL 决定是否停止。"""
from __future__ import annotations

import math


def ppo_update(model, optimizer, batch, *, clip_ratio=0.2, value_coef=0.5,
               entropy_coef=0.01, epochs=4, minibatch_size=128,
               grad_clip=0.5, target_kl=0.015, device=None):
    import torch

    device = device or next(model.parameters()).device
    observations = torch.as_tensor(batch["observations"], dtype=torch.float32, device=device)
    masks = torch.as_tensor(batch["masks"], dtype=torch.bool, device=device)
    actions = torch.as_tensor(batch["actions"], dtype=torch.long, device=device)
    old_log_probs = torch.as_tensor(batch["log_probs"], dtype=torch.float32, device=device)
    returns = torch.as_tensor(batch["returns"], dtype=torch.float32, device=device)
    raw_advantages = torch.as_tensor(batch["advantages"], dtype=torch.float32, device=device)
    advantages = (raw_advantages - raw_advantages.mean()) / (raw_advantages.std() + 1e-8)
    accumulated = {key: 0.0 for key in (
        "policy_loss", "value_loss", "entropy", "total_loss", "approx_kl",
        "clip_fraction", "grad_norm",
    )}
    batches = 0
    epochs_completed = 0
    early_stop = False
    max_minibatch_kl = 0.0
    last_epoch_mean_kl = 0.0
    minibatches_per_epoch = math.ceil(len(actions) / minibatch_size)

    for _ in range(epochs):
        epoch_kls = []
        indices = torch.randperm(len(actions), device=device)
        for selected in indices.split(minibatch_size):
            logits, values = model(observations[selected], masks[selected])
            distribution = torch.distributions.Categorical(logits=logits)
            log_probs = distribution.log_prob(actions[selected])
            log_ratio = log_probs - old_log_probs[selected]
            ratio = log_ratio.exp()
            unclipped = ratio * advantages[selected]
            clipped = ratio.clamp(1.0 - clip_ratio, 1.0 + clip_ratio) * advantages[selected]
            policy_loss = -torch.minimum(unclipped, clipped).mean()
            value_loss = torch.nn.functional.mse_loss(values, returns[selected])
            entropy = distribution.entropy().mean()
            total_loss = policy_loss + value_coef * value_loss - entropy_coef * entropy
            optimizer.zero_grad()
            total_loss.backward()
            grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
            optimizer.step()

            approx_kl = 0.5 * log_ratio.square().mean()
            clip_fraction = ((ratio - 1.0).abs() > clip_ratio).float().mean()
            values_to_add = {
                "policy_loss": policy_loss, "value_loss": value_loss,
                "entropy": entropy, "total_loss": total_loss,
                "approx_kl": approx_kl, "clip_fraction": clip_fraction,
                "grad_norm": grad_norm,
            }
            for key, value in values_to_add.items():
                accumulated[key] += float(value.detach())
            kl_value = float(approx_kl.detach())
            epoch_kls.append(kl_value)
            max_minibatch_kl = max(max_minibatch_kl, kl_value)
            batches += 1

        epochs_completed += 1
        last_epoch_mean_kl = sum(epoch_kls) / max(1, len(epoch_kls))
        if target_kl and last_epoch_mean_kl > target_kl:
            early_stop = True
            break

    with torch.no_grad():
        _, all_values = model(observations, masks)
        variance = torch.var(returns)
        explained = 1.0 - torch.var(returns - all_values) / (variance + 1e-8)
    metrics = {key: value / max(1, batches) for key, value in accumulated.items()}
    metrics.update({
        "explained_variance": float(explained.detach()),
        "advantage_mean": float(raw_advantages.mean().detach()),
        "advantage_std": float(raw_advantages.std().detach()),
        "early_stop_kl": float(early_stop),
        "learning_rate": optimizer.param_groups[0]["lr"],
        "epochs_completed": float(epochs_completed),
        "minibatches_completed": float(batches),
        "minibatch_fraction": batches / max(1, epochs * minibatches_per_epoch),
        "last_epoch_mean_kl": last_epoch_mean_kl,
        "max_minibatch_kl": max_minibatch_kl,
    })
    return metrics
