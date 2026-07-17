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
var _lastTurnSignature = "";

/**
 * 轻量战场声音：全部由 Web Audio 实时合成，不加载外部音频文件。
 * 浏览器要求用户首次交互后才能启动 AudioContext，因此所有播放入口都可安全懒初始化。
 */
var BattleAudio = (function() {
  var ctx = null;
  var master = null;
  var ambience = [];
  var muted = false;
  try { muted = localStorage.getItem("sanguo-muted") === "1"; } catch (e) {}

  function syncButton() {
    var button = document.getElementById("sound-toggle");
    if (!button) return;
    button.textContent = muted ? "声音 关" : "声音 开";
    button.classList.toggle("muted", muted);
    button.setAttribute("aria-pressed", muted ? "true" : "false");
  }

  function ensure() {
    if (window.__stressMode || muted) { syncButton(); return null; }
    if (!ctx) {
      var AudioContext = window.AudioContext || window.webkitAudioContext;
      if (!AudioContext) return null;
      ctx = new AudioContext();
      master = ctx.createGain();
      master.gain.value = 0.38;
      master.connect(ctx.destination);
      startAmbience();
    }
    if (ctx.state === "suspended") ctx.resume();
    return ctx;
  }

  function tone(freq, duration, options) {
    var audio = ensure();
    if (!audio) return;
    options = options || {};
    var now = audio.currentTime + (options.delay || 0);
    var osc = audio.createOscillator();
    var gain = audio.createGain();
    osc.type = options.type || "sine";
    osc.frequency.setValueAtTime(freq, now);
    if (options.to) osc.frequency.exponentialRampToValueAtTime(Math.max(20, options.to), now + duration);
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.exponentialRampToValueAtTime(options.volume || 0.08, now + Math.min(0.025, duration / 3));
    gain.gain.exponentialRampToValueAtTime(0.0001, now + duration);
    osc.connect(gain); gain.connect(master);
    osc.start(now); osc.stop(now + duration + 0.03);
  }

  function noise(duration, volume, cutoff) {
    var audio = ensure();
    if (!audio) return;
    var frames = Math.max(1, Math.floor(audio.sampleRate * duration));
    var buffer = audio.createBuffer(1, frames, audio.sampleRate);
    var data = buffer.getChannelData(0);
    for (var i = 0; i < frames; i++) data[i] = (Math.random() * 2 - 1) * (1 - i / frames);
    var source = audio.createBufferSource();
    var filter = audio.createBiquadFilter();
    var gain = audio.createGain();
    filter.type = "lowpass"; filter.frequency.value = cutoff || 900;
    gain.gain.setValueAtTime(volume || 0.05, audio.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.0001, audio.currentTime + duration);
    source.buffer = buffer; source.connect(filter); filter.connect(gain); gain.connect(master);
    source.start();
  }

  function startAmbience() {
    if (!ctx || ambience.length || muted || window.__stressMode) return;
    [55, 82.4].forEach(function(freq, index) {
      var osc = ctx.createOscillator();
      var filter = ctx.createBiquadFilter();
      var gain = ctx.createGain();
      osc.type = index ? "triangle" : "sine";
      osc.frequency.value = freq;
      filter.type = "lowpass"; filter.frequency.value = 180;
      gain.gain.value = index ? 0.012 : 0.018;
      osc.connect(filter); filter.connect(gain); gain.connect(master); osc.start();
      ambience.push(osc, gain);
    });
  }

  function stopAmbience() {
    ambience.forEach(function(node) { try { if (node.stop) node.stop(); else node.disconnect(); } catch (e) {} });
    ambience = [];
  }

  function play(name) {
    if (window.__stressMode || muted) return;
    switch (name) {
      case "select": tone(210, .08, {to:270, volume:.045, type:"triangle"}); break;
      case "anticipate": tone(92, .18, {to:68, volume:.06, type:"triangle"}); break;
      case "impact": noise(.12, .13, 720); tone(74, .16, {to:45, volume:.1, type:"square"}); break;
      case "block": tone(520, .12, {to:290, volume:.05, type:"square"}); tone(760, .08, {volume:.025, delay:.03}); break;
      case "command": tone(110, .22, {to:72, volume:.09, type:"sawtooth"}); break;
      case "lightning": noise(.25, .1, 2400); tone(880, .18, {to:130, volume:.055, type:"sawtooth"}); break;
      case "fire": noise(.28, .08, 1100); tone(145, .22, {to:70, volume:.05, type:"sawtooth"}); break;
      case "heal": tone(330, .22, {to:494, volume:.045}); tone(494, .25, {to:660, volume:.035, delay:.08}); break;
      case "buff": tone(240, .18, {to:360, volume:.04, type:"triangle"}); break;
      case "damage": noise(.1, .08, 900); tone(105, .14, {to:58, volume:.07, type:"square"}); break;
      case "debuff": tone(190, .3, {to:76, volume:.045, type:"sawtooth"}); break;
      case "morale": tone(72, .28, {to:45, volume:.12, type:"sine"}); noise(.12, .05, 420); break;
      case "dice": noise(.08, .035, 1800); tone(460 + Math.random() * 120, .05, {volume:.025, type:"square"}); break;
      case "success": tone(262, .18, {to:392, volume:.045}); tone(392, .28, {to:523, volume:.04, delay:.12}); break;
      case "failure": tone(180, .2, {to:105, volume:.05, type:"triangle"}); break;
      case "victory": tone(196, .25, {to:294, volume:.06}); tone(294, .3, {to:392, volume:.055, delay:.18}); break;
    }
  }

  function toggle() {
    muted = !muted;
    try { localStorage.setItem("sanguo-muted", muted ? "1" : "0"); } catch (e) {}
    if (muted) stopAmbience(); else { ensure(); startAmbience(); play("select"); }
    syncButton();
  }

  document.addEventListener("pointerdown", function unlockAudio() { ensure(); }, {once:true});
  document.addEventListener("DOMContentLoaded", syncButton);
  return { ensure:ensure, play:play, toggle:toggle, sync:syncButton, isMuted:function() { return muted; } };
})();
window.BattleAudio = BattleAudio;

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
        '<p style="color:#8a7a5a;margin-top:12px">然后访问 <code>http://localhost:8089</code></p>' +
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
  _lastTurnSignature = "";
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
    "连计": {c:"#b09830",l:"连"}, "复活": {c:"#d06840",l:"复"},
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
  id = Number(id);
  var g = G && G.pool ? G.pool.find(function(x) { return x.id == id; }) : null;
  if (!g) return;
  var inPool = selectedGenerals.includes(id);
  document.getElementById("preview-img").src = g.image ? "/generals/" + g.image : "";
  document.getElementById("preview-name").textContent = g.name;
  document.getElementById("preview-info").innerHTML = previewInfoHTML(g, inPool);
  document.getElementById("preview").style.display = "flex";
}

function togglePool(id) {
  id = Number(id);
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
  id = Number(id);
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
  var gridWrap = document.getElementById("form-grid-wrap");
  gridWrap.classList.remove("p1", "p2");
  gridWrap.classList.add(teamKey);
  document.getElementById("form-title").textContent =
    (r.phase === "formation_p1" ? "玩家1" : "玩家2") + " — 布置阵型";
  var generals = r[teamKey] ? (r[teamKey].generals || []) : [];
  renderFormList(generals);
  renderFormGrid(generals);
  renderFormationInspector(generals);
}

function formationRangeText(g) {
  var rule = (typeof SKILL_RANGE_RULES !== "undefined" && SKILL_RANGE_RULES[g.skill_id]) || null;
  if (!rule) return "技能范围：依技能说明";
  return (rule.label || "技能范围：依技能说明").replace(/^技能：/, "技能范围：");
}

