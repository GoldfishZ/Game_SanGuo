# 三国游戏本地 PPO 训练系统说明

> 本文描述当前工作树中已实现的离线强化学习训练系统及其真实运行状态。它是训练与平衡分析工具，**尚未接入网页 PvE**；浏览器玩家目前不会与训练模型对战。

---

## 1. 系统目标与范围

本项目将现有三国回合制战斗规则封装为可训练的强化学习环境，并使用 PPO（Proximal Policy Optimization）训练一方的决策策略。

当前系统覆盖：

- 本地离线对战环境；
- 掩码离散动作空间；
- PyTorch actor-critic 与 PPO；
- CPU rollout worker + GPU learner 的同步训练；
- TensorBoard、CSV、checkpoint、固定 seed 评估；
- 随机/启发式对手；
- 武将实战表现与基础平衡统计。

当前不覆盖：

- Web/PvE API 与前端接入；
- 在线推理服务；
- 自博弈历史池；
- 完整的“固定队友、逐一替换武将”的边际贡献矩阵。

核心入口：

| 类型 | 路径 |
|---|---|
| 训练入口 | `tools/rl/train_ppo.py` |
| 环境 | `src/rl/env.py` |
| 动作编码与掩码 | `src/rl/actions.py` |
| 观测编码 | `src/rl/observation.py` |
| 奖励 | `src/rl/reward.py` |
| PPO 更新 | `src/rl/training/ppo.py` |
| worker-learner | `src/rl/training/vector_env.py` |
| 强度统计 | `src/rl/evaluation/strength.py` |
| 强度报告 | `tools/rl/evaluate_strength.py` |

---

## 2. 训练单位与停止方式

这四个概念必须区分：

| 名称 | 定义 |
|---|---|
| **rollout step（采样步）** | 学习方一次 `env.step(action)`；即一次施法、一次普攻、结束技能阶段或结束普攻阶段。 |
| **game turn（游戏回合）** | 一方完整执行技能阶段和普攻阶段；由 `BattleSystem.turn_count` 计数。 |
| **episode（对局）** | 一局完整战斗，从 `reset()` 到任一方败北或达到回合上限。 |
| **PPO update（策略更新）** | 收集一批 rollout steps 后，learner 对该批数据进行 PPO 更新。 |

包含关系通常为：`episode > game turn > rollout step`。PPO update 则跨越多个 episode 采样。

### 2.1 训练不会无限执行

训练由下列条件控制：

- `--max-updates`：最多 PPO update 数，默认 `5000`；
- `--max-wallclock-minutes`：最多总运行分钟数，默认 `480`（8 小时）；
- `--target-winrate`：固定验证对手胜率达到目标时结束，默认 `0.85`；
- `--patience` / `--min-delta`：多次评估未产生有效提升时平台期停止，默认 `10` 次、提升阈值 `0.01`；
- `--eval-max-steps`：每局固定评估最多执行的子动作数，默认 `4096`；
- `--eval-max-seconds`：一整次固定评估的最长时长，默认 `300` 秒；
- Ctrl+C：保存 latest checkpoint 后退出。

评估若碰到确定性策略重复无进展动作，会在上述限制处中止该局并计为 timeout/draw；timeout 永远不会被当作胜利。

`--target-kl 0.015` 是 **PPO 单次 update 内部**的保护：当近似 KL 过大时，它会提前结束该次 update 的剩余 epoch/minibatch，**不会结束整个训练任务**。

如果达到 update 或时间上限仍未收敛，应读取 `ppo_best.pt`、TensorBoard 与固定评估结果，针对奖励、学习率、对手难度、动作分布或模型容量调整后再续训；不应无限循环。

---

## 3. 战斗环境

`src/rl/env.py::SanguoEnv` 是单方控制、子动作级的环境。学习方每次只决定一个动作，敌方完整回合由对手策略自动执行。

### 3.1 reset 规则

默认配置：

