# 前端架构文档 — 三国武将卡牌游戏

> v7 — 2026-06-29 全面审查清理版

## 文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `index.html` | ~220 | HTML 骨架，8 个屏幕 + 教程遮罩 + Canvas |
| `styles.css` | ~370 | 三国主题样式、阵营卡牌、战场布局、特效动画 |
| `game.js` | ~550 | 游戏核心逻辑（状态/通信/渲染/交互/特效） |
| `tooltips.js` | ~70 | 悬浮提示系统（data-tooltip 自动绑定） |
| `tutorial.js` | ~200 | 新手教程（localStorage + 4步引导） |

## game.js 架构

```
┌─────────────────────────────────────────────────────┐
│ SECTION 1: 全局状态 & 工具函数                        │
│   G, selectedGenerals, selectedFormGen,              │
│   selectedAttacker, battlePhase                      │
│   setStatus(), showScreen(), currentTeamKey(),       │
│   currentTeamData(), enemyTeamData(), findGeneral()  │
├─────────────────────────────────────────────────────┤
│ SECTION 2: API 通信层                                │
│   api() — fetch 封装 + 错误处理                      │
│   call() — POST /api/<endpoint>，自动更新 G          │
├─────────────────────────────────────────────────────┤
│ SECTION 3-5: 战前流程                                 │
│   选将 → 布阵 → 骰子                                 │
├─────────────────────────────────────────────────────┤
│ SECTION 6: 战斗渲染                                   │
│   renderBattle() — 主渲染入口                         │
│   renderBattleGrid() — 网格渲染                       │
│   buildBcellHTML() — 单格 HTML（纯函数）              │
│   updateMoraleBars(), highlightActiveSide()          │
├─────────────────────────────────────────────────────┤
│ SECTION 7: 战斗交互                                   │
│   事件委托 (bcell click → onBattleAlly/EnemyCell)    │
│   updateBattlePhaseUI() — 按钮状态管理               │
│   useSkill() — 技能使用（校验→动画→API→特效）        │
│   chooseAttack() → onBattleEnemyCell() — 普攻流程    │
│   skipPhase() — 跳过回合                              │
├─────────────────────────────────────────────────────┤
│ SECTION 8: 游戏结束 & 图鉴                            │
├─────────────────────────────────────────────────────┤
│ SECTION 9: Canvas 特效系统 (FX IIFE)                  │
│   burst, fireBurst, lightningStrike, slashTrail,     │
│   healSparkles, debuffMiasma, moraleWave,            │
│   deathShatter, formationSwap, drawWeaponArc         │
│   skillEffect(), detectSkillType()                   │
├─────────────────────────────────────────────────────┤
│ SECTION 10: 战斗动画工具                              │
│   getCellCenter, spawnFloatNum, spawnSkillLabel,     │
│   animAttack, animSkill                              │
└─────────────────────────────────────────────────────┘
```

## 核心数据流

```
用户点击 → 事件委托 → onBattleAllyCell/onBattleEnemyCell
                              ↓
                     更新 selectedAttacker/battlePhase
                              ↓
                         renderBattle()
                              ↓
              call("/api/battle/skill") 或 call("/api/battle/attack")
                              ↓
                       G = API响应 (JSON)
                              ↓
                         renderBattle()
                              ↓
                  updateMoraleBars + renderBattleGrid + updateBattlePhaseUI
```

## 关键约定

### 1. G 是唯一数据源
- `G` 存储完整游戏状态（等同于 `/api/state` 返回值）
- 任何状态变更通过 `call(endpoint, body)` → `G = response`
- 所有渲染函数从 `G` 读取数据，不维护本地副本

### 2. 面板布局固定
- `bside1` / `bside1-grid` = **始终 P1**（上半区）
- `bside2` / `bside2-grid` = **始终 P2**（下半区）
- `current_team` 决定 `isAlly` 标志，**不交换面板位置**

