# 协同驱动的全流程 PvE AI 架构

> 本文是未来 PvE AI、选将 AI 与布阵 AI 的训练设计参考。它描述目标架构、数据与验证方法；其中部分模块尚未实现。当前已实现的只有**战斗阶段 PPO 策略**，选将和布阵在本地 RL 环境中仍为随机，Web PvE 尚未接入。

## 1. 目标：完整 PvE AI 不等于单个战斗模型

完整 PvE 应由三个协作策略组成：

```text
候选池 / 已知敌方信息
          │
          ▼
     DraftPolicy ──────────────── 选择合法阵容
          │
          ▼
  FormationPolicy ─────────────── 选择 3×4 阵型
          │
          ▼
    BattlePolicy ──────────────── 技能、攻击、结束阶段
```

| 策略 | 输入 | 输出 | 当前状态 |
|---|---|---|---|
| `DraftPolicy` | 候选池、费用上限、已知敌方信息 | 一组合法武将 | 未实现 |
| `FormationPolicy` | 双方阵容、技能、被动、可用阵位 | 每名武将的 `(row, col)` | 未实现 |
| `BattlePolicy` | 当前战场 observation 与动作 mask | 技能/攻击/结束阶段动作 | 已实现：PPO Actor-Critic |

不应将这三个决策强行塞进同一个端到端 MLP：

- 选将是一次性的组合约束优化；
- 布阵是一次性的空间关系优化；
- 战斗是长时序、逐子动作的决策过程；
- 一局失败时，端到端模型难以判断是选将、布阵还是战斗操作导致失败。

推荐方式是：**共享真实对局数据，但训练不同粒度的模型。**

```text
Episode telemetry
  ├─ V_draft：阵容价值模型
  ├─ V_form：阵型价值模型
  └─ BattlePolicy：现有 PPO 战斗策略
```

所有阶段都必须复用真实游戏规则：

```text
src/battle/battle_system.py
src/battle/turn_actions.py
src/models/general.py
src/models/team.py
```

不得为 Draft/Formation 重新实现另一套伤害、技能、士气或阵型逻辑。

---

## 2. 当前实现与缺口

当前 PPO 环境是：

```text
src/rl/env.py::SanguoEnv
```

它会在 `reset()` 时：

1. 随机生成双方合法阵容；
2. 随机布阵；
3. 掷骰；
4. 将学习方送入技能/攻击阶段；
5. 用 PPO 决定战斗子动作。

因此，现有 `BattlePolicy` 只适用于：

```text
双方已经选将、已经布阵之后的战斗。
```

未来实现 PvE 时，DraftPolicy 和 FormationPolicy 必须替代当前环境中的：

```text
SanguoEnv._choose_selection()  # 当前随机合法组合
SanguoEnv._place_randomly()    # 当前随机阵位
```

Web 当前也没有 AI 分支：`src/web/server.py` 会依次处理 `select_p1` 和 `select_p2` 的人类选择。PvE bridge 应在后续阶段接入，且 AI 仍需通过 `turn_actions.py` 执行实际动作，保证 PvP、PvE 和训练环境规则一致。

---

## 3. 不使用“武力高放前排”的经验规则

本项目的 Draft/Formation AI **不以手写经验规则作为最终决策核心**。

例如，下列规则只能用于调试、解释或冷启动 sanity check，不能作为正式 AI 的决定性逻辑：

```text
武力高 → 一定前排
智力高 → 一定后排
治疗 → 一定最后排
同阵营 → 一定更强
```

原因是武将价值来自具体机制和互动，而不是单一面板：

- 有伏兵的武将可能需要利用邻接关系；
- 连计武将的 Buff/Debuff 同步与伤害分摊依赖队友；
- 曹操与夏侯惇存在守护分伤；
- 嘲讽、同列攻击、击退、2×2 重排会改变阵位价值；
- 高武力武将可能因技能范围、攻击限制、冷却或队友配合而不适合某个前排位置；
- 辅助武将的价值可能完全由其对特定队友技能/被动的放大决定。

正式策略应从实际对局 telemetry 和受控反事实实验中学习这些关系。

---

## 4. 训练数据：Episode Telemetry 是共同基础