```text
team_size   = 3
cost_limit  = 8.0
formation   = 3 × 4
max_turns   = 200
```

每局 reset：

1. 从现有武将数据中洗牌；
2. 双方各选费用不超过 8 的三人阵容；
3. 随机放入 3×4 阵型；
4. 掷骰决定先后手；
5. 后手队伍最大士气与当前士气均 +2；
6. 随机指定物理 p1/p2 中的一方为学习方；观测始终将学习方排在 self 侧；
7. 若敌方先手，环境先自动执行敌方完整回合，再返回学习方首个 observation。

`reset(seed, rosters=None, mirror=False)` 还支持：

- `rosters`：指定双方武将 ID 阵容，供受控实验；
- `mirror=True`：双方使用相同阵容，检查先后手、阵位和随机性偏差。

### 3.2 规则复用边界

RL 环境不重写伤害、技能、士气或阵型规则，而是重用：

- `src/battle/battle_system.py::BattleSystem`；
- `src/battle/turn_actions.py` 的逐动作结算；
- `src/models/general.py` 的攻击、技能、Buff、被动与随机判定；
- `src/models/team.py` 的阵型、攻击目标和士气；
- `src/skills/skill_base.py::TargetType`。

战斗在一方全灭或达到 `max_turns=200` 时结束。

---

## 4. Observation、动作与奖励

### 4.1 Observation：365 维、部分可观测

`src/rl/observation.py` 输出 `numpy.float32` 向量：

```text
OBSERVATION_SIZE = 5 + 12 × 15 × 2 = 365
```

前 5 维为：

1. 当前回合 / 最大回合；
2. 当前行动方是否为学习方；
3. 当前是否为技能子阶段；
4. 学习方当前士气比例；
5. 敌方当前士气比例。

双方各有 12 个阵位，每个武将槽位 15 个特征：

- 是否存活；
- 当前生命比例；
- 基础武力、基础智力；
- 有效武力、有效智力；
- 技能冷却；
- 技能士气消耗；
- 本回合是否已使用技能；
- 本回合是否已普攻；
- 是否仍可攻击；
- 行/列位置；
- 可见 Buff 数；
- 阵营编码。

学习方永远排在 self 侧，避免模型依赖 p1/p2 编号。敌方伏兵等隐藏信息不会写入 observation，因此是**部分可观测**环境。

> 已知限制：当前阵营编码对“凉”和“他”会落入同一个默认编码，不能完全区分六个阵营；这是待修复的 observation 信息缺口。

### 4.2 动作：722 个固定离散 ID

`src/rl/actions.py` 使用 3×4 的 12 个阵位：

| 动作类型 | 说明 |
|---|---|
| `end_skill` | 结束技能阶段 |
| `end_attack` | 结束普攻阶段并进入敌方完整回合 |
| `skill_target` | 施法者 × 单体目标 |
| `skill_area` | 施法者 × 区域/行选择 |
| `attack` | 攻击者 × 目标 × 奇偶猜测 |

动作掩码的约定：

```text
0 = 合法
1 = 非法
```

环境会根据子阶段、存活状态、冷却、士气、技能目标类型、前排/嘲讽/同列限制等实时生成 mask。向 `step()` 传入非法动作会抛出 `ValueError`，不会静默修正。

状态机：

```text
skill → end_skill → attack → end_attack → 敌方完整回合 → skill
```

### 4.3 Reward

默认奖励定义在 `src/rl/reward.py`：

```python
hp_delta      = 0.05
kill          = 0.15
skill_success = 0.01
win           = 1.0
lose          = -1.0
draw          = -0.2
```

每一步以学习方视角计算：

```text
0.05 × (敌方生命减少 - 己方生命减少)
+ 0.15 × (敌方击杀数变化 - 己方阵亡数变化)
+ 成功技能的小额奖励
+ 终局胜/负/平奖励
```

敌方自动回合造成的局面变化，会反映在学习方下一次决策得到的 reward 中。

---

## 5. 模型、GAE 与 PPO