function renderFormList(generals) {
  var html = (generals || []).map(function(g) {
    var isActive = selectedFormGen && selectedFormGen.id === g.id;
    var imgSrc = g.image ? "/generals/" + g.image : "";
    var attrs = (g.attributes || []).map(function(a) { return '<span class="form-attr">' + a + '</span>'; }).join("");
    return '<div class="gi' + (isActive ? " active" : "") + '" onclick="selectFormGen(' + g.id + ')">' +
      (imgSrc ? '<img class="form-roster-portrait" src="' + imgSrc + '" alt="">' : '') +
      '<div class="form-roster-copy"><div class="form-roster-line"><strong>' + g.name + '</strong>' +
      '<span class="form-stats">武 ' + g.force + ' · 智 ' + g.intelligence + ' · HP ' + g.maxHp + '</span></div>' +
      '<div class="form-skill-line"><b>' + (g.skill || "无主动技能") + '</b><span>士气 ' + (g.skill_cost || 0) + '</span></div>' +
      '<div class="form-attr-line">' + (attrs || '<span class="form-attr muted">无特性</span>') + '</div>' +
      '<small>' + (g.row >= 0 ? "已布：第" + (g.col + 1) + "战线 · " + ["前卫", "中坚", "后卫"][g.row] : "待命 · 点击后选择阵位") + '</small></div></div>';
  }).join("");
  document.getElementById("form-list").innerHTML = html ||
    '<div style="font-size:11px;color:var(--muted);padding:8px">无武将可选</div>';
}

function renderFormationInspector(generals) {
  var el = document.getElementById("formation-inspector");
  if (!el) return;
  var g = selectedFormGen || (generals && generals[0]);
  if (!g) { el.innerHTML = '<div class="formation-empty">暂无可用军情</div>'; return; }
  var attrs = (g.attributes || []).map(function(a) { return '<span class="inspector-attr">' + a + '</span>'; }).join("");
  var imgSrc = g.image ? "/generals/" + g.image : "";
  el.innerHTML = '<div class="formation-panel-title"><span>军情</span><small>阵位研判</small></div>' +
    '<div class="inspector-general">' + (imgSrc ? '<img src="' + imgSrc + '" alt="">' : '') +
    '<div><h3>' + g.name + '</h3><p>' + (g.camp || "") + ' · 费用 ' + (g.cost || 0) + '</p></div></div>' +
    '<div class="inspector-numbers"><span><b>' + g.force + '</b>武力</span><span><b>' + g.intelligence + '</b>智力</span><span><b>' + g.maxHp + '</b>生命</span></div>' +
    '<div class="inspector-section"><label>主动技能 · 士气 ' + (g.skill_cost || 0) + '</label><strong>' + (g.skill || "无") + '</strong>' +
    '<p>' + (g.skill_desc || "该武将没有主动技能。") + '</p><em>' + formationRangeText(g) + '</em></div>' +
    '<div class="inspector-section"><label>武将特性</label><div class="inspector-attrs">' + (attrs || "无") + '</div></div>' +
    '<div class="inspector-advice">' + formationAdvice(g) + '</div>';
}

function formationAdvice(g) {
  var desc = g.skill_desc || "";
  var attrs = g.attributes || [];
  if (/一竖列|竖列/.test(desc)) return "阵位建议：与需要同列协同或覆盖的武将排在同一视觉竖列。";
  if (attrs.indexOf("防栅") >= 0 || g.force >= g.intelligence + 2) return "阵位建议：适合置于前卫，承接敌军普攻并保护身后武将。";
  if (g.intelligence > g.force) return "阵位建议：优先置于中坚或后卫，保存兵力以持续发动技能。";
  return "阵位建议：根据敌军前卫分布，选择能集中火力的战线。";
}

function renderFormGrid(generals) {
  var grid = [[null,null,null,null], [null,null,null,null], [null,null,null,null]];
  (generals || []).forEach(function(g) {
    if (g.row >= 0 && g.col >= 0) grid[g.row][g.col] = g;
  });
  var html = "";
  var isP1 = G.phase === "formation_p1";
  for (var r = 0; r < 3; r++) {
    for (var c = 0; c < 4; c++) {
      var g = grid[r][c];
      var visual = formationVisualPosition(isP1, r, c);
      var style = ' style="grid-row:' + visual.row + ';grid-column:' + visual.col + '"';
      if (g) {
        html += '<div class="form-cell filled"' + style + ' onclick="placeGeneral(' + r + ',' + c + ')">' +
          (g.image ? '<img src="/generals/' + g.image + '" alt="">' : '') + '<span>' + g.name + '</span>' +
          '<small>武' + g.force + ' 智' + g.intelligence + '</small></div>';
      } else {
        html += '<div class="form-cell' + (selectedFormGen ? " droptarget" : "") + '"' + style + ' onclick="placeGeneral(' + r + ',' + c + ')">+</div>';
      }
    }
  }
  document.getElementById("form-grid").innerHTML = html;
}

/** 将后端 3 层深度×4条战线转成前端 4排×3列，并让双方前卫朝向中线。 */
function formationVisualPosition(isP1, logicalRow, logicalCol) {
  return {
    row: logicalCol + 1,
    col: isP1 ? 3 - logicalRow : logicalRow + 1
  };
}