选将、布阵和战斗模型都应使用同一批真实对局数据，但消费不同粒度的信息。

### 4.1 每个战斗 step 的记录

每个学习方 `env.step(action)` 应持久化：

| 字段 | 说明 | 当前来源 |
|---|---|---|
| `episode_id` / `step_idx` | 唯一局与局内步骤 | 待新增 |
| `run_id` / `worker_id` / `seed` | 可复现性与数据切分 | 待新增 |
| `turn_count` / `subphase` | 回合与技能/攻击阶段 | `env.py` / `build_debug_dict` |
| `action_id` / 解码动作 | 动作类型、施法者、目标、区域、奇偶猜测 | `actions.decode()` |
| `action_success` | 动作是否成功 | `turn_actions` result |
| `reward` / `no_progress` | 奖励和无进展信号 | `reward.py` |
| `self_hp` / `enemy_hp` | 战斗资源变化 | `RewardHandler` 已计算，待持久化 |
| `self_alive` / `enemy_alive` | 存活数量变化 | `RewardHandler` 已计算，待持久化 |
| `skill_id` / `caster_id` | 技能归因 | `apply_skill_action()` |
| `damage_dealt` | 普攻和技能实际伤害 | 普攻已可得；技能细粒度归因待补齐 |
| `morale` | 双方士气 | env 状态 |

### 4.2 每个 episode 的记录

Draft/Formation 模型主要使用每局汇总数据：

```text
episode_id
seed / run_id / worker_id
opponent_policy_id / opponent_checkpoint_id

roster_self / roster_enemy: [general_id]
cost_self / cost_enemy
camp_multiset_self / camp_multiset_enemy

formation_self / formation_enemy:
  [(general_id, row, col), ...]

first_player: self | enemy
winner: self | enemy | draw
timeout
turns
steps

team_damage_self / team_damage_enemy
skill_usage_by_general
skill_damage_by_general
passive_triggers_by_general
synergy_events
```

### 4.3 当前 telemetry 缺口

当前 `RolloutFragment` 只回传 transition arrays：

```text
observations, masks, actions, log_probs,
rewards, values, dones, bootstrap_value
```

它没有回传 `episode_summaries`。因此多 worker 训练中：

```text
rollout/win_rate = 占位值
rollout/loss_rate = 占位值
rollout/draw_rate = 占位值
general/* 不从 worker rollout 实时产生
```

补齐 worker episode summaries 是后续的第一个前置工作。它会同时解锁：

- 真实多 worker 武将强度统计；
- Draft/Formation 训练标签；
- 协同事件统计；
- 对局 replay、反事实与平衡工具。

推荐保存为按 run 分区的表格数据，例如：

```text
artifacts/rl/episodes/<run-id>/
  steps.parquet
  episodes.parquet
```

运行产物不进入 git。

---

## 5. 武将协同与位置关系特征

协同必须由规则事件、实际收益和胜负标签验证，而不是依赖人工直觉。以下机制应成为 telemetry 事件、模型特征或反事实实验维度。

### 5.1 阵容级协同

| 协同 | 要统计什么 | 规则来源 |
|---|---|---|
| 连计 | Buff/Debuff 同步次数、分伤量、共同存活时间 | `General.sync_chain_effects()` / `take_damage()` |
| 曹操–夏侯惇 | 守护分伤次数、分担生命、是否改变胜负 | `General.share_damage_with_cao_guard()` |
| 募兵/复活/魅力/勇猛 | 触发次数、治疗/反伤/增伤/复活的实际收益 | 被动技能与 combat events |
| 士气/费用曲线 | 费用、技能士气压力、技能使用频率 | `Team.current_morale` / skill cost |
| 阵营组合 | 作为特征而非直接加分规则 | general camp 数据 |

### 5.2 阵型级协同

| 互动 | 要统计什么 | 规则来源 |
|---|---|---|
| 前排遮挡 | 每列可攻击目标、前排被击破后的收益/代价 | `Team.get_front_row_generals()` |
| 伏兵邻接 | 邻接反击触发、反击伤害、隐藏价值 | `Team.resolve_ambush_interception()` |
| 同列限制 | 同列攻击成功率、对位收益 | `front_only_attack` / column target |
| 嘲讽/强制目标 | 强制攻击带来的保护或风险 | `forced_attack_target` |
| 击退 | 击退后阵型与胜率变化 | `knock_back_with_rear_general()` |
| 2×2 重排 | 技能重排前后有效位置变化 | temporary formation APIs |
| 防栅 | 阻挡次数、阻挡伤害、阵位价值 | 防栅 passive / combat event |

