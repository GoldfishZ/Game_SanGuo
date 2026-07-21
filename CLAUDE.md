# CLAUDE.md - 三国武将卡牌游戏

## 项目概述

基于 Python 开发的三国主题武将卡牌对战游戏，卡牌原型来自霸·三国志大战。
两名玩家轮流操作，每回合：技能阶段 → 普攻阶段。一方全部武将阵亡则游戏结束。

## 核心架构

```
src/game_data/              # 游戏数据层
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

src/battle/                 # 战斗容器、上下文与逐动作结算（Web/RL 共用）
src/rl/                     # 本地离线 PPO 环境、训练、评估与强度分析
src/ui/                     # ⚠️ 旧 Pygame GUI，与当前 Web 流程部分脱节
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
- **阵营主色**: 魏=黑红，西凉=黑金，吴=蓝色，蜀=绿色，袁=紫色，他=黑灰。主色用于卡片左侧栏、势力栏、主要 UI 面板与阵营识别，不强制武将服装同色。
- **避免金粉风格**: 禁止金色粒子、碎光、满屏火星、黄金甲、大面积金色浮雕和复杂金属花边。金色只能作为干净哑光色块或清晰边线，避免脏乱闪亮的“撒金粉”效果。
- **卡面方向**: 参考 `assets/images/generals/IMG_20260616_214750.jpg`；优先干净大色块、黑/白/银/阵营色硬边、清晰人物轮廓、适度留白和简洁卡框。
- **兵种图标**: 卡面左下角图标必须匹配定位：骑将使用马/骑兵，步战猛将使用步兵/重步兵，谋士使用羽扇/书卷，女性辅助或非传统武将使用辅助、舞姬、医护、魅力等对应图标。既有卡无需回头重做。
- **新增武将生平**: 新添加工程中不存在的武将时，除 `generals_data.py` 外，还要在 `src/game_data/generals_bios.py` 添加 `text`/`description` 生平简介。
- **图片失败兜底**: 若武将卡生成后无法下载或保存到本地，直接在 `assets/images/generals/` 下创建对应文件名的空 PNG，占位供用户后续手动替换。

## 已知问题与下一步

| 优先级 | 问题 | 说明 |
|--------|------|------|
| 🟡 | 数值未经过平衡测试 | 40 名武将的 force/intelligence/cost 需要通过对局与 RL 强度报告验证 |
| 🟡 | GUI 战前阶段 | 选将/布阵目前仍用 CLI，GUI 只覆盖了战斗阶段 |
| 🟢 | 网页 PvE | 本地 PPO 训练已实现，训练模型尚未接入 Web API 和前端 |
| 🟢 | 武将图片 | assets/images/generals/ 存放武将卡图资源；缺图时运行时使用 fallback 图；生成失败时创建空 PNG 供手动替换 |
| 🟢 | Windows编码 | emoji/中文输出需 PYTHONIOENCODING=utf-8 |
| 🟢 | 数值微调 | generals_data.py 纯数据文件可随时修改

## 当前武将数据

全部武将数据定义在 **[src/game_data/generals_data.py](src/game_data/generals_data.py)**（纯数据文件，无逻辑）。
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
PYTHONIOENCODING=utf-8 python main_web.py    # 启动 Web 服务器 (http://localhost:8089)
PYTHONIOENCODING=utf-8 python tools/testing/run_tests.py  # 运行完整测试套件
PYTHONIOENCODING=utf-8 python tools/rl/train_ppo.py --stage random --device auto  # 本地 PPO 训练
```

## Web 前端架构 (2026-06-26 重构)

```
src/web/static/
├── index.html          # HTML 骨架（8 个游戏屏幕 + 教程遮罩）
├── styles.css          # 所有 CSS（三国主题、阵营卡牌、战斗特效、响应式）
├── game.js             # 游戏逻辑（API 调用、渲染、FX 特效系统、战斗动画）
├── tooltips.js         # 悬浮提示系统（data-tooltip 属性自动绑定，300ms 延迟）
└── tutorial.js         # 新手教程（localStorage 记录，4 步引导：选将→布阵→技能→普攻）
```

- **零构建工具**：纯 HTML/CSS/JS，无框架无打包
- **图片已优化**：WebP 格式，241MB → 8.1MB（96.6% 减少），服务器自动将 .png 请求转为 .webp
- **技能特效**：8 种技能类型专属 Canvas 粒子效果（火、雷、斩击、治疗、Debuff、士气、阵亡、阵型）
- **阵营卡牌**：CSS 类 `.card-shu/.wei/.wu/.liang/.yuan/.ta` 提供独特边框和光效
- **缓存策略**：图片 7 天，CSS/JS 1 小时，HTML 不缓存

## 本地 RL 训练

- 训练系统完整说明：[`docs/rl-training.md`](docs/rl-training.md)
- Windows/CUDA 启动指南：[`docs/rl-training-windows.md`](docs/rl-training-windows.md)
- 全流程 PvE AI（选将、布阵、协同 telemetry 与价值模型）设计：[`docs/pve-ai-architecture.md`](docs/pve-ai-architecture.md)
- 训练模型目前只用于本地环境、评估和武将平衡分析；网页 PvE 接入是后续工作。

## 工具脚本

```bash
python tools/testing/validate_html_templates.py   # 校验 HTML 标签配对
python tools/assets/optimize_images.py            # PNG→WebP 批量转换
```
