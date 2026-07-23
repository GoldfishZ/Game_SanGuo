# PvE 发布模型

此目录是版本控制中的 PvE 运行时模型包。源码 clone 后，Web 人机模式默认从这里加载模型，不依赖本机的 `artifacts/` 训练目录。

- `battle_policy.pt`：战斗阶段 PPO Actor-Critic。
- `prebattle_value.pt`：选将与布阵价值模型。
- `manifest.json`：schema、训练 update、验证指标与 SHA-256。

训练日志、中间 checkpoint 和历史池仍保存在被 Git 忽略的 `artifacts/`。确认某一轮模型可发布后执行：

```powershell
python tools/rl/promote_pve_models.py
```

也可以用 `--battle`、`--prebattle` 和 `--destination` 指定其他来源。脚本会先检查 observation、动作、模型和武将注册表 schema，只有兼容时才覆盖本目录。

不要直接修改 `.pt` 文件；发布新版本时同时提交两个模型、`manifest.json` 以及相关代码/schema 变更。