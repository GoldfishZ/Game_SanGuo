# PvE 发布模型

此目录是版本控制中的 PvE 运行时模型包。源码 clone 后，Web 人机模式默认从这里加载模型，不依赖本机的 `artifacts/` 训练目录。

- `battle_policy_easy.pt` / `normal.pt` / `hard.pt`：三档战斗阶段 PPO
  Actor-Critic。
- `prebattle_value_easy.pt` / `normal.pt` / `hard.pt`：三档选将与布阵价值模型。
- `manifest.json`：schema、训练 update、验证指标与 SHA-256。

运行时默认使用普通档。简单档使用早期 checkpoint 与高温合法动作采样；普通档使用
中期 checkpoint，并保留 30% 合法动作探索；困难档使用固定基准中最强的历史
checkpoint，并始终选择模型的最高分动作。三档的实际部署策略应使用固定种子执行：

```powershell
python tools/rl/benchmark_pve_tiers.py --episodes 1000 --device cuda
```

当前发布基准（同一批 1000 个多阵容种子，对手为启发式策略）为：简单 35.1%、
普通 49.4%、困难 60.5%；报告保存在被 Git 忽略的
`artifacts/rl/pve_tiers/benchmark/deployed_tiers_1000.json`。

训练日志、中间 checkpoint 和历史池仍保存在被 Git 忽略的 `artifacts/`。确认某一轮模型可发布后执行：

```powershell
python tools/rl/promote_pve_models.py
```

也可以用 `--easy-battle`、`--easy-prebattle`（其余档位同理）和
`--destination` 指定其他来源。脚本会先检查 observation、动作、模型和武将注册表
schema，只有兼容时才覆盖本目录。

不要直接修改 `.pt` 文件；发布新版本时同时提交六个模型、`manifest.json` 以及相关
代码/schema 变更。旧的无难度后缀模型仅为历史兼容文件，不再由运行时默认加载。
