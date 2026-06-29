/**
 * 三国武将卡牌游戏 — 前端核心逻辑
 * v7 — 2026-06-29 全面审查清理版
 *
 * 架构概览:
 *   [状态层] G(全局游戏状态) + 5个页面状态变量
 *   [通信层] api() / call() — JSON REST 封装
 *   [渲染层] render*() — 纯函数，从 G 生成 DOM
 *   [交互层] onBattle*() / useSkill() / chooseAttack() — 事件处理
 *   [特效层] FX — Canvas 粒子系统
 *
 * 关键约定:
 *   - G 是唯一数据源，任何状态变更通过 call() → G 更新 → render*()
 *   - 所有 DOM 状态文本通过 setStatus() 更新，便于调试
 *   - P1=bside1(上半区), P2=bside2(下半区)，固定不变
 *   - current_team 决定 isAlly，不交换面板位置
 */

// ============================================================================
// SECTION 1: 全局状态 & 工具函数
// ============================================================================
console.log("=== 三国武将卡牌游戏 v7 已加载 ===");

var G = null;                       // 完整游戏状态 (来自 /api/state)
var selectedGenerals = [];          // 选将池中的武将 ID
var selectedFormGen = null;         // 布阵时选中的武将
var battlePhase = "select";         // "select" | "action" | "target"
var selectedAttacker = null;        // 战斗中选中的己方武将 {general, row, col}
var galleryIdx = 0;
var galleryFiltered = [];

/** 更新战斗状态栏文本（统一入口，便于调试） */
function setStatus(msg) {
  var el = document.getElementById("battle-status");
  if (el) el.textContent = msg;
}

/** 屏幕切换 */
function showScreen(name) {
  document.querySelectorAll(".screen").forEach(function(s) { s.classList.remove("active"); });
  var el = document.getElementById("scr-" + name);
  if (el) el.classList.add("active");
  if (name === "gallery") initGallery();
}

/** 根据 current_team 获取队伍标识 ("p1"|"p2") */
function currentTeamKey() {
  return (G && G.current_team === "p1") ? "p1" : "p2";
}

/** 当前回合方数据 */
function currentTeamData() {
  var key = currentTeamKey();
  return G ? G[key] : null;
}

/** 敌方数据 */
function enemyTeamData() {
  var key = currentTeamKey() === "p1" ? "p2" : "p1";
  return G ? G[key] : null;
}

/** 在队伍数据中按行列查找存活武将 */
function findGeneral(p, r, c) {
  if (!p || !p.generals) return null;
  for (var i = 0; i < p.generals.length; i++) {
    var g = p.generals[i];
    if (g.row === r && g.col === c && g.alive) return g;
  }
  return null;
}

/** 清除战斗选中状态 */
function clearBattleSelection() {
  selectedAttacker = null;
  battlePhase = "select";
}

// ============================================================================
// SECTION 2: API 通信层
// ============================================================================
var SERVER_OK = false;

function api(method, path, body) {
  return fetch(path, {
    method: body ? "POST" : (method || "GET"),
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined
  }).then(function(r) {
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
  }).then(function(data) {
    SERVER_OK = true;
    return data;
  }).catch(function(e) {
    console.error("API error:", path, e);
    if (!SERVER_OK) {
      document.body.innerHTML =
        '<div style="padding:40px;text-align:center;color:#c07070">' +
        '<h2>无法连接到游戏服务器</h2>' +
        '<p>请先运行: <code style="background:#1a1410;padding:6px 12px;border-radius:4px">python main_web.py</code></p>' +
        '<p style="color:#8a7a5a;margin-top:12px">然后访问 <code>http://localhost:8088</code></p>' +
        '</div>';
    }
    return null;
  });
}

/** POST /api/<endpoint>，自动更新 G */
function call(endpoint, body) {
  return api("POST", "/api" + endpoint, body || {}).then(function(r) {
    if (r) G = r;
    return r;
  });
}

// ============================================================================
// SECTION 3: 主菜单 & 选将
// ============================================================================
function startGame() {
  return call("/new").then(function() { return renderSelection(); });
}

function renderSelection() {
  showScreen("select");
  selectedGenerals = [];
  var r = G;
  if (!r) return;
  document.getElementById("sel-title").textContent =
    (r.phase === "select_p1" ? "玩家1" : "玩家2") + " — 选择武将";
  renderCards(r.pool);
  renderPoolBar();
}

function renderCards(pool) {
  var ATTR = {
    "勇猛": {c:"#c04840",l:"勇"}, "魅力": {c:"#b050b8",l:"魅"},
    "募兵": {c:"#48a048",l:"募"}, "防栅": {c:"#4868c0",l:"防"},
    "连环": {c:"#b09830",l:"连"}, "复活": {c:"#d06840",l:"复"},
    "伏兵": {c:"#5068b8",l:"伏"}
  };
  var html = "";
  (pool || []).forEach(function(g) {
    var inPool = selectedGenerals.includes(g.id);
    var imgSrc = g.image ? "/generals/" + g.image : "";
    var attrTags = (g.attributes || []).map(function(a) {
      var ac = ATTR[a] || {c:"#666", l:a[0]};
      return '<span style="background:' + ac.c + ';color:#fff;font-size:9px;width:18px;height:18px;display:inline-flex;align-items:center;justify-content:center;border-radius:50%;font-weight:700;border:1px solid rgba(255,255,255,.2);text-shadow:0 1px 2px rgba(0,0,0,.3)">' + ac.l + '</span>';
    }).join("");
    html +=
      '<div class="card card-' + (g.camp || "ta") + (inPool ? " selected" : "") +
      '" onclick="showGeneralPreview(event,\'' + g.id + '\')" data-id="' + g.id +
      '" style="' + (inPool ? "opacity:.5" : "") + '">' +
      (imgSrc ? '<img src="' + imgSrc + '" alt="' + g.name + '" onerror="this.style.display=\'none\';this.nextSibling.style.display=\'flex\'">' : "") +
      '<div style="width:100%;height:100%;display:' + (imgSrc ? "none" : "flex") +
      ';align-items:center;justify-content:center;font-size:28px;color:#8a7a5a">' + g.name[0] + '</div>' +
      (attrTags ? '<div style="position:absolute;top:6px;right:6px;display:flex;gap:3px">' + attrTags + '</div>' : "") +
      (inPool ? '<div class="badge">✓</div>' : "") +
      '</div>';
  });
  document.getElementById("sel-cards").innerHTML = html;
}

