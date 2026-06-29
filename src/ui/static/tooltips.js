/**
 * 悬浮提示系统
 * 使用 data-tooltip 属性自动显示提示，300ms 延迟
 */
(function() {
  var tip = null;
  var timer = null;
  var currentTarget = null;

  function ensureTip() {
    if (!tip) {
      tip = document.createElement("div");
      tip.id = "tooltip";
      tip.style.cssText =
        "display:none;position:fixed;z-index:200;background:rgba(10,8,6,.96);" +
        "border:2px solid var(--gold);border-radius:8px;padding:10px 14px;" +
        "max-width:280px;font-size:13px;color:var(--text);line-height:1.5;" +
        "pointer-events:none;transition:opacity .15s;box-shadow:0 4px 24px rgba(0,0,0,.6)";
      document.body.appendChild(tip);
    }
    return tip;
  }

  function position(x, y, tipEl) {
    var tw = tipEl.offsetWidth;
    var th = tipEl.offsetHeight;
    var ww = window.innerWidth;
    var wh = window.innerHeight;

    // Default: below cursor, centered
    var left = x - tw / 2;
    var top = y + 16;

    // Keep within viewport
    if (left < 8) left = 8;
    if (left + tw > ww - 8) left = ww - tw - 8;
    // Flip above if would go off bottom
    if (top + th > wh - 8) top = y - th - 16;
    if (top < 8) top = 8;

    tipEl.style.left = left + "px";
    tipEl.style.top = top + "px";
  }

  function show(evt, el) {
    var content = el.getAttribute("data-tooltip");
    if (!content) return;

    currentTarget = el;
    var tipEl = ensureTip();
    tipEl.innerHTML = content;
    tipEl.style.display = "block";
    tipEl.style.opacity = "0";

    // Delay for natural feel
    timer = setTimeout(function() {
      if (currentTarget === el) {
        position(evt.clientX, evt.clientY, tipEl);
        tipEl.style.opacity = "1";
      }
    }, 300);
  }

  function hide() {
    currentTarget = null;
    if (timer) { clearTimeout(timer); timer = null; }
    if (tip) { tip.style.display = "none"; tip.style.opacity = "0"; }
  }

  function move(evt) {
    if (currentTarget && tip && tip.style.opacity === "1") {
      position(evt.clientX, evt.clientY, tip);
    }
  }

  // Auto-bind to elements with data-tooltip
  document.addEventListener("mouseover", function(evt) {
    var el = evt.target.closest("[data-tooltip]");
    if (el) show(evt, el);
    else hide();
  }, true);

  document.addEventListener("mouseout", function(evt) {
    var el = evt.target.closest("[data-tooltip]");
    if (el) hide();
  }, true);

  document.addEventListener("mousemove", function(evt) {
    if (currentTarget) move(evt);
  });

  // Public API
  window.Tooltip = { show: show, hide: hide };
})();