function selectFormGen(id) {
  var teamKey = G.phase === "formation_p1" ? "p1" : "p2";
  var generals = G[teamKey] ? (G[teamKey].generals || []) : [];
  selectedFormGen = generals.find(function(g) { return g.id === id; });
  if (!selectedFormGen) return;
  renderFormList(generals);
  renderFormGrid(generals);
  renderFormationInspector(generals);
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
  renderFormationInspector(generals);
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

// Skill geometry is expressed in logical coordinates: row=front/mid/back, col=battle lane.
var SKILL_RANGE_RULES = {
  siege_all_army:              { pattern:"ally_vertical_column", label:"技能：己方同一竖列" },
  stone_sentinel_maze:         { pattern:"enemy_select_2x2", label:"技能：敌方可选2×2区域" },
  spear_wheel_tactics:         { pattern:"enemy_select_2x2", label:"技能：敌方可选2×2区域" },
  thunder_strike:              { pattern:"enemy_select_2x2", label:"技能：敌方可选2×2区域" },
  taunt:                       { pattern:"enemy_select_2x2", label:"技能：敌方可选2×2区域" },
  discord_strategy:            { pattern:"enemy_select_2x2", label:"技能：敌方可选2×2区域" },
  tooth_for_tooth:             { pattern:"enemy_select_area", label:"技能：敌方可选2×2或2×1区域" },
  momentary_order:             { pattern:"ally_select_2x2_self", label:"技能：己方可选含自身2×2区域" },
  meticulous_offense:          { pattern:"ally_select_front_2x2", label:"技能：己方可选前方2×2区域" },
  jiangdong_beauty:            { pattern:"ally_select_3x3_self", label:"技能：己方可选含自身3×3区域" },
  grand_cavalry_order:         { pattern:"ally_vertical_column", label:"技能：己方同一竖列" },
  bandit_suppression_order:    { pattern:"ally_vertical_column", label:"技能：己方同一竖列" },
  white_horse_formation:       { pattern:"ally_vertical_column", label:"技能：己方同一竖列" },
  master_teaching:             { pattern:"ally_vertical_column", label:"技能：己方同一竖列" },
  imperial_edict:              { pattern:"ally_highest", label:"技能：己方武力最高者" },
  destructive_advice:          { pattern:"ally_highest", label:"技能：己方武力最高者" },
  flying_dance:                { pattern:"all_allies", label:"技能：己方全体" },
  fence_rebuild:               { pattern:"allied_fence", label:"技能：己方防栅武将" },
  taiping_arts:                { pattern:"fallen_allies", label:"技能：己方阵亡武将" },
  corrupt_dance:               { pattern:"all_enemies", label:"技能：敌方全体" },
  meteor_rite:                 { pattern:"enemy_select_vertical_column", label:"技能：敌方可选一竖列" },
  small_chain_plot:            { pattern:"enemy_select_2x1", label:"技能：敌方可选2×1区域" },
  weakening_chain:             { pattern:"enemy_candidates", label:"技能：敌方单体／连计扩散" }
};

function rangeCell(teamKey, row, col) {
  var gridId = teamKey === "p1" ? "#bside1-grid" : "#bside2-grid";
  return document.querySelector(gridId + ' .bcell[data-row="' + row + '"][data-col="' + col + '"]');
}

function markRangePosition(teamKey, row, col, kind) {
  var cell = rangeCell(teamKey, row, col);
  if (cell) cell.classList.add(kind === "attack" ? "range-attack" : "range-skill");
}

function markGeneralRange(teamKey, general, kind) {
  if (general && general.row >= 0 && general.col >= 0) {
    markRangePosition(teamKey, general.row, general.col, kind);
  }
}

function aliveGenerals(teamKey) {
  var team = G && G[teamKey];
  return team ? team.generals.filter(function(g) { return g.alive && g.row >= 0; }) : [];
}

function markWholeBoard(teamKey, kind) {
  for (var row = 0; row < 3; row++) {
    for (var col = 0; col < 4; col++) markRangePosition(teamKey, row, col, kind);
  }
}

function markAliveTeam(teamKey, kind, predicate) {
  aliveGenerals(teamKey).forEach(function(g) {
    if (!predicate || predicate(g)) markGeneralRange(teamKey, g, kind);
  });
}

function markCoordinates(teamKey, coords, kind) {
  coords.forEach(function(pos) { markRangePosition(teamKey, pos[0], pos[1], kind); });
}

function highestForceGeneral(teamKey) {
  var list = aliveGenerals(teamKey).slice();
  list.sort(function(a, b) {
    return (b.effective_force - a.effective_force) ||
      (b.effective_intelligence - a.effective_intelligence) || (b.hp - a.hp);
  });
  return list[0] || null;
}

function attackRangeFor(general, enemyKey) {
  var enemies = aliveGenerals(enemyKey);
  var fronts = [];
  for (var lane = 0; lane < 4; lane++) {
    var laneGenerals = enemies.filter(function(g) { return g.col === lane; })
      .sort(function(a, b) { return a.row - b.row; });
    if (!laneGenerals.length) continue;
    var front = laneGenerals[0];
    var hiddenStillBlocks = front._ambushHidden && enemies.length > 1;
    if (!hiddenStillBlocks) fronts.push(front);
  }
  if (general._frontOnlyAttack) {
    fronts = fronts.filter(function(target) { return target.col === general.col; });
  }
  if (general._forcedTargetId) {
    fronts = fronts.filter(function(target) { return target.id === general._forcedTargetId; });
  }
  return fronts;
}

function markSkillRange(general, allyKey, enemyKey) {
  var rule = SKILL_RANGE_RULES[general.skill_id];
  var pattern = rule ? rule.pattern : "";
  var label = rule ? rule.label : "技能：" + (general.skill || "无");

  if (!pattern) {
    if (general._targetType === "ALL_ALLIES") pattern = "all_allies";
    else if (general._targetType === "ALL_ENEMIES") pattern = "all_enemies";
    else if (general._targetType === "SINGLE_ALLY") pattern = "ally_highest";
    else if (general._targetType === "SINGLE_ENEMY") pattern = "enemy_candidates";
    else if (general._targetType === "AREA_ENEMY") pattern = "enemy_select_area";
    else pattern = "self";
  }

  if (pattern === "self") {
    markGeneralRange(allyKey, general, "skill");
  } else if (pattern === "ally_vertical_column") {
    // 同一逻辑 row 在转置后的 4×3 战场中是一整条视觉竖列。
    for (var lane = 0; lane < 4; lane++) {
      markRangePosition(allyKey, general.row, lane, "skill");
      var columnCell = rangeCell(allyKey, general.row, lane);
      if (columnCell) columnCell.classList.add("range-vertical-column");
    }
  } else if (pattern === "all_allies") {
    markAliveTeam(allyKey, "skill");
  } else if (pattern === "allied_fence") {
    markAliveTeam(allyKey, "skill", function(g) { return (g.attributes || []).indexOf("防栅") >= 0; });
  } else if (pattern === "fallen_allies") {
    (G[allyKey].generals || []).forEach(function(g) {
      if (!g.alive) markGeneralRange(allyKey, g, "skill");
    });
  } else if (pattern === "ally_highest") {
    markGeneralRange(allyKey, highestForceGeneral(allyKey), "skill");
  } else if (pattern === "ally_select_2x2_self") {
    getRectAreaCandidates(allyKey, general, { height:2, width:2, constraint:"contains_caster" })
      .forEach(function(candidate) { markCoordinates(allyKey, candidate.positions, "skill"); });
  } else if (pattern === "ally_select_front_2x2") {
    getRectAreaCandidates(allyKey, general, { height:2, width:2, constraint:"front_of_caster" })
      .forEach(function(candidate) { markCoordinates(allyKey, candidate.positions, "skill"); });
  } else if (pattern === "ally_select_3x3_self") {
    getRectAreaCandidates(allyKey, general, { height:3, width:3, constraint:"contains_caster" })
      .forEach(function(candidate) { markCoordinates(allyKey, candidate.positions, "skill"); });
  } else if (pattern === "all_enemies" || pattern === "enemy_candidates") {
    markAliveTeam(enemyKey, "skill");
  } else if (pattern.indexOf("enemy_select_") === 0) {
    markWholeBoard(enemyKey, "skill");
  }
  return label;
}

function applySelectionRangePreview() {
  var legend = document.getElementById("battle-range-legend");
  document.querySelectorAll(".bside").forEach(function(side) { side.classList.remove("selection-active"); });
  if (!selectedAttacker || !G || !legend) {
    if (legend) { legend.style.display = "none"; legend.innerHTML = ""; }
    return;
  }

  var allyKey = currentTeamKey();
  var enemyKey = allyKey === "p1" ? "p2" : "p1";
  var selectedSide = document.getElementById(allyKey === "p1" ? "bside1" : "bside2");
  if (selectedSide) selectedSide.classList.add("selection-active");

  var parts = [];
  if (!selectedAttacker.general._hasAttacked) {
    attackRangeFor(selectedAttacker.general, enemyKey).forEach(function(target) {
      markGeneralRange(enemyKey, target, "attack");
    });
    parts.push('<span class="range-key attack">普攻可达</span>');
  }
  if (battlePhase !== "target" && selectedAttacker.general.skill) {
    var skillLabel = markSkillRange(selectedAttacker.general, allyKey, enemyKey);
    parts.push('<span class="range-key skill">' + skillLabel + '</span>');
  }
  legend.innerHTML = parts.join("");
  legend.style.display = parts.length ? "inline-flex" : "none";
}

function announceTurn(state) {
  if (!state || state.phase !== "battle") return;
  var signature = state.turn + ":" + state.current_team;
  if (_lastTurnSignature === signature) return;
  _lastTurnSignature = signature;
  var banner = document.getElementById("turn-banner");
  if (!banner || window.__stressMode) return;
  banner.textContent = "第" + state.turn + "回合 · " + (state.current_player || "") + "执令";
  banner.classList.remove("show");
  void banner.offsetWidth;
  banner.classList.add("show");
  BattleAudio.play("morale");
}

function showSkillCinematic(name, caster, kind) {
  if (window.__stressMode) return Promise.resolve();
  var layer = document.getElementById("skill-cinematic");
  var battle = document.getElementById("scr-battle");
  if (!layer) return Promise.resolve();
  layer.setAttribute("data-kind", kind || "buff");
  layer.innerHTML = '<div class="skill-command"><strong>' + name + '</strong><small>' + caster + ' · 军令既出</small></div>';
  layer.classList.add("active");
  if (battle) battle.classList.add("battle-cinematic-focus");
  BattleAudio.play("command");
  return sleep(720).then(function() {
    layer.classList.remove("active");
    layer.innerHTML = "";
    if (battle) battle.classList.remove("battle-cinematic-focus");
  });
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
    announceTurn(r);

    setStatus(r.event || "点击己方武将，下达本回合军令");
    updateBattlePhaseUI();
    applySelectionRangePreview();
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
 * 视觉布局为 4排×3列：后端 col 对应视觉排，后端 row 对应前/中/后列。
 * 玩家1 row=0 在最右列，玩家2 row=0 在最左列，双方前卫朝向战场中线。
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
      var visual = formationVisualPosition(gridId === "bside1-grid", r, c);

      if (g) {
        cells += buildBcellHTML(g, r, c, visual.row, visual.col, isAlly);
      } else {
        cells += '<div class="bcell empty" data-row="' + r + '" data-col="' + c +
          '" style="grid-row:' + visual.row + ';grid-column:' + visual.col + ';font-size:9px;color:#3a2e1c">—</div>';
      }
    }
  }
  document.getElementById(gridId).innerHTML = cells;
}

