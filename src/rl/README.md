# 本地离线 PPO 训练

该模块将三国战斗规则封装为子动作级、合法动作掩码环境。网页 PvE 尚未接入；训练、评估与武将平衡分析都在本地执行。

详细 Windows/CUDA/worker runbook：[`docs/rl-training-windows.md`](../../docs/rl-training-windows.md)。

## 安装与检查

```powershell
pip install -r requirements.txt
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

PyTorch CUDA wheel 必须按本机驱动安装。环境无法识别 CUDA 时会自动回退到 CPU。

## 训练单位

- **rollout step**：学习方一次技能、攻击或结束阶段；
- **game turn**：一方完整行动；
- **episode**：一局战斗；
- **PPO update**：对一个 rollout batch 的一次策略更新。

`--max-updates` 是训练的硬更新上限，`--rollout-steps` 是每次更新收集的学习方子动作数量。另有 8 小时 wall-clock、目标胜率与平台期早停，因此不会无限训练。每次固定评估也受 `--eval-max-steps`（默认 4096 步/局）和 `--eval-max-seconds`（默认 300 秒/次）保护；超限局会记为 timeout/draw，绝不会作为胜利。

训练会对失败且没有造成任何生命/击杀变化的动作施加小型 `no_progress` 负奖励，避免策略反复选择无进展动作。`--learning-rate-final` 与 `--entropy-coef-final` 可在线性退火中降低后期策略漂移；从 checkpoint 恢复时会保留原 best 评估基线，避免较差模型覆盖 `ppo_best.pt`。

## 快速验证

```powershell
python tools/rl/smoke_env.py
python tools/rl/train_ppo.py --stage random --device auto --num-workers 1 --rollout-steps 256 --max-updates 3 --eval-every 1 --eval-episodes 8 --checkpoint-every 1
```

## 正式训练与监控

```powershell
python tools/rl/train_ppo.py --stage random --device auto --num-workers auto --max-updates 5000 --max-wallclock-minutes 480 --run-name random-stage
tensorboard --logdir artifacts/rl/runs --port 6006
```

训练产物：

- `artifacts/rl/runs/<run-id>/`：TensorBoard events、CSV、解析后的配置；
- `artifacts/rl/checkpoints/ppo_latest.pt`：最近 checkpoint；
- `artifacts/rl/checkpoints/ppo_best.pt`：固定验证胜率最佳 checkpoint。

重点查看 `eval/heuristic/win_rate`（实际强度）、`train/approx_kl`/`clip_fraction`（PPO 稳定性）、`train/explained_variance`（critic）、`rollout/fps`（吞吐）以及 `general/*`、`balance/*`（武将表现）。

## 武将强度

```powershell
python tools/rl/evaluate_strength.py --checkpoint artifacts/rl/checkpoints/ppo_best.pt --mode practical --episodes 500
python tools/rl/evaluate_strength.py --checkpoint artifacts/rl/checkpoints/ppo_best.pt --mode mirror --episodes 500
```

`practical` 反映随机搭配下当前策略的实战表现；`mirror` 可用于检查对称阵容下的阵位/先后手偏差。样本很少时强度排名没有统计意义；建议至少数百局后再据此调数值。

环境的 observation 始终将学习方置于 self 侧；动作掩码中 `0` 表示合法、`1` 表示非法。敌方伏兵隐藏状态不会编码进 observation。