function renderPoolBar() {
  var poolEl = document.getElementById("sel-pool-area");
  var selGens = selectedGenerals.map(function(id) {
    return G && G.pool ? G.pool.find(function(g) { return g.id == id; }) : null;
  }).filter(Boolean);
  var costLimit = G ? (G.cost_limit || 8.0) : 8.0;
  var spent = selGens.reduce(function(sum, g) { return sum + (g.cost || 0); }, 0);
  var remaining = Math.max(0, costLimit - spent);

  var html = '<div style="display:flex;align-items:center;gap:10px;margin-right:12px;padding:2px 12px;background:rgba(200,170,70,.1);border-radius:6px;border:1px solid ' +
    (remaining > 0 ? "var(--gold)" : "#a0524d") + '">' +
    '<span style="font-size:11px;color:var(--muted)">费用</span>' +
    '<span style="font-size:18px;font-weight:700;color:' + (remaining > 0 ? "var(--gold)" : "#c07070") + '">' + remaining + '</span>' +
    '<span style="font-size:10px;color:var(--muted)">/' + costLimit + '</span></div>';

  html += selGens.map(function(g) {
    return '<div style="background:var(--panel);border:1px solid var(--gold);border-radius:6px;padding:4px 10px;cursor:pointer;display:flex;align-items:center;gap:6px;font-size:12px" onclick="removeFromPool(' + g.id + ')">' +
      '<span style="color:var(--muted);font-size:10px">' + g.cost + '费</span>' +
      '<span style="font-weight:700">' + g.name + '</span>' +
      '<span style="color:var(--muted);font-size:10px">×</span></div>';
  }).join("");

  if (selGens.length === 0) {
    html += '<span id="sel-pool-empty" style="font-size:11px;color:var(--muted);padding:4px 12px">点击武将卡预览后「加入选将池」</span>';
  }
  poolEl.innerHTML = html;
  document.getElementById("sel-done").disabled = selectedGenerals.length === 0;
  document.getElementById("sel-done").textContent =
    "完成选择 (" + selectedGenerals.length + "人 · " + spent + "/" + costLimit + "费)";
}

/** 武将预览 HTML（单一来源，showGeneralPreview 和 togglePool 共用） */
function previewInfoHTML(g, inPool) {
  return g.camp + " · " + g.rarity + " · 费用" + g.cost + "<br>" +
    "武" + g.force + " 智" + g.intelligence + " · " + g.skill + "<br>" +
    "属性: " + ((g.attributes || []).join(" · ") || "无") + "<br>" +
    '<small style="color:var(--muted)">' + (g.skill_desc || "") + '</small><br><br>' +
    '<span class="btn ' + (inPool ? "danger" : "primary") +
    '" style="font-size:12px;padding:4px 14px" onclick="togglePool(\'' + g.id + '\')">' +
    (inPool ? "移出选将池" : "加入选将池") + '</span>';
}

function showGeneralPreview(evt, id) {
  var g = G && G.pool ? G.pool.find(function(x) { return x.id == id; }) : null;
  if (!g) return;
  var inPool = selectedGenerals.includes(id);
  document.getElementById("preview-img").src = g.image ? "/generals/" + g.image : "";
  document.getElementById("preview-name").textContent = g.name;
  document.getElementById("preview-info").innerHTML = previewInfoHTML(g, inPool);
  document.getElementById("preview").style.display = "flex";
}

function togglePool(id) {
  if (selectedGenerals.includes(id)) {
    selectedGenerals = selectedGenerals.filter(function(x) { return x !== id; });
  } else {
    var g = G && G.pool ? G.pool.find(function(x) { return x.id == id; }) : null;
    var costLimit = G ? (G.cost_limit || 8.0) : 8.0;
    var spent = selectedGenerals.reduce(function(sum, x) {
      var gen = G && G.pool ? G.pool.find(function(g2) { return g2.id == x; }) : null;
      return sum + (gen ? gen.cost : 0);
    }, 0);
    if (g && spent + g.cost > costLimit) {
      alert("费用不足！\n当前已用 " + spent + " 费，" + g.name + " 需要 " + g.cost + " 费，剩余 " + (costLimit - spent).toFixed(1) + " 费");
      return;
    }
    selectedGenerals.push(id);
  }
  renderCards(G.pool);
  renderPoolBar();
  var g2 = G && G.pool ? G.pool.find(function(x) { return x.id == id; }) : null;
  if (g2 && document.getElementById("preview").style.display === "flex") {
    document.getElementById("preview-info").innerHTML = previewInfoHTML(g2, selectedGenerals.includes(id));
  }
}

function removeFromPool(id) {
  selectedGenerals = selectedGenerals.filter(function(x) { return x !== id; });
  renderCards(G.pool);
  renderPoolBar();
}

function closePreview() {
  document.getElementById("preview").style.display = "none";
}

function confirmSelection() {
  if (selectedGenerals.length === 0) return;
  return call("/select", { general_ids: selectedGenerals }).then(function() {
    if (G.phase === "select_p2") {
      selectedGenerals = [];
      return renderSelection();
    }
    return renderFormation();
  });
}

// ============================================================================
// SECTION 4: 布阵
// ============================================================================
function renderFormation() {
  showScreen("formation");
  selectedFormGen = null;
  var r = G;
  if (!r) return;
  var teamKey = r.phase === "formation_p1" ? "p1" : "p2";
  document.getElementById("form-title").textContent =
    (r.phase === "formation_p1" ? "玩家1" : "玩家2") + " — 布置阵型";
  var generals = r[teamKey] ? (r[teamKey].generals || []) : [];
  renderFormList(generals);
  renderFormGrid(generals);
}

function renderFormList(generals) {
  var html = (generals || []).map(function(g) {
    var isActive = selectedFormGen && selectedFormGen.id === g.id;
    return '<div class="gi' + (isActive ? " active" : "") + '" onclick="selectFormGen(' + g.id + ')">' +
      '<span style="font-weight:600">' + g.name + '</span>' +
      '<span style="font-size:10px;color:var(--muted);margin-left:6px">' +
      (g.row >= 0 ? "已放:(" + g.row + "," + g.col + ")" : "未放置") + '</span></div>';
  }).join("");
  document.getElementById("form-list").innerHTML = html ||
    '<div style="font-size:11px;color:var(--muted);padding:8px">无武将可选</div>';
}

function renderFormGrid(generals) {
  var grid = [[null,null,null,null], [null,null,null,null], [null,null,null,null]];
  (generals || []).forEach(function(g) {
    if (g.row >= 0 && g.col >= 0) grid[g.row][g.col] = g;
  });
  var html = "";
  for (var r = 0; r < 3; r++) {
    for (var c = 0; c < 4; c++) {
      var g = grid[r][c];
      if (g) {
        html += '<div class="form-cell filled" onclick="placeGeneral(' + r + ',' + c + ')">' + g.name + '</div>';
      } else {
        html += '<div class="form-cell' + (selectedFormGen ? " droptarget" : "") + '" onclick="placeGeneral(' + r + ',' + c + ')">+</div>';
      }
    }
  }
  document.getElementById("form-grid").innerHTML = html;
}