/** 构建单个武将格子的 HTML（纯函数，便于测试和维护） */
function buildBcellHTML(g, r, c, gridRow, gridColumn, isAlly) {
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
  if (attrs.indexOf("连计") >= 0) cls.push("chain");
  if (attrs.indexOf("勇猛") >= 0 && g.hp <= g.maxHp / 2) cls.push("bravery-active");
  if (attrs.indexOf("魅力") >= 0) cls.push("charisma");
  if (attrs.indexOf("募兵") >= 0 && g.hp < g.maxHp) cls.push("recruit");
  if (attrs.indexOf("复活") >= 0) cls.push(g._reviveUsed ? "revive-used" : "revive");
  if (attrs.indexOf("伏兵") >= 0) {
    cls.push(g._ambushTriggered ? "ambush-triggered" : (g._ambushHidden ? "ambush-hidden" : "ambush-revealed"));
  }
  if ((g.buffs || []).length) cls.push("has-persistent-buff");
  if ((g.debuffs || []).length) cls.push("has-persistent-debuff");

  var effForce = g.effective_force !== undefined ? g.effective_force : (g.force || 0);
  var effIntel = g.effective_intelligence !== undefined ? g.effective_intelligence : (g.intelligence || 0);
  var attrStr = attrs.join(" · ") || "无属性";
  var shield = (g.buffs || []).find(function(effect) { return effect.type === "damage_shield"; });
  var statusHtml = '<div class="trait-ribbon">' + attrs.map(function(attr) {
    var icon = {"勇猛":"勇", "魅力":"魅", "募兵":"募", "防栅":"栅", "连计":"连", "复活":"生", "伏兵":"伏"}[attr] || attr.charAt(0);
    return '<span class="trait-mark trait-' + attr + '" title="' + attr + '">' + icon + '</span>';
  }).join("") + '</div>';
  if (g._fenceActive) statusHtml += '<div class="passive-fence" aria-label="防栅尚未被攻破"><i></i><i></i><i></i></div>';
  if (shield) statusHtml += '<div class="damage-shield" aria-label="护盾可吸收' + shield.value + '点伤害"><span>盾</span><b>' + shield.value + '</b></div>';
  if (attrs.indexOf("连计") >= 0) statusHtml += '<div class="chain-link" aria-hidden="true"></div>';
  if (g._ambushHidden) statusHtml += '<div class="ambush-veil" aria-label="伏兵隐藏中">伏</div>';
  var effectNames = {
    force_boost:"武+", intelligence_boost:"智+", force_reduction:"武-", intelligence_reduction:"智-",
    debuff_immunity:"免疫", attack_speed_judgment:"神速", attack_speed_required:"迟滞",
    front_only_attack:"攻城", ignore_fence:"破栅", knockback_on_damage:"击退",
    forced_attack_target:"挑衅", poison:"中毒"
  };
  var persistentEffects = (g.buffs || []).filter(function(effect) { return effect.type !== "damage_shield"; }).map(function(effect) {
    return {kind:"buff", type:effect.type, value:effect.value, duration:effect.duration};
  }).concat((g.debuffs || []).map(function(effect) {
    return {kind:"debuff", type:effect.type, value:effect.value, duration:effect.duration};
  }));
  if (persistentEffects.length) statusHtml += '<div class="persistent-status-stack">' + persistentEffects.map(function(effect) {
    var label = effectNames[effect.type] || (effect.kind === "buff" ? "增益" : "减益");
    var value = typeof effect.value === "number" && effect.value !== 1 ? effect.value : "";
    return '<span class="persistent-status ' + effect.kind + '" title="' + effect.type + '，剩余' + effect.duration + '回合">' + label + value + '<i>' + effect.duration + '</i></span>';
  }).join("") + '</div>';

  return '<div class="' + cls.join(" ") + '"' +
    ' data-name="' + g.name + '" data-id="' + g.id + '" data-row="' + r + '" data-col="' + c + '"' +
    ' data-isally="' + (isAlly ? "1" : "0") + '"' +
    ' data-force="' + effForce + '" data-intel="' + effIntel + '"' +
    ' data-skill="' + (g.skill || "") + '" data-skill-desc="' + (g.skill_desc || "") + '"' +
    ' data-attrs="' + (attrs.join(",")) + '"' +
    ' data-tooltip="<b>' + g.name + '</b> 武' + effForce + ' 智' + effIntel +
    ' HP ' + g.hp + '/' + g.maxHp + '<br>技能：' + (g.skill || "无") + '<br>' +
    (g.skill_desc || "") + '<br>属性：' + attrStr + '"' +
    ' style="grid-row:' + gridRow + ';grid-column:' + gridColumn + '">' +
    (imgSrc ? '<img src="' + imgSrc + '">' : "") +
    statusHtml +
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
    if (isAlly) {
      Promise.resolve(onBattleAllyCell(r, c)).then(unlock).catch(unlock);
    } else {
      Promise.resolve(onBattleEnemyCell(r, c)).then(unlock).catch(unlock);
    }
    function unlock() { _battleClickLock = false; }
  });
})();