### 5.1 Actor-Critic

`src/rl/models/actor_critic.py`：

```text
365 维 observation
  → Linear(256) + Tanh
  → Linear(256) + Tanh
  ├─ actor: 722 logits
  └─ critic: 1 state value
```

非法动作对应的 logits 被设为极小值（`-1e9`），策略不会采样这些动作。

### 5.2 PPO 参数

默认实现位于 `src/rl/training/ppo.py`：

| 参数 | 默认值 |
|---|---:|
| learning rate | `3e-4` |
| clip ratio | `0.2` |
| value coefficient | `0.5` |
| entropy coefficient | `0.01` |
| epochs | `4` |
| gradient clip | `0.5` |
| target KL | `0.015` |
| gamma | `0.99` |
| GAE lambda | `0.95` |

`src/rl/training/gae.py` 用 GAE(λ) 计算 advantage 和 return。worker 采样时每个 fragment 会使用自己的 bootstrap value 计算截断 GAE，再拼接给 learner。

### 5.3 如何看 PPO 指标

| TensorBoard 标签 | 含义与建议 |
|---|---|
| `train/policy_loss` | PPO 策略目标，不应单独用来判断“变强”。 |
| `train/value_loss` | critic 拟合误差；持续异常增大需检查奖励尺度或模型。 |
| `train/entropy` | 探索程度；缓慢下降正常，过快接近 0 说明策略可能过早确定。 |
| `train/approx_kl` | 新旧策略差异；持续很高说明更新激进。 |
| `train/clip_fraction` | 有多少样本被 PPO clip；过高表示更新幅度过大。 |
| `train/explained_variance` | critic 对 return 的解释能力，越接近 1 通常越好。 |
| `train/grad_norm` | 梯度大小；持续异常大说明训练不稳定。 |
| `train/early_stop_kl` | `1` 代表当前 update 因 target-KL 提前结束内部 epoch。 |
| `eval/heuristic/win_rate` | **最重要的策略强度指标**，看固定 seed 下对启发式对手的胜率。 |

---

## 6. Worker-Learner 架构

训练采用**同步、on-policy** worker-learner，而不是异步 IMPALA：

```text
                    CPU workers (N 个，Windows spawn)
                  ┌─────────────────────────────────┐
learner 广播权重 ─► 每个 worker 独立 env.reset / rollout
                  │ CPU ActorCritic 推理 + 游戏结算    │
                  └───────────────┬─────────────────┘
                                  │ RolloutFragment (numpy)
                                  ▼
                  ┌─────────────────────────────────┐
                  │ 中心 learner：GPU ActorCritic     │
                  │ GAE 汇总 → PPO update → 日志/评估 │
                  └─────────────────────────────────┘
```

实现：`src/rl/training/vector_env.py`。

- worker 只在 CPU 采样；每个拥有独立 `SanguoEnv`、随机种子、对手和 CPU 模型副本；
- learner 持有 GPU 模型与 optimizer；
- learner 通过 Queue 发送 CPU `state_dict`；worker 回传 numpy arrays；不传 CUDA handle；
- 同一轮所有 worker 用同一版本权重采样，全部 fragment 到齐后 learner 才更新，保证 PPO 的 on-policy 性质；
- Windows 使用 `spawn`，worker target 是模块顶层函数；训练入口必须以 `if __name__ == "__main__":` 启动。

`--num-workers 1` 时回退到同进程采样路径，适合调试与最小 smoke。

---

## 7. 自适应 GPU/CPU 配置

`src/rl/training/runtime.py::detect_runtime()` 读取 CUDA、显存和 CPU 核数，在 `--device auto --num-workers auto` 下自动选择 profile。

| 条件 | workers | rollout steps | minibatch |
|---|---:|---:|---:|
| 无 CUDA | `CPU核数 / 2` | 4096 | 256 |
| 显存 ≤ 6GB | 最多 6 | 4096 | 256 |
| 显存 6–12GB | 最多 8 | 8192 | 512 |
| 显存 > 12GB | 最多 12 | 16384 | 1024 |

