# 战斗强化学习 v2

当前框架使用 observation v2、统一战斗规则服务、masked PPO 和加权历史池
self-play。Web、离线环境和未来 PvE 推理都通过
`src/battle/rules_service.py` / `turn_actions.py` 结算动作。

## 快速验证

```powershell
$env:PYTHONIOENCODING='utf-8'
python tools/testing/run_tests.py
python tools/rl/smoke_env.py
```

## YAML 训练

默认配置：`tools/rl/configs/ppo_default.yaml`。

```powershell
python tools/rl/train_ppo.py --config tools/rl/configs/ppo_default.yaml
```

命令行参数覆盖 YAML，例如：

```powershell
python tools/rl/train_ppo.py --config tools/rl/configs/ppo_default.yaml `
  --max-updates 500 --num-workers 6 --run-name selfplay-round-1
```

`max_updates` 是本轮训练硬上限；`schedule_updates` 是学习率和 entropy 的退火
周期。传 `max_updates: 0` 才表示无限训练。

checkpoint 与 observation schema 绑定。v1 的 365 维 checkpoint 会被明确拒绝，
不能加载到 v2。

## PvE 预战模型

```powershell
python tools/rl/train_prebattle.py --config tools/rl/configs/prebattle_pve.yaml
```

该工具从 episode telemetry 训练选将和布阵价值网络，训练产物默认写入 `artifacts/rl/pve/prebattle_value.pt`。使用 `python tools/rl/promote_pve_models.py` 将选定的预战模型与 PPO checkpoint 校验并发布到 `assets/models/pve/`；Web 的“人机对战”默认只加载这个 Git 跟踪目录。模型缺失或不兼容时会记录错误并降级到合法的安全基线。