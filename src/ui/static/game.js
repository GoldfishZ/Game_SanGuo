// ===== STATE =====
let G = null;
let selectedGenerals = [];
let selectedFormGen = null;
let battlePhase = "select";
let selectedAttacker = null;
let galleryIdx = 0;
let galleryFiltered = [];

// ===== API =====
let SERVER_OK = false;

async function api(method, path, body) {
  try {
    let opts = {method: method || "GET", headers: {"Content-Type":"application/json"}};
    if (body) { opts.body = JSON.stringify(body); opts.method = "POST"; }
    let r = await fetch(path, opts);
    if (!r.ok) throw new Error("HTTP "+r.status);
    let data = await r.json();
    SERVER_OK = true;
    return data;
  } catch(e) {
    console.error("API error:", path, e);
    if (!SERVER_OK) {
      document.body.innerHTML = '<div style="padding:40px;text-align:center;color:#c07070">' +
        '<h2>无法连接到游戏服务器</h2>' +
        '<p>请先运行: <code style="background:#1a1410;padding:6px 12px;border-radius:4px">python main_web.py</code></p>' +
        '<p style="color:#8a7a5a;margin-top:12px">然后访问 <code>http://localhost:8088</code></p>' +
        '</div>';
    }
    return null;
  }
}

async function call(endpoint, body) {
  let r = await api("POST", "/api" + endpoint, body || {});
  if (r) G = r;
  return r;
}

// ===== Screen switching =====
function showScreen(name) {
  document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
  let el = document.getElementById("scr-" + name);
  if (el) el.classList.add("active");
  if (name === "gallery") initGallery();
}

// ===== Menu → Start =====
async function startGame() {
  let r = await call("/new");
  await renderSelection();
}

// ===== Selection =====
async function renderSelection() {
  showScreen("select");
  selectedGenerals = [];
  let r = G || await call("/state");
  document.getElementById("sel-title").textContent =
    (r.phase === "select_p1" ? "玩家1" : "玩家2") + " — 选择武将";
  renderCards(r.pool);
  renderPoolBar();
}

function renderCards(pool) {
  let html = "";
  let attrConf = {
    "勇猛":{c:"#c04840",l:"勇"}, "魅力":{c:"#b050b8",l:"魅"}, "募兵":{c:"#48a048",l:"募"},
    "防栅":{c:"#4868c0",l:"防"}, "连环":{c:"#b09830",l:"连"}, "复活":{c:"#d06840",l:"复"},
    "伏兵":{c:"#5068b8",l:"伏"}
  };
  (pool || []).forEach(g => {
    let inPool = selectedGenerals.includes(g.id);
    let imgSrc = g.image ? "/generals/" + g.image : "";
    let attrTags = (g.attributes||[]).map(a => {
      let ac = attrConf[a]||{c:"#666",l:a[0]};
      return '<span style="background:' + ac.c + ';color:#fff;font-size:9px;width:18px;height:18px;display:inline-flex;align-items:center;justify-content:center;border-radius:50%;font-weight:700;border:1px solid rgba(255,255,255,.2);text-shadow:0 1px 2px rgba(0,0,0,.3)">' + ac.l + '</span>';
    }).join("");
    html += '<div class="card card-' + (g.camp||'ta') + (inPool?' selected':'') + '" onclick="showGeneralPreview(event,\'' + g.id + '\')" data-id="' + g.id + '" style="' + (inPool?'opacity:.5':'') + '">' +
      (imgSrc ? '<img src="' + imgSrc + '" alt="' + g.name + '" onerror="this.style.display=\'none\';this.nextSibling.style.display=\'flex\'">' : "") +
      '<div style="width:100%;height:100%;display:' + (imgSrc?'none':'flex') + ';align-items:center;justify-content:center;font-size:28px;color:#8a7a5a">' + g.name[0] + '</div>' +
      (attrTags ? '<div style="position:absolute;top:6px;right:6px;display:flex;gap:3px">' + attrTags + '</div>' : '') +
      (inPool?'<div class="badge">✓</div>':'') +
    '</div>';
  });
  document.getElementById("sel-cards").innerHTML = html;
}

function renderPoolBar() {
  let poolEl = document.getElementById("sel-pool-area");
  let selGens = selectedGenerals.map(id => G && G.pool ? G.pool.find(g => g.id == id) : null).filter(Boolean);
  let costLimit = G ? G.cost_limit || 8.0 : 8.0;
  let spent = selGens.reduce(function(sum,g) { return sum + (g.cost||0); }, 0);
  let remaining = Math.max(0, costLimit - spent);

  var html = '';
  html += '<div style="display:flex;align-items:center;gap:10px;margin-right:12px;padding:2px 12px;background:rgba(200,170,70,.1);border-radius:6px;border:1px solid ' + (remaining > 0 ? 'var(--gold)' : '#a0524d') + '">' +
    '<span style="font-size:11px;color:var(--muted)">费用</span>' +
    '<span style="font-size:18px;font-weight:700;color:' + (remaining > 0 ? 'var(--gold)' : '#c07070') + '">' + remaining + '</span>' +
    '<span style="font-size:10px;color:var(--muted)">/' + costLimit + '</span>' +
    '</div>';

  html += selGens.map(function(g,i) {
    return '<div style="background:var(--panel);border:1px solid var(--gold);border-radius:6px;padding:4px 10px;cursor:pointer;display:flex;align-items:center;gap:6px;font-size:12px" onclick="removeFromPool(' + g.id + ')">' +
      '<span style="color:var(--muted);font-size:10px">' + g.cost + '费</span>' +
      '<span style="font-weight:700">' + g.name + '</span>' +
      '<span style="color:var(--muted);font-size:10px">×</span>' +
      '</div>';
  }).join("");

  if (selGens.length === 0) {
    html += '<span id="sel-pool-empty" style="font-size:11px;color:var(--muted);padding:4px 12px">点击武将卡预览后「加入选将池」</span>';
  }

  poolEl.innerHTML = html;
  document.getElementById("sel-done").disabled = selectedGenerals.length === 0;
  document.getElementById("sel-done").textContent = '完成选择 (' + selectedGenerals.length + '人 · ' + spent + '/' + costLimit + '费)';
}