GPU 主要用于 learner PPO update；游戏逻辑是 Python CPU 工作，worker 数通常比增大 GPU 更能提升采样速度。

### 本机实测 profile

```text
GPU: NVIDIA GeForce RTX 5070
显存: 11.94 GiB
CPU: 24 逻辑核
自动选择:
  device          = cuda:0
  workers         = 8
  rollout_steps   = 8192
  minibatch_size  = 512
```

3060 等机器直接使用同一命令即可自动调整；也可手动覆盖：

```powershell
python tools/rl/train_ppo.py `
  --device cuda `
  --num-workers 6 `
  --rollout-steps 4096 `
  --minibatch-size 256
```

---

## 8. 日志、TensorBoard 与 checkpoint

### 8.1 运行产物

```text
artifacts/rl/
├─ runs/<run-name>/
│  ├─ events.out.tfevents.*     # TensorBoard
│  ├─ metrics.csv               # step/tag/value 长表
│  └─ resolved_config.json      # 本次解析后的 CLI + runtime profile
├─ checkpoints/
│  ├─ ppo_step_000020.pt
│  ├─ ppo_latest.pt
│  └─ ppo_best.pt
└─ character_strength/
   └─ strength.json
```

checkpoint 保存 model、optimizer、update 编号、config 和最佳验证胜率。编号 checkpoint 原子写入，并按 `--keep-last`（默认 5）清理旧文件。

### 8.2 启动 TensorBoard

```powershell
$env:PYTHONIOENCODING='utf-8'
tensorboard --logdir artifacts/rl/runs --port 6006
```

打开：<http://localhost:6006>

建议重点看：

```text
eval/heuristic/*    # 是否真正变强
train/approx_kl     # 策略更新是否太大
train/clip_fraction # PPO clip 是否过多
train/explained_variance
rollout/fps          # 吞吐
balance/*
general/*
```

### 8.3 checkpoint 恢复

```powershell
python tools/rl/train_ppo.py `
  --stage heuristic `
  --resume artifacts/rl/checkpoints/ppo_best.pt `
  --device auto --num-workers auto `
  --max-updates 5000 --max-wallclock-minutes 480 `
  --run-name heuristic-stage
```

---

## 9. 训练启动命令

### 9.1 检查环境

```powershell
$env:PYTHONIOENCODING='utf-8'
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
python tools/rl/smoke_env.py
```

### 9.2 最小 smoke

```powershell
python tools/rl/train_ppo.py `
  --stage random `
  --device auto `
  --num-workers 1 `
  --rollout-steps 256 `
  --minibatch-size 64 `
  --max-updates 3 `
  --eval-every 1 `
  --eval-episodes 8 `
  --checkpoint-every 1 `
  --run-name first-smoke
```

### 9.3 正式随机对手阶段

```powershell
python tools/rl/train_ppo.py `
  --stage random `
  --device auto `
  --num-workers auto `
  --max-updates 5000 `
  --max-wallclock-minutes 480 `
  --eval-every 20 `
  --eval-episodes 64 `
  --checkpoint-every 20 `
  --run-name random-stage
```

### 9.4 启发式阶段

随机阶段得到可靠 `ppo_best.pt` 后再运行：

```powershell
python tools/rl/train_ppo.py `
  --stage heuristic `
  --resume artifacts/rl/checkpoints/ppo_best.pt `
  --device auto --num-workers auto `
  --max-updates 5000 --max-wallclock-minutes 480 `
  --run-name heuristic-stage
