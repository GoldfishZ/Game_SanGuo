# Windows 本地 PPO 训练

## 概念

- **rollout step**：学习方的一次施法、普攻或结束阶段。
- **game turn**：一方完整行动回合。
- **episode**：一局战斗。
- **PPO update**：收集一批 rollout steps 后的一次策略更新。

`--max-updates` 限制 PPO update 数，`--rollout-steps` 限制每个 update 的学习方子动作数。训练还有 wall-clock、目标胜率和平台期早停保护，不会自动无限执行。固定评估额外受 `--eval-max-steps`（单局）和 `--eval-max-seconds`（整次评估）保护；超限局记为 timeout/draw，避免确定性策略卡在无进展动作时阻塞训练。

## 环境检查

```powershell
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

若输出 CUDA 为 False，请按本机驱动从 PyTorch 官网安装匹配的 CUDA wheel。Windows 多进程使用 `spawn`；不要从 notebook 或缺少 `if __name__ == '__main__'` 的脚本启动 worker。

## 第一次 smoke 训练

```powershell
$env:PYTHONIOENCODING='utf-8'
python tools/rl/train_ppo.py --stage random --device auto --num-workers 1 --rollout-steps 256 --minibatch-size 64 --max-updates 3 --eval-every 1 --eval-episodes 8 --checkpoint-every 1 --run-name first-smoke
```

## 正式随机阶段

```powershell
python tools/rl/train_ppo.py --stage random --device auto --num-workers auto --max-updates 5000 --max-wallclock-minutes 480 --run-name random-stage
```

完成后，从最佳模型开始启发式阶段：

```powershell
python tools/rl/train_ppo.py --stage heuristic --resume artifacts/rl/checkpoints/ppo_best.pt --device auto --num-workers auto --max-updates 5000 --max-wallclock-minutes 480 --run-name heuristic-stage
```

## 监控与平衡

```powershell
tensorboard --logdir artifacts/rl/runs --port 6006
python tools/rl/evaluate_strength.py --checkpoint artifacts/rl/checkpoints/ppo_best.pt --mode practical --episodes 500
python tools/rl/evaluate_strength.py --checkpoint artifacts/rl/checkpoints/ppo_best.pt --mode mirror --episodes 500
```

重点看 `eval/heuristic/win_rate`、`train/approx_kl`、`train/clip_fraction`、`train/explained_variance`、`rollout/fps`、`general/*`、`balance/*`。武将样本过少时不应据此调数值；受控镜像和大样本报告更适合平衡判断。
