set PYTHONIOENCODING=utf-8set PYTHONIOENCODING=utf-8# AGENTS.md - 三国武将卡牌游戏

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
- **属性→被动技能映射**: 勇猛/魅力/募兵/防栅/连计/复活/伏兵 → 7个被动技能

## 关键设计约束

1. **被动技能每次新建**: `get_passive_skills_for_attributes()` 从 `ATTRIBUTE_TO_PASSIVE_CLASS`（类引用）实例化，不可共享单例
2. **General.is_alive 是 bool 属性**，不是方法
3. **Team 的 max_morale 参数**在 __init__ 中会被强制设为12（不通过参数修改），初始士气=12
4. **技能冷却由 General.active_skill_cooldown 管理**，不是 Skill 对象

## 武将卡生成约定

- **默认生成卡图**: 用户要求“生成武将”时，默认包含视觉武将卡生成与项目图片替换；若用户未给特殊视觉要求，应根据人物生平、阵营、技能和既有卡面约定自行设计。
- **阵营主色**: 魏=黑红，西凉=黑金，吴=蓝色，蜀=绿色，袁=紫色，他=黑灰。这里的主色主要指卡片左侧栏、势力栏、主要UI面板和阵营识别，不强制武将服装同色。
- **禁止金粉风格**: 后续武将卡不要金粉、金色粒子、碎光、满屏火星、黄金甲、大面积金色浮雕或复杂金属花边。需要金色时只能作为干净的哑光色块或清晰边线，不能呈现撒金粉、闪亮金属金、画面脏乱的效果。
- **参考视觉方向**: 参考 `assets/images/generals/IMG_20260616_214750.jpg`。优先使用干净大色块、黑/白/银/阵营色硬边、清晰人物轮廓、适度留白、简洁卡框。避免把每个角落都塞满装饰。
- **兵种图标**: 卡面左下角兵种/类型图标要按武将定位设计。骑将可用马/骑兵，典韦这类步战猛将可用步兵/重步兵，谋士可用羽扇/书卷，女性辅助或非传统武将要设计对应的辅助、舞姬、医护、魅力等类型图标。已生成卡无需回头重做。
- **新武将背景**: 新添加工程中不存在的武将时，除 `generals_data.py` 外，还要在 `game_data/generals_bios.py` 添加对应生平简介 `text`/`description` 内容。
- **图片失败兜底**: 若武将卡生成后无法下载或保存到本地，直接在 `assets/images/generals/` 下创建对应文件名的空 PNG，占位供用户后续手动替换。

## 已知问题与下一步

| 优先级 | 问题 | 说明 |
|--------|------|------|
| 🟡 | 数值未经过平衡测试 | 27武将的 force/intelligence/cost 需要实际对战验证 |
| 🟡 | GUI 战前阶段 | 选将/布阵目前仍用CLI，GUI只覆盖了战斗阶段 |
| 🟡 | Pygame 未安装 | 当前环境无 pygame，GUI模式需 `pip install pygame` |
| 🟢 | 武将图片 | assets/images/generals/ 存放武将卡图资源；缺图时运行时使用 fallback 图 |
| 🟢 | Windows编码 | emoji/中文输出需 PYTHONIOENCODING=utf-8 |
| 🟢 | 数值微调 | generals_data.py 纯数据文件可随时修改

## 当前武将数据

全部武将数据定义在 **[game_data/generals_data.py](game_data/generals_data.py)**（纯数据文件，无逻辑）。
修改数值、添加新武将都在该文件中操作，无需改其他文件。

共计 **40 名武将**：
- 蜀 6：张飞 / 诸葛亮 / 夏侯月姬 / 周仓 / 马岱 / 姜维
- 魏 10：曹操 / 夏侯惇 / 曹仁 / 贾诩 / 王异 / 许褚 / 夏侯渊 / 郭皇后 / 蔡文姬 / 于禁
- 吴 6：甘宁 / 鲁肃 / 大乔 / 小乔 / 太史慈 / 朱然
- 凉 6：吕布 / 张辽 / 董卓 / 陈宫 / 邹氏 / 李傕和郭汜
- 袁 4：田丰 / 于夫罗 / 张郃 / 文丑
- 他 8：张任 / 汉献帝 / 司马徽 / 皇甫嵩 / 公孙瓒 / 张角 / 带来洞主 / 王允

## 运行方式

```bash
PYTHONIOENCODING=utf-8 python main.py        # 启动游戏 (CLI)
PYTHONIOENCODING=utf-8 python tests/test_game_flow.py  # 运行主流程测试
```