function selectFormGen(id) {
  var teamKey = G.phase === "formation_p1" ? "p1" : "p2";
  var generals = G[teamKey] ? (G[teamKey].generals || []) : [];
  selectedFormGen = generals.find(function(g) { return g.id === id; });
  if (!selectedFormGen) return;
  renderFormList(generals);
  renderFormGrid(generals);
}

function placeGeneral(r, c) {
  if (!selectedFormGen) return;
  var teamKey = G.phase === "formation_p1" ? "p1" : "p2";
  var generals = G[teamKey] ? (G[teamKey].generals || []) : [];
  // 清除该位置的旧武将
  generals.forEach(function(g) {
    if (g.id !== selectedFormGen.id && g.row === r && g.col === c) { g.row = -1; g.col = -1; }
  });
  selectedFormGen.row = r;
  selectedFormGen.col = c;
  renderFormList(generals);
  renderFormGrid(generals);
}

function confirmFormation() {
  var teamKey = G.phase === "formation_p1" ? "p1" : "p2";
  var generals = G[teamKey] ? (G[teamKey].generals || []) : [];
  var positions = generals
    .filter(function(g) { return g.row >= 0 && g.col >= 0; })
    .map(function(g) { return { general_id: g.id, row: g.row, col: g.col }; });

  if (positions.length < generals.length) {
    document.getElementById("form-hint").textContent = "请将所有武将放置到阵型中";
    return;
  }
  return call("/place", { positions: positions }).then(function() {
    if (G.phase === "formation_p2") {
      selectedFormGen = null;
      return renderFormation();
    }
    showScreen("dice");
  });
}

// ============================================================================
// SECTION 5: 骰子
// ============================================================================
function rollDice() {
  return call("/dice").then(function() {
    var finalD1 = G.d1 || 1;
    var finalD2 = G.d2 || 1;
    var d1El = document.getElementById("d1");
    var d2El = document.getElementById("d2");
    var resultEl = document.getElementById("dice-result");
    var totalFrames = 20, frame = 0;

    function tick() {
      if (frame < totalFrames) {
        d1El.textContent = Math.floor(Math.random() * 6) + 1;
        d2El.textContent = Math.floor(Math.random() * 6) + 1;
        frame++;
        setTimeout(tick, 30 + (frame / totalFrames) * 120);
      } else {
        d1El.textContent = finalD1;
        d2El.textContent = finalD2;
        if (finalD1 > finalD2) { d1El.style.color = "#ff6040"; d1El.style.fontSize = "80px"; }
        else if (finalD2 > finalD1) { d2El.style.color = "#ff6040"; d2El.style.fontSize = "80px"; }
        resultEl.textContent = (G.first || "") + " 先手！" + (G.compensation || "");
        setTimeout(function() { renderBattle(); }, 2000);
      }
    }
    tick();
  });
}

// ============================================================================
// SECTION 6: 战斗渲染
// ============================================================================

/** 更新双方士气条 */
function updateMoraleBars(r) {
  document.getElementById("m1name").textContent = r.p1 ? r.p1.name : "玩家1";
  document.getElementById("m2name").textContent = r.p2 ? r.p2.name : "玩家2";
  document.getElementById("m1text").textContent = (r.p1 ? r.p1.morale : 0) + "/" + (r.p1 ? r.p1.maxMorale : 12);
  document.getElementById("m2text").textContent = (r.p2 ? r.p2.morale : 0) + "/" + (r.p2 ? r.p2.maxMorale : 12);
  document.getElementById("m1fill").style.width = (r.p1 && r.p1.maxMorale ? (r.p1.morale / r.p1.maxMorale * 100) : 0) + "%";
  document.getElementById("m2fill").style.width = (r.p2 && r.p2.maxMorale ? (r.p2.morale / r.p2.maxMorale * 100) : 0) + "%";
}

/** 高亮当前行动方 */
function highlightActiveSide(r) {
  var b1 = document.getElementById("bside1");
  var b2 = document.getElementById("bside2");
  if (!b1 || !b2) return;
  if (r.current_team === "p1") {
    b1.style.borderColor = "var(--gold-bright)";
    b1.style.boxShadow = "0 0 20px rgba(228,192,96,.35)";
    b2.style.borderColor = "rgba(201,168,76,.22)";
    b2.style.boxShadow = "none";
  } else {
    b2.style.borderColor = "var(--gold-bright)";
    b2.style.boxShadow = "0 0 20px rgba(228,192,96,.35)";
    b1.style.borderColor = "rgba(201,168,76,.22)";
    b1.style.boxShadow = "none";
  }
}

function renderBattle() {
  var r = G;
  if (!r) return call("/state").then(renderBattle);

  try {
    showScreen("battle");
    updateMoraleBars(r);

    document.getElementById("bturn").textContent =
      "第" + (r.turn || 1) + "回合 — " + (r.current_player || "");

    var p1IsAlly = (r.current_team === "p1");
    renderBattleGrid("bside1-grid", r.p1, p1IsAlly);
    renderBattleGrid("bside2-grid", r.p2, !p1IsAlly);
    highlightActiveSide(r);

    setStatus(r.event || "👆 点击己方武将，选择本回合动作");
    updateBattlePhaseUI();
  } catch (e) {
    setStatus("渲染错误: " + e.message);
    console.error("renderBattle error:", e);
  }
}

/**
 * 渲染一方战斗网格
 * @param {string} gridId - "bside1-grid" 或 "bside2-grid"
 * @param {object} p        - 队伍数据 (r.p1 或 r.p2)
 * @param {boolean} isAlly  - 是否当前回合方
 *
 * 视觉布局:
 *   P1(bside1-grid): row=0(前排)→grid-row:3(底部), row=2(后排)→grid-row:1(顶部)
 *   P2(bside2-grid): row=0(前排)→grid-row:1(顶部), row=2(后排)→grid-row:3(底部)
 *   双方前排紧邻战场中线，实现"短兵相接"
 */
function renderBattleGrid(gridId, p, isAlly) {
  var grid = [[null,null,null,null], [null,null,null,null], [null,null,null,null]];
  if (p && p.generals) {
    p.generals.forEach(function(g) {
      if (g.row >= 0 && g.alive) grid[g.row][g.col] = g;
    });
  }

  var cells = "";
  for (var r = 0; r < 3; r++) {
    for (var c = 0; c < 4; c++) {
      var g = grid[r][c];
      var gridRow = (gridId === "bside1-grid") ? (3 - r) : (r + 1);

      if (g) {
        cells += buildBcellHTML(g, r, c, gridRow, isAlly);
      } else {
        cells += '<div class="bcell empty" style="grid-row:' + gridRow + ';grid-column:' + (c+1) + ';font-size:9px;color:#3a2e1c">—</div>';
      }
    }
  }
  document.getElementById(gridId).innerHTML = cells;
}

