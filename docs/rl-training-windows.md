# Windows 本地 PPO 训练

## 概念

- **rollout step**：学习方的一次施法、普攻或结束阶段。
- **game turn**：一方完整行动回合。
- **episode**：一局战斗。
- **PPO update**：收集一批 rollout steps 后的一次策略更新。

`--rollout-steps` 限制每个 update 的学习方子动作数。`--max-updates` 仅控制学习率/探索系数退火周期，达到后保持最终参数继续训练；它不再停止训练。默认 `--max-wallclock-minutes 0`，训练由你在 TensorBoard 观察后通过 Ctrl+C 主动停止；显式传入正数时才启用 wall-clock 硬保险。固定评估额外受 `--eval-max-steps`（单局）和 `--eval-max-seconds`（整次评估）保护；超限局记为 timeout/draw，避免确定性策略卡在无进展动作时阻塞训练。

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

## 过夜随机阶段

推荐从已经通过固定评估的 `ppo_best.pt` 恢复。训练会对无进展失败动作施加轻微负反馈，并线性退火学习率和探索系数；评估质量分为 `win_rate - timeout_rate`，含 timeout 的模型不会因偶然胜率覆盖稳定 best。

```powershell
python tools/rl/train_ppo.py `
  --stage random `
  --resume artifacts/rl/checkpoints/ppo_best.pt `
  --device auto --num-workers auto `
  --max-updates 3000 --max-wallclock-minutes 540 `
  --learning-rate 0.0002 --learning-rate-final 0.00002 `
  --entropy-coef 0.02 --entropy-coef-final 0.005 `
  --eval-every 25 --eval-episodes 96 `
  --eval-max-steps 4096 --eval-max-seconds 300 `
  --checkpoint-every 10 --keep-last 8 `
  --target-winrate 0.8 --patience 12 --min-delta 0.02 `
  --run-name random-stage-overnight
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
