# Windows / CUDA self-play v2

## 环境检查

```powershell
$env:PYTHONIOENCODING='utf-8'
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
python tools/rl/smoke_env.py
```

Windows worker 使用 `spawn`，训练必须从 `tools/rl/train_ppo.py` 启动。

## 第一轮配置

```powershell
Copy-Item tools/rl/configs/ppo_selfplay_round1.yaml tools/rl/configs/round_01.yaml
```

编辑 `round_01.yaml` 后运行：

```powershell
python tools/rl/train_ppo.py --config tools/rl/configs/round_01.yaml `
  --run-name selfplay-round-01
```

命令行参数覆盖 YAML。`max_updates` 会真正停止本轮；`schedule_updates` 只控制
学习率/entropy 退火。

## 建议首轮

RTX 5070 / 24 逻辑核可先使用 auto profile：

```yaml
device: auto
num_workers: auto
rollout_steps: auto
minibatch_size: auto
max_updates: 500
schedule_updates: 500
max_wallclock_minutes: 480
eval_every: 20
eval_episodes: 96
checkpoint_every: 10
selfplay_current_ratio: 0.5
selfplay_pool_size: 24
selfplay_top_k: 8
selfplay_snapshot_every: 20
reward_draw: 0.0
```

## 监控

```powershell
tensorboard --logdir artifacts/rl/runs --port 6006
```

优先观察：

- `eval/heuristic/win_rate`、`timeout_rate`；
- `rollout/vs_current_win_rate`、`vs_history_win_rate`；
- `selfplay/pool_size`、`best_score`；
- `train/approx_kl`、`clip_fraction`、`entropy`、`explained_variance`；
- `rollout/fps`、`no_progress_rate`。

Ctrl+C 会保存包含当前 update、optimizer、best score 和 schema 的 latest checkpoint。

## 恢复

```powershell
python tools/rl/train_ppo.py --config tools/rl/configs/round_01.yaml `
  --resume artifacts/rl/checkpoints/ppo_latest.pt `
  --max-updates 1000 --run-name selfplay-round-01-resume
```

v1 checkpoint 会因 observation schema 不兼容而被明确拒绝。
