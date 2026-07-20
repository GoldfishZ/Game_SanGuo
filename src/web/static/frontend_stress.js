/*
 * 真实浏览器前端自走测试。
 * 在同一个页面内串行运行完整 Web API 流程，并让每一局都经过真实 DOM 渲染函数。
 * 用法：await FrontendStress.run({ games: 10000, batchSize: 100, seed: 20260717 })
 */
(function() {
  "use strict";

  var running = false;
  var cancelled = false;

  function rngFromSeed(seed) {
    var value = seed >>> 0;
    return function() {
      value += 0x6D2B79F5;
      var t = value;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function pick(array, random) {
    return array[Math.floor(random() * array.length)];
  }

  async function post(path, body) {
    var response = await fetch("/api" + path, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(body || {})
    });
    if (!response.ok) throw new Error(path + " HTTP " + response.status);
    var state = await response.json();
    if (state && state.error) throw new Error(path + " " + state.error);
    return state;
  }

  function assertState(state) {
    var phases = ["select_p1", "select_p2", "formation_p1", "formation_p2", "dice", "battle", "over"];
    if (!state || phases.indexOf(state.phase) < 0) throw new Error("非法阶段: " + (state && state.phase));
    ["p1", "p2"].forEach(function(key) {
      var team = state[key];
      if (!team) return;
      if (team.morale < 0 || team.morale > team.maxMorale) throw new Error(key + " 士气越界");
      var occupied = {};
      (team.generals || []).forEach(function(general) {
        if (general.hp < 0 || general.hp > general.maxHp) throw new Error(general.name + " 生命越界");
        if (general.alive !== (general.hp > 0)) throw new Error(general.name + " 存活状态不一致");
        if (general.row >= 0) {
          var cell = general.row + ":" + general.col;
          if (occupied[cell]) throw new Error(key + " 阵位重叠 " + cell);
          occupied[cell] = true;
        }
      });
    });
  }

  function chooseOne(pool, random) {
    if (!pool || !pool.length) throw new Error("选将池为空");
    return pick(pool, random);
  }

  function formation(generals, random) {
    var free = [];
    // 优先放在中列，确保“前方2x2”等方向技能也存在合法区域。
    for (var col = 0; col < 4; col++) free.push([1, col]);
    for (var row of [0, 2]) for (var c = 0; c < 4; c++) free.push([row, c]);
    return generals.map(function(general) {
      var index = Math.floor(random() * free.length);
      var cell = free.splice(index, 1)[0];
      return {general_id:general.id, row:cell[0], col:cell[1]};
    });
  }

  function alive(team) {
    return ((team && team.generals) || []).filter(function(general) { return general.alive && general.row >= 0; });
  }

  function frontTargets(team) {
    var byColumn = {};
    alive(team).forEach(function(general) {
      var prior = byColumn[general.col];
      if (!prior || general.row < prior.row) byColumn[general.col] = general;
    });
    return Object.keys(byColumn).map(function(key) { return byColumn[key]; })
      .filter(function(general) { return !general._ambushHidden; });
  }

  function areaAt(general, height, width) {
    return {
      area_row:Math.max(0, Math.min(3 - height, general.row)),
      area_col:Math.max(0, Math.min(4 - width, general.col))
    };
  }

  function skillPayload(general, ally, enemy, random) {
    var payload = {general_id:general.id};
    var enemyTarget = alive(enemy)[0];
    var id = general.skill_id || "";
    if (id === "meteor_rite") {
      payload.skill_row = enemyTarget ? enemyTarget.row : 0;
    } else if (["stone_sentinel_maze", "spear_wheel_tactics", "thunder_strike", "taunt", "discord_strategy", "tooth_for_tooth"].indexOf(id) >= 0) {
      Object.assign(payload, areaAt(enemyTarget || {row:0,col:0}, 2, 2));
    } else if (id === "small_chain_plot") {
      Object.assign(payload, areaAt(enemyTarget || {row:0,col:0}, 1, 2));
      payload.area_orientation = "horizontal";
    } else if (["momentary_order", "meticulous_offense"].indexOf(id) >= 0) {
      Object.assign(payload, areaAt(general, 2, 2));
    } else if (id === "jiangdong_beauty") {
      Object.assign(payload, areaAt(general, 3, 3));
    } else if (general._targetType === "AREA_ENEMY") {
      Object.assign(payload, areaAt(enemyTarget || {row:0,col:0}, 2, 2));
    } else if (general._targetType === "AREA_ALLY") {
      Object.assign(payload, areaAt(general, 2, 2));
    }
    if (id === "discord_strategy") payload.skill_timing = random() < .5 ? "ally_attack" : "enemy_attack";
    if (id === "tooth_for_tooth") payload.skill_mode = "wide";
    if (id === "thunder_strike") payload.guess = random() < .5 ? "奇" : "偶";
    return payload;
  }

  function setAndRender(state, renderer) {
    window.G = state;
    if (typeof renderer === "function") renderer();
    var status = document.getElementById("battle-status");
    if (status && /渲染错误/.test(status.textContent)) throw new Error(status.textContent);
  }

  function cleanupTransientDom() {
    document.querySelectorAll(".speed-judgment-overlay,.skill-area-overlay,.skill-option-overlay,.general-closeup-overlay,.float-num,.skill-burst,#stress-status").forEach(function(node) {
      if (node.id !== "stress-status") node.remove();
    });
    var cinematic = document.getElementById("skill-cinematic");
    if (cinematic) { cinematic.classList.remove("active"); cinematic.removeAttribute("data-camp"); cinematic.innerHTML = ""; }
    var battle = document.getElementById("scr-battle");
    if (battle) battle.classList.remove("battle-cinematic-focus");
    if (window.FX && FX.clear) FX.clear();
    window.selectedAttacker = null;
    window.battlePhase = "select";
  }

  function sampleMetrics(report) {
    var nodes = document.getElementsByTagName("*").length;
    report.dom.min = Math.min(report.dom.min, nodes);
    report.dom.max = Math.max(report.dom.max, nodes);
    report.dom.current = nodes;
    if (performance.memory) {
      var heap = performance.memory.usedJSHeapSize;
      if (report.heap.start === null) report.heap.start = heap;
      report.heap.current = heap;
      report.heap.peak = Math.max(report.heap.peak || 0, heap);
    }
    if (window.FX && FX.stats) report.fx = FX.stats();
  }

  function statusPanel(report) {
    var panel = document.getElementById("stress-status");
    if (!panel) {
      panel = document.createElement("div");
      panel.id = "stress-status";
      panel.style.cssText = "position:fixed;right:10px;bottom:10px;z-index:9999;padding:8px 11px;background:#120d08e8;border:1px solid #82663d;color:#d8c59c;font:12px/1.45 monospace;pointer-events:none";
      document.body.appendChild(panel);
    }
    panel.textContent = "前端自走 " + report.completed + "/" + report.games + " · 异常 " + (report.crashes + report.stalls);
  }

  async function nextFrame() {
    await new Promise(function(resolve) { requestAnimationFrame(function() { setTimeout(resolve, 0); }); });
  }

  async function playOne(number, config, report) {
    var random = rngFromSeed(config.seed + number * 7919);
    var state = await post("/new");
    setAndRender(state, window.renderSelection);

    var p1Choice = chooseOne(state.pool, random);
    state = await post("/select", {general_ids:[p1Choice.id]});
    setAndRender(state, window.renderSelection);
    var p2Choice = chooseOne(state.pool, random);
    state = await post("/select", {general_ids:[p2Choice.id]});
    report.generalCoverage.add(p1Choice.name); report.generalCoverage.add(p2Choice.name);
    setAndRender(state, window.renderFormation);

    state = await post("/place", {positions:formation(state.p1.generals, random)});
    setAndRender(state, window.renderFormation);
    state = await post("/place", {positions:formation(state.p2.generals, random)});
    window.G = state; showScreen("dice");
    state = await post("/dice");
    assertState(state);
    setAndRender(state, window.renderBattle);

    var actions = 0;
    while (state.phase === "battle" && state.turn <= config.maxTurns) {
      if (cancelled) throw new Error("测试被取消");
      var currentKey = state.current_team;
      var enemyKey = currentKey === "p1" ? "p2" : "p1";
      var current = alive(state[currentKey])[0];
      if (current && current.skill && current.skill !== "无" && !current.cooldown && !current._hasUsedSkill && state[currentKey].morale >= current.skill_cost) {
        var beforeUsed = current._hasUsedSkill;
        state = await post("/battle/skill", skillPayload(current, state[currentKey], state[enemyKey], random));
        actions++;
        assertState(state);
        var afterSkill = state[currentKey] && state[currentKey].generals.find(function(general) { return general.id === current.id; });
        if (state.skill_result && state.skill_result.success && afterSkill && !beforeUsed && afterSkill._hasUsedSkill) report.skillCoverage.add(current.skill);
        setAndRender(state, window.renderBattle);
      }
      if (state.phase !== "battle") break;

      currentKey = state.current_team;
      enemyKey = currentKey === "p1" ? "p2" : "p1";
      current = alive(state[currentKey])[0];
      var targets = frontTargets(state[enemyKey]);
      if (current && !current._hasAttacked && targets.length) {
        var target = pick(targets, random);
        var attack = {attacker_id:current.id, target_id:target.id};
        if (current._hasSpeedJudgment || current._hasSpeedRequired) attack.guess = random() < .5 ? "奇" : "偶";
        state = await post("/battle/attack", attack);
        actions++;
        assertState(state);
        setAndRender(state, window.renderBattle);
      }
      if (state.phase !== "battle") break;
      state = await post("/battle/skip");
      actions++;
      assertState(state);
      setAndRender(state, window.renderBattle);
    }

    report.actions += actions;
    report.maxTurn = Math.max(report.maxTurn, state.turn || 0);
    if (state.phase !== "over") return {completed:false, event:state.event, turn:state.turn};
    setAndRender(state, window.showGameOver);
    return {completed:true, winner:state.winner, turn:state.turn};
  }

  async function run(options) {
    if (running) throw new Error("前端自走测试正在运行");
    var config = Object.assign({games:10000, batchSize:100, seed:20260717, maxTurns:220}, options || {});
    if (!Number.isInteger(config.games) || config.games < 1) throw new Error("games 必须是正整数");
    running = true; cancelled = false; window.__stressMode = true;
    var started = performance.now();
    var report = {
      status:"running", games:config.games, completed:0, crashes:0, stalls:0, actions:0, maxTurn:0,
      generalCoverage:new Set(), skillCoverage:new Set(), winners:{}, samples:[], failures:[],
      heap:{start:null,current:null,peak:null}, dom:{min:Infinity,max:0,current:0}, fx:null
    };
    window.__frontendStressReport = report;
    if (window.BattleAudio) BattleAudio.sync();
    sampleMetrics(report); statusPanel(report);

    try {
      for (var number = 1; number <= config.games; number++) {
        try {
          var result = await playOne(number, config, report);
          if (result.completed) {
            report.completed++;
            report.winners[result.winner] = (report.winners[result.winner] || 0) + 1;
          } else {
            report.stalls++;
            if (report.failures.length < 20) report.failures.push({game:number, type:"stall", turn:result.turn, event:result.event});
          }
        } catch (error) {
          report.crashes++;
          if (report.failures.length < 20) report.failures.push({game:number, type:"crash", error:String(error && error.stack || error)});
          // 下一局 /new 会重置后端状态，因此单局异常不会扩大内存占用或中断覆盖测试。
        }
        report.processed = number;

        if (number % config.batchSize === 0 || number === config.games) {
          cleanupTransientDom(); sampleMetrics(report);
          var elapsed = (performance.now() - started) / 1000;
          report.samples.push({game:number, elapsed:elapsed, heap:report.heap.current, dom:report.dom.current});
          report.rate = number / Math.max(.001, elapsed);
          statusPanel(report);
          console.log("[FrontendStress]", number + "/" + config.games, "completed=" + report.completed,
            "failures=" + (report.crashes + report.stalls), "heap=" + report.heap.current, "dom=" + report.dom.current,
            "rate=" + report.rate.toFixed(2) + "/s");
          await nextFrame();
        }
        if (cancelled) break;
      }
    } finally {
      cleanupTransientDom(); sampleMetrics(report);
      report.elapsed = (performance.now() - started) / 1000;
      report.rate = (report.processed || config.games) / Math.max(.001, report.elapsed);
      report.generalCoverage = Array.from(report.generalCoverage).sort();
      report.skillCoverage = Array.from(report.skillCoverage).sort();
      report.generalCoverageCount = report.generalCoverage.length;
      report.skillCoverageCount = report.skillCoverage.length;
      report.status = cancelled ? "cancelled" : ((report.completed === config.games && !report.crashes && !report.stalls) ? "passed" : "failed");
      report.finished = true;
      window.__stressMode = false;
      running = false;
      statusPanel(report);
      console.log("[FrontendStress] DONE", report);
    }
    return report;
  }

  window.FrontendStress = {
    run:run,
    cancel:function() { cancelled = true; },
    isRunning:function() { return running; },
    report:function() { return window.__frontendStressReport || null; }
  };
})();
