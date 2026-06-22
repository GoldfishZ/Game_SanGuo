# 三国武将卡牌游戏

基于 Python 开发的三国主题武将卡牌对战游戏，卡牌原型来自霸·三国志大战。

## 项目简介

两名玩家轮流操作，从随机武将池中挑选武将、排兵布阵、掷骰决定先手、进入回合制战斗。每回合分为技能使用阶段和普攻阶段。一方全部武将阵亡则游戏结束。

---

## 快速开始

### Web 版（推荐）

```bash
# 零依赖，Python 标准库即可运行
python main_web.py
```

浏览器打开 `http://localhost:8080` 即可游玩。

### 命令行版

```bash
PYTHONIOENCODING=utf-8 python main.py
# 选择 1: 命令行模式
```

### 图形界面版

```bash
PYTHONIOENCODING=utf-8 python main.py
# 选择 2: 图形界面模式
# 或直接: python main.py --gui
```

---

## 游戏规则

### 阵型
3行x4列方格。前列武将挡住后列，敌方只能攻击最前排的武将。

### 伤害计算
- 攻击方武力 > 目标武力：伤害 = 武力差
- 攻击方武力 <= 目标武力：伤害 = min(3, (武力+智力)差)，最低1点

### 士气系统
- 初始12点，队伍共用士气池
- 主动技能消耗士气
- 后手玩家士气上限+2作为补偿

### 回合制
- 掷骰子决定先手，点数大方先手
- A-B-A-B交替回合
- 每回合：技能使用阶段 -> 普攻阶段

### 费用系统
- 每位武将有不同的费用（1.0/1.5/2.0/2.5/3.0）
- 选将时有费用上限（默认8费），需在预算内组队

### 胜利条件
一方全体武将阵亡则游戏结束。

---

## 武将系统

### 六大阵营

| 阵营 | 数量 | 武将 |
|------|------|------|
| 蜀 | 6 | 张飞、诸葛亮、夏侯月姬、周仓、马岱、姜维 |
| 魏 | 10 | 曹操、夏侯惇、曹仁、贾诩、王异、许褚、夏侯渊、郭皇后、蔡文姬、于禁 |
| 吴 | 6 | 甘宁、大乔、太史慈、朱然、小乔、鲁肃 |
| 凉 | 6 | 张辽、吕布、董卓、陈宫、邹氏、李傕和郭汜 |
| 袁 | 4 | 田丰、于夫罗、张郃、文丑 |
| 他 | 8 | 张任、汉献帝、司马徽、皇甫嵩、公孙瓒、张角、带来洞主、王允 |

共计 **40名武将**，42种主动技能。

### 七大被动属性

| 属性 | 效果 |
|------|------|
| 勇猛 | 低血量时普攻伤害x1.5 |
| 魅力 | 被击杀时反弹致死伤害的一半给攻击者 |
| 募兵 | 有生命损失时每回合回复1点 |
| 防栅 | 完全抵挡一次攻击后失效 |
| 连环 | 同属性武将分担伤害+共享buff/debuff |
| 复活 | 死亡时以50%HP复活一次 |
| 伏兵 | 使用技能前不可被敌方选中 |

---

## 项目结构

```
├── main.py                      CLI/GUI入口
├── main_web.py                  Web版游戏服务器
├── game_data/                  游戏数据层
│   ├── generals_data.py         40名武将数据
│   ├── generals_bios.py         武将生平
│   └── skills_config.py         42种主动技能
├── src/
│   ├── models/                  数据模型(General/Team/Flow)
│   ├── skills/                  技能基类
│   ├── battle/                  战斗引擎BattleSystem
│   ├── ui/                      界面(Pygame/CLI/Web)
│   └── utils/                   图片加载器
├── assets/images/               武将卡+背景图片
└── tests/                       测试文件
```

---

## 启动方式

| 模式 | 命令 | 说明 |
|------|------|------|
| Web | `python main_web.py` | 浏览器访问 localhost:8080 |
| CLI | `python main.py` -> 1 | 纯命令行交互 |
| GUI | `python main.py` -> 2 | Pygame图形窗口 |
| GUI直达 | `python main.py --gui` | 跳过菜单直接GUI |

---

## 测试

```bash
PYTHONIOENCODING=utf-8 python tests/test_game_flow.py
PYTHONIOENCODING=utf-8 python tests/test_clean_system.py
PYTHONIOENCODING=utf-8 python tests/test_passive_skills.py
```
