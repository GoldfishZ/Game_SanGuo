# 可恢复训练种子

`multi_roster_v1/` 保存本轮多阵容 PPO 的可恢复训练状态：

- update 4906 的 `ppo_latest.pt`，包含模型和 Adam 优化器状态；
- `self_play/` 中的历史策略池与评分；
- `manifest.json` 中的 schema、update、文件大小和 SHA-256。

这些文件是只读的版本化训练起点。clone 后先验证并复制到被 Git 忽略的可写目录：

```powershell
python tools/rl/bootstrap_tracked_training.py --verify-only
python tools/rl/bootstrap_tracked_training.py
```

脚本随后会打印续训命令。不要直接把 `artifact_root` 指向
`assets/models/training/`，否则训练过程会修改版本控制中的基准模型。

不同机器仍需根据 CPU、内存和显存调整本地配置。正式训练前必须确认
`torch.cuda.is_available()` 为 `True`，并先执行小规模冒烟训练。