function updateBattlePhaseUI() {
  var phTag = battlePhase === "target" ? "ph-target" : (selectedAttacker ? "ph-attack" : "ph-skill");
  var phText = battlePhase === "target" ? "择定普攻目标" :
    (selectedAttacker ? "已执 " + selectedAttacker.general.name + " · 请下令" : "点选武将 · 下达军令");
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
  var skillCost = selected ? (selected.skill_cost || 0) : 0;
  var canSkill = canAct && selected && selected.skill && selected.skill !== "无" && !selected.cooldown && !hasUsedSkill && morale >= skillCost;
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
    } else if (morale < skillCost && selected.skill) {
      skillBtn.setAttribute("data-tooltip", "士气不足！需要 " + skillCost + " 点士气");
    } else if (canSkill && selected.skill) {
      skillBtn.setAttribute("data-tooltip", selected.skill + " — " + (selected.skill_desc || ""));
    }

    if (hasAttacked) {
      attackBtn.setAttribute("data-tooltip", selected.name + " 本回合已普攻过");
    } else if (canAttack) {
      attackBtn.setAttribute("data-tooltip", selected.name + " 普攻 — 武力 " + (selected.force || 0));
    }
  }

  skipBtn.textContent = battlePhase === "target" ? "收回攻令" : "结束行动";
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
    BattleAudio.play("select");
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
async function onBattleEnemyCell(r, c) {
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
    guess = await askOddEven();
    if (!guess) {
      battlePhase = "action";
      return renderBattle();
    }
  }

  setStatus(guess ? "正在进行攻速判定……" : "正在发动普攻……");
  var result = await call("/battle/attack", {
    attacker_id: selectedAttacker.general.id,
    target_id: target.id,
    guess: guess
  });
  if (!result) {
    setStatus("普攻请求失败，请检查服务器连接");
    return;
  }

  if (result.speed_judgment) {
    await showSpeedJudgment(result.speed_judgment);
  }

  var attackResult = result.attack_result;
  if (attackResult && attackResult.performed && aCell && tCell) {
    await animAttack(aCell, tCell, attackResult.damage || 0, attackResult.target_hp_after <= 0);
    await playCombatEvents(attackResult.events || []);
  }

  clearBattleSelection();
  if (G && G.phase === "over") { showGameOver(); return; }
  return renderBattle();
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
async function useSkill() {
  if (!selectedAttacker) { setStatus("未选择武将，无法使用技能"); return; }
  var sk = selectedAttacker.general.skill;
  if (!sk || sk === "无") { setStatus(selectedAttacker.general.name + " 没有主动技能"); return; }
  if (selectedAttacker.general.cooldown) { setStatus(sk + " 冷却中 (剩余" + selectedAttacker.general.cooldown + "回合)"); return; }
  if (selectedAttacker.general._hasUsedSkill) { setStatus(selectedAttacker.general.name + " 本回合已使用过技能"); return; }

  // 按技能规则先选择实际落点；取消选区时不消耗技能和士气。
  var skillId = selectedAttacker.general.skill_id || "";
  var castOptions = await chooseSkillCastOptions(selectedAttacker.general);
  if (castOptions === null) return;
  var guess = null;
  if (skillId === "thunder_strike") {
    guess = await askOddEven("雷击判定——由夏侯月姬猜奇偶；猜对则在选定2×2区域落雷，猜错则无事发生");
    if (!guess) return;
  }

  setStatus("正在使用 " + sk + "...");
  var skillType = detectSkillType(sk);
  var aIsP1 = (G.current_team === "p1");
  var allyGrid = aIsP1 ? "#bside1-grid" : "#bside2-grid";

  // 施法者先抬卡并进入技能暗场，随后才结算真实目标反馈。
  var cellEl = document.querySelector(allyGrid + ' .bcell[data-row="' + selectedAttacker.row + '"][data-col="' + selectedAttacker.col + '"]');
  if (cellEl) cellEl.classList.add("casting");
  await showSkillCinematic(sk, selectedAttacker.general.name, skillType);

  var body = { general_id: selectedAttacker.general.id };
  if (castOptions.area) {
    body.area_row = castOptions.area.r;
    body.area_col = castOptions.area.c;
    body.area_orientation = castOptions.area.orientation || undefined;
  }
  if (castOptions.skillRow !== undefined) body.skill_row = castOptions.skillRow;
  if (castOptions.mode) body.skill_mode = castOptions.mode;
  if (castOptions.timing) body.skill_timing = castOptions.timing;
  if (guess) { body.guess = guess; }
  var result = await call("/battle/skill", body);
  if (!result) {
    setStatus("技能请求失败，请检查服务器连接");
    clearBattleSelection();
    return renderBattle();
  }
  setStatus(result.event || (sk + " 已使用"));
  if (result.skill_result && result.skill_result.success) {
    await playSkillResolution(result.skill_result, sk, skillType, skillId);
    await playCombatEvents(result.combat_events || []);
  } else {
    BattleAudio.play("failure");
  }

  clearBattleSelection();
  if (G.phase === "over") { showGameOver(); return; }
  return renderBattle();
}

function findBattleCellByName(name) {
  return Array.prototype.find.call(document.querySelectorAll("#scr-battle .bcell[data-name]"), function(cell) {
    return cell.getAttribute("data-name") === name;
  }) || null;
}

function generalStateByName(name) {
  var all = [].concat((G && G.p1 && G.p1.generals) || [], (G && G.p2 && G.p2.generals) || []);
  return all.find(function(general) { return general.name === name; }) || null;
}

function detailVisualKind(detail, result, fallback) {
  var effect = (detail && detail.effect) || "";
  if (fallback === "lightning" || fallback === "fire") return fallback;
  if ((detail && (detail.healed > 0 || detail.heal > 0)) || /回复|恢复|治疗|生命上限/.test(effect)) return "heal";
  if ((detail && detail.damage > 0) || result.type === "damage") return "damage";
  if (/削弱|降低|减少|减益|武力-|智力-|中毒|离间|挑衅/.test(effect) || fallback === "debuff") return "debuff";
  if (/士气|号令|鼓舞/.test(effect) || fallback === "morale") return "morale";
  return "buff";
}

async function playSkillResolution(skillResult, skillName, fallbackKind, skillId) {
  if (window.__stressMode) return;
  var details = skillResult.details || [];
  var sounded = {};
  if (!details.length) {
    BattleAudio.play(skillResult.success ? (fallbackKind || "command") : "failure");
    return sleep(180);
  }
  if (skillId === "thunder_strike") {
    var thunderJudgment = Object.assign({}, skillResult.judgment || (details[0] && details[0].judgment) || {}, {
      title: "雷击判定",
      message: skillResult.triggered ? "判定成功，天雷将至" : "判定失败，雷击未能发动"
    });
    await showSpeedJudgment(thunderJudgment);
    if (!skillResult.triggered) {
      BattleAudio.play("failure");
      await sleep(280);
      return;
    }
    for (var thunderIndex = 0; thunderIndex < details.length; thunderIndex++) {
      var thunderDetail = details[thunderIndex];
      var thunderCell = findBattleCellByName(thunderDetail.target);
      if (!thunderCell) continue;
      var thunderCenter = getCellCenter(thunderCell);
      FX.lightningStrike(thunderCenter.x, thunderCenter.y);
      BattleAudio.play("lightning");
      await sleep(220);
      thunderCell.classList.add("resolve-lightning");
      await sleep(100);
      spawnFloatNum(thunderCell, thunderDetail.damage, "damage");
      await sleep(420);
      thunderCell.classList.remove("resolve-lightning");
    }
    return;
  }
  if (skillId === "meteor_rite") {
    for (var meteorIndex = 0; meteorIndex < details.length; meteorIndex++) {
      var meteorDetail = details[meteorIndex];
      var meteorCell = findBattleCellByName(meteorDetail.target);
      if (!meteorCell) continue;
      var meteorCenter = getCellCenter(meteorCell);
      FX.meteorStrike(meteorCenter.x, meteorCenter.y);
      BattleAudio.play("fire");
      await sleep(300);
      meteorCell.classList.add("resolve-damage");
      spawnFloatNum(meteorCell, meteorDetail.damage || 0, "damage");
      await sleep(240);
      meteorCell.classList.remove("resolve-damage");
    }
    return;
  }
  details.forEach(function(detail) {
    var cell = findBattleCellByName(detail.target);
    if (!cell) return;
    var kind = detailVisualKind(detail, skillResult, fallbackKind);
    var cssKind = kind === "fire" ? "damage" : kind;
    cell.classList.add("resolve-" + cssKind);
    var center = getCellCenter(cell);
    if (kind === "lightning") FX.lightningStrike(center.x, center.y);
    else if (kind === "fire") FX.fireBurst(center.x, center.y);
    else if (kind === "heal") FX.healSparkles(center.x, center.y);
    else if (kind === "debuff") FX.debuffMiasma(center.x, center.y);
    else if (kind === "morale") FX.moraleWave(center.x, center.y);
    else FX.burst(center.x, center.y, "#91aa8e", 10, 2.5);

    if (detail.damage > 0) spawnFloatNum(cell, detail.damage, "damage");
    else if ((detail.healed || detail.heal) > 0) spawnFloatNum(cell, -(detail.healed || detail.heal), "heal");
    else if (detail.judgment && detail.damage === 0) spawnSkillLabel(cell, "避");
    else if (detail.effect) spawnSkillLabel(cell, detail.effect.length > 10 ? skillName : detail.effect);

    if (!sounded[kind]) { BattleAudio.play(kind); sounded[kind] = true; }
    var finalState = generalStateByName(detail.target);
    if (finalState && !finalState.alive) cell.classList.add("defeated-card");
  });
  await sleep(680);
}

