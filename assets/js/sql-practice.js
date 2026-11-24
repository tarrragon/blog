// SQL 練習頁：讀 layouts/partials/sql-practice/bank.html 產生的題庫 JSON，出選擇題、記錄作答。
// 畫面只從元件庫 assets/js/sqlp-components.js 選件與排位；畫面、狀態與退出路徑照
// scripts/sql-practice/ui/components.md〈7. 畫面狀態表〉，元件的契約在同一份檔案的第 6 章。
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
//   再按上一頁回來時，用它還原同一題與翻開的磚。
// - localStorage「sqlp.v1」：每題的作答紀錄，抽題與熟練度用。讀不到或寫不進去（無痕視窗、封鎖網站資料）
//   時照樣能作答，畫面上提示這次的紀錄不會保存。
import * as C from "./sqlp-components.js";

const { h } = C;
const root = document.getElementById("sql-practice");

const BLIND_SIZE = 10;
const BLIND_QUOTA = [
  { stages: [9], count: 2 },
  { stages: [7], count: 1 },
  { stages: [8], count: 1 },
];
const STAGE_LABEL = ["", "階段一", "階段二", "階段三", "階段四", "階段五", "階段六", "階段七", "階段八", "綜合挑戰"];
// 樞紐關鍵字（KeywordBanner）的取值：每個階段一個 SQL 關鍵字，契約在 components.md 的 KeywordBanner
const STAGE_KW = ["", "select", "join", "exists", "update", "explain", "commit", "create", "grant", "with"];
const PERSPECTIVE = {
  "choose-query": "在題目給的資料量、索引與引擎前提下，選出符合需求、代價最可控的寫法。",
  "pick-counterexample": "這段查詢在小資料上看起來是對的。選出插入之後會讓它靜默算錯的那一筆資料。",
  "diagnose-plan": "依題目描述的現象，選出根因與最小的修法。",
  "tradeoff-design": "依題目給的負載與業務前提，選出最合適的設計。",
};
const LEVELS = [
  { id: "mastered", label: "已掌握" },
  { id: "initial", label: "初通" },
  { id: "review", label: "待鞏固" },
  { id: "none", label: "尚未練習" },
];
const LETTERS = "abcdefgh";
const LOAD_TIMEOUT = 15000; // ErrorState 的逾時：fetch 超過 15 秒視同失敗
const SKELETON_DELAY = 400; // LoadingSkeleton 超過 400ms 才出現，避免閃一下

let bank = null;
const byId = {};
const byConcept = {};
const schemaOf = {};
const store = openStore();
const fallbackUrl = root ? root.getAttribute("data-fallback") || "/" : "/";
const siteRoot = root ? root.getAttribute("data-site-root") || "/" : "/";
let live = null;
let detachCompact = null;

// ---- 儲存 ----

function openStore() {
  const KEY = "sqlp.v1";
  let data = { attempts: {}, lastSession: [] };
  let ok = true;
  try {
    const raw = window.localStorage.getItem(KEY);
    if (raw) data = JSON.parse(raw);
    window.localStorage.setItem(KEY + ".probe", "1");
    window.localStorage.removeItem(KEY + ".probe");
  } catch (e) {
    ok = false;
  }
  if (!data.attempts) data.attempts = {};
  if (!data.lastSession) data.lastSession = [];
  return {
    ok,
    data,
    save() {
      if (!this.ok) return;
      try {
        window.localStorage.setItem(KEY, JSON.stringify(data));
      } catch (e) {
        this.ok = false;
      }
    },
    clear() {
      data.attempts = {};
      data.lastSession = [];
      this.save();
    },
  };
}

let memorySession = null;
function loadSession() {
  try {
    return JSON.parse(window.sessionStorage.getItem("sqlp.session") || "null") || memorySession;
  } catch (e) {
    return memorySession;
  }
}
function saveSession(s) {
  memorySession = s;
  try {
    window.sessionStorage.setItem("sqlp.session", JSON.stringify(s));
  } catch (e) {
    // sessionStorage 不能用時留在記憶體：這一頁不重新載入就還原得了
  }
}

