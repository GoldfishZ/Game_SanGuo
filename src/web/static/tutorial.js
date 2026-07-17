/**
 * 新手教程系统
 * 首次游戏时自动触发，通过 localStorage 记录状态
 * 4 步引导：选将 → 布阵 → 技能阶段 → 普攻阶段
 */
(function() {
  var STORAGE_KEY = "sanguo_tutorial_seen";
  var overlay = null;
  var highlight = null;
  var bubble = null;
  var arrow = null;
  var currentStep = 0;
  var active = false;

  var STEPS = [
    {
      id: "select",
      title: "第一步：选择武将",
      text: "浏览武将卡牌，<b>单击</b>查看详情，<b>点击「加入选将池」</b>来招募武将。<br>费用上限为 8 费，合理搭配高费和低费武将。<br>选择完毕后点击「完成选择」。",
      target: function() { return document.getElementById("sel-cards") || document.getElementById("scr-select"); },
      screen: "select"
    },
    {
      id: "formation",
      title: "第二步：布置阵型",
      text: "点击左侧武将名选中，再点击右侧格子放置。<br>战场为<b>4排×3列</b>：玩家1最右列、玩家2最左列是前卫。<br>高武力武将适合放在前卫，智力型武将放在后卫。",
      target: function() { return document.getElementById("form-grid") || document.getElementById("scr-formation"); },
      screen: "formation"
    },
    {
      id: "skill",
      title: "第三步：技能阶段",
      text: "每回合先进入<b>技能阶段</b>。<br>点击己方武将选中，再点「使用技能」消耗士气释放。<br>技能有冷却时间，需要合理规划使用时机。",
      target: function() { return document.getElementById("bside1") || document.getElementById("bact-skill"); },
      screen: "battle"
    },
    {
      id: "attack",
      title: "第四步：普攻阶段",
      text: "技能阶段后进入<b>普攻阶段</b>。<br>选中武将点击「普攻」，再点击敌方前排目标。<br>前卫挡住后排，只能攻击最前面的敌人。<br>祝君旗开得胜！",
      target: function() { return document.getElementById("bside2") || document.getElementById("bact-attack"); },
      screen: "battle"
    }
  ];

  function createElements() {
    overlay = document.createElement("div");
    overlay.id = "tutorial-overlay";
    overlay.style.cssText =
      "position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.75);z-index:300;" +
      "display:none;transition:opacity .3s";

    highlight = document.createElement("div");
    highlight.id = "tutorial-highlight";
    highlight.style.cssText =
      "position:fixed;z-index:301;border:3px solid var(--gold-bright);border-radius:10px;" +
      "box-shadow:0 0 30px rgba(228,192,96,.5),0 0 0 9999px rgba(0,0,0,.75);" +
      "display:none;transition:all .35s cubic-bezier(.34,1.56,.64,1);pointer-events:none";

    bubble = document.createElement("div");
    bubble.id = "tutorial-bubble";
    bubble.style.cssText =
      "position:fixed;z-index:302;background:linear-gradient(180deg,#1a1410,#0b0906);" +
      "border:2px solid var(--gold);border-radius:12px;padding:20px 24px;" +
      "max-width:380px;color:var(--text);font-size:14px;line-height:1.7;" +
      "box-shadow:0 8px 40px rgba(0,0,0,.8);display:none";

    document.body.appendChild(overlay);
    document.body.appendChild(highlight);
    document.body.appendChild(bubble);
  }

  function positionHighlight(target) {
    if (!target) return;
    var r = target.getBoundingClientRect();
    var pad = 8;
    highlight.style.left = (r.left - pad) + "px";
    highlight.style.top = (r.top - pad) + "px";
    highlight.style.width = (r.width + pad * 2) + "px";
    highlight.style.height = (r.height + pad * 2) + "px";
    highlight.style.display = "block";
  }

  function positionBubble(target) {
    if (!target) return;
    var r = target.getBoundingClientRect();
    var bw = Math.min(380, window.innerWidth - 40);

    // Place below target if room, otherwise above
    var top = r.bottom + 20;
    var left = Math.max(20, r.left + r.width / 2 - bw / 2);
    if (top + 200 > window.innerHeight) {
      top = r.top - 220;
    }
    if (left + bw > window.innerWidth - 20) {
      left = window.innerWidth - bw - 20;
    }

    bubble.style.left = left + "px";
    bubble.style.top = top + "px";
    bubble.style.maxWidth = bw + "px";

    // Update arrow direction
    if (r.bottom + 20 <= window.innerHeight - 200) {
      bubble.style.borderTopLeftRadius = "4px";
    }
  }

  function renderStep(step) {
    var target = typeof step.target === "function" ? step.target() : null;
    positionHighlight(target);
    positionBubble(target);

    bubble.innerHTML =
      '<div style="font-size:18px;font-weight:700;color:var(--gold);margin-bottom:8px">' +
      step.title + '</div>' +
      '<div>' + step.text + '</div>' +
      '<div style="margin-top:16px;display:flex;gap:8px;align-items:center;justify-content:space-between">' +
        '<span style="font-size:11px;color:var(--muted)">' + (currentStep + 1) + ' / ' + STEPS.length + '</span>' +
        '<div style="display:flex;gap:8px">' +
          (currentStep < STEPS.length - 1
            ? '<span class="btn primary" style="font-size:12px;padding:6px 18px" onclick="Tutorial.next()">下一步 →</span>'
            : '<span class="btn primary" style="font-size:12px;padding:6px 18px" onclick="Tutorial.finish()">开始游戏！</span>') +
          '<span class="btn" style="font-size:11px;padding:4px 12px" onclick="Tutorial.skip()">跳过教程</span>' +
        '</div>' +
      '</div>';

    highlight.style.display = "block";
    bubble.style.display = "block";
    overlay.style.display = "block";
  }

  function showStep(idx) {
    currentStep = idx;
    if (idx >= STEPS.length) { finish(); return; }
    var step = STEPS[idx];

    // Navigate to correct screen if needed
    if (step.screen && window.G) {
      // In a game, don't auto-navigate — let the game flow handle it
    }
    renderStep(step);
  }

  function next() {
    showStep(currentStep + 1);
  }

  function finish() {
    active = false;
    if (overlay) overlay.style.display = "none";
    if (highlight) highlight.style.display = "none";
    if (bubble) bubble.style.display = "none";
    try { localStorage.setItem(STORAGE_KEY, "1"); } catch(e) {}
  }

  function skip() {
    finish();
  }

  function start() {
    if (active) return;
    // Check if already seen
    try {
      if (localStorage.getItem(STORAGE_KEY) === "1") return;
    } catch(e) {}

    createElements();
    active = true;
    currentStep = 0;
    showStep(0);
  }

  function reset() {
    try { localStorage.removeItem(STORAGE_KEY); } catch(e) {}
  }

  // Auto-start on first game start
  // 延迟包装 startGame（等 game.js 加载完成后再包装）
  function wrapStartGame() {
    if (typeof window.startGame !== 'function') {
      setTimeout(wrapStartGame, 100);
      return;
    }
    var origStartGame = window.startGame;
    window.startGame = function() {
      var result = origStartGame.apply(this, arguments);
      setTimeout(function() {
        try {
          if (localStorage.getItem(STORAGE_KEY) !== "1") {
            start();
          }
        } catch(e) {}
      }, 800);
      return result;
    };
  }
  wrapStartGame();

  // Public API
  window.Tutorial = {
    start: start,
    next: next,
    finish: finish,
    skip: skip,
    reset: reset
  };
})();