/** 构建单个武将格子的 HTML（纯函数，便于测试和维护） */
function buildBcellHTML(g, r, c, gridRow, isAlly) {
  var hpPct = g.maxHp > 0 ? (g.hp / g.maxHp * 100) : 0;
  var hpClass = hpPct > 60 ? "" : (hpPct > 30 ? "warn" : "danger");
  var imgSrc = g.image ? "/generals/" + g.image : "";
  var selected = isAlly && selectedAttacker && selectedAttacker.general.id === g.id;
  var hasActed = isAlly && (g._hasAttacked || g._hasUsedSkill);
  var isLocked = !isAlly && battlePhase !== "target";
  var attrs = g.attributes || [];

  // 被动属性 CSS 类
  var cls = ["bcell"];
  if (selected) cls.push("selected");
  if (isLocked) cls.push("locked");
  if (hasActed) cls.push("acted");
  if (!g.alive) cls.push("dead");

  if (attrs.indexOf("防栅") >= 0) {
    cls.push((g._fenceBroken || g.hp < g.maxHp) ? "fence-broken" : "fence");
  }
  if (attrs.indexOf("连环") >= 0) cls.push("chain");
  if (attrs.indexOf("勇猛") >= 0 && g.hp <= g.maxHp / 2) cls.push("bravery-active");
  if (attrs.indexOf("魅力") >= 0) cls.push("charisma");
  if (attrs.indexOf("募兵") >= 0 && g.hp < g.maxHp) cls.push("recruit");
  if (attrs.indexOf("复活") >= 0) cls.push(g._reviveUsed ? "revive-used" : "revive");
  if (attrs.indexOf("伏兵") >= 0) {
    cls.push(g._ambushTriggered ? "ambush-triggered" : (g._ambushHidden ? "ambush-hidden" : "ambush-revealed"));
  }

  var effForce = g.effective_force !== undefined ? g.effective_force : (g.force || 0);
  var effIntel = g.effective_intelligence !== undefined ? g.effective_intelligence : (g.intelligence || 0);
  var attrStr = attrs.join(" · ") || "无属性";

  return '<div class="' + cls.join(" ") + '"' +
    ' data-name="' + g.name + '" data-id="' + g.id + '" data-row="' + r + '" data-col="' + c + '"' +
    ' data-isally="' + (isAlly ? "1" : "0") + '"' +
    ' data-force="' + effForce + '" data-intel="' + effIntel + '"' +
    ' data-skill="' + (g.skill || "") + '" data-skill-desc="' + (g.skill_desc || "") + '"' +
    ' data-attrs="' + (attrs.join(",")) + '"' +
    ' data-tooltip="<b>' + g.name + '</b> 武' + effForce + ' 智' + effIntel +
    ' HP ' + g.hp + '/' + g.maxHp + '<br>技能：' + (g.skill || "无") + '<br>' +
    (g.skill_desc || "") + '<br>属性：' + attrStr + '"' +
    ' style="grid-row:' + gridRow + ';grid-column:' + (c + 1) + '">' +
    (imgSrc ? '<img src="' + imgSrc + '">' : "") +
    '<div class="bcell-tip"><img src="' + (imgSrc || "") + '"><div class="tip-name">' + g.name +
    '</div><div class="tip-stat">武' + effForce + ' 智' + effIntel + ' | ' + (g.skill || "无") +
    '</div><div class="tip-attr">' + attrStr + '</div></div>' +
    '<div class="cname">' + (g.alive ? g.name : "阵亡") + '</div>' +
    '<div class="chp">' + (g.alive ? g.hp + "/" + g.maxHp : "--") + '</div>' +
    '<div class="hpbar"><div class="hpf ' + hpClass + '" style="width:' + (g.alive ? hpPct : 0) + '%"></div></div>' +
    '</div>';
}

// ============================================================================
// SECTION 7: 战斗交互（事件委托 + UI 状态 + 技能/普攻/跳过）
// ============================================================================
var _battleClickLock = false;
(function initBattleDelegation() {
  document.addEventListener("click", function(e) {
    if (_battleClickLock) return;
    var cell = e.target.closest(".bcell");
    if (!cell) return;
    if (cell.classList.contains("locked") || cell.classList.contains("empty") || cell.classList.contains("dead")) return;

    var r = parseInt(cell.getAttribute("data-row"));
    var c = parseInt(cell.getAttribute("data-col"));
    if (isNaN(r) || isNaN(c)) return;

    var isAlly = cell.getAttribute("data-isally") === "1";
    _battleClickLock = true;
    var promise = isAlly ? onBattleAllyCell(r, c) : onBattleEnemyCell(r, c);
    promise.then(function() { _battleClickLock = false; }).catch(function() { _battleClickLock = false; });
  });
})();

function updateBattlePhaseUI() {
  var phTag = battlePhase === "target" ? "ph-target" : (selectedAttacker ? "ph-attack" : "ph-skill");
  var phText = battlePhase === "target" ? "🎯 选择普攻目标" :
    (selectedAttacker ? "✅ 已选：" + selectedAttacker.general.name + " — 点击下方按钮" : "🔍 点击武将选择动作");
  document.getElementById("bphase").className = "phase-tag " + phTag;
  document.getElementById("bphase").textContent = phText;

  var attackBtn = document.getElementById("bact-attack");
  var skillBtn = document.getElementById("bact-skill");
  var skipBtn = document.getElementById("bact-skip");
  var canAct = !!selectedAttacker && battlePhase !== "target";
  var selected = selectedAttacker ? selectedAttacker.general : null;
  var morale = currentTeamData() ? (currentTeamData().morale || 0) : 0;

  var hasAttacked = selected && selected._hasAttacked;
  var hasUsedSkill = selected && selected._hasUsedSkill;
  var canSkill = canAct && selected && selected.skill && selected.skill !== "无" && !selected.cooldown && !hasUsedSkill && morale >= 2;
  var canAttack = canAct && !hasAttacked;

  attackBtn.style.display = canAct ? "" : "none";
  skillBtn.style.display = canAct ? "" : "none";

  if (canAct) {
    skillBtn.style.opacity = canSkill ? "1" : ".4";
    skillBtn.style.pointerEvents = canSkill ? "auto" : "none";
    attackBtn.style.opacity = canAttack ? "1" : ".4";
    attackBtn.style.pointerEvents = canAttack ? "auto" : "none";

    if (hasUsedSkill && selected.skill) {
      skillBtn.setAttribute("data-tooltip", selected.skill + " — 本回合已使用过技能");
    } else if (selected.cooldown) {
      skillBtn.setAttribute("data-tooltip", selected.skill + " 冷却中（剩余 " + selected.cooldown + " 回合）");
    } else if (morale < 2 && selected.skill) {
      skillBtn.setAttribute("data-tooltip", "士气不足！需要消耗士气才能使用技能");
    } else if (canSkill && selected.skill) {
      skillBtn.setAttribute("data-tooltip", selected.skill + " — " + (selected.skill_desc || ""));
    }

    if (hasAttacked) {
      attackBtn.setAttribute("data-tooltip", selected.name + " 本回合已普攻过");
    } else if (canAttack) {
      attackBtn.setAttribute("data-tooltip", selected.name + " 普攻 — 武力 " + (selected.force || 0));
    }
  }

  skipBtn.textContent = battlePhase === "target" ? "取消普攻" : "⏭ 跳过";
}

