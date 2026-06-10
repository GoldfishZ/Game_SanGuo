# CLAUDE.md - 三国武将卡牌游戏

## 项目概述

基于 Python 开发的三国主题武将卡牌对战游戏，卡牌原型来自霸·三国志大战。
两名玩家轮流操作，每回合：技能阶段 → 普攻阶段。一方全部武将阵亡则游戏结束。

## 核心架构

```
game_data/                  # 游戏数据层
├── generals_config.py      # 武将创建工厂函数 + GENERAL_CREATORS 字典
├── skills_config.py        # 主动技能定义 (ALL_SKILLS 字典)
├── passive_skills_config.py # 被动技能类和属性→技能类映射
├── game_data_manager.py    # 统一数据查询接口 (GameDataManager)
└── generals_gallery.py     # 图鉴演示工具

src/models/                 # 数据模型
├── general.py              # General(武将): force/intelligence/cost/attribute，伤害计算，技能使用
├── team.py                 # Team(队伍): 3×4阵型，士气管理，前排掩护机制
└── game_flow.py            # GameFlowController: 选将→布阵→骰子→战斗→结束 完整流程

src/skills/
└── skill_base.py           # Skill(抽象基类), DamageSkill, EnhanceWeakenSkill, PassiveSkill

src/battle/                 # ⚠️ 旧战斗系统遗留代码，与当前架构不兼容
src/ui/                     # ⚠️ 旧Pygame GUI，与当前系统脱节
tests/                      # 测试文件
```

## 游戏规则摘要

- **阵型**: 3行×4列，前列武将挡住后列，只能攻击敌方最前排
- **伤害**: 攻击方force > 目标force → damage=force差；否则 damage = min(3, (force+int)差)，最低1
- **士气**: 初始12点，主动技能消耗士气。队伍共用士气池
- **先手**: 抛骰子(1-6)决定，后手补偿士气上限+2
- **属性→被动技能映射**: 勇猛/魅力/募兵/防栅/连环/复活/伏兵 → 7个被动技能

## 关键设计约束

1. **被动技能每次新建**: `get_passive_skills_for_attributes()` 从 `ATTRIBUTE_TO_PASSIVE_CLASS`（类引用）实例化，不可共享单例
2. **General.is_alive 是 bool 属性**，不是方法
3. **Team 的 max_morale 参数**在 __init__ 中会被强制设为12（不通过参数修改），初始士气=12
4. **技能冷却由 General.active_skill_cooldown 管理**，不是 Skill 对象

## 已知问题与下一步

| 优先级 | 问题 | 说明 |
|--------|------|------|
| 🔴 | 武将池仅3人 | 张任/金环三结/鲁肃，15人随机池只能重复 |
| 🔴 | 旧系统遗留 | src/models/game.py + src/battle/* + src/ui/* 与当前架构脱节 |
| 🟡 | 判定系统留白 | 勇猛/魅力的 judgment_check() 默认返回 True |
| 🟡 | 连环未集成 | 连环被动技能需要团队系统配合才能正确工作 |
| 🟡 | test_skill_cooldown.py | 引用已删除的旧武将，需重写 |
| 🟢 | Pygame GUI | 需从头重做以适应新系统 |
| 🟢 | Windows编码 | emoji/中文输出需 PYTHONIOENCODING=utf-8 |

## 当前武将数据

| 武将 | 阵营 | 稀有度 | 武力 | 智力 | 生命 | 属性 | 主动技能 |
|------|------|--------|------|------|------|------|----------|
| 张任 | 他 | COMMON | 6 | 6 | 12 | 伏兵 | 强化战术(武力+4) |
| 金环三结 | 他 | COMMON | 3 | 1 | 4 | - | 强化战术(武力+4) |
| 鲁肃 | 吴 | RARE | 4 | 8 | 12 | 防栅 | 同盟缔结(士气上限+2) |

## 运行方式

```bash
PYTHONIOENCODING=utf-8 python main.py        # 启动游戏 (CLI)
PYTHONIOENCODING=utf-8 python tests/test_game_flow.py  # 运行主流程测试
```