async function playCombatEvents(events) {
  if (window.__stressMode || !events || !events.length) return;
  for (var i = 0; i < events.length; i++) {
    var event = events[i];
    var cell = document.querySelector('#scr-battle .bcell[data-id="' + event.general_id + '"]');
    if (!cell) continue;
    var center = getCellCenter(cell);
    if (event.type === "fence_block") {
      cell.classList.add("fence-breaking"); spawnSkillLabel(cell, "破栅"); BattleAudio.play("block");
    } else if (event.type === "shield_absorb") {
      cell.classList.add("shield-impact"); spawnSkillLabel(cell, "护盾 -" + event.absorbed); BattleAudio.play("block");
    } else if (event.type === "recruit_heal") {
      cell.classList.add("recruit-trigger"); FX.healSparkles(center.x, center.y); spawnFloatNum(cell, -event.amount, "heal"); BattleAudio.play("heal");
    } else if (event.type === "bravery_judgment") {
      cell.classList.add("bravery-trigger"); spawnSkillLabel(cell, event.bonus > 0 ? "勇猛 +" + event.bonus : "勇猛");
    } else if (event.type === "charisma_judgment") {
      cell.classList.add("charisma-trigger"); spawnSkillLabel(cell, event.reflected > 0 ? "魅力反噬" : "魅力判定");
    } else if (event.type === "chain_share") {
      cell.classList.add("chain-trigger"); FX.burst(center.x, center.y, "#b59b62", 14, 2.2); spawnSkillLabel(cell, "连计分伤");
    } else if (event.type === "revive") {
      cell.classList.add("revive-trigger"); FX.healSparkles(center.x, center.y); spawnSkillLabel(cell, "再起 · " + event.hp + " HP"); BattleAudio.play("success");
    } else if (event.type === "ambush_counter") {
      cell.classList.add("ambush-trigger-fx"); FX.debuffMiasma(center.x, center.y); spawnSkillLabel(cell, "伏兵反击 -" + event.damage); BattleAudio.play("impact");
    }
    await sleep(520);
    cell.classList.remove("fence-breaking", "shield-impact", "recruit-trigger", "bravery-trigger", "charisma-trigger", "chain-trigger", "revive-trigger", "ambush-trigger-fx");
  }
}

async function playTurnEvents(events) {
  if (window.__stressMode || !events) return;
  var morale = events.find(function(event) { return event.type === "morale_restore"; });
  if (morale && morale.amount > 0) {
    var header = document.querySelector(morale.team === "p1" ? "#bside1 .morale-inline" : "#bside2 .morale-inline");
    if (header) { spawnSkillLabel(header, "士气 +" + morale.amount); BattleAudio.play("morale"); }
    await sleep(460);
  }
  await playCombatEvents(events.filter(function(event) { return event.type !== "morale_restore"; }));
}

/** 跳过当前阶段/回合 */
function skipPhase() {
  if (battlePhase === "target") {
    battlePhase = "action";
    return renderBattle();
  }
  clearBattleSelection();
  return call("/battle/skip").then(async function(result) {
    await playTurnEvents((result && result.turn_events) || []);
    if (G && G.phase === "over") { showGameOver(); return; }
    return renderBattle();
  });
}

/** 奇偶选择弹窗 */
function askOddEven(msg) {
  msg = msg || "攻速判定——猜对则额外普攻一次";
  if (window.__stressMode) return Promise.resolve(Math.random() < .5 ? "奇" : "偶");
  return new Promise(function(resolve) {
    var overlay = document.createElement("div");
    overlay.className = "speed-judgment-overlay odd-even-order";
    overlay.innerHTML =
      '<div class="speed-judgment-panel"><div class="speed-title">听骰定势</div>' +
      '<div class="speed-choice">' + msg + '</div><div class="speed-die">骰</div>' +
      '<div class="odd-even-actions"><button type="button" data-guess="奇">押 奇</button>' +
      '<button type="button" data-guess="偶">押 偶</button></div><div class="speed-message">点击暗处可收回军令</div></div>';
    var wrapper = overlay.firstElementChild;
    wrapper.querySelectorAll("[data-guess]").forEach(function(button) {
      button.addEventListener("click", function(e) {
        e.stopPropagation();
        BattleAudio.play("dice");
        overlay.remove(); resolve(button.getAttribute("data-guess"));
      });
    });
    overlay.addEventListener("click", function(e) { if (e.target === overlay) { overlay.remove(); resolve(null); } });
    document.body.appendChild(overlay);
    BattleAudio.play("dice");
  });
}

/** 将服务器返回的真实骰点以滚动动画呈现，并明确显示判定影响。 */
function showSpeedJudgment(judgment) {
  if (window.__stressMode) return Promise.resolve();
  return new Promise(function(resolve) {
    var faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"];
    var overlay = document.createElement("div");
    overlay.className = "speed-judgment-overlay";
    overlay.innerHTML =
      '<div class="speed-judgment-panel">' +
      '<div class="speed-title">' + (judgment.title || "攻速判定") + '</div>' +
      '<div class="speed-choice">你选择了 <strong>' + (judgment.guess === "odd" ? "奇" : "偶") + '</strong></div>' +
      '<div class="speed-die rolling">⚀</div>' +
      '<div class="speed-points">正在掷骰……</div>' +
      '<div class="speed-result"></div>' +
      '<div class="speed-message"></div>' +
      '<div class="speed-continue">点击任意位置继续</div>' +
      '</div>';
    document.body.appendChild(overlay);

    var die = overlay.querySelector(".speed-die");
    var points = overlay.querySelector(".speed-points");
    var result = overlay.querySelector(".speed-result");
    var message = overlay.querySelector(".speed-message");
    var frame = 0;
    var finished = false;
    var closeTimer = null;

    function close() {
      if (!finished) return;
      if (closeTimer) clearTimeout(closeTimer);
      overlay.remove();
      resolve();
    }
    overlay.addEventListener("click", close);

    function rollFrame() {
      if (frame < 15) {
        die.textContent = faces[Math.floor(Math.random() * faces.length)];
        die.style.transform = "rotate(" + (frame * 31) + "deg) scale(" + (1 + (frame % 3) * 0.08) + ")";
        if (frame % 3 === 0) BattleAudio.play("dice");
        frame++;
        setTimeout(rollFrame, 35 + frame * 7);
        return;
      }

      var dice = Math.max(1, Math.min(6, parseInt(judgment.dice) || 1));
      var parity = judgment.parity === "odd" ? "奇" : "偶";
      die.classList.remove("rolling");
      die.style.transform = "rotate(0deg) scale(1)";
      die.textContent = faces[dice - 1];
      points.textContent = dice + " 点 · " + parity;
      result.textContent = judgment.success ? "判定成功" : "判定失败";
      result.className = "speed-result " + (judgment.success ? "success" : "failure");
      message.textContent = judgment.message || "";
      overlay.querySelector(".speed-judgment-panel").classList.add(judgment.success ? "success" : "failure");
      BattleAudio.play(judgment.success ? "success" : "failure");
      finished = true;
      closeTimer = setTimeout(close, 1600);
    }
    rollFrame();
  });
}