/**
 * 点击己方武将 —— 选中该武将，进入行动状态
 * 搜索逻辑：先搜当前回合方，避免双方同位置时选错
 */
function onBattleAllyCell(r, c) {
  try {
    if (!G) { setStatus("游戏状态为空，请刷新页面"); return; }
    var isP1Turn = (G.current_team === "p1");
    var g = isP1Turn
      ? (findGeneral(G.p1, r, c) || findGeneral(G.p2, r, c))
      : (findGeneral(G.p2, r, c) || findGeneral(G.p1, r, c));
    if (!g) { setStatus("未找到该位置武将 (row=" + r + ", col=" + c + ")"); return; }

    selectedAttacker = { general: g, row: r, col: c };
    battlePhase = "action";
    setStatus("已选中 " + g.name + " (武" + (g.effective_force || g.force || 0) + " 智" + (g.effective_intelligence || g.intelligence || 0) + ")");
    return renderBattle();
  } catch (e) {
    setStatus("点击错误: " + e.message);
    console.error(e);
  }
}

/**
 * 点击敌方武将 —— 在瞄准模式下执行普攻
 * 搜索逻辑：先搜敌方，避免双方同位置时选错
 */
function onBattleEnemyCell(r, c) {
  if (battlePhase !== "target" || !selectedAttacker) {
    setStatus("请先选择己方武将并点击「普攻」进入瞄准模式");
    return;
  }
  var isP1Turn = (G.current_team === "p1");
  var target = isP1Turn
    ? (findGeneral(G.p2, r, c) || findGeneral(G.p1, r, c))
    : (findGeneral(G.p1, r, c) || findGeneral(G.p2, r, c));
  if (!target) { setStatus("未找到目标武将"); return; }

  // 格子查找：P1在bside1-grid，P2在bside2-grid
  var aIsP1 = isP1Turn;
  var tIsP1 = !isP1Turn;
  var aCell = document.querySelector((aIsP1 ? "#bside1-grid" : "#bside2-grid") +
    ' .bcell[data-row="' + selectedAttacker.row + '"][data-col="' + selectedAttacker.col + '"]');
  var tCell = document.querySelector((tIsP1 ? "#bside1-grid" : "#bside2-grid") +
    ' .bcell[data-row="' + r + '"][data-col="' + c + '"]');

  // 攻速判定：弹窗选择奇偶
  var guess = null;
  if (selectedAttacker.general._hasSpeedJudgment || selectedAttacker.general._hasSpeedRequired) {
    guess = askOddEven();
    if (!guess) {
      battlePhase = "action";
      return renderBattle();
    }
  }

  if (aCell && tCell) {
    animAttack(aCell, tCell, Math.max(1, (selectedAttacker.general.force || 5) - (target.force || 3)));
  }
  return sleep(250).then(function() {
    return call("/battle/attack", {
      attacker_id: selectedAttacker.general.id,
      target_id: target.id,
      guess: guess
    });
  }).then(function() {
    clearBattleSelection();
    if (G && G.phase === "over") { showGameOver(); return; }
    return renderBattle();
  });
}

/** 进入瞄准模式 */
function chooseAttack() {
  if (!selectedAttacker) return;
  battlePhase = "target";
  return renderBattle();
}

/**
 * 使用主动技能 —— 核心战斗交互
 *
 * 流程: 校验 → 动画 → API调用 → 特效反馈 → 重新渲染
 *
 * 防御性检查:
 *   1. 是否选中武将
 *   2. 武将有技能且非"无"
 *   3. 技能不在冷却
 *   4. 本回合未使用过技能
 *   5. API返回有效结果
 */
function useSkill() {
  if (!selectedAttacker) { setStatus("未选择武将，无法使用技能"); return; }
  var sk = selectedAttacker.general.skill;
  if (!sk || sk === "无") { setStatus(selectedAttacker.general.name + " 没有主动技能"); return; }
  if (selectedAttacker.general.cooldown) { setStatus(sk + " 冷却中 (剩余" + selectedAttacker.general.cooldown + "回合)"); return; }
  if (selectedAttacker.general._hasUsedSkill) { setStatus(selectedAttacker.general.name + " 本回合已使用过技能"); return; }

  setStatus("正在使用 " + sk + "...");
  var skillType = detectSkillType(sk);
  var aIsP1 = (G.current_team === "p1");
  var allyGrid = aIsP1 ? "#bside1-grid" : "#bside2-grid";
  var enemyGrid = aIsP1 ? "#bside2-grid" : "#bside1-grid";

  // 施法者特效
  var cellEl = document.querySelector(allyGrid + ' .bcell[data-row="' + selectedAttacker.row + '"][data-col="' + selectedAttacker.col + '"]');
  if (cellEl) animSkill(cellEl, sk, "", skillType);

  // 记录敌方战前 HP
  var enemyBefore = {};
  document.querySelectorAll(enemyGrid + " .bcell").forEach(function(ec) {
    var n = ec.getAttribute("data-name");
    var hpEl = ec.querySelector(".chp");
    if (n && hpEl) {
      var parts = hpEl.textContent.split("/");
      enemyBefore[n] = parseInt(parts[0]) || 0;
    }
  });

  return call("/battle/skill", { general_id: selectedAttacker.general.id }).then(function(result) {
    if (!result) {
      setStatus("技能请求失败，请检查服务器连接");
      clearBattleSelection();
      return renderBattle();
    }
    setStatus(result.event || (sk + " 已使用"));

    // 技能执行后，对受损目标显示特效
    setTimeout(function() {
      document.querySelectorAll(enemyGrid + " .bcell").forEach(function(ec) {
        var n = ec.getAttribute("data-name");
        if (n && enemyBefore[n] !== undefined) {
          var hpEl = ec.querySelector(".chp");
          if (!hpEl) return;
          var afterHp = parseInt(hpEl.textContent.split("/")[0]) || 0;
          var dmg = enemyBefore[n] - afterHp;
          if (dmg > 0) {
            var center = getCellCenter(ec);
            if (skillType === "lightning") FX.lightningStrike(center.x, center.y);
            else if (skillType === "fire") FX.fireBurst(center.x, center.y);
            spawnFloatNum(ec, dmg, "damage");
            ec.classList.add("impact-flash");
            setTimeout(function() { ec.classList.remove("impact-flash"); }, 400);
          } else if (afterHp > enemyBefore[n]) {
            spawnFloatNum(ec, afterHp - enemyBefore[n], "heal");
          }
        }
      });
    }, 100);

    clearBattleSelection();
    if (G.phase === "over") { showGameOver(); return; }
    return renderBattle();
  });
}

