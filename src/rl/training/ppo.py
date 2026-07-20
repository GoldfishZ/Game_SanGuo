"""单进程 PPO 更新。PyTorch 为训练阶段可选依赖。"""
from __future__ import annotations


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
    metrics = {key: 0.0 for key in (
        "policy_loss", "value_loss", "entropy", "total_loss", "approx_kl",
        "clip_fraction", "grad_norm", "explained_variance", "advantage_mean", "advantage_std",
    )}
    indices = torch.randperm(len(actions), device=device)
    batches = 0
    early_stop = False

    for _ in range(epochs):
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
            metrics["policy_loss"] += float(policy_loss.detach())
            metrics["value_loss"] += float(value_loss.detach())
            metrics["entropy"] += float(entropy.detach())
            metrics["total_loss"] += float(total_loss.detach())
            metrics["approx_kl"] += float(approx_kl.detach())
            metrics["clip_fraction"] += float(clip_fraction.detach())
            metrics["grad_norm"] += float(grad_norm.detach())
            batches += 1
            if target_kl and approx_kl > target_kl:
                early_stop = True
                break
        if early_stop:
            break
    with torch.no_grad():
        _, all_values = model(observations, masks)
        variance = torch.var(returns)
        explained = 1.0 - torch.var(returns - all_values) / (variance + 1e-8)
    metrics["explained_variance"] = float(explained.detach())
    metrics["advantage_mean"] = float(raw_advantages.mean().detach())
    metrics["advantage_std"] = float(raw_advantages.std().detach())
    metrics["early_stop_kl"] = float(early_stop)
    metrics["learning_rate"] = optimizer.param_groups[0]["lr"]
    averaged = {key: value / max(1, batches) for key, value in metrics.items()}
    averaged["explained_variance"] = metrics["explained_variance"]
    averaged["advantage_mean"] = metrics["advantage_mean"]
    averaged["advantage_std"] = metrics["advantage_std"]
    averaged["early_stop_kl"] = metrics["early_stop_kl"]
    averaged["learning_rate"] = metrics["learning_rate"]
    return averaged