/** 简单二选一弹窗，返回选项 value；点击遮罩取消。 */
function askSkillOption(title, message, options) {
  if (window.__stressMode) return Promise.resolve(options && options[0] ? options[0].value : null);
  return new Promise(function(resolve) {
    var overlay = document.createElement("div");
    overlay.className = "skill-option-overlay";
    var buttons = options.map(function(option) {
      return '<button type="button" class="skill-option-btn" data-value="' + option.value + '">' +
        '<strong>' + option.label + '</strong><span>' + (option.description || "") + '</span></button>';
    }).join("");
    overlay.innerHTML = '<div class="skill-option-panel"><h3>' + title + '</h3><p>' + message +
      '</p><div class="skill-option-list">' + buttons + '</div></div>';
    overlay.querySelectorAll(".skill-option-btn").forEach(function(button) {
      button.addEventListener("click", function(e) {
        e.stopPropagation();
        var value = button.getAttribute("data-value");
        overlay.remove();
        resolve(value);
      });
    });
    overlay.addEventListener("click", function(e) {
      if (e.target === overlay) { overlay.remove(); resolve(null); }
    });
    document.body.appendChild(overlay);
  });
}

function rectPositions(row, col, height, width) {
  var positions = [];
  for (var r = row; r < row + height; r++) {
    for (var c = col; c < col + width; c++) positions.push([r, c]);
  }
  return positions;
}

/**
 * 生成逻辑 3×4 阵型中的合法矩形落点。画面虽已转置，data-row/data-col 仍保存逻辑坐标，
 * 因而高亮后会自然呈现为玩家实际看到的横向或纵向范围。
 */
function getRectAreaCandidates(teamKey, caster, config) {
  var height = config.height;
  var width = config.width;
  var candidates = [];
  var living = aliveGenerals(teamKey);
  for (var row = 0; row <= 3 - height; row++) {
    for (var col = 0; col <= 4 - width; col++) {
      var positions = rectPositions(row, col, height, width);
      var containsCaster = caster && positions.some(function(pos) {
        return pos[0] === caster.row && pos[1] === caster.col;
      });
      if (config.constraint === "contains_caster" && !containsCaster) continue;
      if (config.constraint === "front_of_caster") {
        var includesCasterLane = positions.some(function(pos) { return pos[1] === caster.col; });
        var reachesFront = positions.some(function(pos) { return pos[0] < caster.row; });
        if (!includesCasterLane || !reachesFront) continue;
      }
      var hasLivingTarget = living.some(function(general) {
        return positions.some(function(pos) {
          return pos[0] === general.row && pos[1] === general.col;
        });
      });
      if (!hasLivingTarget) continue;
      candidates.push({
        r: row,
        c: col,
        height: height,
        width: width,
        orientation: config.orientation || null,
        positions: positions
      });
    }
  }
  return candidates;
}

/** 在复制的战场中悬停预览并点击确定一个矩形技能范围。 */
function selectRectAreaForSkill(config) {
  return new Promise(function(resolve) {
    var allyKey = currentTeamKey();
    var teamKey = config.side === "ally" ? allyKey : (allyKey === "p1" ? "p2" : "p1");
    var gridSelector = teamKey === "p1" ? "#bside1-grid" : "#bside2-grid";
    var sourceGrid = document.querySelector(gridSelector);
    if (!sourceGrid) { resolve(null); return; }

    var candidates = getRectAreaCandidates(teamKey, selectedAttacker.general, config);
    if (!candidates.length) {
      setStatus("当前没有符合该技能规则的可选范围");
      resolve(null);
      return;
    }
    if (window.__stressMode) { resolve(candidates[0]); return; }

    var overlay = document.createElement("div");
    overlay.className = "skill-area-overlay";
    var panel = document.createElement("div");
    panel.className = "skill-area-panel";
    panel.innerHTML = '<h3>' + config.title + '</h3><p>金色框为可选落点；悬停查看蓝色覆盖范围，点击确认</p>';

    var gridClone = sourceGrid.cloneNode(true);
    gridClone.removeAttribute("id");
    gridClone.classList.add("skill-area-grid");
    var cells = Array.prototype.slice.call(gridClone.querySelectorAll(".bcell"));
    cells.forEach(function(cell) {
      cell.classList.remove("selected", "range-attack", "range-skill", "range-vertical-column", "locked", "acted");
      cell.removeAttribute("data-tooltip");
      cell.onclick = null;
    });

    function cellAt(row, col) {
      return cells.find(function(cell) {
        return parseInt(cell.getAttribute("data-row")) === row &&
          parseInt(cell.getAttribute("data-col")) === col;
      });
    }
    var activeCandidate = null;
    function preview(candidate) {
      activeCandidate = candidate;
      cells.forEach(function(cell) { cell.classList.remove("cast-area-preview"); });
      candidate.positions.forEach(function(pos) {
        var cell = cellAt(pos[0], pos[1]);
        if (cell) cell.classList.add("cast-area-preview");
      });
    }

    candidates.forEach(function(candidate) {
      var anchor = cellAt(candidate.r, candidate.c);
      if (!anchor) return;
      anchor.classList.add("cast-area-anchor");
      anchor.addEventListener("mouseenter", function() { preview(candidate); });
      anchor.addEventListener("focus", function() { preview(candidate); });
    });
    cells.forEach(function(cell) {
      cell.addEventListener("click", function(e) {
        if (!activeCandidate || !cell.classList.contains("cast-area-preview")) return;
        e.stopPropagation();
        overlay.remove();
        resolve(activeCandidate);
      });
    });
    preview(candidates[0]);
    panel.appendChild(gridClone);
    overlay.appendChild(panel);
    overlay.addEventListener("click", function(e) {
      if (e.target === overlay) { overlay.remove(); resolve(null); }
    });
    document.body.appendChild(overlay);
  });
}