/** 跳过当前阶段/回合 */
function skipPhase() {
  if (battlePhase === "target") {
    battlePhase = "action";
    return renderBattle();
  }
  clearBattleSelection();
  return call("/battle/skip").then(function() {
    if (G && G.phase === "over") { showGameOver(); return; }
    return renderBattle();
  });
}

/** 奇偶选择弹窗 —— 攻速判定时弹出 */
function askOddEven() {
  return new Promise(function(resolve) {
    var overlay = document.createElement("div");
    overlay.style.cssText = "position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.8);z-index:400;display:flex;align-items:center;justify-content:center";
    overlay.innerHTML =
      '<div style="background:linear-gradient(180deg,#1a1410,#0b0906);border:2px solid var(--gold);border-radius:14px;padding:28px 36px;text-align:center;color:var(--text)">' +
      '<div style="font-size:20px;color:var(--gold);margin-bottom:8px">🎲 猜奇偶</div>' +
      '<div style="font-size:14px;color:var(--muted);margin-bottom:20px">攻速判定——猜对则额外普攻一次</div>' +
      '<div style="display:flex;gap:16px;justify-content:center">' +
      '<div class="btn primary" style="font-size:18px;padding:12px 32px" onclick="this.closest(\'div\').parentElement._resolve(\'奇\')">奇</div>' +
      '<div class="btn" style="font-size:18px;padding:12px 32px" onclick="this.closest(\'div\').parentElement._resolve(\'偶\')">偶</div>' +
      '</div></div>';
    overlay._resolve = function(v) { overlay.remove(); resolve(v); };
    overlay.addEventListener("click", function(e) { if (e.target === overlay) { overlay.remove(); resolve(null); } });
    document.body.appendChild(overlay);
  });
}

/** setTimeout 的 Promise 包装 */
function sleep(ms) {
  return new Promise(function(resolve) { setTimeout(resolve, ms); });
}

// ============================================================================
// SECTION 8: 游戏结束 & 武将图鉴
// ============================================================================
function showGameOver() {
  showScreen("over");
  document.getElementById("over-winner").textContent = (G ? G.winner : "?") + " 获得胜利！";
  document.getElementById("over-stats").textContent = "总回合数: " + (G ? G.turn : "?");
}

function initGallery() {
  fetch("/api/generals").then(function(r) { return r.json(); }).then(function(r) {
    var all = r.pool || [];
    var campFilter = ((document.querySelector("#dm-camp .opt.active") || {}).dataset || {}).val || "";
    var attrFilter = ((document.querySelector("#dm-attr .opt.active") || {}).dataset || {}).val || "";
    galleryFiltered = all.filter(function(g) {
      if (campFilter && g.camp !== campFilter) return false;
      if (attrFilter && !(g.attributes || []).includes(attrFilter)) return false;
      return true;
    });
    if (galleryIdx >= galleryFiltered.length) galleryIdx = 0;
    renderGallery();
    if (!document.getElementById("dm-camp").innerHTML) {
      var camps = ["全部"].concat(Array.from(new Set(all.map(function(g) { return g.camp; }))));
      var attrs = ["全部"].concat(Array.from(new Set(all.flatMap(function(g) { return g.attributes || []; }))));
      document.getElementById("dm-camp").innerHTML = camps.map(function(c) {
        return '<div class="opt' + (c === "全部" ? " active" : "") + '" data-val="' + (c === "全部" ? "" : c) + '" onclick="filterGallery(\'camp\',\'' + c + '\',event)">' + c + '</div>';
      }).join("");
      document.getElementById("dm-attr").innerHTML = attrs.map(function(a) {
        return '<div class="opt' + (a === "全部" ? " active" : "") + '" data-val="' + (a === "全部" ? "" : a) + '" onclick="filterGallery(\'attr\',\'' + a + '\',event)">' + a + '</div>';
      }).join("");
    }
  });
}

function filterGallery(type, val, evt) {
  document.querySelectorAll("#dm-" + type + " .opt").forEach(function(o) { o.classList.remove("active"); });
  if (evt && evt.target) evt.target.classList.add("active");
  initGallery();
}

function renderGallery() {
  if (galleryFiltered.length === 0) {
    document.getElementById("gallery-content").innerHTML = '<p style="color:var(--muted)">无符合条件的武将</p>';
    return;
  }
  var g = galleryFiltered[galleryIdx];
  var imgSrc = g.image ? "/generals/" + g.image : "";
  var bio = (g.bio || "").slice(0, 200);
  var html =
    '<div class="gallery-card">' +
    (imgSrc ? '<img src="' + imgSrc + '" alt="' + g.name + '">' : '<div style="height:300px;display:flex;align-items:center;justify-content:center;font-size:60px;color:var(--shu)">' + g.name[0] + '</div>') +
    '<div class="gn">' + g.name + '</div></div>' +
    '<div class="gallery-bio">' + (g.years || "") + ' · ' + (g.courtesy || "") + '<br><br>' + bio + '</div>' +
    '<div class="gallery-nav">' +
    '<div class="nav-btn" onclick="galleryIdx=(galleryIdx-1+galleryFiltered.length)%galleryFiltered.length;renderGallery()">◀</div>' +
    '<div style="font-size:12px;color:var(--muted);line-height:36px">' + (galleryIdx + 1) + '/' + galleryFiltered.length + '</div>' +
    '<div class="nav-btn" onclick="galleryIdx=(galleryIdx+1)%galleryFiltered.length;renderGallery()">▶</div></div>';
  document.getElementById("gallery-content").innerHTML = html;
}

function toggleDropdown(id) {
  document.getElementById(id).classList.toggle("open");
}
document.addEventListener("click", function(e) {
  if (!e.target.closest(".dropdown")) {
    document.querySelectorAll(".dropdown").forEach(function(d) { d.classList.remove("open"); });
  }
});

