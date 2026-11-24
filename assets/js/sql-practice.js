// SQL 練習頁：讀 layouts/partials/sql-practice/bank.html 產生的題庫 JSON，出選擇題、記錄作答。
// 畫面的狀態與退出路徑在 content/backend/01-database/sql/practice/_index.md〈練習網站的 UX 決定〉。
//
// 網址只記篩選條件與目前這一題，換題用 replaceState：讀者按瀏覽器的上一頁，回到的是進練習頁之前的那一頁，
// 不是上一題。從練習首頁開始一輪才用 pushState，上一頁回到練習首頁。
//   ?mode=stage&stage=2   分階段學習
//   ?mode=blind           盲測（隱藏階段與考點）
//   ?doc=/backend/.../    只出 relatedDocs 指到這一篇的題目（文章結尾的入口）
//   &q=<variantId>        目前這一題；&done=1 是這一輪的結果
//
// 兩種儲存：
// - sessionStorage「sqlp.session」：這一輪的題目、選項的洗牌順序與已作答的選項。讀者點解析裡的文章、
//   再按上一頁回來時，用它還原同一題與展開的解析。
// - localStorage「sqlp.v1」：每題的作答紀錄，抽題與熟練度用。讀不到或寫不進去（無痕視窗、封鎖網站資料）
//   時照樣能作答，畫面上提示這次的紀錄不會保存。
(function () {
  "use strict";

  var root = document.getElementById("sql-practice");
  if (!root) return;

  var BLIND_SIZE = 10;
  var BLIND_QUOTA = [
    { stages: [9], count: 2 },
    { stages: [7], count: 1 },
    { stages: [8], count: 1 },
  ];
  var STAGE_LABEL = ["", "階段一", "階段二", "階段三", "階段四", "階段五", "階段六", "階段七", "階段八", "綜合挑戰"];
  var PERSPECTIVE = {
    "choose-query": { label: "選寫法", ask: "在題目給的資料量、索引與引擎前提下，選出符合需求、代價最可控的寫法。" },
    "pick-counterexample": { label: "找反例", ask: "這段查詢在小資料上看起來是對的。選出插入之後會讓它靜默算錯的那一筆資料。" },
    "diagnose-plan": { label: "診斷", ask: "依題目描述的現象，選出根因與最小的修法。" },
    "tradeoff-design": { label: "設計取捨", ask: "依題目給的負載與業務前提，選出最合適的設計。" },
  };
  var CONFUSION_TYPES = ["基礎語法缺口", "論證斷層", "術語障礙", "現實情境缺口"];
  var LEVELS = [
    { id: "mastered", label: "已掌握" },
    { id: "initial", label: "初通" },
    { id: "review", label: "待鞏固" },
    { id: "none", label: "尚未練習" },
  ];

  var bank = null;
  var byId = {};
  var byConcept = {};
  var domainName = {};
  var schemaOf = {};
  var store = openStore();
  var fallbackUrl = root.getAttribute("data-fallback") || "/";
  var siteRoot = root.getAttribute("data-site-root") || "/";

  // ---- 儲存 ----

  function openStore() {
    var KEY = "sqlp.v1";
    var data = { attempts: {}, lastSession: [] };
    var ok = true;
    try {
      var raw = window.localStorage.getItem(KEY);
      if (raw) data = JSON.parse(raw);
      window.localStorage.setItem(KEY + ".probe", "1");
      window.localStorage.removeItem(KEY + ".probe");
    } catch (e) {
      ok = false;
    }
    if (!data.attempts) data.attempts = {};
    if (!data.lastSession) data.lastSession = [];
    return {
      ok: ok,
      data: data,
      save: function () {
        if (!ok) return;
        try {
          window.localStorage.setItem(KEY, JSON.stringify(data));
        } catch (e) {
          ok = false;
        }
      },
      clear: function () {
        data.attempts = {};
        data.lastSession = [];
        this.save();
      },
    };
  }

  function loadSession() {
    try {
      return JSON.parse(window.sessionStorage.getItem("sqlp.session") || "null");
    } catch (e) {
      return memorySession;
    }
  }
  var memorySession = null;
  function saveSession(s) {
    memorySession = s;
    try {
      window.sessionStorage.setItem("sqlp.session", JSON.stringify(s));
    } catch (e) {
      // sessionStorage 不能用時留在記憶體：這一頁不重新載入就還原得了
    }
  }

  // ---- DOM ----

  function h(tag, attrs) {
    var el = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        var v = attrs[k];
        if (v === null || v === undefined || v === false) return;
        if (k === "class") el.className = v;
        else if (k === "text") el.textContent = v;
        else if (k.slice(0, 2) === "on") el.addEventListener(k.slice(2), v);
        else el.setAttribute(k, v === true ? "" : v);
      });
    }
    for (var i = 2; i < arguments.length; i++) append(el, arguments[i]);
    return el;
  }
  function append(el, child) {
    if (child === null || child === undefined || child === false) return;
    if (Array.isArray(child)) child.forEach(function (c) { append(el, c); });
    else if (typeof child === "string") el.appendChild(document.createTextNode(child));
    else el.appendChild(child);
  }
  function render(node, focusSelector) {
    root.textContent = "";
    root.appendChild(node);
    if (focusSelector) {
      var f = root.querySelector(focusSelector);
      if (f) f.focus();
    }
  }

  // ---- 網址 ----

  function params() {
    return new URLSearchParams(window.location.search);
  }
  function urlFor(p) {
    var q = new URLSearchParams();
    Object.keys(p).forEach(function (k) {
      if (p[k] !== null && p[k] !== undefined && p[k] !== "") q.set(k, p[k]);
    });
    var s = q.toString();
    return window.location.pathname + (s ? "?" + s : "");
  }
  function modeFromParams(p) {
    if (p.get("doc")) return { kind: "doc", doc: p.get("doc") };
    if (p.get("mode") === "blind") return { kind: "blind" };
    if (p.get("mode") === "stage" && p.get("stage")) return { kind: "stage", stage: parseInt(p.get("stage"), 10) };
    return null;
  }
  function modeKey(m) {
    if (m.kind === "doc") return "doc:" + m.doc;
    if (m.kind === "stage") return "stage:" + m.stage;
    return "blind";
  }
  function modeParams(m) {
    if (m.kind === "doc") return { doc: m.doc };
    if (m.kind === "stage") return { mode: "stage", stage: m.stage };
    return { mode: "blind" };
  }

  // 「離開練習」回到哪裡：從文章進來的回那篇文章；從站內其他頁面進來的回那一頁；其餘回 SQL 分類首頁
  function exitTarget(m) {
    if (m && m.kind === "doc" && bank.docs[m.doc]) {
      return { url: bank.docs[m.doc].url, label: "回到〈" + bank.docs[m.doc].title + "〉" };
    }
    try {
      var ref = new URL(document.referrer);
      if (ref.origin === window.location.origin && ref.pathname.indexOf(siteRoot) === 0 && ref.pathname !== window.location.pathname) {
        return { url: ref.pathname + ref.search + ref.hash, label: "回到剛才的頁面" };
      }
    } catch (e) {
      // 沒有 referrer，或 referrer 不是網址
    }
    return { url: fallbackUrl, label: "回到 SQL 分類" };
  }

  // ---- 抽題 ----

  function attemptsOf(id) {
    return store.data.attempts[id] || [];
  }
  function lastAttempt(id) {
    var a = attemptsOf(id);
    return a.length ? a[a.length - 1] : null;
  }

  // 每個能力節點挑一題：未做過 → 上次答錯 → 跟這個節點最近一次作答的領域、表路徑、出題視角不同 → 最久沒做
  function pickVariant(variants) {
    var recent = null;
    variants.forEach(function (q) {
      var a = lastAttempt(q.variantId);
      if (a && (!recent || a.t > recent.a.t)) recent = { q: q, a: a };
    });
    var lastIds = store.data.lastSession || [];
    var scored = variants.map(function (q) {
      var a = lastAttempt(q.variantId);
      var tier = !a ? 0 : a.ok ? 2 : 1;
      var diff = 0;
      if (recent) {
        if (q.domain !== recent.q.domain) diff += 4;
        if (q.tablePath.join(",") !== recent.q.tablePath.join(",")) diff += 2;
        if (q.perspective !== recent.q.perspective) diff += 1;
      }
      return {
        q: q,
        key: [lastIds.indexOf(q.variantId) >= 0 ? 1 : 0, tier, -diff, a ? a.t : 0, Math.random()],
      };
    });
    scored.sort(function (x, y) {
      for (var i = 0; i < x.key.length; i++) {
        if (x.key[i] !== y.key[i]) return x.key[i] < y.key[i] ? -1 : 1;
      }
      return 0;
    });
    return scored[0].q;
  }

  function conceptsWhere(pred) {
    return Object.keys(byConcept)
      .filter(function (c) { return byConcept[c].some(pred); })
      .sort(compareConcept);
  }
  function compareConcept(a, b) {
    var qa = byConcept[a][0], qb = byConcept[b][0];
    if (qa.stage !== qb.stage) return qa.stage - qb.stage;
    return a < b ? -1 : a > b ? 1 : 0;
  }
  function shuffle(arr) {
    var a = arr.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }

  function buildQueue(m) {
    var picked = [];
    if (m.kind === "stage") {
      conceptsWhere(function (q) { return q.stage === m.stage; }).forEach(function (c) {
        picked.push(pickVariant(byConcept[c].filter(function (q) { return q.stage === m.stage; })));
      });
    } else if (m.kind === "doc") {
      var hit = function (q) { return q.relatedDocs.indexOf(m.doc) >= 0; };
      conceptsWhere(hit).forEach(function (c) {
        picked.push(pickVariant(byConcept[c].filter(hit)));
      });
    } else {
      var used = {};
      BLIND_QUOTA.forEach(function (quota) {
        shuffle(conceptsWhere(function (q) { return quota.stages.indexOf(q.stage) >= 0; }))
          .slice(0, quota.count)
          .forEach(function (c) { used[c] = true; });
      });
      var rest = shuffle(conceptsWhere(function (q) { return q.stage <= 6; }).filter(function (c) { return !used[c]; }));
      rest.slice(0, BLIND_SIZE - Object.keys(used).length).forEach(function (c) { used[c] = true; });
      shuffle(Object.keys(used)).forEach(function (c) { picked.push(pickVariant(byConcept[c])); });
    }
    return picked.map(function (q) {
      return { id: q.variantId, order: shuffle(q.options.map(function (o) { return o.key; })) };
    });
  }

  function startSession(m, firstId) {
    var queue = buildQueue(m);
    if (firstId) {
      var at = queue.map(function (x) { return x.id; }).indexOf(firstId);
      if (at > 0) queue.unshift(queue.splice(at, 1)[0]);
    }
    var s = { key: modeKey(m), mode: m, queue: queue, answers: {}, startedAt: Date.now() };
    saveSession(s);
    store.data.lastSession = queue.map(function (x) { return x.id; });
    store.save();
    return s;
  }

  // ---- 熟練度 ----

  function levelOf(concept) {
    var rules = bank.masteryRules || {};
    var variants = byConcept[concept];
    var all = [];
    variants.forEach(function (q) {
      attemptsOf(q.variantId).forEach(function (a) { all.push({ q: q, a: a }); });
    });
    if (!all.length) return "none";
    all.sort(function (x, y) { return x.a.t - y.a.t; });
    var correct = all.filter(function (x) { return x.a.ok; });
    var spread = {};
    correct.forEach(function (x) { spread[x.q.domain + "|" + x.q.tablePath.join(",")] = true; });
    var hasNonChoose = variants.some(function (q) { return q.perspective !== "choose-query"; });
    var mastered =
      Object.keys(spread).length >= (rules.minDistinctDomainsOrPaths || 2) &&
      (!rules.requireNonChooseQueryPerspective || !hasNonChoose || correct.some(function (x) { return x.q.perspective !== "choose-query"; })) &&
      (!rules.requireBlindModePass || correct.some(function (x) { return x.a.m === "blind"; }));
    var last = all[all.length - 1];
    if (mastered && last.a.ok) return "mastered";
    if (!last.a.ok || !correct.length) return "review";
    return "initial";
  }

  // ---- 畫面：練習首頁 ----

  function viewHome() {
    var stages = bank.stages.map(function (st) {
      var concepts = conceptsWhere(function (q) { return q.stage === st.stage; });
      var count = bank.questions.filter(function (q) { return q.stage === st.stage; }).length;
      var tally = {};
      concepts.forEach(function (c) {
        var l = levelOf(c);
        tally[l] = (tally[l] || 0) + 1;
      });
      return h("li", { class: "sqlp-stage" },
        h("div", { class: "sqlp-stage-head" },
          h("span", { class: "sqlp-stage-label", text: STAGE_LABEL[st.stage] || "階段 " + st.stage }),
          h("span", { class: "sqlp-stage-name", text: st.name })),
        h("p", { class: "sqlp-stage-meta", text: concepts.length + " 個觀念、" + count + " 題變體。" +
          LEVELS.filter(function (l) { return tally[l.id]; }).map(function (l) { return l.label + " " + tally[l.id]; }).join("、") }),
        h("button", { type: "button", class: "sqlp-btn", onclick: function () { go({ kind: "stage", stage: st.stage }); } },
          "開始" + (STAGE_LABEL[st.stage] || "")));
    });

    var attempted = Object.keys(store.data.attempts).length;
    var clearBtn = h("button", { type: "button", class: "sqlp-btn sqlp-btn-quiet" }, "清除我的作答紀錄");
    clearBtn.addEventListener("click", function () {
      // 第一下只把按鈕換成確認，第二下才清除；不用 confirm() 對話框
      if (clearBtn.getAttribute("data-armed") === null) {
        clearBtn.setAttribute("data-armed", "");
        clearBtn.textContent = "再按一次就清除 " + attempted + " 題的紀錄（不能復原）";
        return;
      }
      store.clear();
      viewHome();
      announce("作答紀錄已清除");
    });

    var exit = exitTarget(null);
    render(h("div", { class: "sqlp-home" },
      storageNotice(),
      h("nav", { class: "sqlp-bar", "aria-label": "練習" },
        h("a", { href: exit.url, class: "sqlp-exit" }, exit.label)),
      h("section", { "aria-labelledby": "sqlp-blind-h" },
        h("h2", { id: "sqlp-blind-h", tabindex: "-1", text: "盲測：不提示階段與考點" }),
        h("p", { text: "從八個階段與綜合挑戰隨機抽 " + BLIND_SIZE + " 題，其中 2 題跨概念複合陷阱、1 題 Schema 讀寫取捨、1 題資安權限。題目看不到它在考哪個觀念，用來檢查觀念離開提示之後還在不在。" }),
        h("button", { type: "button", class: "sqlp-btn", onclick: function () { go({ kind: "blind" }); } }, "開始 " + BLIND_SIZE + " 題盲測")),
      h("section", { "aria-labelledby": "sqlp-stage-h" },
        h("h2", { id: "sqlp-stage-h", text: "分階段學習" }),
        h("p", { text: "每個觀念出一題，同一個觀念有不同領域與表的變體；再做一次時，優先出沒做過與上次答錯的變體。建議照階段順序做，但每個階段都能直接開始。" }),
        h("ol", { class: "sqlp-stages" }, stages)),
      h("section", { "aria-labelledby": "sqlp-record-h" },
        h("h2", { id: "sqlp-record-h", text: "作答紀錄" }),
        h("p", { text: store.ok
          ? "紀錄存在這個瀏覽器裡（localStorage），不會送到任何伺服器。目前有 " + attempted + " 題的紀錄。"
          : "這個瀏覽器不讓網頁存資料，這次的作答不會留下紀錄。" }),
        attempted ? clearBtn : null),
      liveRegion()));
  }

  // ---- 畫面：題目 ----

  function viewQuestion(s, idx) {
    var item = s.queue[idx];
    var q = byId[item.id];
    var m = s.mode;
    var blind = m.kind === "blind";
    var chosen = s.answers[item.id] || null;
    var answered = chosen !== null;
    var exit = exitTarget(m);
    var letters = "ABCDEFGH";
    var optByKey = {};
    q.options.forEach(function (o) { optByKey[o.key] = o; });
    var recommended = q.recommendedKeys;
    var persp = PERSPECTIVE[q.perspective] || { label: q.perspective, ask: "" };

    var heading = answered || !blind ? q.title : "第 " + (idx + 1) + " 題";
    var where = blind
      ? "盲測 · 第 " + (idx + 1) + "／" + s.queue.length + " 題"
      : (m.kind === "doc" ? "這篇文章的題目" : STAGE_LABEL[q.stage]) + " · 第 " + (idx + 1) + "／" + s.queue.length + " 題";

    var options = item.order.map(function (key, i) {
      var o = optByKey[key];
      var isRec = recommended.indexOf(key) >= 0;
      var isChosen = chosen === key;
      var badges = [];
      if (answered && isRec) badges.push(h("span", { class: "sqlp-badge sqlp-badge-rec", text: "推薦" }));
      if (answered && isChosen) badges.push(h("span", { class: "sqlp-badge sqlp-badge-mine", text: "你的選擇" }));
      var cls = "sqlp-option" + (answered ? (isRec ? " is-rec" : " is-not-rec") : "") + (isChosen ? " is-chosen" : "");
      var body = [
        h("span", { class: "sqlp-letter", text: letters[i] }),
        h("pre", { class: "sqlp-sql" }, h("code", { text: o.sql })),
      ];
      var control = answered
        ? h("div", { class: "sqlp-option-body" }, body, h("div", { class: "sqlp-badges" }, badges))
        : h("button", { type: "button", class: "sqlp-option-body", onclick: function () { answer(s, idx, key); } }, body);
      return h("li", { class: cls }, control, answered ? analysis(o, isRec || isChosen) : null);
    });

    var docs = q.relatedDocs.map(function (d) {
      var info = bank.docs[d];
      return info ? h("li", null, h("a", { href: info.url, text: info.title })) : null;
    });

    var isLast = idx === s.queue.length - 1;
    var nextBtn = h("button", { type: "button", class: "sqlp-btn", onclick: function () {
      if (isLast) showSummary(s);
      else showQuestion(s, idx + 1, true);
    } }, isLast ? "看這一輪的結果" : "下一題");

    var ok = answered && recommended.indexOf(chosen) >= 0;
    var recLetters = item.order
      .map(function (k, i) { return recommended.indexOf(k) >= 0 ? letters[i] : null; })
      .filter(Boolean).join("、");

    render(h("div", { class: "sqlp-question" },
      storageNotice(),
      h("nav", { class: "sqlp-bar", "aria-label": "練習" },
        h("span", { class: "sqlp-where", text: where }),
        h("a", { href: exit.url, class: "sqlp-exit" }, exit.label),
        h("button", { type: "button", class: "sqlp-btn sqlp-btn-quiet", onclick: function () { showSummary(s); } }, "結束這一輪")),
      h("h2", { id: "sqlp-q-h", tabindex: "-1", text: heading }),
      h("p", { class: "sqlp-meta" },
        blind ? null : h("span", { text: q.conceptId }),
        h("span", { text: domainName[q.domain] || q.domain }),
        h("span", { text: persp.label })),
      h("p", { class: "sqlp-requirement", text: q.businessRequirement }),
      workload(q.workloadProfile),
      schemaDrawer(q),
      h("p", { class: "sqlp-ask", text: persp.ask + (recommended.length > 1 ? "（這一題有不只一個推薦選項，選中其中一個就算對。）" : "") }),
      answered ? h("div", { class: "sqlp-result " + (ok ? "is-ok" : "is-miss") },
        h("h3", { id: "sqlp-result-h", tabindex: "-1", text: ok ? "答對了" : "這一題推薦的是 " + recLetters }),
        q.alternativeNote ? h("p", null, h("strong", { text: "前提改變時：" }), q.alternativeNote) : null) : null,
      h("ol", { class: "sqlp-options" }, options),
      answered ? h("section", { class: "sqlp-docs", "aria-labelledby": "sqlp-docs-h" },
        h("h3", { id: "sqlp-docs-h", text: "這一題的觀念在這幾篇" }),
        h("ul", null, docs),
        h("p", { class: "sqlp-hint", text: "文章在同一個分頁打開；讀完按瀏覽器的上一頁，會回到這一題。" })) : null,
      answered ? confusionNote(q) : null,
      answered ? h("div", { class: "sqlp-next" }, nextBtn) : null,
      liveRegion()), answered ? "#sqlp-result-h" : null);
  }

  function workload(w) {
    if (!w) return null;
    var rows = [
      ["引擎", w.engine],
      ["資料量", w.scale],
      ["讀寫比", w.readWriteRatio],
      ["索引", (w.indexes || []).join("；")],
    ].filter(function (r) { return r[1]; });
    return h("dl", { class: "sqlp-workload" }, rows.map(function (r) {
      return [h("dt", { text: r[0] }), h("dd", { text: r[1] })];
    }));
  }

  function schemaDrawer(q) {
    var defs = schemaOf[q.domain] || {};
    var parts = q.tablePath.map(function (t) { return defs[t]; }).filter(Boolean);
    if (!parts.length) return null;
    return h("details", { class: "sqlp-schema" },
      h("summary", { text: "資料表結構：" + q.tablePath.join("、") }),
      h("pre", { class: "sqlp-sql" }, h("code", { text: parts.join("\n\n") })));
  }

  function analysis(o, open) {
    var list = function (items) {
      return h("ul", null, (items || []).map(function (x) { return h("li", { text: x }); }));
    };
    return h("details", { class: "sqlp-analysis", open: open },
      h("summary", { text: "這個選項的結果與取捨" }),
      h("dl", null,
        h("dt", { text: "正常資料" }), h("dd", { text: o.normalResult }),
        h("dt", { text: "邊界資料" }), h("dd", { text: o.edgeCaseResult }),
        h("dt", { text: "優點" }), h("dd", null, list(o.pros)),
        h("dt", { text: "缺點" }), h("dd", null, list(o.cons)),
        h("dt", { text: "成立的前提" }), h("dd", { text: o.validWhen }),
        h("dt", { text: "失效的條件" }), h("dd", { text: o.failsWhen })));
  }

  function confusionNote(q) {
    var select = h("select", { id: "sqlp-confusion-type" }, CONFUSION_TYPES.map(function (t) { return h("option", { text: t }); }));
    var text = h("textarea", { id: "sqlp-confusion-text", rows: "3" });
    var out = h("textarea", { class: "sqlp-confusion-out", rows: "2", readonly: true, "aria-label": "Markdown 表格列", hidden: true });
    var btn = h("button", { type: "button", class: "sqlp-btn", onclick: function () {
      var cell = function (s) { return String(s).replace(/\|/g, "\\|").replace(/\s*\n\s*/g, " ").trim(); };
      var day = new Date();
      var date = day.getFullYear() + "-" + String(day.getMonth() + 1).padStart(2, "0") + "-" + String(day.getDate()).padStart(2, "0");
      var row = "| " + [date, q.conceptId + " " + q.variantId + "（" + q.domain + "，" + q.tablePath.join("→") + "）",
        select.value, cell(text.value || "（未填）"), "—", "待處理"].map(cell).join(" | ") + " |";
      out.value = row;
      var shown = function (msg) { out.hidden = false; announce(msg); };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(row).then(
          function () { shown("已複製成 Markdown 表格列"); },
          function () { shown("無法寫入剪貼簿，表格列在下面的欄位裡，請自己複製"); out.select(); });
      } else {
        shown("無法寫入剪貼簿，表格列在下面的欄位裡，請自己複製");
        out.select();
      }
    } }, "複製成 Markdown 表格列");
    return h("details", { class: "sqlp-confusion" },
      h("summary", { text: "記下不懂的地方" }),
      h("p", { class: "sqlp-hint", text: "產生一列 Markdown 表格，可以貼回練習規格的〈練習回饋紀錄表〉，或寄給作者。內容只在你的瀏覽器裡，不會自動送出。" }),
      h("label", { for: "sqlp-confusion-type", text: "困惑類型" }), select,
      h("label", { for: "sqlp-confusion-text", text: "哪裡不懂" }), text,
      h("div", null, btn), out);
  }

  // ---- 畫面：這一輪的結果 ----

  function viewSummary(s) {
    var m = s.mode;
    var exit = exitTarget(m);
    var done = s.queue.filter(function (x) { return s.answers[x.id]; });
    var right = done.filter(function (x) { return byId[x.id].recommendedKeys.indexOf(s.answers[x.id]) >= 0; });
    var missDocs = {};
    done.forEach(function (x) {
      if (right.indexOf(x) >= 0) return;
      byId[x.id].relatedDocs.forEach(function (d) { missDocs[d] = true; });
    });
    var rows = s.queue.map(function (x, i) {
      var q = byId[x.id];
      var a = s.answers[x.id];
      var state = !a ? "沒有作答" : q.recommendedKeys.indexOf(a) >= 0 ? "答對" : "答錯";
      return h("li", { class: "sqlp-sum-" + (!a ? "skip" : state === "答對" ? "ok" : "miss") },
        h("button", { type: "button", class: "sqlp-link", onclick: function () { showQuestion(s, i, true); } }, q.title),
        h("span", { class: "sqlp-sum-state", text: "：" + state }));
    });
    render(h("div", { class: "sqlp-summary" },
      storageNotice(),
      h("nav", { class: "sqlp-bar", "aria-label": "練習" },
        h("a", { href: exit.url, class: "sqlp-exit" }, exit.label)),
      h("h2", { id: "sqlp-sum-h", tabindex: "-1", text: "這一輪的結果" }),
      h("p", { class: "sqlp-score", text: "做了 " + done.length + "／" + s.queue.length + " 題，答對 " + right.length + " 題。" }),
      h("ol", { class: "sqlp-sum-list" }, rows),
      Object.keys(missDocs).length ? h("section", { "aria-labelledby": "sqlp-miss-h" },
        h("h3", { id: "sqlp-miss-h", text: "答錯的題目對應的文章" }),
        h("ul", null, Object.keys(missDocs).map(function (d) {
          var info = bank.docs[d];
          return info ? h("li", null, h("a", { href: info.url, text: info.title })) : null;
        }))) : null,
      h("div", { class: "sqlp-next" },
        h("button", { type: "button", class: "sqlp-btn", onclick: function () {
          var ns = startSession(m);
          if (!ns.queue.length) return;
          showQuestion(ns, 0, true);
        } }, "再來一輪"),
        h("button", { type: "button", class: "sqlp-btn sqlp-btn-quiet", onclick: function () {
          history.pushState(null, "", urlFor({}));
          viewHome();
          focusHeading();
        } }, "回練習首頁")),
      liveRegion()), "#sqlp-sum-h");
  }

  function viewEmpty(m) {
    var exit = exitTarget(m);
    render(h("div", { class: "sqlp-empty" },
      h("h2", { id: "sqlp-empty-h", tabindex: "-1", text: m.kind === "doc" ? "這篇文章還沒有練習題" : "這個階段還沒有題目" }),
      h("p", { text: "可以回到原本的頁面，或到練習首頁選別的階段。" }),
      h("div", { class: "sqlp-next" },
        h("a", { href: exit.url, class: "sqlp-btn" }, exit.label),
        h("button", { type: "button", class: "sqlp-btn sqlp-btn-quiet", onclick: function () {
          history.replaceState(null, "", urlFor({}));
          viewHome();
        } }, "到練習首頁"))), "#sqlp-empty-h");
  }

  function viewError() {
    render(h("div", { class: "sqlp-error" },
      h("p", { role: "alert", text: "題庫載入失敗，可能是網路斷了。" }),
      h("div", { class: "sqlp-next" },
        h("button", { type: "button", class: "sqlp-btn", onclick: boot }, "重試"),
        h("a", { href: fallbackUrl, class: "sqlp-btn sqlp-btn-quiet" }, "回到 SQL 分類"))));
  }

  function storageNotice() {
    return store.ok ? null : h("p", { class: "sqlp-notice", role: "note", text: "這個瀏覽器不讓網頁存資料（例如無痕視窗），這次的作答紀錄不會保存。" });
  }
  function liveRegion() {
    return h("p", { id: "sqlp-live", class: "sqlp-visually-hidden", "aria-live": "polite" });
  }
  function announce(msg) {
    var el = document.getElementById("sqlp-live");
    if (el) el.textContent = msg;
  }
  function focusHeading() {
    var el = root.querySelector("h2[tabindex]");
    if (el) el.focus();
  }

  // ---- 動作 ----

  function go(m) {
    var s = startSession(m);
    if (!s.queue.length) {
      history.pushState(null, "", urlFor(modeParams(m)));
      viewEmpty(m);
      return;
    }
    history.pushState(null, "", urlFor(Object.assign(modeParams(m), { q: s.queue[0].id })));
    viewQuestion(s, 0);
    focusHeading();
  }

  function showQuestion(s, idx, focus) {
    history.replaceState(null, "", urlFor(Object.assign(modeParams(s.mode), { q: s.queue[idx].id })));
    viewQuestion(s, idx);
    if (focus && !s.answers[s.queue[idx].id]) focusHeading();
    window.scrollTo(0, root.getBoundingClientRect().top + window.scrollY - 16);
  }

  function showSummary(s) {
    history.replaceState(null, "", urlFor(Object.assign(modeParams(s.mode), { done: 1 })));
    viewSummary(s);
    window.scrollTo(0, root.getBoundingClientRect().top + window.scrollY - 16);
  }

  function answer(s, idx, key) {
    var id = s.queue[idx].id;
    if (s.answers[id]) return;
    s.answers[id] = key;
    saveSession(s);
    var list = store.data.attempts[id] || (store.data.attempts[id] = []);
    list.push({ t: Date.now(), ok: byId[id].recommendedKeys.indexOf(key) >= 0, k: key, m: s.mode.kind });
    store.save();
    viewQuestion(s, idx);
  }

  // 依網址畫出畫面：第一次載入、上一頁／下一頁都走這裡
  function route() {
    var p = params();
    var m = modeFromParams(p);
    if (!m) {
      viewHome();
      return;
    }
    if (m.kind === "stage" && !bank.stages.some(function (st) { return st.stage === m.stage; })) {
      viewEmpty(m);
      return;
    }
    var s = loadSession();
    var qid = p.get("q");
    if (!s || s.key !== modeKey(m) || (qid && !s.queue.some(function (x) { return x.id === qid; }))) {
      s = startSession(m, qid && byId[qid] ? qid : null);
    }
    if (!s.queue.length) {
      viewEmpty(m);
      return;
    }
    if (p.get("done")) {
      viewSummary(s);
      return;
    }
    var idx = Math.max(0, s.queue.map(function (x) { return x.id; }).indexOf(qid));
    history.replaceState(null, "", urlFor(Object.assign(modeParams(m), { q: s.queue[idx].id })));
    viewQuestion(s, idx);
  }

  function indexBank(b) {
    bank = b;
    b.questions.forEach(function (q) {
      byId[q.variantId] = q;
      (byConcept[q.conceptId] || (byConcept[q.conceptId] = [])).push(q);
    });
    b.domains.forEach(function (d) {
      domainName[d.id] = d.name;
      schemaOf[d.id] = parseSchema(d.schema || "");
    });
  }

  // schema.sql 依表名切開：CREATE TABLE 到它的結尾分號，加上建在這張表上的 CREATE INDEX
  function parseSchema(sql) {
    var out = {};
    var re = /CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(\w+)\s*\([\s\S]*?\n\)[^;]*;/g;
    var mt;
    while ((mt = re.exec(sql))) out[mt[1]] = mt[0];
    var ix = /CREATE (?:UNIQUE )?INDEX[^;]*?\bON\s+(\w+)[^;]*;/g;
    while ((mt = ix.exec(sql))) {
      if (out[mt[1]]) out[mt[1]] += "\n" + mt[0];
    }
    return out;
  }

  function boot() {
    render(h("p", { class: "sqlp-status", role: "status", text: "載入題庫中…" }));
    fetch(root.getAttribute("data-bank"))
      .then(function (r) {
        if (!r.ok) throw new Error(r.status);
        return r.json();
      })
      .then(function (b) {
        indexBank(b);
        route();
      })
      .catch(function () { viewError(); });
  }

  window.addEventListener("popstate", function () {
    if (bank) route();
  });
  boot();
})();