/** 根据每项技能的真实规则收集落点、方向、模式等施放参数。 */
async function chooseSkillCastOptions(general) {
  var skillId = general.skill_id || "";
  var area;
  var choice;

  if (skillId === "meteor_rite") {
    var selectedRow = await selectVerticalColumnForSkill();
    return selectedRow === null ? null : { skillRow:selectedRow };
  }

  if (["stone_sentinel_maze", "spear_wheel_tactics", "thunder_strike", "taunt"].indexOf(skillId) >= 0) {
    area = await selectRectAreaForSkill({ side:"enemy", height:2, width:2, title:"选择敌方 2×2 技能范围" });
    return area ? { area:area } : null;
  }

  if (skillId === "discord_strategy") {
    area = await selectRectAreaForSkill({ side:"enemy", height:2, width:2, title:"离间谋略：选择敌方 2×2 范围" });
    if (!area) return null;
    choice = await askSkillOption("选择生效时机", "决定离间谋略何时削弱目标", [
      { value:"ally_attack", label:"我方进攻", description:"立即生效" },
      { value:"enemy_attack", label:"敌方进攻", description:"延迟至对方行动" }
    ]);
    return choice ? { area:area, timing:choice } : null;
  }

  if (skillId === "tooth_for_tooth") {
    choice = await askSkillOption("以牙还牙", "先选择技能模式，再选择对应范围", [
      { value:"wide", label:"2×2 广域", description:"范围内武力-3" },
      { value:"focused", label:"相邻2格", description:"武力-3并附加攻速限制" }
    ]);
    if (!choice) return null;
    if (choice === "wide") {
      area = await selectRectAreaForSkill({ side:"enemy", height:2, width:2, title:"选择敌方 2×2 范围" });
    } else {
      var toothDirection = await askAdjacentDirection();
      if (!toothDirection) return null;
      area = await selectRectAreaForSkill({ side:"enemy", height:toothDirection.height, width:toothDirection.width,
        orientation:toothDirection.orientation, title:"选择敌方相邻 2 格" });
    }
    return area ? { area:area, mode:choice } : null;
  }

  if (skillId === "small_chain_plot") {
    var chainDirection = await askAdjacentDirection();
    if (!chainDirection) return null;
    area = await selectRectAreaForSkill({ side:"enemy", height:chainDirection.height, width:chainDirection.width,
      orientation:chainDirection.orientation, title:"小连环计：选择敌方相邻 2 格" });
    return area ? { area:area } : null;
  }

  if (skillId === "momentary_order") {
    area = await selectRectAreaForSkill({ side:"ally", height:2, width:2, constraint:"contains_caster",
      title:"刹那的号令：选择包含曹仁的 2×2 范围" });
    return area ? { area:area } : null;
  }

  if (skillId === "meticulous_offense") {
    area = await selectRectAreaForSkill({ side:"ally", height:2, width:2, constraint:"front_of_caster",
      title:"缜密的攻势：选择前方 2×2 范围" });
    return area ? { area:area } : null;
  }

  if (skillId === "jiangdong_beauty") {
    area = await selectRectAreaForSkill({ side:"ally", height:3, width:3, constraint:"contains_caster",
      title:"江东的大美人：选择包含大乔的 3×3 范围" });
    return area ? { area:area } : null;
  }

  return {};
}

async function askAdjacentDirection() {
  var direction = await askSkillOption("选择相邻方向", "范围由两个相邻格组成", [
    { value:"visual_horizontal", label:"横向相邻", description:"画面中左右两个格子" },
    { value:"visual_vertical", label:"纵向相邻", description:"画面中上下两个格子" }
  ]);
  if (direction === "visual_horizontal") {
    // 画面已转置：视觉横向对应 logical row 方向。
    return { height:2, width:1, orientation:"vertical" };
  }
  if (direction === "visual_vertical") {
    return { height:1, width:2, orientation:"horizontal" };
  }
  return null;
}

/**
 * 流星的仪式：选择敌方一条视觉竖列。
 * 后端 logical row 对应转置布局中的视觉竖列，因此返回 0~2 的 logical row。
 */
function selectVerticalColumnForSkill() {
  if (window.__stressMode) return Promise.resolve(0);
  return new Promise(function(resolve) {
    var overlay = document.createElement("div");
    overlay.className = "skill-area-overlay";

    var enemyGrid = document.querySelector(G.current_team === "p1" ? "#bside2-grid" : "#bside1-grid");
    if (!enemyGrid) { resolve(null); return; }

    var gridClone = enemyGrid.cloneNode(true);
    gridClone.removeAttribute("id");
    gridClone.classList.add("skill-area-grid");

    var cells = Array.prototype.slice.call(gridClone.querySelectorAll(".bcell"));
    cells.forEach(function(cell) {
      cell.classList.remove("selected", "range-attack", "range-skill", "range-vertical-column", "locked", "acted");
      cell.removeAttribute("data-tooltip");
    });
    function highlightColumn(row) {
      cells.forEach(function(cell) {
        cell.classList.toggle("cast-area-preview", parseInt(cell.getAttribute("data-row")) === row);
      });
    }

    cells.forEach(function(cell) {
      var row = parseInt(cell.getAttribute("data-row"));
      if (isNaN(row)) return;
      cell.style.cursor = "pointer";
      cell.onmouseenter = function() { highlightColumn(row); };
      cell.onclick = function(e) {
        e.stopPropagation();
        overlay.remove();
        resolve(row);
      };
      cell.setAttribute("data-tooltip", "点击选择这一整条竖列");
    });
    highlightColumn(0);

    var wrapper = document.createElement("div");
    wrapper.className = "skill-area-panel";
    wrapper.innerHTML = '<h3>流星的仪式：选择一条竖列</h3>' +
      '<p>悬停可预览范围，点击敌方阵型中的任意格选择整列</p>';
    wrapper.appendChild(gridClone);
    overlay.appendChild(wrapper);

    overlay.addEventListener("click", function() { overlay.remove(); resolve(null); });
    document.body.appendChild(overlay);
  });
}

/** setTimeout 的 Promise 包装 */
function sleep(ms) {
  if (window.__stressMode) return Promise.resolve();
  return new Promise(function(resolve) { setTimeout(resolve, ms); });
}

// ============================================================================
// SECTION 8: 游戏结束 & 武将图鉴
// ============================================================================
function showGameOver() {
  showScreen("over");
  document.getElementById("over-winner").textContent = (G ? G.winner : "?") + " 获得胜利！";
  document.getElementById("over-stats").textContent = "总回合数: " + (G ? G.turn : "?");
  BattleAudio.play("victory");
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
  _lastTurnSignature = "";
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
    meteorStrike: function(x, y) {
      var projectile = document.createElement("div");
      projectile.className = "meteor-projectile";
      projectile.style.left = x + "px";
      projectile.style.top = y + "px";
      document.body.appendChild(projectile);
      setTimeout(function() { projectile.remove(); FX.fireBurst(x, y); FX.screenShake(); }, 270);
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
    },
    stats: function() { return { particles:particles.length, ambient:ambientParticles.length }; },
    clear: function() { particles.length = 0; }
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
  // 暴露给全局（useSkill 需要）
  window.detectSkillType = detectSkillType;

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

function animAttack(aEl, tEl, dmg, defeated) {
  if (window.__stressMode) return Promise.resolve();
  var aCenter = getCellCenter(aEl);
  var tCenter = getCellCenter(tEl);
  var dx = (tCenter.x - aCenter.x) * .78;
  var dy = (tCenter.y - aCenter.y) * .78;
  aEl.classList.remove("selected");
  aEl.classList.add("attack-anticipation");
  BattleAudio.play("anticipate");
  return sleep(130).then(function() {
    aEl.classList.remove("attack-anticipation");
    aEl.style.transition = "transform .13s cubic-bezier(.7,0,1,.55)";
    aEl.style.transform = "translate(" + dx + "px," + dy + "px) scale(1.09)";
    FX.drawWeaponArc(aCenter.x, aCenter.y, tCenter.x, tCenter.y, "rgba(230,218,188,.72)");
    return sleep(110);
  }).then(function() {
    FX.slashTrail(aCenter.x, aCenter.y, tCenter.x, tCenter.y);
    FX.screenShake();
    tEl.classList.add("impact-flash", "resolve-damage");
    BattleAudio.play(dmg > 0 ? "impact" : "block");
    if (dmg > 0) spawnFloatNum(tEl, dmg, "damage"); else spawnSkillLabel(tEl, "格挡");
    if (defeated) tEl.classList.add("defeated-card");
    aEl.style.transition = "transform .2s cubic-bezier(.16,1,.3,1)";
    aEl.style.transform = "translate(0,0) scale(1)";
    return sleep(240);
  }).then(function() {
    aEl.style.transition = ""; aEl.style.transform = "";
    tEl.classList.remove("impact-flash", "resolve-damage");
  });
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
