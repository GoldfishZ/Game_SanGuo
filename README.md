# 三国武将卡牌游戏 v1.0

基于 Python 的三国主题武将卡牌对战游戏，卡牌原型来自霸·三国志大战。
两名玩家轮流操作，在同一个浏览器上对战。

## 🚀 快速开始（给别人玩）

你的朋友只需要 3 步：

```bash
# 1. 安装 Python 3（如果还没有）
#    官网下载: https://www.python.org/downloads/

# 2. 解压游戏文件夹，双击运行
python main_web.py

# 3. 浏览器打开 http://localhost:8088
```

**零外部依赖**——不需要 `pip install` 任何东西，Python 自带的标准库就够了。

## 🎮 怎么玩

1. 两位玩家轮流选将（费用上限 8 费）
2. 排兵布阵：前排（第 0 行）挡攻击，后排安全
3. 掷骰子决定先手
4. 每回合：**技能阶段** → **普攻阶段** → 换人
5. 一方全部武将阵亡 → 游戏结束

## 📦 给别人玩的方式

### 方式 1：直接发文件夹（推荐）

把整个项目文件夹打包成 zip，发给对方。对方解压后运行 `python main_web.py`，浏览器打开 `http://localhost:8088`。

### 方式 2：局域网对战

如果两台电脑在同一网络下：
```bash
# 主机运行
python main_web.py
# 客机浏览器打开 http://主机的IP地址:8088
# 主机IP获取方式：命令行输入 ipconfig，找 IPv4 地址
```

### 方式 3：GitHub 发布

```bash
git tag v1.0.0
git push origin v1.0.0
```

然后在 GitHub 仓库页面的 Releases 里创建发布，上传 zip 文件。

## 🏗️ 技术栈

- **后端**：Python 3 标准库（`http.server`），零外部依赖
- **前端**：纯 HTML/CSS/JS，零框架零构建工具
- **图片**：WebP 格式，241MB→8.1MB 优化
- **特效**：Canvas 粒子系统 + GSAP 动画

## 📁 项目结构

```
├── main_web.py              Web 服务器入口
├── game_data/               40 武将 + 42 技能数据
├── src/
│   ├── models/              游戏逻辑（General/Team/Battle）
│   ├── skills/              技能系统
│   ├── battle/              战斗引擎
│   └── ui/static/           前端文件（HTML/CSS/JS）
├── assets/images/           武将卡图 + 背景（WebP）
├── docs/                    开发文档
├── tools/                   工具脚本
└── tests/                   测试
```

## ⚙️ 配置

环境变量 `PORT` 可修改端口号：
```bash
# Windows
set PORT=9090 && python main_web.py

# Mac/Linux
PORT=9090 python main_web.py
```