function showGeneralPreview(evt, id) {
  var g = G && G.pool ? G.pool.find(function(x) { return x.id == id; }) : null;
  if (!g) return;
  var inPool = selectedGenerals.includes(id);
  var imgSrc = g.image ? "/generals/" + g.image : "";
  document.getElementById("preview-img").src = imgSrc;
  document.getElementById("preview-name").textContent = g.name;
  document.getElementById("preview-info").innerHTML = previewInfoHTML(g, inPool);
  document.getElementById("preview").style.display = "flex";
}

// Consolidated preview info HTML — single source of truth
function previewInfoHTML(g, inPool) {
  return g.camp + ' · ' + g.rarity + ' · 费用' + g.cost + '<br>' +
    '武' + g.force + ' 智' + g.intelligence + ' · ' + g.skill + '<br>' +
    '属性: ' + ((g.attributes||[]).join(" · ") || "无") + '<br>' +
    '<small style="color:var(--muted)">' + (g.skill_desc||"") + '</small><br><br>' +
    '<span class="btn ' + (inPool?'danger':'primary') + '" style="font-size:12px;padding:4px 14px" onclick="togglePool(\'' + g.id + '\')">' +
      (inPool ? '移出选将池' : '加入选将池') +
    '</span>';
}

function togglePool(id) {
  if (selectedGenerals.includes(id)) {
    selectedGenerals = selectedGenerals.filter(function(x) { return x !== id; });
  } else {
    // 检查费用上限
    var g = G && G.pool ? G.pool.find(function(x) { return x.id == id; }) : null;
    var costLimit = G ? G.cost_limit || 8.0 : 8.0;
    var spent = selectedGenerals.reduce(function(sum,x) {
      var gen = G && G.pool ? G.pool.find(function(g2) { return g2.id == x; }) : null;
      return sum + (gen ? gen.cost : 0);
    }, 0);
    if (g && spent + g.cost > costLimit) {
      alert('费用不足！\n当前已用 ' + spent + ' 费，' + g.name + ' 需要 ' + g.cost + ' 费，剩余 ' + (costLimit-spent).toFixed(1) + ' 费');
      return;
    }
    selectedGenerals.push(id);
  }
  renderCards(G.pool);
  renderPoolBar();
  // Update preview button text without closing
  var g2 = G && G.pool ? G.pool.find(function(x) { return x.id == id; }) : null;
  if (g2 && document.getElementById("preview").style.display === "flex") {
    var inPool = selectedGenerals.includes(id);
    document.getElementById("preview-info").innerHTML = previewInfoHTML(g2, inPool);
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

async function confirmSelection() {
  if (selectedGenerals.length === 0) return;
  await call("/select", {general_ids: selectedGenerals});
  if (G.phase === "select_p2") {
    selectedGenerals = [];
    await renderSelection();
  } else {
    await renderFormation();
  }
}

// ===== Formation =====
async function renderFormation() {
  showScreen("formation");
  selectedFormGen = null;

  var r = G || await call("/state");
  var teamKey = r.phase === "formation_p1" ? "p1" : "p2";
  document.getElementById("form-title").textContent =
    (r.phase === "formation_p1" ? "玩家1" : "玩家2") + " — 布置阵型";

  var generals = r[teamKey] ? r[teamKey].generals || [] : [];
  renderFormList(generals);
  renderFormGrid(generals);
}

function renderFormList(generals) {
  var html = "";
  (generals || []).forEach(function(g) {
    var isActive = selectedFormGen && selectedFormGen.id === g.id;
    var rowInfo = g.row >= 0 ? ('已放:(' + g.row + ',' + g.col + ')') : '未放置';
    html += '<div class="gi' + (isActive ? ' active' : '') + '" onclick="selectFormGen(' + g.id + ')">' +
      '<span style="font-weight:600">' + g.name + '</span>' +
      '<span style="font-size:10px;color:var(--muted);margin-left:6px">' + rowInfo + '</span>' +
      '</div>';
  });
  document.getElementById("form-list").innerHTML = html ||
    '<div style="font-size:11px;color:var(--muted);padding:8px">无武将可选</div>';
}

function renderFormGrid(generals) {
  var grid = Array.from({length:3}, function() { return Array(4).fill(null); });
  (generals || []).forEach(function(g) {
    if (g.row >= 0 && g.col >= 0) grid[g.row][g.col] = g;
  });

  var html = "";
  for (var r = 0; r < 3; r++) {
    for (var c = 0; c < 4; c++) {
      var g = grid[r][c];
      if (g) {
        html += '<div class="form-cell filled" onclick="placeGeneral(' + r + ',' + c + ')">' +
          g.name + '</div>';
      } else {
        html += '<div class="form-cell' + (selectedFormGen ? ' droptarget' : '') + '" onclick="placeGeneral(' + r + ',' + c + ')">+</div>';
      }
    }
  }
  document.getElementById("form-grid").innerHTML = html;
}

function selectFormGen(id) {
  var teamKey = G.phase === "formation_p1" ? "p1" : "p2";
  var generals = G[teamKey] ? G[teamKey].generals || [] : [];
  selectedFormGen = generals.find(function(g) { return g.id === id; });
  if (!selectedFormGen) return;
  renderFormList(generals);
  renderFormGrid(generals);
}

function placeGeneral(r, c) {
  if (!selectedFormGen) return;
  var teamKey = G.phase === "formation_p1" ? "p1" : "p2";
  var generals = G[teamKey] ? G[teamKey].generals || [] : [];
  selectedFormGen.row = r;
  selectedFormGen.col = c;
  // Remove any other general from this position
  generals.forEach(function(g) {
    if (g.id !== selectedFormGen.id && g.row === r && g.col === c) {
      g.row = -1; g.col = -1;
    }
  });
  renderFormList(generals);
  renderFormGrid(generals);
}

async function confirmFormation() {
  var teamKey = G.phase === "formation_p1" ? "p1" : "p2";
  var generals = G[teamKey] ? G[teamKey].generals || [] : [];
  var positions = generals
    .filter(function(g) { return g.row >= 0 && g.col >= 0; })
    .map(function(g) { return {general_id: g.id, row: g.row, col: g.col}; });

  if (positions.length < generals.length) {
    document.getElementById("form-hint").textContent = "请将所有武将放置到阵型中";
    return;
  }

  await call("/place", {positions: positions});
  if (G.phase === "formation_p2") {
    selectedFormGen = null;
    await renderFormation();
  } else {
    showScreen("dice");
  }
}

// ===== Dice =====
async function rollDice() {
  // 先请求服务器获取结果
  var r = await call("/dice");
  var finalD1 = G.d1 || 1;
  var finalD2 = G.d2 || 1;

  // 骰子滚动动画：快速交替显示随机数字 1.5 秒
  var d1El = document.getElementById("d1");
  var d2El = document.getElementById("d2");
  var resultEl = document.getElementById("dice-result");

  var totalFrames = 20;  // 1.5 秒约 20 帧
  var frame = 0;

  function tick() {
    if (frame < totalFrames) {
      // 动画阶段：随机数字
      d1El.textContent = Math.floor(Math.random() * 6) + 1;
      d2El.textContent = Math.floor(Math.random() * 6) + 1;
      d1El.style.color = "#c07070";
      d2El.style.color = "#4a6fa5";
      frame++;
      // 越接近结束越慢
      var delay = 30 + (frame / totalFrames) * 120;
      setTimeout(tick, delay);
    } else {
      // 最终结果
      d1El.textContent = finalD1;
      d2El.textContent = finalD2;
      // 赢家的骰子高亮
      if (finalD1 > finalD2) {
        d1El.style.color = "#ff6040"; d1El.style.fontSize = "80px";
      } else if (finalD2 > finalD1) {
        d2El.style.color = "#ff6040"; d2El.style.fontSize = "80px";
      }
      resultEl.textContent = (G.first||"") + " 先手！" + (G.compensation||"");
      // 2 秒后进入战斗
      setTimeout(async function() {
        await renderBattle();
      }, 2000);
    }
  }
  tick();
}

// ===== Battle =====
function findBattleGeneral(p, r, c) {
  if (!p || !p.generals) return null;
  return p.generals.find(function(g) { return g.row === r && g.col === c && g.alive; });
}

function currentBattleTeams() {
  var r = G;
  if (!r || !r.current_team) return {current: r.p1, enemy: r.p2};
  return r.current_team === "p1"
    ? {current: r.p1, enemy: r.p2}
    : {current: r.p2, enemy: r.p1};
}

async function renderBattle() {
  try {
  var r = G || await call("/state");
  showScreen("battle");

  document.getElementById("bturn").textContent =
    "第" + (r.turn||1) + "回合 — " + (r.current_player||"");
  document.getElementById("m1name").textContent = (r.p1 ? r.p1.name : "玩家1");
  document.getElementById("m2name").textContent = (r.p2 ? r.p2.name : "玩家2");
  document.getElementById("m1text").textContent = (r.p1 ? r.p1.morale : 0) + "/" + (r.p1 ? r.p1.maxMorale : 12);
  document.getElementById("m2text").textContent = (r.p2 ? r.p2.morale : 0) + "/" + (r.p2 ? r.p2.maxMorale : 12);
  document.getElementById("m1fill").style.width = (r.p1 && r.p1.maxMorale ? (r.p1.morale/r.p1.maxMorale*100) : 0) + "%";
  document.getElementById("m2fill").style.width = (r.p2 && r.p2.maxMorale ? (r.p2.morale/r.p2.maxMorale*100) : 0) + "%";

  // 固定布局：P1 在上方 (bside1)，P2 在下方 (bside2)
  // 渲染到独立网格容器（不覆盖面板头部）
  var p1IsAlly = (r.current_team === "p1");
  renderBattleGrid("bside1-grid", r.p1, p1IsAlly);
  renderBattleGrid("bside2-grid", r.p2, !p1IsAlly);

  // 当前行动方高亮
  var b1 = document.getElementById("bside1");
  var b2 = document.getElementById("bside2");
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
  document.getElementById("battle-status").textContent = r.event || "👆 点击己方武将，选择本回合动作";
  updateBattlePhaseUI();
  } catch(e) {
    var el = document.getElementById("battle-status");
    if (el) el.textContent = "渲染错误: " + e.message;
    console.error("renderBattle error:", e);
  }
}

function renderBattleGrid(elemId, p, isAlly) {
  var grid = Array.from({length:3}, function() { return Array(4).fill(null); });
  (p && p.generals ? p.generals : []).forEach(function(g) { if (g.row >= 0 && g.alive) grid[g.row][g.col] = g; });
  var cells = "";
  for (var r = 0; r < 3; r++) {
    for (var c = 0; c < 4; c++) {
      var g = grid[r][c];
      if (g) {
        var hpPct = g.maxHp > 0 ? (g.hp/g.maxHp*100) : 0;
        var hpClass = hpPct > 60 ? "" : (hpPct > 30 ? "warn" : "danger");
        var imgSrc = g.image ? "/generals/" + g.image : "";
        var selected = isAlly && selectedAttacker && selectedAttacker.general.id === g.id;
        // 已行动武将仍可点击选中，但攻击/技能按钮会被锁定
        var hasActed = isAlly && (g._hasAttacked || g._hasUsedSkill);
        var clickable = isAlly || battlePhase === "target";
        var clickHandler = isAlly ? "onBattleAllyCell(" + r + "," + c + ")" : "onBattleEnemyCell(" + r + "," + c + ")";
        var attrs = g.attributes || [];

        // Build attribute CSS classes
        var attrParts = [];
        if (attrs.indexOf("防栅") >= 0) {
          if (g._fenceBroken || g.hp < g.maxHp) { attrParts.push("fence-broken"); }
          else { attrParts.push("fence"); }
        }
        if (attrs.indexOf("连环") >= 0) attrParts.push("chain");
        if (attrs.indexOf("勇猛") >= 0 && g.hp <= g.maxHp/2) attrParts.push("bravery-active");
        if (attrs.indexOf("魅力") >= 0) attrParts.push("charisma");
        if (attrs.indexOf("募兵") >= 0 && g.hp < g.maxHp) attrParts.push("recruit");
        if (attrs.indexOf("复活") >= 0) attrParts.push(g._reviveUsed ? "revive-used" : "revive");
        if (attrs.indexOf("伏兵") >= 0) {
          if (g._ambushTriggered) { attrParts.push("ambush-triggered"); }
          else if (g._ambushHidden) { attrParts.push("ambush-hidden"); }
          else { attrParts.push("ambush-revealed"); }
        }
        // 本回合已行动过的武将（仍可点击，但按钮会锁定）
        if (hasActed) { attrParts.push("acted"); }
        if (!g.alive) attrParts.push("dead");
        var attrClass = attrParts.length ? " " + attrParts.join(" ") : "";

        // Use data-eff-force/data-eff-intel for real-time stats (with buffs/debuffs)
        var effForce = g.effective_force !== undefined ? g.effective_force : (g.force||0);
        var effIntel = g.effective_intelligence !== undefined ? g.effective_intelligence : (g.intelligence||0);

        cells += '<div class="bcell' + (selected?' selected':'') + (clickable?'':' locked') + attrClass + '"' +
          ' data-name="' + g.name + '" data-id="' + g.id + '" data-row="' + r + '" data-col="' + c + '"' +
          ' data-force="' + effForce + '" data-intel="' + effIntel + '"' +
          ' data-skill="' + (g.skill||'') + '" data-skill-desc="' + (g.skill_desc||'') + '" data-attrs="' + (attrs.join(',')) + '"' +
          ' data-tooltip="<b>' + g.name + '</b> 武' + effForce + ' 智' + effIntel + ' HP ' + g.hp + '/' + g.maxHp + '<br>技能：' + (g.skill||'无') + '<br>' + (g.skill_desc||'') + '<br>属性：' + (attrs.join(' · ')||'无属性') + '"' +
          ' onclick="' + (clickable?clickHandler:'') + '">' +
          (imgSrc ? '<img src="' + imgSrc + '">' : '') +
          '<div class="bcell-tip"><img src="' + (imgSrc||'') + '"><div class="tip-name">' + g.name + '</div><div class="tip-stat">武' + effForce + ' 智' + effIntel + ' | ' + (g.skill||'无') + '</div><div class="tip-attr">' + (attrs.join(' · ')||'无属性') + '</div></div>' +
          '<div class="cname">' + (g.alive?g.name:'阵亡') + '</div>' +
          '<div class="chp">' + (g.alive?g.hp+'/'+g.maxHp:'--') + '</div>' +
          '<div class="hpbar"><div class="hpf ' + hpClass + '" style="width:' + (g.alive?hpPct:0) + '%"></div></div>' +
        '</div>';
      } else {
        cells += '<div class="bcell empty" style="font-size:9px;color:#3a2e1c">—</div>';
      }
    }
  }
  document.getElementById(elemId).innerHTML = cells;
}

function updateBattlePhaseUI() {
  var phTag = battlePhase === "target" ? "ph-target" : (selectedAttacker ? "ph-attack" : "ph-skill");
  var phText = battlePhase === "target" ? "🎯 选择普攻目标" : (selectedAttacker ? '✅ 已选：' + selectedAttacker.general.name + ' — 点击下方按钮' : "🔍 点击武将选择动作");
  document.getElementById("bphase").className = "phase-tag " + phTag;
  document.getElementById("bphase").textContent = phText;

  var attackBtn = document.getElementById("bact-attack");
  var skillBtn = document.getElementById("bact-skill");
  var skipBtn = document.getElementById("bact-skip");
  var canAct = !!selectedAttacker && battlePhase !== "target";
  var selected = selectedAttacker ? selectedAttacker.general : null;
  var teams = currentBattleTeams();
  var morale = teams.current ? (teams.current.morale || 0) : 0;

  // 检查选中武将是否已行动
  var hasAttacked = selected && selected._hasAttacked;
  var hasUsedSkill = selected && selected._hasUsedSkill;
  var canSkill = canAct && selected && selected.skill && !selected.cooldown && !hasUsedSkill && morale >= 2;
  var canAttack = canAct && !hasAttacked;

  // 始终显示按钮，根据状态禁用
  attackBtn.style.display = canAct ? "" : "none";
  skillBtn.style.display = canAct ? "" : "none";

  if (canAct) {
    skillBtn.style.opacity = canSkill ? "1" : ".4";
    skillBtn.style.pointerEvents = canSkill ? "auto" : "none";
    attackBtn.style.opacity = canAttack ? "1" : ".4";
    attackBtn.style.pointerEvents = canAttack ? "auto" : "none";

    if (hasUsedSkill && selected.skill) {
      skillBtn.setAttribute("data-tooltip", selected.skill + " — 本回合已使用过技能");
    } else if (!canSkill && selected.skill) {
      if (selected.cooldown) {
        skillBtn.setAttribute("data-tooltip", selected.skill + " 冷却中（剩余 " + selected.cooldown + " 回合）");
      } else if (morale < 2) {
        skillBtn.setAttribute("data-tooltip", "士气不足！需要消耗士气才能使用技能");
      }
    } else if (canSkill && selected.skill) {
      skillBtn.setAttribute("data-tooltip", selected.skill + " — " + (selected.skill_desc||""));
    }
    if (hasAttacked) {
      attackBtn.setAttribute("data-tooltip", selected.name + " 本回合已普攻过");
    } else if (canAttack && selected) {
      attackBtn.setAttribute("data-tooltip", selected.name + " 普攻 — 武力 " + (selected.force||0));
    }
  }

  skipBtn.textContent = battlePhase === "target" ? "取消普攻" : "⏭ 跳过";
}

async function onBattleAllyCell(r, c) {
  try {
    if (!G) { document.getElementById("battle-status").textContent = "游戏状态为空，请刷新页面"; return; }
    // 从双方面板查找武将（P1=bside1 始终在上半区）
    var g = findBattleGeneral(G.p1, r, c) || findBattleGeneral(G.p2, r, c);
    if (!g) { document.getElementById("battle-status").textContent = "未找到该位置武将"; return; }
    selectedAttacker = {general: g, row: r, col: c};
    battlePhase = "action";
    await renderBattle();
  } catch(e) {
    document.getElementById("battle-status").textContent = "点击错误: " + e.message;
    console.error(e);
  }
}

async function onBattleEnemyCell(r, c) {
  if (battlePhase !== "target" || !selectedAttacker) return;
  var target = findBattleGeneral(G.p2, r, c) || findBattleGeneral(G.p1, r, c);
  if (!target) return;

  // P1=bside1, P2=bside2: 根据目标所在阵营确定格子位置
  var aIsP1 = (selectedAttacker.general.id === (findBattleGeneral(G.p1, selectedAttacker.row, selectedAttacker.col)||{}).id);
  var tIsP1 = (target.id === (findBattleGeneral(G.p1, r, c)||{}).id);
  var aCell = document.querySelector((aIsP1 ? '#bside1-grid' : '#bside2-grid') + ' .bcell[data-row="' + selectedAttacker.row + '"][data-col="' + selectedAttacker.col + '"]');
  var tCell = document.querySelector((tIsP1 ? '#bside1-grid' : '#bside2-grid') + ' .bcell[data-row="' + r + '"][data-col="' + c + '"]');

  // 攻速判定：弹窗让玩家选择奇偶
  var guess = null;
  if (selectedAttacker.general._hasSpeedJudgment || selectedAttacker.general._hasSpeedRequired) {
    guess = await askOddEven();
    if (!guess) {
      // 玩家取消了
      battlePhase = "action";
      await renderBattle();
      return;
    }
  }

  if (aCell && tCell) animAttack(aCell, tCell, Math.max(1, (selectedAttacker.general.force || 5) - (target.force || 3)));
  await new Promise(function(resolve) { setTimeout(resolve, 250); });
  await call("/battle/attack", {attacker_id: selectedAttacker.general.id, target_id: target.id, guess: guess});
  selectedAttacker = null;
  battlePhase = "select";
  if (G.phase === "over") { showGameOver(); return; }
  await renderBattle();
}

// 奇偶选择弹窗
function askOddEven() {
  return new Promise(function(resolve) {
    var overlay = document.createElement("div");
    overlay.style.cssText = "position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.8);z-index:400;display:flex;align-items:center;justify-content:center";
    overlay.innerHTML = '<div style="background:linear-gradient(180deg,#1a1410,#0b0906);border:2px solid var(--gold);border-radius:14px;padding:28px 36px;text-align:center;color:var(--text)">' +
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

async function chooseAttack() {
  if (!selectedAttacker) return;
  battlePhase = "target";
  await renderBattle();
}

async function useSkill() {
  if (!selectedAttacker) return;
  var skillName = selectedAttacker.general.skill || "技能";
  var skillType = detectSkillType(skillName);

  // 技能施放者特效
  var cellEl = document.querySelector('#bside1-grid .bcell[data-row="' + selectedAttacker.row + '"][data-col="' + selectedAttacker.col + '"]');
  if (!cellEl) {
    cellEl = document.querySelector('#bside2-grid .bcell[data-row="' + selectedAttacker.row + '"][data-col="' + selectedAttacker.col + '"]');
  }
  if (cellEl) animSkill(cellEl, skillName, "", skillType);

  // 记录敌方战前 HP
  var enemyBefore = {};
  var enemyCells = document.querySelectorAll("#bside2-grid .bcell");
  enemyCells.forEach(function(ec) {
    var n = ec.getAttribute("data-name");
    var hpText = ec.querySelector(".chp");
    if (n && hpText) {
      var parts = hpText.textContent.split("/");
      enemyBefore[n] = parseInt(parts[0]) || 0;
    }
  });
  // Also check P1 enemies (if caster is P2)
  var allyCells = document.querySelectorAll("#bside1-grid .bcell");
  allyCells.forEach(function(ec) {
    var n = ec.getAttribute("data-name");
    var hpText = ec.querySelector(".chp");
    if (n && hpText && !(n in enemyBefore)) {
      var parts = hpText.textContent.split("/");
      enemyBefore[n] = parseInt(parts[0]) || 0;
    }
  });

  await call("/battle/skill", {general_id: selectedAttacker.general.id});

  // 技能执行后，对受损目标显示特效
  setTimeout(function() {
    // 查找 HP 变化的目标
    ["#bside2-grid .bcell", "#bside1-grid .bcell"].forEach(function(sel) {
      document.querySelectorAll(sel).forEach(function(ec) {
        var n = ec.getAttribute("data-name");
        if (n && enemyBefore[n] !== undefined) {
          var hpEl = ec.querySelector(".chp");
          if (hpEl) {
            var parts = hpEl.textContent.split("/");
            var afterHp = parseInt(parts[0]) || 0;
            var dmg = enemyBefore[n] - afterHp;
            if (dmg > 0) {
              // 对受损目标显示伤害数字和特效
              var center = getCellCenter(ec);
              if (skillType === "lightning") {
                FX.lightningStrike(center.x, center.y);
              } else if (skillType === "fire") {
                FX.fireBurst(center.x, center.y);
              }
              spawnFloatNum(ec, dmg, "damage");
              // 目标闪白
              ec.classList.add("impact-flash");
              setTimeout(function() { ec.classList.remove("impact-flash"); }, 400);
            } else if (afterHp > enemyBefore[n]) {
              // 治疗
              spawnFloatNum(ec, afterHp - enemyBefore[n], "heal");
            }
          }
        }
      });
    });
  }, 100);

  selectedAttacker = null;
  battlePhase = "select";
  if (G.phase === "over") { showGameOver(); return; }
  await renderBattle();
}

async function skipPhase() {
  if (battlePhase === "target") {
    battlePhase = "action";
    await renderBattle();
    return;
  }
  selectedAttacker = null;
  battlePhase = "select";
  await call("/battle/skip");
  if (G.phase === "over") { showGameOver(); return; }
  await renderBattle();
}

// ===== Game Over =====
function showGameOver() {
  showScreen("over");
  document.getElementById("over-winner").textContent = G.winner + " 获得胜利！";
  document.getElementById("over-stats").textContent = "总回合数: " + G.turn;
}

// ===== Gallery =====
function initGallery() {
  fetch("/api/generals").then(function(r) { return r.json(); }).then(function(r) {
    var all = r.pool || [];
    var campFilter = (document.querySelector("#dm-camp .opt.active")||{}).dataset || {};
    campFilter = campFilter.val || "";
    var attrFilter = (document.querySelector("#dm-attr .opt.active")||{}).dataset || {};
    attrFilter = attrFilter.val || "";
    galleryFiltered = all.filter(function(g) {
      if (campFilter && g.camp !== campFilter) return false;
      if (attrFilter && !(g.attributes||[]).includes(attrFilter)) return false;
      return true;
    });
    if (galleryIdx >= galleryFiltered.length) galleryIdx = 0;
    renderGallery();
    if (!document.getElementById("dm-camp").innerHTML) {
      var camps = ["全部"].concat(Array.from(new Set(all.map(function(g) { return g.camp; }))));
      var attrs = ["全部"].concat(Array.from(new Set(all.flatMap(function(g) { return g.attributes||[]; }))));
      document.getElementById("dm-camp").innerHTML = camps.map(function(c) {
        return '<div class="opt' + (c==="全部"?" active":"") + '" data-val="' + (c==="全部"?"":c) + '" onclick="filterGallery(\'camp\',\'' + c + '\',event)">' + c + '</div>';
      }).join("");
      document.getElementById("dm-attr").innerHTML = attrs.map(function(a) {
        return '<div class="opt' + (a==="全部"?" active":"") + '" data-val="' + (a==="全部"?"":a) + '" onclick="filterGallery(\'attr\',\'' + a + '\',event)">' + a + '</div>';
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
  var bio = (g.bio||"").slice(0, 200);
  var years = g.years||"";
  var cou = g.courtesy||"";
  var html = '<div class="gallery-card">' +
    (imgSrc ? '<img src="' + imgSrc + '" alt="' + g.name + '">' : '<div style="height:300px;display:flex;align-items:center;justify-content:center;font-size:60px;color:var(--shu)">' + g.name[0] + '</div>') +
    '<div class="gn">' + g.name + '</div>' +
    '</div>' +
    '<div class="gallery-bio">' + years + ' · ' + cou + '<br><br>' + bio + '</div>' +
    '<div class="gallery-nav">' +
      '<div class="nav-btn" onclick="galleryIdx=(galleryIdx-1+galleryFiltered.length)%galleryFiltered.length;renderGallery()">◀</div>' +
      '<div style="font-size:12px;color:var(--muted);line-height:36px">' + (galleryIdx+1) + '/' + galleryFiltered.length + '</div>' +
      '<div class="nav-btn" onclick="galleryIdx=(galleryIdx+1)%galleryFiltered.length;renderGallery()">▶</div>' +
    '</div>';
  document.getElementById("gallery-content").innerHTML = html;
}

function toggleDropdown(id) {
  document.getElementById(id).classList.toggle("open");
}

// Close dropdowns on outside click
document.addEventListener("click", function(e) {
  if (!e.target.closest(".dropdown")) {
    document.querySelectorAll(".dropdown").forEach(function(d) { d.classList.remove("open"); });
  }
});

// ===== Quit to menu =====
function quitToMenu() {
  G = null; selectedGenerals = []; selectedAttacker = null;
  battlePhase = "skill";
  showScreen("menu");
}

// ===== FX: Canvas-based combat effects (Phase 4 upgrade) =====
(function(){
  var c = document.getElementById("fx-canvas");
  var ctx = c.getContext("2d");
  var particles = [];
  var ambientParticles = [];
  var W, H;

  function resize() { W = c.width = window.innerWidth; H = c.height = window.innerHeight; }
  window.addEventListener("resize", resize);
  resize();

  // Init ambient floating embers for battle atmosphere
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
        var spd = (1 + Math.random() * speed);
        particles.push({type:"burst", x:x, y:y, vx:Math.cos(angle)*spd, vy:Math.sin(angle)*spd, life:1, color:color||"#ffb840", size:2+Math.random()*4});
      }
    },

    // Fire burst — orange/red embers with smoke trail (rising)
    fireBurst: function(x, y) {
      for (var i = 0; i < 20; i++) {
        var angle = (Math.random() - 0.5) * Math.PI;
        var spd = 2 + Math.random() * 5;
        particles.push({type:"fire", x:x, y:y, vx:Math.cos(angle)*spd, vy:-(1+Math.random()*3)+Math.sin(angle)*spd*.3, life:1, color:Math.random()>0.5?"#ff6020":"#ffb830", size:2+Math.random()*5});
      }
      // Smoke trail
      for (var j = 0; j < 6; j++) {
        particles.push({type:"smoke", x:x+(Math.random()-0.5)*20, y:y+(Math.random()-0.5)*10, vx:(Math.random()-0.5)*0.5, vy:-0.5-Math.random(), life:1, color:"#666", size:8+Math.random()*8, alpha:.3});
      }
    },

    // Lightning strike — jagged bolt + flash
    lightningStrike: function(x, y) {
      // White flash
      ctx.save(); ctx.globalAlpha = 0.6; ctx.fillStyle = "#fff"; ctx.fillRect(0,0,W,H); ctx.restore();
      // Bolt particles
      for (var i = 0; i < 25; i++) {
        particles.push({type:"bolt", x:x+(Math.random()-0.5)*60, y:y+(Math.random()-0.5)*80, vx:(Math.random()-0.5)*8, vy:(Math.random()-0.5)*8, life:.4+Math.random()*.3, color:"#ffe840", size:1.5+Math.random()*3});
      }
      // Screen shake
      FX.screenShake();
      // Afterglow
      for (var j = 0; j < 10; j++) {
        particles.push({type:"glow", x:x+(Math.random()-0.5)*40, y:y+(Math.random()-0.5)*40, vx:0, vy:0, life:.6+Math.random()*.4, color:"#ffffc0", size:6+Math.random()*8, alpha:.5});
      }
    },

    // Slash trail — crescent arc for physical attacks
    slashTrail: function(x1, y1, x2, y2) {
      var midX = (x1 + x2) / 2, midY = (y1 + y2) / 2;
      var angle = Math.atan2(y2 - y1, x2 - x1);
      for (var i = 0; i < 18; i++) {
        var t = i / 17;
        var sx = x1 + (x2 - x1) * t + (Math.random() - 0.5) * 20;
        var sy = y1 + (y2 - y1) * t + (Math.random() - 0.5) * 20;
        particles.push({type:"slash", x:sx, y:sy, vx:Math.cos(angle)*2, vy:Math.sin(angle)*2, life:.3+Math.random()*.3, color:"#e0e0f0", size:2+Math.random()*3});
      }
      // Impact spark
      FX.burst(x2, y2, "#ffe0c0", 8, 3);
    },

    // Heal sparkles — green upward sparkles
    healSparkles: function(x, y) {
      for (var i = 0; i < 15; i++) {
        var angle = (Math.random() - 0.5) * Math.PI;
        particles.push({type:"heal", x:x+(Math.random()-0.5)*30, y:y+(Math.random()-0.5)*20, vx:Math.cos(angle)*1.5, vy:-(2+Math.random()*3), life:1, color:"#40e040", size:2+Math.random()*3});
      }
    },

    // Debuff miasma — purple downward particles
    debuffMiasma: function(x, y) {
      for (var i = 0; i < 18; i++) {
        particles.push({type:"miasma", x:x+(Math.random()-0.5)*40, y:y, vx:(Math.random()-0.5)*2, vy:0.5+Math.random()*2, life:1, color:"#c080ff", size:3+Math.random()*5});
      }
    },

    // Morale wave — golden expanding ring
    moraleWave: function(x, y) {
      for (var i = 0; i < 12; i++) {
        var angle = Math.random() * Math.PI * 2;
        var spd = 3 + Math.random() * 3;
        particles.push({type:"morale", x:x, y:y, vx:Math.cos(angle)*spd, vy:Math.sin(angle)*spd, life:.8, color:"#ffb840", size:3+Math.random()*3});
      }
    },

    // Death shatter — dark particles dissolve
    deathShatter: function(x, y) {
      for (var i = 0; i < 20; i++) {
        var angle = Math.random() * Math.PI * 2;
        var spd = 2 + Math.random() * 5;
        particles.push({type:"death", x:x, y:y, vx:Math.cos(angle)*spd, vy:Math.sin(angle)*spd - 2, life:1, color:"#333", size:3+Math.random()*6});
      }
      for (var j = 0; j < 8; j++) {
        particles.push({type:"death", x:x, y:y, vx:(Math.random()-0.5)*3, vy:-(1+Math.random()*4), life:1.2, color:"#8a2020", size:2+Math.random()*4});
      }
    },

    // Formation swap — teleport exchange
    formationSwap: function(x1, y1, x2, y2) {
      FX.burst(x1, y1, "#c0c0ff", 8, 3);
      FX.burst(x2, y2, "#c0c0ff", 8, 3);
    },

    // Draw weapon arc on canvas (called directly, not stored as particle)
    drawWeaponArc: function(x1, y1, x2, y2, color) {
      color = color || "rgba(255,255,240,.7)";
      ctx.save();
      ctx.strokeStyle = color;
      ctx.lineWidth = 3;
      ctx.shadowColor = color;
      ctx.shadowBlur = 12;
      ctx.beginPath();
      var cx = (x1 + x2) / 2, cy = Math.min(y1, y2) - 40;
      ctx.moveTo(x1, y1);
      ctx.quadraticCurveTo(cx, cy, x2, y2);
      ctx.stroke();
      // Twin arc for double slash feel
      ctx.globalAlpha = 0.4;
      ctx.strokeStyle = "#fff";
      ctx.lineWidth = 1;
      ctx.moveTo(x1 + 3, y1 + 3);
      ctx.quadraticCurveTo(cx + 3, cy + 3, x2 + 3, y2 + 3);
      ctx.stroke();
      ctx.restore();
      // Fade out
      setTimeout(function() { /* Arc is single-frame */ }, 300);
    },

    screenShake: function() {
      var app = document.getElementById("app");
      if (!app) return;
      app.classList.add("shaking");
      setTimeout(function() { app.classList.remove("shaking"); }, 500);
    },

    // Trigger correct effect based on skill name
    skillEffect: function(el, skillName, skillType) {
      var center = getCellCenter(el);
      var name = (skillName||"").toLowerCase();
      skillType = skillType || detectSkillType(skillName);

      switch(skillType) {
        case "fire": FX.fireBurst(center.x, center.y); break;
        case "lightning": FX.lightningStrike(center.x, center.y); break;
        case "heal": FX.healSparkles(center.x, center.y); break;
        case "debuff": FX.debuffMiasma(center.x, center.y); break;
        case "morale": FX.moraleWave(center.x, center.y); break;
        case "death": FX.deathShatter(center.x, center.y); break;
        default: FX.burst(center.x, center.y, skillType==="damage"?"#ff6040":"#ffb840", 18, 5);
      }
      spawnSkillLabel(el, skillName, skillType);
    }
  };

  // Detect skill type from name
  function detectSkillType(name) {
    var n = name||"";
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

    // Draw ambient floating embers
    for (var a = 0; a < ambientParticles.length; a++) {
      var ap = ambientParticles[a];
      ap.x += ap.vx; ap.y += ap.vy;
      if (ap.y < -10) { ap.y = H + 10; ap.x = Math.random() * W; }
      if (ap.x < -10 || ap.x > W + 10) { ap.x = Math.random() * W; }
      ctx.globalAlpha = 0.15 + ap.life * 0.2;
      ctx.fillStyle = ap.color;
      ctx.beginPath(); ctx.arc(ap.x, ap.y, ap.size, 0, Math.PI*2); ctx.fill();
    }

    // Draw active particles
    for (var i = particles.length - 1; i >= 0; i--) {
      var p = particles[i];
      p.x += p.vx; p.y += p.vy; p.life -= 0.025;
      if (p.type === "fire" || p.type === "smoke") { p.vx *= 0.95; p.vy *= 0.95; }
      else if (p.type === "miasma") { p.vx *= 0.98; p.vy *= 0.98; }
      else { p.vx *= 0.96; p.vy *= 0.96; }

      ctx.globalAlpha = Math.max(0, p.life * (p.alpha || 1));
      ctx.fillStyle = p.color;
      if (p.type === "smoke") {
        ctx.beginPath(); ctx.arc(p.x, p.y, p.size * Math.max(0.1, p.life), 0, Math.PI*2); ctx.fill();
      } else if (p.type === "glow") {
        var grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.size);
        grad.addColorStop(0, p.color); grad.addColorStop(1, "transparent");
        ctx.fillStyle = grad; ctx.beginPath(); ctx.arc(p.x, p.y, p.size, 0, Math.PI*2); ctx.fill();
      } else {
        ctx.beginPath(); ctx.arc(p.x, p.y, p.size * Math.max(0.1, p.life), 0, Math.PI*2); ctx.fill();
      }
      if (p.life <= 0) particles.splice(i, 1);
    }
    ctx.globalAlpha = 1;
    requestAnimationFrame(loop);
  }
  loop();
})();

// ===== Combat Animations =====
function getCellCenter(el) {
  var r = el.getBoundingClientRect();
  return {x: r.left + r.width/2, y: r.top + r.height/2};
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

function spawnSkillLabel(el, text, cssClass) {
  var d = document.createElement("div");
  d.className = "skill-burst";
  d.textContent = text;
  el.appendChild(d);
  setTimeout(function() { d.remove(); }, 1600);
}

function animAttack(aEl, tEl, dmg) {
  var aCenter = getCellCenter(aEl);
  var tCenter = getCellCenter(tEl);

  // Draw weapon arc
  FX.drawWeaponArc(aCenter.x, aCenter.y, tCenter.x, tCenter.y, "rgba(255,255,240,.7)");

  // Target impact flash
  tEl.classList.add("impact-flash");
  setTimeout(function() { tEl.classList.remove("impact-flash"); }, 400);

  if (window.gsap) {
    gsap.timeline()
      .to(aEl, {duration:0.15, x: tCenter.x - aCenter.x, y: tCenter.y - aCenter.y, scale:1.15, ease:"power2.in"})
      .call(function(){ FX.slashTrail(aCenter.x, aCenter.y, tCenter.x, tCenter.y); FX.screenShake(); spawnFloatNum(tEl, dmg||3, "damage"); })
      .to(aEl, {duration:0.2, x:0, y:0, scale:1, ease:"power2.out"});
  } else {
    aEl.classList.add("attacking");
    setTimeout(function() { aEl.classList.remove("attacking"); }, 350);
    FX.slashTrail(aCenter.x, aCenter.y, tCenter.x, tCenter.y);
    FX.screenShake();
    spawnFloatNum(tEl, dmg||3, "damage");
  }
}

function animSkill(el, name, detail, kind) {
  var center = getCellCenter(el);

  // Use skill-type-specific effect
  FX.skillEffect(el, name, kind);

  var colorMap = {buff:"#ffb840", debuff:"#c080ff", heal:"#40e040", damage:"#ff6040", lightning:"#ffe840", fire:"#ff6020"};
  var color = colorMap[kind] || "#ffb840";

  if (window.gsap) {
    gsap.timeline()
      .to(el, {duration:0.1, scale:1.08, boxShadow:"0 0 30px " + color})
      .to(el, {duration:0.25, scale:1, boxShadow:"none"});
  } else {
    el.classList.add("flash-pulse");
    setTimeout(function() { el.classList.remove("flash-pulse"); }, 300);
  }
}

// ===== Init =====
showScreen("menu");
