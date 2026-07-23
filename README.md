# 三国武将卡牌游戏

基于 Python 的三国主题武将卡牌对战游戏，支持浏览器本地双人 PvP，以及由选将、布阵和 PPO 战斗模型共同驱动的单人 PvE。

## 快速开始

只运行本地双人 PvP 时无需第三方依赖。要使用仓库自带的 PvE 模型，先安装项目依赖（训练机器可按 CUDA 指南安装 PyTorch）：

```powershell
pip install -r requirements.txt
python main_web.py
```

浏览器访问 `http://localhost:8089`，主菜单可选择 PvP 或 PvE。发布模型已随仓库保存在 `assets/models/pve/`，clone 后不需要复制本机 `artifacts/`。

CLI/Pygame 入口仍可通过以下命令启动：

```powershell
python main.py
```

## 分享给朋友

推荐发送 `dist/Game_SanGuo_Windows.zip`。朋友解压后双击
`Game_SanGuo.exe` 即可，无需安装 Python。构建方法见
[`docs/packaging-windows.md`](docs/packaging-windows.md)。

也可以发送源码 ZIP，对方解压并运行 `python main_web.py`。

## 基本玩法

1. 两位玩家轮流选将，队伍费用不能超过上限。
2. 在 4 条战线、前中后 3 层阵位中排兵布阵。
3. 掷骰决定先手，双方交替使用技能和普通攻击。
4. 一方全部武将阵亡后战斗结束。

## 技术栈

- 后端：Python 标准库 `http.server`
- 前端：原生 HTML、CSS、JavaScript
- 战斗表现：Canvas 粒子与 CSS 动画
- 图片：开发原图与 WebP 运行资源

## 项目结构

```text
Game_SanGuo/
├── main.py                  CLI/Pygame 兼容入口
├── main_web.py              Web 服务器兼容入口
├── desktop_launcher.py      Windows 发行版兼容入口
├── src/
│   ├── app/                 CLI 应用实现
│   ├── battle/              战斗流程
│   ├── game_data/           武将、技能与生平数据
│   ├── models/              General、Team、GameFlow 等模型
│   ├── rl/                  本地 PPO 环境、训练与武将评估
│   ├── skills/              技能基类
│   ├── ui/                  CLI/Pygame 界面
│   ├── web/                 Web 服务、桌面启动器与静态前端
│   └── paths.py             统一项目资源路径
├── assets/images/           武将卡和背景资源
├── assets/models/pve/       Git 跟踪的 PvE 发布模型
├── docs/                    架构、流程、打包与 RL 训练文档
├── requirements/            分组构建依赖
├── tests/                   自动化测试
└── tools/
    ├── assets/              图片处理工具
    ├── build/               Windows 打包脚本
    ├── maintenance/         历史维护脚本
    ├── testing/             单测、模拟与浏览器压力测试
    └── rl/                  PPO 训练、评估与强度报告工具
```

## 本地 AI 训练

本地 PPO 训练、TensorBoard、checkpoint 恢复和武将强度评估见：

- [`docs/rl-training.md`](docs/rl-training.md)：完整训练系统说明；
- [`docs/rl-training-windows.md`](docs/rl-training-windows.md)：Windows/CUDA 启动手册。

训练中间产物位于被忽略的 `artifacts/`；选定版本通过 `python tools/rl/promote_pve_models.py` 校验并发布到 `assets/models/pve/`，供 Web PvE 默认加载。

## 常用开发命令

```powershell
# 全部 Python 测试
$env:PYTHONIOENCODING='utf-8'; python tools/testing/run_tests.py

# HTML 模板检查
python tools/testing/validate_html_templates.py

# 真实浏览器前端回归
python tools/testing/run_frontend_browser_stress.py --games 100

# Windows 单文件发行包
powershell -ExecutionPolicy Bypass -File .\tools\build\build_windows_exe.ps1
```

## 修改 Web 端口

```powershell
$env:PORT=9090
python main_web.py
```

Web 服务器默认监听所有本机网络接口；桌面发行版只监听 `127.0.0.1`。