function quitToMenu() {
  G = null;
  selectedGenerals = [];
  clearBattleSelection();
  battlePhase = "select";
  showScreen("menu");
}

// ============================================================================
// SECTION 9: Canvas 特效系统 (FX)
// ============================================================================
(function() {
  var c = document.getElementById("fx-canvas");
  var ctx = c.getContext("2d");
  var particles = [];
  var ambientParticles = [];
  var W, H;

  function resize() { W = c.width = window.innerWidth; H = c.height = window.innerHeight; }
  window.addEventListener("resize", resize);
  resize();

  function initAmbient() {
    ambientParticles = [];
    for (var i = 0; i < 8; i++) {
      ambientParticles.push({
        x: Math.random() * W, y: Math.random() * H,
        vx: (Math.random() - 0.5) * 0.3, vy: -(0.2 + Math.random() * 0.4),
        life: Math.random(), size: 1 + Math.random() * 2,
        color: Math.random() > 0.5 ? "#ffb840" : "#ff6020"
      });
    }
  }
  initAmbient();
  window.addEventListener("resize", initAmbient);

  window.FX = {
    burst: function(x, y, color, count, speed) {
      count = count || 15; speed = speed || 4;
      for (var i = 0; i < count; i++) {
        var angle = Math.random() * Math.PI * 2;
        var spd = 1 + Math.random() * speed;
        particles.push({ type: "burst", x: x, y: y, vx: Math.cos(angle) * spd, vy: Math.sin(angle) * spd, life: 1, color: color || "#ffb840", size: 2 + Math.random() * 4 });
      }
    },
    fireBurst: function(x, y) {
      for (var i = 0; i < 20; i++) {
        var angle = (Math.random() - 0.5) * Math.PI;
        var spd = 2 + Math.random() * 5;
        particles.push({ type: "fire", x: x, y: y, vx: Math.cos(angle) * spd, vy: -(1 + Math.random() * 3), life: 1, color: Math.random() > 0.5 ? "#ff6020" : "#ffb830", size: 2 + Math.random() * 5 });
      }
      for (var j = 0; j < 6; j++) {
        particles.push({ type: "smoke", x: x + (Math.random() - 0.5) * 20, y: y + (Math.random() - 0.5) * 10, vx: (Math.random() - 0.5) * 0.5, vy: -0.5 - Math.random(), life: 1, color: "#666", size: 8 + Math.random() * 8, alpha: 0.3 });
      }
    },
    lightningStrike: function(x, y) {
      ctx.save(); ctx.globalAlpha = 0.6; ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, W, H); ctx.restore();
      for (var i = 0; i < 25; i++) {
        particles.push({ type: "bolt", x: x + (Math.random() - 0.5) * 60, y: y + (Math.random() - 0.5) * 80, vx: (Math.random() - 0.5) * 8, vy: (Math.random() - 0.5) * 8, life: 0.4 + Math.random() * 0.3, color: "#ffe840", size: 1.5 + Math.random() * 3 });
      }
      FX.screenShake();
      for (var j = 0; j < 10; j++) {
        particles.push({ type: "glow", x: x + (Math.random() - 0.5) * 40, y: y + (Math.random() - 0.5) * 40, vx: 0, vy: 0, life: 0.6 + Math.random() * 0.4, color: "#ffffc0", size: 6 + Math.random() * 8, alpha: 0.5 });
      }
    },
    slashTrail: function(x1, y1, x2, y2) {
      var angle = Math.atan2(y2 - y1, x2 - x1);
      for (var i = 0; i < 18; i++) {
        var t = i / 17;
        particles.push({ type: "slash", x: x1 + (x2 - x1) * t + (Math.random() - 0.5) * 20, y: y1 + (y2 - y1) * t + (Math.random() - 0.5) * 20, vx: Math.cos(angle) * 2, vy: Math.sin(angle) * 2, life: 0.3 + Math.random() * 0.3, color: "#e0e0f0", size: 2 + Math.random() * 3 });
      }
      FX.burst(x2, y2, "#ffe0c0", 8, 3);
    },
    healSparkles: function(x, y) {
      for (var i = 0; i < 15; i++) {
        var angle = (Math.random() - 0.5) * Math.PI;
        particles.push({ type: "heal", x: x + (Math.random() - 0.5) * 30, y: y + (Math.random() - 0.5) * 20, vx: Math.cos(angle) * 1.5, vy: -(2 + Math.random() * 3), life: 1, color: "#40e040", size: 2 + Math.random() * 3 });
      }
    },
    debuffMiasma: function(x, y) {
      for (var i = 0; i < 18; i++) {
        particles.push({ type: "miasma", x: x + (Math.random() - 0.5) * 40, y: y, vx: (Math.random() - 0.5) * 2, vy: 0.5 + Math.random() * 2, life: 1, color: "#c080ff", size: 3 + Math.random() * 5 });
      }
    },
    moraleWave: function(x, y) {
      for (var i = 0; i < 12; i++) {
        var angle = Math.random() * Math.PI * 2;
        var spd = 3 + Math.random() * 3;
        particles.push({ type: "morale", x: x, y: y, vx: Math.cos(angle) * spd, vy: Math.sin(angle) * spd, life: 0.8, color: "#ffb840", size: 3 + Math.random() * 3 });
      }
    },
    deathShatter: function(x, y) {
      for (var i = 0; i < 20; i++) {
        var angle = Math.random() * Math.PI * 2;
        var spd = 2 + Math.random() * 5;
        particles.push({ type: "death", x: x, y: y, vx: Math.cos(angle) * spd, vy: Math.sin(angle) * spd - 2, life: 1, color: "#333", size: 3 + Math.random() * 6 });
      }
      for (var j = 0; j < 8; j++) {
        particles.push({ type: "death", x: x, y: y, vx: (Math.random() - 0.5) * 3, vy: -(1 + Math.random() * 4), life: 1.2, color: "#8a2020", size: 2 + Math.random() * 4 });
      }
    },
    formationSwap: function(x1, y1, x2, y2) {
      FX.burst(x1, y1, "#c0c0ff", 8, 3);
      FX.burst(x2, y2, "#c0c0ff", 8, 3);
    },
    drawWeaponArc: function(x1, y1, x2, y2, color) {
      color = color || "rgba(255,255,240,.7)";
      ctx.save();
      ctx.strokeStyle = color;
      ctx.lineWidth = 3;
      ctx.shadowColor = color;
      ctx.shadowBlur = 12;
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.quadraticCurveTo((x1 + x2) / 2, Math.min(y1, y2) - 40, x2, y2);
      ctx.stroke();
      ctx.globalAlpha = 0.4;
      ctx.strokeStyle = "#fff";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x1 + 3, y1 + 3);
      ctx.quadraticCurveTo((x1 + x2) / 2 + 3, Math.min(y1, y2) - 37, x2 + 3, y2 + 3);
      ctx.stroke();
      ctx.restore();
    },
    screenShake: function() {
      var app = document.getElementById("app");
      if (!app) return;
      app.classList.add("shaking");
      setTimeout(function() { app.classList.remove("shaking"); }, 500);
    },
    skillEffect: function(el, skillName, skillType) {
      var center = getCellCenter(el);
      skillType = skillType || detectSkillType(skillName);
      switch (skillType) {
        case "fire": FX.fireBurst(center.x, center.y); break;
        case "lightning": FX.lightningStrike(center.x, center.y); break;
        case "heal": FX.healSparkles(center.x, center.y); break;
        case "debuff": FX.debuffMiasma(center.x, center.y); break;
        case "morale": FX.moraleWave(center.x, center.y); break;
        case "death": FX.deathShatter(center.x, center.y); break;
        default: FX.burst(center.x, center.y, skillType === "damage" ? "#ff6040" : "#ffb840", 18, 5);
      }
      spawnSkillLabel(el, skillName, skillType);
    }
  };

  function detectSkillType(name) {
    var n = name || "";
    if (/雷|电|闪/.test(n)) return "lightning";
    if (/火|烧|炎|燃/.test(n)) return "fire";
    if (/美|舞|回|复|治|疗|愈|防栅/.test(n)) return "heal";
    if (/离间|衰|削弱|挑衅|以牙/.test(n)) return "debuff";
    if (/号令|同|士|鼓/.test(n)) return "morale";
    if (/攻|枪|轮|突|击|神速|猛|弓|箭/.test(n)) return "damage";
    return "buff";
  }

  function loop() {
    ctx.clearRect(0, 0, W, H);
    for (var a = 0; a < ambientParticles.length; a++) {
      var ap = ambientParticles[a];
      ap.x += ap.vx; ap.y += ap.vy;
      if (ap.y < -10) { ap.y = H + 10; ap.x = Math.random() * W; }
      if (ap.x < -10 || ap.x > W + 10) ap.x = Math.random() * W;
      ctx.globalAlpha = 0.15 + ap.life * 0.2;
      ctx.fillStyle = ap.color;
      ctx.beginPath(); ctx.arc(ap.x, ap.y, ap.size, 0, Math.PI * 2); ctx.fill();
    }
    for (var i = particles.length - 1; i >= 0; i--) {
      var p = particles[i];
      p.x += p.vx; p.y += p.vy; p.life -= 0.025;
      if (p.type === "fire" || p.type === "smoke") { p.vx *= 0.95; p.vy *= 0.95; }
      else if (p.type === "miasma") { p.vx *= 0.98; p.vy *= 0.98; }
      else { p.vx *= 0.96; p.vy *= 0.96; }
      ctx.globalAlpha = Math.max(0, p.life * (p.alpha || 1));
      ctx.fillStyle = p.color;
      if (p.type === "smoke") {
        ctx.beginPath(); ctx.arc(p.x, p.y, p.size * Math.max(0.1, p.life), 0, Math.PI * 2); ctx.fill();
      } else if (p.type === "glow") {
        var grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.size);
        grad.addColorStop(0, p.color); grad.addColorStop(1, "transparent");
        ctx.fillStyle = grad; ctx.beginPath(); ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2); ctx.fill();
      } else {
        ctx.beginPath(); ctx.arc(p.x, p.y, p.size * Math.max(0.1, p.life), 0, Math.PI * 2); ctx.fill();
      }
      if (p.life <= 0) particles.splice(i, 1);
    }
    ctx.globalAlpha = 1;
    requestAnimationFrame(loop);
  }
  loop();
})();