```

当前 `HeuristicOpponent` 会优先选择低生命的普攻目标；技能阶段仍有随机选择成分，因此它是轻量基线，而不是完整战术 AI。

---

## 10. 武将强度与平衡评估

### 10.1 当前实战统计

`GeneralStrengthTracker` 记录每名武将：

- 出场次数；
- 所在队伍胜率；
- 存活率；
- 终局平均生命比例；
- 平均普攻伤害（技能伤害会安全降级）；
- `practical_strength = win_rate - 0.5`。

整体平衡指标：

```text
balance/strength_std
balance/strength_range
balance/general_count
```

### 10.2 离线报告

```powershell
python tools/rl/evaluate_strength.py `
  --checkpoint artifacts/rl/checkpoints/ppo_best.pt `
  --mode practical `
  --episodes 500

python tools/rl/evaluate_strength.py `
  --checkpoint artifacts/rl/checkpoints/ppo_best.pt `
  --mode mirror `
  --episodes 500
```

- `practical`：随机阵容与当前策略下的实际表现；
- `mirror`：双方同阵容，主要用于检查阵位、先后手和随机偏差。

结果写入：

```text
artifacts/rl/character_strength/strength.json
```

> 不要用 1–几十局的强度排名直接调数值。每名武将出现概率低，需要至少数百乃至数千局，且应同时参考 mirror/受控实验。

> 完整的“固定两名队友、替换第三名、计算边际胜率”的受控替换矩阵尚未实现；当前 strength 更适合发现明显异常和策略偏好，不是严格的独立数值平衡分。

---

## 11. 当前正式训练状态

本机已启动的随机对手阶段使用：

```text
run name               random-stage-20260720
stage                  random
GPU                    RTX 5070 / cuda:0
CPU rollout workers    8
rollout steps/update   8192
minibatch              512
max updates            5000
max wall-clock         480 minutes
eval cadence           20 updates
eval episodes          64
checkpoint cadence     20 updates
```

训练输出与 TensorBoard 会实时写入：

```text
artifacts/rl/runs/random-stage-20260720/
```

### 重要：多 worker 指标限制

当前多 worker coordinator 已能正确采样、回传 fragment、计算 GAE 并在 GPU 上 PPO update；但其 rollout episode summary 还没有汇总到训练侧 tracker。因此在多 worker 训练中：

```text
rollout/win_rate / loss_rate / draw_rate = 占位值
balance/general_count = 0
general/* = 不会从训练 rollout 产生
```

这不是“模型胜率为 0”或“没有武将数据”。在当前实现中，请以以下指标为准：

```text
eval/heuristic/win_rate
eval/heuristic/loss_rate
eval/heuristic/draw_rate
eval_balance/*
```

离线 `evaluate_strength.py` 也可生成真实的强度统计。

---

## 12. 已知限制与后续路线

| 项目 | 当前状态 | 后续方向 |
|---|---|---|
| 网页 PvE | 未接入 | 训练稳定后加载 `ppo_best.pt` 并通过 Web bridge 自动执行 AI 回合。 |
| 多 worker 实时武将统计 | 未汇总 episode summary | 在 `RolloutFragment` 中返回 episode summaries 与 damage，更新 tracker。 |
| 多 worker rollout 胜负统计 | 占位值 | 同上。 |
| YAML 配置 | `tools/rl/configs/ppo_default.yaml` 存在，但 CLI 尚未读取 | 实现 `--config` 并让 CLI 覆盖 YAML。 |
| 受控边际强度 | 仅有 practical/mirror | 实现固定锚点阵容、单武将替换和 match-up matrix。 |
| 阵营观察编码 | 凉/他尚未区分 | 将 camp one-hot 与实际六阵营数据对齐。 |
| 自博弈 | 未实现 | 启发式阶段稳定后引入冻结历史 checkpoint 池。 |

---

## 13. 相关文档与文件

- 简短入口：`src/rl/README.md`
- Windows runbook：`docs/rl-training-windows.md`
- 训练参数镜像：`tools/rl/configs/ppo_default.yaml`
- 环境测试：`tests/test_rl_env.py`
- 动作测试：`tests/test_rl_actions.py`

运行完整游戏回归测试：

```powershell
$env:PYTHONIOENCODING='utf-8'
python tools/testing/run_tests.py
```