// ---- 網址 ----

function urlFor(p) {
  const q = new URLSearchParams();
  Object.keys(p).forEach((k) => {
    if (p[k] !== null && p[k] !== undefined && p[k] !== "") q.set(k, p[k]);
  });
  const s = q.toString();
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
function modeLabel(m) {
  if (m.kind === "doc") return "這篇文章的題目";
  if (m.kind === "blind") return "盲測";
  return STAGE_LABEL[m.stage] || "階段 " + m.stage;
}

// 「離開練習」回到哪裡：從文章進來的回那篇文章；從站內其他頁面進來的回那一頁；其餘回 SQL 分類首頁。
// 按鈕文字依去向固定三選一，文章標題放在 detail（title 與 aria-label），不塞進按鈕
function exitTarget(m) {
  if (m && m.kind === "doc" && bank.docs[m.doc]) {
    return { url: bank.docs[m.doc].url, label: "回到文章", detail: bank.docs[m.doc].title };
  }
  try {
    const ref = new URL(document.referrer);
    if (ref.origin === window.location.origin && ref.pathname.indexOf(siteRoot) === 0 && ref.pathname !== window.location.pathname) {
      return { url: ref.pathname + ref.search + ref.hash, label: "回到剛才的頁面" };
    }
  } catch (e) {
    // 沒有 referrer，或 referrer 不是網址
  }
  return { url: fallbackUrl, label: "回到 SQL 分類" };
}

// ---- 抽題 ----

const attemptsOf = (id) => store.data.attempts[id] || [];
function lastAttempt(id) {
  const a = attemptsOf(id);
  return a.length ? a[a.length - 1] : null;
}

// 每個能力節點挑一題：未做過 → 上次答錯 → 跟這個節點最近一次作答的領域、表路徑、出題視角不同 → 最久沒做
function pickVariant(variants) {
  let recent = null;
  variants.forEach((q) => {
    const a = lastAttempt(q.variantId);
    if (a && (!recent || a.t > recent.a.t)) recent = { q, a };
  });
  const lastIds = store.data.lastSession || [];
  const scored = variants.map((q) => {
    const a = lastAttempt(q.variantId);
    const tier = !a ? 0 : a.ok ? 2 : 1;
    let diff = 0;
    if (recent) {
      if (q.domain !== recent.q.domain) diff += 4;
      if (q.tablePath.join(",") !== recent.q.tablePath.join(",")) diff += 2;
      if (q.perspective !== recent.q.perspective) diff += 1;
    }
    return { q, key: [lastIds.indexOf(q.variantId) >= 0 ? 1 : 0, tier, -diff, a ? a.t : 0, Math.random()] };
  });
  scored.sort((x, y) => {
    for (let i = 0; i < x.key.length; i++) {
      if (x.key[i] !== y.key[i]) return x.key[i] < y.key[i] ? -1 : 1;
    }
    return 0;
  });
  return scored[0].q;
}

function compareConcept(a, b) {
  const qa = byConcept[a][0];
  const qb = byConcept[b][0];
  if (qa.stage !== qb.stage) return qa.stage - qb.stage;
  return a < b ? -1 : a > b ? 1 : 0;
}
const conceptsWhere = (pred) => Object.keys(byConcept).filter((c) => byConcept[c].some(pred)).sort(compareConcept);
function shuffle(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function buildQueue(m) {
  const picked = [];
  if (m.kind === "stage") {
    const inStage = (q) => q.stage === m.stage;
    conceptsWhere(inStage).forEach((c) => picked.push(pickVariant(byConcept[c].filter(inStage))));
  } else if (m.kind === "doc") {
    const hit = (q) => q.relatedDocs.indexOf(m.doc) >= 0;
    conceptsWhere(hit).forEach((c) => picked.push(pickVariant(byConcept[c].filter(hit))));
  } else {
    const used = {};
    BLIND_QUOTA.forEach((quota) => {
      shuffle(conceptsWhere((q) => quota.stages.indexOf(q.stage) >= 0))
        .slice(0, quota.count)
        .forEach((c) => { used[c] = true; });
    });
    const rest = shuffle(conceptsWhere((q) => q.stage <= 6).filter((c) => !used[c]));
    rest.slice(0, BLIND_SIZE - Object.keys(used).length).forEach((c) => { used[c] = true; });
    shuffle(Object.keys(used)).forEach((c) => picked.push(pickVariant(byConcept[c])));
  }
  return picked.map((q) => ({ id: q.variantId, order: shuffle(q.options.map((o) => o.key)) }));
}

function startSession(m, firstId) {
  const queue = buildQueue(m);
  if (firstId) {
    const at = queue.map((x) => x.id).indexOf(firstId);
    if (at > 0) queue.unshift(queue.splice(at, 1)[0]);
  }
  const s = { key: modeKey(m), mode: m, queue, answers: {}, startedAt: Date.now() };
  saveSession(s);
  store.data.lastSession = queue.map((x) => x.id);
  store.save();
  return s;
}

// ---- 熟練度 ----

function levelOf(concept) {
  const rules = bank.masteryRules || {};
  const variants = byConcept[concept];
  const all = [];
  variants.forEach((q) => attemptsOf(q.variantId).forEach((a) => all.push({ q, a })));
  if (!all.length) return "none";
  all.sort((x, y) => x.a.t - y.a.t);
  const correct = all.filter((x) => x.a.ok);
  const spread = {};
  correct.forEach((x) => { spread[x.q.domain + "|" + x.q.tablePath.join(",")] = true; });
  const hasNonChoose = variants.some((q) => q.perspective !== "choose-query");
  const mastered =
    Object.keys(spread).length >= (rules.minDistinctDomainsOrPaths || 2) &&
    (!rules.requireNonChooseQueryPerspective || !hasNonChoose || correct.some((x) => x.q.perspective !== "choose-query")) &&
    (!rules.requireBlindModePass || correct.some((x) => x.a.m === "blind"));
  const last = all[all.length - 1];
  if (mastered && last.a.ok) return "mastered";
  if (!last.a.ok || !correct.length) return "review";
  return "initial";
}

// ---- 練習框 PracticeFrame：樞紐列、提示、畫面內容、播報區 ----

function announce(msg) {
  if (!live) return;
  // 先清空再寫入：同一句連續出現兩次時（例如連續兩題都答錯同一句），螢幕閱讀器才會再唸一次
  live.textContent = "";
  requestAnimationFrame(() => { live.textContent = msg; });
}

// current：樞紐列上目前所在的那一項（"home"、"blind" 或階段編號）；doc 模式沒有對應的項
function frame({ current, mode, compactLabel, compactShort, content }) {
  if (detachCompact) detachCompact();
  detachCompact = null;
  const exit = exitTarget(mode);
  const item = (key, label, m) => ({
    label,
    current: current === key,
    href: m ? urlFor(modeParams(m)) : urlFor({}),
    // 目前所在的那一項不重新開始一輪：讀者點它多半只是確認自己在哪裡
    onClick: current === key ? () => {} : m ? () => go(m) : () => goHome(),
  });
  const items = [item("home", "練習首頁", null), item("blind", "盲測", { kind: "blind" })]
    .concat(bank.stages.map((st) => item(st.stage, STAGE_LABEL[st.stage] || "階段 " + st.stage, { kind: "stage", stage: st.stage })));
  const pivot = C.pivotBar({ items, exit });
  const compact = C.compactBar({ label: compactLabel, shortLabel: compactShort, exit, onTop: () => C.scrollToPracticeTop(root) });
  const kids = [compact, pivot, store.ok ? null : C.notice("這個瀏覽器不讓網頁存資料（例如無痕視窗），這次的作答紀錄不會保存。"), content];
  // 播報區留在原位不重建：重建的播報區在螢幕閱讀器上常常唸不出第一句
  Array.from(root.childNodes).forEach((n) => { if (n !== live) n.remove(); });
  kids.filter(Boolean).forEach((k) => root.insertBefore(k, live));
  detachCompact = C.attachCompactBar(compact, pivot);
}

function focusEl(selector) {
  const el = root.querySelector(selector);
  if (el) el.focus();
}
function scrollToPractice() {
  window.scrollTo(0, Math.max(0, root.getBoundingClientRect().top + window.scrollY - 16));
}

// ---- 畫面：練習首頁 ----

// 頁面正文（play.md 的使用說明）：layout 把它放在 hidden 的 #sqlp-about，首頁複製進 AboutPanel
function aboutNodes() {
  const src = document.getElementById("sqlp-about");
  if (!src) return [];
  return Array.from(src.children).filter((el) => !el.hasAttribute("data-pagefind-meta")).map((el) => el.cloneNode(true));
}

function viewHome() {
  const tally = (stage) => {
    const concepts = conceptsWhere((q) => q.stage === stage);
    const count = {};
    concepts.forEach((c) => { const l = levelOf(c); count[l] = (count[l] || 0) + 1; });
    return concepts.length + " 個觀念・" + LEVELS.map((l) => l.label + " " + (count[l.id] || 0)).join("・");
  };
  const tiles = [
    C.roundTile({
      variant: "blind", kw: "blind", wide: true, name: "盲測：不提示階段與考點",
      meta: BLIND_SIZE + " 題，跨八個階段與綜合挑戰；其中 2 題複合陷阱、1 題 Schema 取捨、1 題資安權限",
      onClick: () => go({ kind: "blind" }),
    }),
  ].concat(bank.stages.map((st) => C.roundTile({
    variant: "stage", kw: STAGE_KW[st.stage] || "sql",
    name: (STAGE_LABEL[st.stage] || "階段 " + st.stage) + "　" + st.name,
    meta: tally(st.stage),
    onClick: () => go({ kind: "stage", stage: st.stage }),
  })));

  const attempted = Object.keys(store.data.attempts).length;
  const record = h("section", { class: "sqlp-record", "aria-labelledby": "sqlp-record-h" },
    C.sectionTitle("作答紀錄", "sqlp-record-h"),
    C.hint(store.ok
      ? "紀錄存在這個瀏覽器裡（localStorage），不會送到任何伺服器。目前有 " + attempted + " 題的紀錄。"
      : "這個瀏覽器不讓網頁存資料，這次的作答不會留下紀錄。"),
    attempted ? h("div", null, C.dangerButton({
      label: "清除我的作答紀錄",
      confirmLabel: "再按一次就清除 " + attempted + " 題的紀錄（不能復原）",
      announce,
      onConfirm: () => {
        store.clear();
        viewHome();
        announce("作答紀錄已清除");
        focusEl("#sqlp-home-h");
      },
    })) : null);

  frame({
    current: "home", mode: null, compactLabel: "練習首頁",
    content: h("div", { class: "sqlp-home" },
      h("div", null,
        C.keywordBanner("practice"),
        C.screenTitle("選一輪開始", "sqlp-home-h"),
        C.hint("每一輪每個觀念出一題，再做一次時優先出沒做過與上次答錯的變體。建議照階段順序做，每個階段都能直接開始。")),
      C.aboutPanel(aboutNodes()),
      C.roundGrid(tiles),
      record),
  });
}

// ---- 畫面：題目 ----

function viewQuestion(s, idx, { justAnswered } = {}) {
  const item = s.queue[idx];
  const q = byId[item.id];
  const m = s.mode;
  const blind = m.kind === "blind";
  const chosen = s.answers[item.id] || null;
  const answered = chosen !== null;
  const rec = q.recommendedKeys;
  const optByKey = {};
  q.options.forEach((o) => { optByKey[o.key] = o; });
  const n = idx + 1;
  const total = s.queue.length;

  // 盲測作答前不露考點：標題換成題號，樞紐關鍵字換成「#」加題號
  const heading = answered || !blind ? q.title : "第 " + n + " 題";
  const kw = blind && !answered ? "#" + n : STAGE_KW[q.stage] || "sql";
  const ask = (PERSPECTIVE[q.perspective] || "") + (rec.length > 1 ? "（這一題有不只一個推薦選項，選中其中一個就算對。）" : "");

  const stateOf = (key) => {
    const isRec = rec.indexOf(key) >= 0;
    if (!answered) return "idle";
    if (key === chosen) return isRec ? "revealed-chosen-rec" : "revealed-chosen-miss";
    return isRec ? "revealed-rec" : "revealed-other";
  };
  const tiles = item.order.map((key, i) => C.optionTile({
    letter: LETTERS[i], option: optByKey[key], state: stateOf(key),
    onAnswer: () => answer(s, idx, key),
    delay: justAnswered ? i * 40 : undefined, // 依閱讀順序各延遲 0、40、80、120ms 翻面
  }));
  const ok = answered && rec.indexOf(chosen) >= 0;
  const recLetters = item.order.map((k, i) => (rec.indexOf(k) >= 0 ? LETTERS[i] : null)).filter(Boolean).join("、");
  const docs = q.relatedDocs.map((d) => bank.docs[d]).filter(Boolean);

  // 進度：每題一段；作答過的段依對錯，目前這一題未作答時是白色粗段
  let right = 0;
  let wrong = 0;
  const states = s.queue.map((x, i) => {
    const a = s.answers[x.id];
    if (a) {
      const good = byId[x.id].recommendedKeys.indexOf(a) >= 0;
      if (good) right++; else wrong++;
      return good ? "ok" : "miss";
    }
    return i === idx ? "current" : null;
  });
  const progressText = "第 " + n + "／" + total + " 題・答對 " + right + "・答錯 " + wrong;

  const isLast = idx === total - 1;
  const buttons = [C.button({ label: "結束這一輪", onClick: () => showSummary(s) })];
  if (answered) {
    buttons.push(C.button({
      label: isLast ? "看這一輪的結果" : "下一題", variant: "primary",
      onClick: () => (isLast ? showSummary(s) : showQuestion(s, idx + 1)),
    }));
  }

  const where = modeLabel(m) + "・第 " + n + "／" + total + " 題";
  frame({
    current: m.kind === "stage" ? m.stage : m.kind === "blind" ? "blind" : null,
    mode: m, compactLabel: where, compactShort: "第 " + n + "／" + total + " 題",
    content: h("div", { class: "sqlp-question" },
      C.keywordBanner(kw),
      C.questionLayout({
        title: C.screenTitle(heading, "sqlp-q-h"),
        side: [C.requirement(q.businessRequirement), C.premiseList(q.workloadProfile), C.hint(ask, true)],
        main: [
          C.schemaPanel(q.tablePath, schemaOf[q.domain] || {}),
          answered ? C.resultBanner({ ok, recLetters, note: q.alternativeNote }) : null,
          C.tileGrid(tiles),
          answered ? C.docLinks(docs) : null,
          answered ? C.confusionNote({ question: q, announce }) : null,
        ],
      }),
      C.actionBar({ sticky: true, start: C.progressStrip(states, progressText), buttons })),
  });
}

// ---- 畫面：這一輪的結果 ----

function viewSummary(s) {
  const m = s.mode;
  const done = s.queue.filter((x) => s.answers[x.id]);
  const isRight = (x) => byId[x.id].recommendedKeys.indexOf(s.answers[x.id]) >= 0;
  const right = done.filter(isRight);
  const missDocs = [];
  done.filter((x) => !isRight(x)).forEach((x) => byId[x.id].relatedDocs.forEach((d) => {
    if (bank.docs[d] && missDocs.indexOf(bank.docs[d]) < 0) missDocs.push(bank.docs[d]);
  }));
  const rows = s.queue.map((x, i) => {
    const a = s.answers[x.id];
    const state = !a ? "skip" : isRight(x) ? "ok" : "miss";
    // 盲測沒作答的題目不露標題，跟題目畫面一致
    const title = m.kind === "blind" && !a ? "第 " + (i + 1) + " 題" : byId[x.id].title;
    return C.summaryRow({ title, state, onClick: () => showQuestion(s, i, { fromSummary: true }) });
  });

  frame({
    current: m.kind === "stage" ? m.stage : m.kind === "blind" ? "blind" : null,
    mode: m, compactLabel: modeLabel(m) + "・這一輪的結果", compactShort: "這一輪的結果",
    content: h("div", { class: "sqlp-home" },
      h("div", null,
        C.screenTitle("這一輪的結果", "sqlp-sum-h"),
        h("p", { class: "sqlp-score" }, String(right.length),
          h("small", { text: "／" + s.queue.length + " 題答對" + (done.length < s.queue.length ? "，做了 " + done.length + " 題" : "") }))),
      h("ul", { class: "sqlp-summary-list", "aria-label": "這一輪的題目" }, rows),
      C.docLinks(missDocs, "sqlp-miss-h", "答錯的題目對應的文章", "文章在同一個分頁打開；讀完按瀏覽器的上一頁，會回到這個結果畫面。"),
      C.actionBar({ buttons: [
        C.button({ label: "回練習首頁", onClick: () => goHome() }),
        C.button({ label: "再來一輪", variant: "primary", onClick: () => go(m, { replace: true }) }),
      ] })),
  });
}

// ---- 畫面：空狀態、錯誤、載入 ----

function viewEmpty(m) {
  const exit = exitTarget(m);
  frame({
    current: null, mode: m, compactLabel: "沒有題目",
    content: C.stateView({
      title: m.kind === "doc" ? "這篇文章還沒有練習題" : "這個階段還沒有題目",
      text: "可以回到原本的頁面，或到練習首頁選別的階段。",
      actions: [C.exitLink(exit), C.button({ label: "到練習首頁", variant: "primary", onClick: () => goHome({ replace: true }) })],
    }),
  });
  focusEl(".sqlp-title");
}

// 載入失敗時題庫還沒有，樞紐列畫不出階段，所以只放錯誤狀態本身
function viewError() {
  Array.from(root.childNodes).forEach((n) => { if (n !== live) n.remove(); });
  root.insertBefore(C.stateView({
    title: "題庫沒有載入", text: "可能是網路斷了。", alert: true,
    actions: [
      C.button({ label: "重試", variant: "primary", onClick: boot }),
      C.exitLink({ url: fallbackUrl, label: "回到 SQL 分類" }),
    ],
  }), live);
}

// ---- 動作 ----

function goHome({ replace } = {}) {
  history[replace ? "replaceState" : "pushState"](null, "", urlFor({}));
  viewHome();
  scrollToPractice();
  focusEl("#sqlp-home-h");
}

// 開始新的一輪：從首頁或樞紐列開始用 pushState，上一頁回到開始前的畫面；結果畫面的「再來一輪」用 replaceState
function go(m, { replace } = {}) {
  const s = startSession(m);
  const nav = replace ? "replaceState" : "pushState";
  if (!s.queue.length) {
    history[nav](null, "", urlFor(modeParams(m)));
    viewEmpty(m);
    return;
  }
  history[nav](null, "", urlFor(Object.assign(modeParams(m), { q: s.queue[0].id })));
  viewQuestion(s, 0);
  scrollToPractice();
  focusEl("#sqlp-q-h");
}

function showQuestion(s, idx, { fromSummary } = {}) {
  history.replaceState(null, "", urlFor(Object.assign(modeParams(s.mode), { q: s.queue[idx].id })));
  viewQuestion(s, idx);
  scrollToPractice();
  // 從結果畫面跳回已作答的題目時，焦點落在作答結果；其餘落在題目標題
  if (fromSummary && s.answers[s.queue[idx].id]) focusEl("#sqlp-result-h");
  else focusEl("#sqlp-q-h");
}

function showSummary(s) {
  history.replaceState(null, "", urlFor(Object.assign(modeParams(s.mode), { done: 1 })));
  viewSummary(s);
  scrollToPractice();
  focusEl("#sqlp-sum-h");
}

function answer(s, idx, key) {
  const id = s.queue[idx].id;
  if (s.answers[id]) return;
  s.answers[id] = key;
  saveSession(s);
  const list = store.data.attempts[id] || (store.data.attempts[id] = []);
  list.push({ t: Date.now(), ok: byId[id].recommendedKeys.indexOf(key) >= 0, k: key, m: s.mode.kind });
  store.save();
  viewQuestion(s, idx, { justAnswered: true });
  // 焦點移到作答結果，螢幕閱讀器從結果讀起；播報區另外唸一次，焦點移動不被朗讀時也聽得到
  focusEl("#sqlp-result-h");
  const h3 = root.querySelector("#sqlp-result-h");
  if (h3) announce(h3.textContent);
}

// 依網址畫出畫面：第一次載入、上一頁／下一頁都走這裡。不移動焦點，捲動位置交給瀏覽器還原
function route() {
  const p = new URLSearchParams(window.location.search);
  const m = modeFromParams(p);
  if (!m) {
    viewHome();
    return;
  }
  if (m.kind === "stage" && !bank.stages.some((st) => st.stage === m.stage)) {
    viewEmpty(m);
    return;
  }
  let s = loadSession();
  const qid = p.get("q");
  if (!s || s.key !== modeKey(m) || (qid && !s.queue.some((x) => x.id === qid))) {
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
  const idx = Math.max(0, s.queue.map((x) => x.id).indexOf(qid));
  history.replaceState(null, "", urlFor(Object.assign(modeParams(m), { q: s.queue[idx].id })));
  viewQuestion(s, idx);
}

function indexBank(b) {
  bank = b;
  b.questions.forEach((q) => {
    byId[q.variantId] = q;
    (byConcept[q.conceptId] || (byConcept[q.conceptId] = [])).push(q);
  });
  b.domains.forEach((d) => { schemaOf[d.id] = C.parseSchema(d.schema || ""); });
}

function boot() {
  Array.from(root.childNodes).forEach((n) => { if (n !== live) n.remove(); });
  const status = C.hint("載入題庫中…");
  status.setAttribute("role", "status");
  root.insertBefore(status, live);
  const timer = setTimeout(() => { if (status.isConnected) status.replaceWith(C.skeleton()); }, SKELETON_DELAY);
  const ctrl = typeof AbortController === "function" ? new AbortController() : null;
  const timeout = setTimeout(() => { if (ctrl) ctrl.abort(); }, LOAD_TIMEOUT);
  fetch(root.getAttribute("data-bank"), ctrl ? { signal: ctrl.signal } : undefined)
    .then((r) => {
      if (!r.ok) throw new Error(String(r.status));
      return r.json();
    })
    .then((b) => {
      clearTimeout(timer);
      clearTimeout(timeout);
      if (!bank) indexBank(b);
      route();
    })
    .catch(() => {
      clearTimeout(timer);
      clearTimeout(timeout);
      viewError();
      focusEl(".sqlp-title");
    });
}

if (root) {
  root.textContent = "";
  live = C.liveRegion();
  root.appendChild(live);
  window.addEventListener("popstate", () => { if (bank) route(); });
  boot();
}