// ============================================================================
// SECTION 10: 战斗动画工具
// ============================================================================
function getCellCenter(el) {
  var r = el.getBoundingClientRect();
  return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
}

function spawnFloatNum(el, num, cssClass) {
  var d = document.createElement("div");
  d.className = "float-num " + (cssClass || "damage");
  d.textContent = (num > 0 ? "-" : "+") + Math.abs(num);
  d.style.left = "50%"; d.style.top = "40%";
  d.style.transform = "translateX(-50%)";
  el.appendChild(d);
  setTimeout(function() { d.remove(); }, 1300);
}

function spawnSkillLabel(el, text) {
  var d = document.createElement("div");
  d.className = "skill-burst";
  d.textContent = text;
  el.appendChild(d);
  setTimeout(function() { d.remove(); }, 1600);
}

function animAttack(aEl, tEl, dmg) {
  var aCenter = getCellCenter(aEl);
  var tCenter = getCellCenter(tEl);
  FX.drawWeaponArc(aCenter.x, aCenter.y, tCenter.x, tCenter.y, "rgba(255,255,240,.7)");
  tEl.classList.add("impact-flash");
  setTimeout(function() { tEl.classList.remove("impact-flash"); }, 400);

  if (window.gsap) {
    gsap.timeline()
      .to(aEl, { duration: 0.15, x: tCenter.x - aCenter.x, y: tCenter.y - aCenter.y, scale: 1.15, ease: "power2.in" })
      .call(function() { FX.slashTrail(aCenter.x, aCenter.y, tCenter.x, tCenter.y); FX.screenShake(); spawnFloatNum(tEl, dmg || 3, "damage"); })
      .to(aEl, { duration: 0.2, x: 0, y: 0, scale: 1, ease: "power2.out" });
  } else {
    aEl.classList.add("attacking");
    setTimeout(function() { aEl.classList.remove("attacking"); }, 350);
    FX.slashTrail(aCenter.x, aCenter.y, tCenter.x, tCenter.y);
    FX.screenShake();
    spawnFloatNum(tEl, dmg || 3, "damage");
  }
}

function animSkill(el, name, detail, kind) {
  FX.skillEffect(el, name, kind);
  var colorMap = { buff: "#ffb840", debuff: "#c080ff", heal: "#40e040", damage: "#ff6040", lightning: "#ffe840", fire: "#ff6020" };
  var color = colorMap[kind] || "#ffb840";
  if (window.gsap) {
    gsap.timeline()
      .to(el, { duration: 0.1, scale: 1.08, boxShadow: "0 0 30px " + color })
      .to(el, { duration: 0.25, scale: 1, boxShadow: "none" });
  } else {
    el.classList.add("flash-pulse");
    setTimeout(function() { el.classList.remove("flash-pulse"); }, 300);
  }
}

// ============================================================================
// 初始化
// ============================================================================
showScreen("menu");
