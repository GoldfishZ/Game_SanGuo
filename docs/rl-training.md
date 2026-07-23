# 三国游戏 PPO / Self-play v2

## 1. 当前架构

```text
Web client ───────────────┐
SanguoEnv simulated client├─> BattleRulesService -> turn_actions -> domain models
PvE inference adapter ────┘

CPU rollout workers -> PPO learner -> current policy
                         ├-> current-policy opponent snapshot
                         └-> scored historical policy pool
```

规则只在 `src/models`、`src/skills`、`src/battle` 中结算。客户端只提交选择，
不能直接重写伤害、目标合法性、士气或回合推进。

## 2. Observation v2

`src/rl/observation.py` 定义可版本化的固定维度 schema：

- 回合、子阶段、双方士气、生命、存活数和延迟士气；
- 武将 ID、六阵营、费用、基础/有效武力智力；
- 主动技能 ID、技能类型、目标类型、费用和冷却；
- 七种被动属性；
- Buff/Debuff 的类型、数值、持续时间；
- 延迟 Buff/Debuff；
- 防栅、护盾、复活、伏兵、连计、追加普攻和强制攻击目标；
- 3×4 阵位。

离散身份使用 one-hot。未来骰子和随机判定结果不会进入 observation。
checkpoint 保存 `observation_schema`、输入维度和动作维度；不兼容模型拒绝加载。

## 3. 动作与权威规则

动作仍是 722 个 masked discrete ID：结束技能、结束普攻、单体技能、区域技能、
普攻与奇偶选择。mask 中 `0=合法`、`1=非法`。

Web 和 RL 均通过 `BattleRulesService` 调用：

- `skill()` / `skill_targets()`；
- `attack()`；
- `end_turn()`；
- `outcome()`。

达到 `max_turns` 的对局一律为 draw，不再按剩余生命判胜。冷启动默认
`reward_draw: 0.0`；待策略能够稳定结束对局后，可逐步改为负值。

## 4. Self-play

每轮 worker 接收两个互不共享更新的权重：

1. rollout 学习策略；
2. 冻结对手策略。

冻结对手由 YAML 中 `selfplay_current_ratio` 决定：一部分使用当前版本快照，
其余从历史池选择。历史池：

- 每隔 `selfplay_snapshot_every` 次 update 保存一次；
- 评分使用固定启发式评估的 `win_rate - timeout_rate`；
- 只在历史最高分的 `selfplay_top_k` 中选择；
- 按 `softmax(score / selfplay_temperature)` 加权；
- 最多保留 `selfplay_pool_size` 个独立冻结模型。

历史池位于 `artifacts/rl/self_play/`，不会被普通 checkpoint 清理影响。

## 5. Telemetry

每个 run 输出：

```text
artifacts/rl/runs/<run-name>/
  events.out.tfevents.*
  metrics.csv
  episodes.jsonl
  resolved_config.json
```

`episodes.jsonl` 包含 update、seed、对手版本、胜负、timeout、阵容、初始阵型、
回合/步数、技能使用、按武将归因伤害和规则产生的协同事件。它是后续
DraftPolicy、FormationPolicy 和反事实分析的数据基础。

## 6. YAML 与参数优先级

默认配置：`tools/rl/configs/ppo_default.yaml`。

```powershell
python tools/rl/train_ppo.py --config tools/rl/configs/ppo_default.yaml
```

优先级：命令行 > YAML > 程序默认值。YAML 中出现未知键会立即报错，避免参数
拼写错误被静默忽略。

主要参数：

- 运行：`max_updates`、`max_wallclock_minutes`、`num_workers`；
- 产物：`artifact_root`（可用于隔离不同实验或 smoke）；
- 退火：`schedule_updates`、`learning_rate(_final)`、`entropy_coef(_final)`；
- PPO：`gamma`、`gae_lambda`、`clip_ratio`、`value_coef`、`target_kl`；
- 环境：`team_size`（0=多阵容）、`min_team_size`、`max_team_size`、`team_size_power`、`roster_candidate_samples`、`roster_cost_bias`、`cost_limit`、`max_turns`；
- 奖励：全部 `reward_*`；
- self-play：全部 `selfplay_*`。

## 7. 第一轮训练建议

仓库已经提供 `tools/rl/configs/ppo_selfplay_round1.yaml`。第一轮参数为：

```yaml
stage: selfplay
max_updates: 500
schedule_updates: 500
max_wallclock_minutes: 480
eval_every: 20
eval_episodes: 96
checkpoint_every: 10
selfplay_current_ratio: 0.5
selfplay_snapshot_every: 20
reward_draw: 0.0
```

验收重点：

- timeout/no-progress 接近 0；
- 对启发式 held-out seeds 的胜率稳定提升；
- `vs_current_win_rate` 不长期塌到 0 或 1；
- `vs_history_win_rate` 随历史池增强仍能恢复；
- KL、clip fraction、entropy 和 explained variance 无异常；
- 不依据小样本 `general/*` 直接调整武将数值。

稳定后再把 `reward_draw` 调到 `-0.05`，观察是否减少拖平且没有诱发冒险送死。

## 8. PvE 选将与布阵价值模型

预战模型从本轮 `episodes.jsonl` 训练，并使用 update 时间切分而不是随机拆分。配置位于 `tools/rl/configs/prebattle_pve.yaml`：

```powershell
python tools/rl/train_prebattle.py --config tools/rl/configs/prebattle_pve.yaml
```

命令行参数可覆盖 YAML。训练输出仍写入被 Git 忽略的 `artifacts/rl/pve/prebattle_value.pt`，其中同时保存 `V_draft`、`V_form`、武将注册表、schema 和验证指标。确认战斗与预战模型可发布后执行：

```powershell
python tools/rl/promote_pve_models.py
```

发布脚本会验证 schema，并把选中的模型复制到 Git 跟踪的 `assets/models/pve/`。Web 运行时只默认读取该发布目录，因此新 clone 无需本机训练产物即可进入 PvE。部署时：

- `DraftPolicy` 枚举候选池内满足费用上限的组合；
- `FormationPolicy` 对1～4人阵容精确枚举；5人以上使用确定性的4096候选有界搜索；
- 价值最高的合法候选交给 `src/rl/pve.py`；
- 战斗继续使用 PPO checkpoint，三层规则都由服务端执行。

当前 round_v3 数据的首次验证结果：Draft AUC 0.902、Formation AUC 0.877。该指标证明模型能从 held-out 后期对局区分相对价值，但不能替代固定 seed 的端到端胜率评估；后续还需与随机预战策略进行受控对局比较。