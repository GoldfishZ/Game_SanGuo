# Agent / Contributor 快速入口

本项目的完整开发约定、游戏规则、架构边界、武将卡视觉规范和本地 RL 训练范围均以根目录的 **[`CLAUDE.md`](CLAUDE.md)** 为唯一权威来源。开始修改代码、生成武将卡或运行训练前，请先阅读该文件。

## 新 clone 后的阅读顺序

1. [`README.md`](README.md)：快速启动、项目结构和常用命令；
2. [`CLAUDE.md`](CLAUDE.md)：完整项目约定与关键设计约束；
3. [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md)：代码与工具目录职责；
4. [`docs/rl-training.md`](docs/rl-training.md)：本地 PPO 训练、TensorBoard、checkpoint 与强度评估；
5. [`docs/rl-training-windows.md`](docs/rl-training-windows.md)：Windows/CUDA 运行手册。

## 最小验证命令

```powershell
$env:PYTHONIOENCODING='utf-8'
python tools/testing/run_tests.py
```

训练产物、个人 Claude 权限和 agent worktree 都是本地文件，不应提交到仓库；具体忽略规则见 [`.gitignore`](.gitignore)。