### 5.3 事件来源原则

`General` 已通过 `record_combat_event()` 为 Web 表现生成部分事件，例如：

```text
chain_share
ambush_counter
fence_block
shield_absorb
bravery_judgment
charisma_judgment
revive
recruit_heal
```

未来 telemetry 应在每个 step drain 并归档这些事件，而不是另行猜测协同是否发生。

技能伤害归因是待补齐项：普攻的 `apply_attack_action()` 已返回攻击者/目标/伤害；技能应同样记录 `caster_id`、目标 ID 和每个目标实际伤害，避免把技能价值错误归到队伍总伤害。

---

## 6. 反事实实验：识别真实组合价值

随机对局中“武将 A 常与武将 B 一起赢”不等于 A/B 有协同，也可能只是抽到了弱对手。必须使用受控反事实实验。

### 6.1 单武将替换

固定：

```text
两名队友
敌方阵容与阵型
双方策略 checkpoint
随机 seeds
```

只替换第三名武将：

```text
P(win | A, B, X) - P(win | A, B, C)
```

这个差值才是候选 X 在该上下文中的边际贡献。

### 6.2 阵型替换

固定同一阵容、对手、策略与 seeds，仅改变阵型：

```text
P(win | roster, formation_1)
- P(win | roster, formation_2)
```

这会让模型学习某武将和某阵位/队友位置的互动，而不是使用“高武力前排”的经验模板。

### 6.3 镜像与版本控制

- 使用 `SanguoEnv.reset(rosters=..., mirror=True)` 检查先后手和阵位偏差；
- 对手 checkpoint 必须冻结并记录版本；
- timeout 一律按 draw；
- 训练 seeds 与 held-out 评估 seeds 不可重叠；
- 每个组合/阵型 cell 必须达到足够样本量（通常数百局以上）才允许用于数值平衡。

---

## 7. Draft Value Model 与 Formation Value Model

### 7.1 阵容价值模型

```text
V_draft(roster_self, roster_enemy/context) → P(win)
```

输入不应只是武力和智力，而包括：

```text
general embedding
技能 ID / 目标类型 / 范围 / 冷却 / 士气成本
被动技能集合
费用
阵营多重集合
队友对特征
协同事件历史统计
对手已知阵容或对手先验
```

训练标签来自 episode telemetry：

```text
winner == self
```

DraftPolicy 在真实候选池和费用约束下枚举或 beam-search 合法阵容，选择 `V_draft` 最高的组合。

```text
不是：武力最高的三人
而是：面对当前候选池/敌方上下文，预期对局价值最高的合法组合。
```

### 7.2 阵型价值模型

```text
V_form(roster, formation_self, formation_enemy/context) → P(win)
```

输入包括：

```text
阵容 embedding
3×4 阵型网格
列前排结构
邻接图
伏兵邻接关系
同列攻击/限制关系
嘲讽与强制目标可达性
技能区域覆盖关系
敌方阵容与可见阵型
```

每队通常为 3 名武将，合法有序 placement 数：

```text
12 × 11 × 10 = 1320
```

因此初期可以直接枚举所有合法布阵，用 `V_form` 选最大值：

```python
best_formation = max(legal_formations, key=value_model)
```

不必一开始为布阵单独训练 PPO。

### 7.3 模型边界

```text
V_draft / V_form：预战价值预测
BattlePolicy：战斗阶段实时操作
```

三者共享数据和规则，但不互相替代。

---

## 8. 数据泄漏与公平性原则

未来部署到 PvE 时，模型只能使用玩家在对应阶段可以知道的信息。

禁止用于 PvE 决策的特征：

```text
敌方隐藏伏兵内部 is_hidden 状态
未来随机判定结果
敌方未公开被动内部变量
训练时才能看到的完整 combat event 未来信息
```

这些信息可用于离线诊断，但必须标记为 analysis-only，不能进入部署的 Draft/Formation/Battle 输入。

