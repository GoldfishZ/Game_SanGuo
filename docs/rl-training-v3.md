# PPO / Self-play v3

v3 针对第一轮训练暴露出的三个瓶颈设计：组合覆盖稀疏、722 维平铺动作头、
以及单 minibatch KL 尖峰导致 PPO epoch 几乎全部提前终止。

## 版本边界

- observation：继续使用 `sanguo-battle-observation-v2`；
- model：`sanguo-structured-action-actor-critic-v3`；
- v2 checkpoint 不能加载到 v3，schema 校验会明确拒绝；
- v3 默认产物目录为 `artifacts/rl/round_v3`，不会污染 v2 历史池。

## 主要变化

1. Actor 按动作类型、actor 槽位、双方 target 槽位、区域和奇偶字段共享参数；
2. `end_skill` / `end_attack` 不再获得 action-success 奖励；
3. 栅栏、护盾、buff/debuff 使用双方对称的势能差奖励；
4. KL early-stop 在完整 epoch 后使用 epoch 平均值判断，并记录实际利用率；
5. self-play worker 使用分层配额，而不是6次独立伯努利抽样；
6. 对手加入启发式和随机锚点，防止只学习对历史池的循环克制；
7. 同一阵容默认重复4局，并以15%概率生成镜像阵容；
8. 固定启发式评估额外包含镜像局指标。

## 启动

```powershell
conda activate sanguo-rl
python tools/rl/train_ppo_v3.py --config tools/rl/configs/ppo_selfplay_v3.yaml
```

短 smoke：

```powershell
python tools/rl/train_ppo_v3.py `
  --config tools/rl/configs/ppo_selfplay_v3.yaml `
  --artifact-root artifacts/rl/smoke_archive_v3 `
  --rollout-steps 512 --minibatch-size 128 `
  --max-updates 1 --eval-every 100 --checkpoint-every 100
```

重点观察：

- `train/epochs_completed`、`train/minibatch_fraction`；
- `train/last_epoch_mean_kl`、`train/max_minibatch_kl`；
- `rollout/vs_current_win_rate`、`rollout/vs_history_win_rate`；
- `rollout/vs_heuristic_win_rate`、`rollout/vs_random_win_rate`；
- `eval/heuristic/mirror_win_rate`；
- timeout/draw/no-progress 和各类动作比例。