### 3. 网格视觉布局
```
P1 面板 (bside1-grid):
  后排(row=2) → grid-row:1 ← 视觉顶部
  中坚(row=1) → grid-row:2
  前排(row=0) → grid-row:3 ← 视觉底部
═══════════ 战场中线 ═══════════
P2 面板 (bside2-grid):
  前排(row=0) → grid-row:1 ← 视觉顶部
  中坚(row=1) → grid-row:2
  后排(row=2) → grid-row:3 ← 视觉底部
```

### 4. 己方/敌方搜索规则
- `onBattleAllyCell`: 先搜当前回合方，再搜对方
- `onBattleEnemyCell`: 先搜敌方，再搜己方
- `useSkill` / 格子查找: 用 `G.current_team` 判断身份

### 5. 状态栏日志
- 所有用户可见状态通过 `setStatus(msg)` 更新
- 不要直接 `document.getElementById("battle-status").textContent = ...`
- 便于调试和追踪交互流程

## fetch → call → api 调用链

```
call(endpoint, body)
  └→ api("POST", "/api" + endpoint, body)
      └→ fetch(path, {method, headers, body})
          ├ 成功: r.json() → SERVER_OK=true → return data
          └ 失败: catch → console.error → return null
  └→ if (r) G = r
  └→ return r
```

**注意**: `call()` 失败时返回 `null` 且 `G` 保持旧值。调用方必须检查返回值：
```javascript
var result = await call("/battle/skill", {...});
if (!result) { /* 处理失败 */ }
```

## 后端 API 对照表

| 前端调用 | 后端端点 | 请求体 | 更新 G |
|---------|---------|--------|--------|
| `call("/new")` | POST /api/new | `{}` | ✓ |
| `call("/select", {general_ids})` | POST /api/select | `{general_ids: [int]}` | ✓ |
| `call("/place", {positions})` | POST /api/place | `{positions: [{general_id, row, col}]}` | ✓ |
| `call("/dice")` | POST /api/dice | `{}` | ✓ |
| `call("/battle/skill", {general_id})` | POST /api/battle/skill | `{general_id: int}` | ✓ |
| `call("/battle/attack", {attacker_id, target_id, guess})` | POST /api/battle/attack | `{attacker_id, target_id, guess?}` | ✓ |
| `call("/battle/skip")` | POST /api/battle/next | `{}` | ✓ |
| `call("/state")` | GET /api/state | - | ✓ |

## G (游戏状态) JSON 结构

```json
{
  "phase": "battle",
  "event": "技能/攻击描述文本",
  "turn": 3,
  "winner": "",
  "cost_limit": 8.0,
  "current_team": "p1",
  "current_player": "玩家1",
  "first": "玩家1",
  "second": "玩家2",
  "d1": 5, "d2": 3,
  "compensation": "玩家2 后手，士气上限+2",
  "p1": {
    "name": "玩家1",
    "morale": 6, "maxMorale": 12,
    "generals": [{
      "name": "吕布", "id": 3001,
      "hp": 12, "maxHp": 14,
      "force": 10, "intelligence": 1,
      "effective_force": 16, "effective_intelligence": 1,
      "alive": true,
      "row": 0, "col": 0,
      "skill": "天下无双", "skill_desc": "...",
      "cooldown": 0,
      "image": "lv_bu.png",
      "attributes": ["勇猛"],
      "_hasAttacked": false, "_hasUsedSkill": true,
      "_hasSpeedJudgment": false, "_hasSpeedRequired": false,
      "_ambushHidden": false, "_ambushTriggered": false,
      "_fenceBroken": false, "_reviveUsed": false
    }]
  },
  "p2": { /* 同上 */ }
}
```

## 调试技巧

1. **浏览器 F12 → Console** 查看 `"=== v7 已加载 ==="` 确认版本
2. **页面底部状态栏** (`#battle-status`) 显示所有交互反馈
3. **Network 标签** 查看 `/api/*` 请求的响应内容
4. **Application → Local Storage** 查看 `sanguo_play_count` 和 `sanguo_tutorial_seen`
5. **HTML 验证**: `python tools/testing/validate_html_templates.py`