还需要：

- 使用严格时间切分：value model 训练数据必须早于待评估 checkpoint；
- 记录 opponent checkpoint 版本；
- 修复 observation 中“凉/他”阵营编码混淆后，再将阵营作为正式 value-model 特征；
- Web PvE 使用双方独立候选池语义，而不是当前 RL env 的共享洗牌 roster 语义。

---

## 9. 实施路线

### Stage 0：遥测基础设施

- 扩展 `RolloutFragment`，回传 `episode_summaries`；
- 汇总 worker episode 数据，修复多 worker win/loss/strength 占位指标；
- 记录 step 与 episode 数据；
- 完整区分六个阵营；
- 为技能添加可归因伤害事件。

**验证产物：** 每个 run 都能输出真实 episode 表、真实 general telemetry 和可重放 seed。

### Stage 1：协同事件与强度统计

- 汇总 passive triggers 和 `synergy_events`；
- 以真实事件而非面板推断协同收益；
- 将武将强度从单将 win rate 扩展为 pair/team/formation 条件统计。

**验证产物：** 可解释的协同报告，能回答“某组合为何有效”。

### Stage 2：离线价值模型

- 新增 `V_draft` / `V_form` 模型与训练工具；
- 用 earlier telemetry 训练，用 held-out seeds/checkpoints 验证；
- 不接入 Web，不改变 PvP。

**验证产物：** 阵容/阵型价值预测在 held-out 对局上优于简单随机/面板基线。

### Stage 3：反事实 harness

- 新增单武将替换和阵型替换评估；
- 输出 substitution matrix 和 formation matrix；
- 只在足够样本后用于数值平衡。

**验证产物：** 在固定对手与 seed 下可复现的边际胜率表。

### Stage 4：预战策略

- 实现 `DraftPolicy`：候选池、费用约束、价值搜索；
- 实现 `FormationPolicy`：合法 placement 枚举 + `V_form` argmax；
- 让 RL env 可选使用预战策略替代随机选将/布阵。

**验证产物：** AI 选将/布阵在 held-out 对局中优于随机预战策略。

### Stage 5：Web PvE

- Web server 增加人机模式；
- AI 使用 DraftPolicy、FormationPolicy、PPO BattlePolicy；
- 所有战斗操作走 `turn_actions.py`；
- 模型加载失败时降级为可解释的安全 baseline。

### Stage 6：冻结历史策略池

- 收集历史 `ppo_best` checkpoints；
- 作为训练/评估对手池；
- 为 Draft/Formation model 提供更丰富且稳定的敌方先验。

---

## 10. 现有代码索引

| 主题 | 文件 |
|---|---|
| 当前战斗 RL 环境、随机选将/布阵 | `src/rl/env.py` |
| 365 维战斗 observation | `src/rl/observation.py` |
| 722 动作与 mask | `src/rl/actions.py` |
| 奖励 | `src/rl/reward.py` |
| 多 worker fragment | `src/rl/training/vector_env.py` |
| 当前强度统计 | `src/rl/evaluation/strength.py` |
| 固定 seed 评估 | `src/rl/training/evaluation.py` |
| 战斗动作统一结算 | `src/battle/turn_actions.py` |
| 武将互动/事件 | `src/models/general.py` |
| 阵型、前排、伏兵邻接、重排 | `src/models/team.py` |
| 被动技能 | `src/game_data/passive_skills_config.py` |
| 技能基类与伤害结果 | `src/skills/skill_base.py` |
| 当前 Web 人类流程 | `src/web/server.py` |
| 当前 PPO 策略适配器 | `src/rl/policy.py` |

## 11. 当前规则一致性提醒

在把机制作为正式 AI 特征前，先核对以下问题：

1. `observation.py` 当前未完全区分凉/他阵营；
2. 防栅的重建行为在 passive 实现、General 调用和已有文档之间需要确认最终规则；
3. 当前 Web 使用双方独立候选池，RL env 使用共享洗牌 roster；未来 PvE DraftPolicy 必须遵循 Web 的真实候选池规则；
4. 当前 `practical_strength = win_rate - 0.5` 是单将实战统计，不能直接等同于阵容价值或协同价值。
