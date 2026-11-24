// SQL 練習頁的元件庫：每個函式產生一個元件的 DOM，契約在 scripts/sql-practice/ui/components.md。
// 畫面（assets/js/sql-practice.js）只從這裡選件與排位；元件展示頁（scripts/sql-practice/ui/gallery.html）
// 也用同一份，所以展示頁看到的就是練習頁畫出來的東西。
// 文字一律用 textContent 寫入，不用 innerHTML。
import { renderSql, highlightInline } from "./sql-format.js";

// ---- 基礎 ----

export function h(tag, attrs, ...children) {
  const el = document.createElement(tag);
  if (attrs) {
    for (const [k, v] of Object.entries(attrs)) {
      if (v === null || v === undefined || v === false) continue;
      if (k === "class") el.className = v;
      else if (k === "text") el.textContent = v;
      else if (k === "style") el.setAttribute("style", v);
      else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? "" : v);
    }
  }
  append(el, children);
  return el;
}
function append(el, child) {
  if (child === null || child === undefined || child === false) return;
  if (Array.isArray(child)) child.forEach((c) => append(el, c));
  else if (typeof child === "string") el.appendChild(document.createTextNode(child));
  else el.appendChild(child);
}

const SVG = "http://www.w3.org/2000/svg";
// 只剩展開區的狀態標記：加號（已收合）與減號（已展開）。按鈕與連結只放文字，不放圖示
const PATHS = {
  plus: "M6 1h2v12H6zM1 6h12v2H1z",
  minus: "M1 6h12v2H1z",
};
// 圖示：實心、14px，筆畫風格跟 Metro 按鈕上的三角箭頭一致
export function icon(name, cls) {
  const svg = document.createElementNS(SVG, "svg");
  svg.setAttribute("width", "14");
  svg.setAttribute("height", "14");
  svg.setAttribute("viewBox", "0 0 14 14");
  svg.setAttribute("aria-hidden", "true");
  if (cls) svg.setAttribute("class", cls);
  const p = document.createElementNS(SVG, "path");
  p.setAttribute("d", PATHS[name]);
  p.setAttribute("fill", "currentColor");
  svg.appendChild(p);
  return svg;
}

// 需求文字裡用反引號包住的片段轉成 <code>
function withCode(text) {
  return String(text).split(/(`[^`]+`)/).map((s) => (/^`[^`]+`$/.test(s) ? h("code", { text: s.slice(1, -1) }) : s));
}

// ---- PivotBar / PivotItem / ExitLink ----

export function pivotBar({ items, exit }) {
  const list = h("ul", { class: "sqlp-pivot-items" }, items.map((it) =>
    h("li", null, h("a", {
      class: "sqlp-pivot-item", href: it.href, "aria-current": it.current ? "page" : null,
      onclick: it.onClick ? (e) => { e.preventDefault(); it.onClick(); } : null,
    }, it.label))));
  // 清單放不下時，畫好之後把目前這一輪捲到清單中間，避免落在邊緣的捲動漸層底下；
  // 只改清單自己的 scrollLeft，不動整頁的捲動位置
  requestAnimationFrame(() => {
    const cur = list.querySelector("[aria-current]");
    if (!cur || list.scrollWidth <= list.clientWidth) return;
    const item = cur.parentElement;
    list.scrollLeft = item.offsetLeft - list.offsetLeft - (list.clientWidth - item.offsetWidth) / 2;
  });
  return h("nav", { class: "sqlp-pivot", "aria-label": "練習" }, list, exit ? exitLink(exit) : null);
}
// 離開練習：外觀是固定大小的按鈕，文字依去向固定（回到文章／回到剛才的頁面／回到 SQL 分類），
// 不把文章標題塞進按鈕；完整標題放在 title 與 aria-label。語意上仍是連結（會離開練習頁）。
export function exitLink({ url, label, detail }) {
  const full = detail ? `${label}：${detail}` : label;
  // 只放文字、不放圖示：按鈕用文字或圖示其中一種表達，不重複（2026-11-24 使用者決定）
  return h("a", { class: "sqlp-exit", href: url, title: detail || null, "aria-label": full }, h("span", { text: label }));
}

// ---- CompactBar：捲過導覽列之後出現的精簡頂列 ----
// 讀者捲到很深時，離開與回到頂部都只要一步。桌機在導覽列捲出畫面後常駐；手機（窄於 600px）
// 往下讀時收起、往上捲時出現。放在練習區最前面，用 sticky 且高度 0 的外框掛在頂端，寬度跟練習區對齊。
export function compactBar({ label, shortLabel, exit, onTop }) {
  const topBtn = button({ label: "回到頂部", onClick: onTop });
  const bar = h("div", { class: "sqlp-compact", role: "navigation", "aria-label": "練習捷徑" },
    h("p", { class: "sqlp-compact-where" },
      h("span", { class: "sqlp-compact-long", text: label }),
      h("span", { class: "sqlp-compact-short", text: shortLabel || label })),
    h("div", { class: "sqlp-compact-actions" }, topBtn, exit ? exitLink(exit) : null));
  return h("div", { class: "sqlp-compact-wrap" }, bar);
}

// 把精簡頂列接到導覽列：導覽列看不見時顯示；手機上另外依捲動方向收起或出現。回傳解除函式。
export function attachCompactBar(wrap, pivotEl) {
  const bar = wrap.querySelector(".sqlp-compact");
  const narrow = window.matchMedia("(max-width: 599px)");
  let pivotGone = false;
  let lastY = window.scrollY;
  let goingUp = false;
  const update = () => {
    const show = pivotGone && (!narrow.matches || goingUp);
    if (show) bar.setAttribute("data-shown", "");
    else bar.removeAttribute("data-shown");
  };
  const io = new IntersectionObserver(([entry]) => { pivotGone = !entry.isIntersecting; update(); });
  io.observe(pivotEl);
  const onScroll = () => {
    const y = window.scrollY;
    if (Math.abs(y - lastY) > 6) { goingUp = y < lastY; lastY = y; update(); }
  };
  window.addEventListener("scroll", onScroll, { passive: true });
  narrow.addEventListener("change", update);
  return () => { io.disconnect(); window.removeEventListener("scroll", onScroll); narrow.removeEventListener("change", update); };
}

// 回到頂部：捲回練習區頂端，焦點移到導覽列上目前這一輪（沒有就移到第一項）；減少動態效果時直接跳回
export function scrollToPracticeTop(root) {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  window.scrollTo({ top: Math.max(0, root.getBoundingClientRect().top + window.scrollY - 16), behavior: reduce ? "auto" : "smooth" });
  const target = root.querySelector(".sqlp-pivot-item[aria-current]") || root.querySelector(".sqlp-pivot-item");
  if (target) target.focus({ preventScroll: true });
}

// ---- KeywordBanner / ScreenTitle / 內文 ----

export function keywordBanner(text) {
  return h("p", { class: "sqlp-keyword", "aria-hidden": "true", text });
}
export function screenTitle(text, id) {
  return h("h2", { class: "sqlp-title", tabindex: "-1", id: id || null, text });
}
export function sectionTitle(text, id) {
  return h("h3", { class: "sqlp-section", id: id || null, text });
}
export function requirement(text) {
  return h("p", { class: "sqlp-req" }, withCode(text));
}
export function premiseList(w) {
  if (!w) return null;
  const rows = [["引擎", w.engine], ["資料量", w.scale], ["讀寫比", w.readWriteRatio], ["索引", (w.indexes || []).join("；")]]
    .filter((r) => r[1]);
  return h("dl", { class: "sqlp-premise" }, rows.map((r) => [h("dt", { text: r[0] }), h("dd", { text: r[1] })]));
}
export function hint(text, strong) {
  return h("p", { class: strong ? "sqlp-hint-strong" : "sqlp-hint", text });
}

// ---- SqlBlock ----

// 整段是 -- 註解的選項是文字描述的設計方案，用一般文字顯示
export function isProseSql(sql) {
  return /^\s*--/.test(sql) && !sql.trim().includes("\n");
}
export function sqlBlock(sql) {
  if (isProseSql(sql)) return h("p", { class: "sqlp-prose", text: sql.trim().replace(/^--\s*/, "") });
  const code = h("code");
  renderSql(code, sql);
  return h("div", { class: "sqlp-code", tabindex: "0", role: "region", "aria-label": "SQL" }, h("pre", { class: "sqlp-sql" }, code));
}

// ---- SchemaPanel：資料表結構 ----
// 從 domains/<領域>/schema.sql 切出這一題用到的表，排成「欄位、型別、約束、說明」的表格。
// schema.sql 的格式是一欄一行、註解用 --，表級約束（CHECK、FOREIGN KEY…）各佔一行。

const TABLE_CONSTRAINT = /^(CHECK|FOREIGN|PRIMARY|UNIQUE|CONSTRAINT|EXCLUDE)\b/i;
const TYPES = /^(INTEGER|INT|BIGINT|TEXT|REAL|NUMERIC|BLOB|BOOLEAN|DATE|TIMESTAMP|TIMESTAMPTZ|JSONB?|VARCHAR(\(\d+\))?|SERIAL|BIGSERIAL)$/i;

// 把一行切成「定義」與「行尾註解」：-- 在單引號字串外才算註解
function splitComment(line) {
  let inStr = false;
  for (let i = 0; i < line.length - 1; i++) {
    if (line[i] === "'") inStr = !inStr;
    if (!inStr && line[i] === "-" && line[i + 1] === "-") return [line.slice(0, i).trim(), line.slice(i + 2).trim()];
  }
  return [line.trim(), ""];
}
export function parseSchema(sql) {
  const tables = {};
  for (const m of sql.matchAll(/CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(\w+)\s*\(([\s\S]*?)\n\)([^;]*);/g)) {
    const t = { name: m[1], columns: [], constraints: [], indexes: [], options: m[3].trim() };
    let pendingComment = "";
    for (const raw of m[2].split("\n")) {
      const [def0, comment] = splitComment(raw);
      const def = def0.replace(/,$/, "").trim();
      if (!def) { if (comment) pendingComment = comment; continue; }
      const note = [pendingComment, comment].filter(Boolean).join("；");
      pendingComment = "";
      if (TABLE_CONSTRAINT.test(def)) { t.constraints.push({ def, note }); continue; }
      const mm = /^("?[\w]+"?)\s+(\S+)?\s*([\s\S]*)$/.exec(def);
      if (!mm) { t.constraints.push({ def, note }); continue; }
      const hasType = mm[2] && TYPES.test(mm[2]);
      t.columns.push({ name: mm[1], type: hasType ? mm[2] : "", rest: hasType ? mm[3] : [mm[2], mm[3]].filter(Boolean).join(" "), note });
    }
    tables[t.name] = t;
  }
  for (const m of sql.matchAll(/CREATE (UNIQUE )?INDEX\s+(?:IF NOT EXISTS\s+)?(\w+)\s+ON\s+(\w+)\s*([^;]*);/g)) {
    if (tables[m[3]]) tables[m[3]].indexes.push({ def: `${m[1] ? "UNIQUE " : ""}${m[2]} ${m[4].trim()}` });
  }
  return tables;
}
function sqlSpan(text) {
  const el = h("code", { class: "sqlp-sql-inline" });
  highlightInline(el, text);
  return el;
}
function schemaTable(t) {
  const rows = t.columns.map((c) => h("tr", null,
    h("th", { scope: "row" }, h("code", { text: c.name })),
    h("td", null, c.type ? sqlSpan(c.type) : null),
    h("td", null, c.rest ? sqlSpan(c.rest) : null),
    h("td", { class: "sqlp-schema-note", text: c.note })));
  t.constraints.forEach((c) => rows.push(h("tr", { class: "sqlp-schema-tc" },
    h("th", { scope: "row", text: "表約束" }), h("td", { colspan: "2" }, sqlSpan(c.def)), h("td", { class: "sqlp-schema-note", text: c.note }))));
  t.indexes.forEach((x) => rows.push(h("tr", { class: "sqlp-schema-tc" },
    h("th", { scope: "row", text: "索引" }), h("td", { colspan: "2" }, sqlSpan(x.def)), h("td", { class: "sqlp-schema-note" }))));
  return h("section", { class: "sqlp-schema-table", "aria-label": "資料表 " + t.name },
    h("h4", null, h("code", { text: t.name }), t.options ? h("span", { class: "sqlp-schema-opt", text: t.options }) : null),
    h("div", { class: "sqlp-schema-scroll", tabindex: "0", role: "region", "aria-label": t.name + " 的欄位" },
      h("table", null,
        h("thead", null, h("tr", null, ["欄位", "型別", "約束", "說明"].map((x) => h("th", { scope: "col", text: x })))),
        h("tbody", null, rows))));
}
export function schemaPanel(tablePath, tables) {
  const list = tablePath.map((n) => tables[n]).filter(Boolean);
  if (!list.length) return null;
  return h("details", { class: "sqlp-schema" },
    h("summary", null, icon("plus", "sqlp-plus"), icon("minus", "sqlp-minus"),
      h("span", null, "資料表結構", h("span", { class: "sqlp-schema-names", text: "：" + tablePath.join("、") }))),
    h("div", { class: "sqlp-schema-body" }, list.map(schemaTable)));
}

// ---- OptionTile / OptionAnalysis / TileGrid ----

const STATE_LABEL = {
  "revealed-chosen-rec": ["你的選擇", "推薦"],
  "revealed-chosen-miss": ["你的選擇", "不推薦"],
  "revealed-rec": ["推薦"],
  "revealed-other": ["不推薦"],
};

export function optionAnalysis(o) {
  const list = (items) => h("ul", null, (items || []).map((x) => h("li", { text: x })));
  const rows = [
    ["正常資料", o.normalResult],
    ["邊界資料", o.edgeCaseResult],
    ["優點", o.pros && o.pros.length ? list(o.pros) : null],
    ["缺點", o.cons && o.cons.length ? list(o.cons) : null],
    ["成立前提", o.validWhen],
    ["失效條件", o.failsWhen],
  ].filter((r) => r[1]);
  return h("dl", { class: "sqlp-analysis" }, rows.map((r) => [h("dt", { text: r[0] }), h("dd", null, r[1])]));
}

// state: idle | revealed-chosen-rec | revealed-chosen-miss | revealed-rec | revealed-other
export function optionTile({ letter, option, state, onAnswer, delay }) {
  const head = h("div", { class: "sqlp-tile-head" },
    h("span", { class: "sqlp-tile-letter", text: letter }),
    state === "idle" ? null : h("p", { class: "sqlp-tile-state" }, STATE_LABEL[state].map((t) => h("span", { text: t }))));
  const body = sqlBlock(option.sql);
  if (state === "idle") {
    const preview = option.sql.replace(/\s+/g, " ").trim().slice(0, 80);
    // 程式碼區在按鈕裡不能有自己的 tab 停駐點
    body.removeAttribute && body.removeAttribute("tabindex");
    return h("button", { type: "button", class: "sqlp-tile", "data-state": "idle", "aria-label": `選項 ${letter}：${preview}`, onclick: onAnswer }, head, body);
  }
  const tile = h("article", { class: "sqlp-tile" + (delay !== undefined ? " is-flipping" : ""), "data-state": state,
    "aria-label": `選項 ${letter}，${STATE_LABEL[state].join("，")}`, style: delay !== undefined ? `--sqlp-delay:${delay}ms` : null },
    head, body, optionAnalysis(option));
  return tile;
}
export function tileGrid(tiles) {
  return h("ol", { class: "sqlp-tiles", "aria-label": "選項" }, tiles.map((t) => h("li", null, t)));
}

// ---- ResultBanner / DocLinks / ConfusionNote ----

export function resultBanner({ ok, recLetters, note }) {
  return h("div", { class: "sqlp-result", "data-v": ok ? "ok" : "miss" },
    h("h3", { id: "sqlp-result-h", tabindex: "-1", text: ok ? "答對了" : "這一題推薦的是 " + recLetters }),
    note ? h("p", null, h("strong", { text: "前提改變時：" }), note) : null);
}
export function docLinks(docs, id) {
  if (!docs.length) return null;
  return h("section", { class: "sqlp-docs", "aria-labelledby": id || "sqlp-docs-h" },
    sectionTitle("這一題的觀念在這幾篇", id || "sqlp-docs-h"),
    h("ul", null, docs.map((d) => h("li", null, h("a", { href: d.url, text: d.title })))),
    hint("文章在同一個分頁打開；讀完按瀏覽器的上一頁，會回到這一題。"));
}

export const CONFUSION_TYPES = ["基礎語法缺口", "論證斷層", "術語障礙", "現實情境缺口"];
export function confusionNote({ question, announce }) {
  const select = h("select", { id: "sqlp-confusion-type" }, CONFUSION_TYPES.map((t) => h("option", { text: t })));
  const text = h("textarea", { id: "sqlp-confusion-text", rows: "3", placeholder: "例如：為什麼 ORDER BY 可以用別名，WHERE 不行" });
  const out = h("textarea", { class: "sqlp-note-out", rows: "2", readonly: true, "aria-label": "Markdown 表格列", hidden: true });
  const btn = button({ label: "複製成 Markdown 表格列", onClick: () => {
    const cell = (s) => String(s).replace(/\|/g, "\\|").replace(/\s*\n\s*/g, " ").trim();
    const d = new Date();
    const date = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    const id = `${question.conceptId} ${question.variantId}（${question.domain}，${question.tablePath.join("→")}）`;
    const row = "| " + [date, id, select.value, text.value || "（未填）", "—", "待處理"].map(cell).join(" | ") + " |";
    out.value = row;
    const fail = () => { out.hidden = false; out.select(); announce("無法寫入剪貼簿，表格列在下面的欄位裡"); };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(row).then(() => {
        out.hidden = false;
        btn.firstChild.textContent = "已複製";
        setTimeout(() => { btn.firstChild.textContent = "複製成 Markdown 表格列"; }, 3000);
        announce("已複製成 Markdown 表格列");
      }, fail);
    } else fail();
  } });
  return h("details", { class: "sqlp-note" },
    h("summary", null, icon("plus", "sqlp-plus"), icon("minus", "sqlp-minus"), "記下不懂的地方"),
    h("div", { class: "sqlp-note-body" },
      hint("產生一列 Markdown 表格，可以貼回練習規格的〈練習回饋紀錄表〉，或寄給作者。內容只在你的瀏覽器裡，不會自動送出。"),
      h("label", { for: "sqlp-confusion-type", text: "困惑類型" }), select,
      h("label", { for: "sqlp-confusion-text", text: "哪裡不懂" }), text,
      h("div", null, btn), out));
}

// ---- Button / ActionBar / ProgressStrip ----

// variant: primary | secondary | danger；只放文字，主次靠外框粗細與字重區分，不加圖示
export function button({ label, variant, onClick, href }) {
  const kids = [h("span", { text: label })];
  if (href) return h("a", { class: "sqlp-btn", "data-v": variant || null, href }, kids);
  return h("button", { type: "button", class: "sqlp-btn", "data-v": variant || null, onclick: onClick }, kids);
}
// danger 按鈕：第一下換成確認文字，第二下才執行；焦點離開或 5 秒後恢復
export function dangerButton({ label, confirmLabel, onConfirm, announce }) {
  const b = button({ label, variant: "danger" });
  let timer = null;
  const reset = () => { b.removeAttribute("data-armed"); b.firstChild.textContent = label; clearTimeout(timer); };
  b.addEventListener("click", () => {
    if (!b.hasAttribute("data-armed")) {
      b.setAttribute("data-armed", "");
      b.firstChild.textContent = confirmLabel;
      if (announce) announce(confirmLabel);
      timer = setTimeout(reset, 5000);
      return;
    }
    reset();
    onConfirm();
  });
  b.addEventListener("blur", reset);
  return b;
}
export function progressStrip(states, text) {
  return h("div", { class: "sqlp-progress" },
    h("div", { class: "sqlp-progress-bar", "aria-hidden": "true" }, states.map((s) => h("i", { "data-s": s || null }))),
    h("p", { class: "sqlp-progress-text", text }));
}
export function actionBar({ start, buttons, sticky }) {
  return h("div", { class: "sqlp-actions", "data-v": sticky ? "sticky" : null, role: "group", "aria-label": "動作" },
    start || null, h("div", { class: "sqlp-actions-end" }, buttons));
}

// ---- QuestionLayout（左欄題目可摺疊）----

export function questionLayout({ title, side, main }) {
  const layout = h("div", { class: "sqlp-q" });
  const toggle = h("button", { type: "button", class: "sqlp-q-toggle", "aria-expanded": "true", "aria-controls": "sqlp-q-body" },
    h("span", { text: "收合題目" }));
  toggle.addEventListener("click", () => {
    const collapsed = layout.toggleAttribute("data-collapsed");
    toggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
    toggle.lastChild.textContent = collapsed ? "展開題目" : "收合題目";
  });
  layout.append(
    h("div", { class: "sqlp-q-side" }, h("div", { class: "sqlp-q-head" }, title, toggle), h("div", { class: "sqlp-q-body", id: "sqlp-q-body" }, side)),
    h("div", { class: "sqlp-q-main" }, main));
  return layout;
}

// ---- RoundTile / RoundGrid / SummaryRow ----

export function roundTile({ variant, kw, name, meta, onClick, wide }) {
  const li = h("li", { "data-wide": wide ? "" : null },
    h("button", { type: "button", class: "sqlp-round", "data-v": variant, onclick: onClick },
      h("span", { class: "sqlp-round-kw", "aria-hidden": "true", text: kw }),
      h("span", null, h("span", { class: "sqlp-round-name", text: name }), h("br"), h("span", { class: "sqlp-round-meta", text: meta }))));
  return li;
}
export function roundGrid(tiles) {
  return h("ul", { class: "sqlp-rounds" }, tiles);
}
export function summaryRow({ title, state, onClick }) {
  const label = state === "ok" ? "答對" : state === "miss" ? "答錯" : "沒有作答";
  return h("li", null, h("button", { type: "button", class: "sqlp-row", "data-s": state, onclick: onClick, "aria-label": `${title}，${label}` },
    h("span", { class: "sqlp-row-mark", "aria-hidden": "true" }), h("span", { text: title }), h("span", { class: "sqlp-row-state", text: label })));
}

// ---- Notice / EmptyState / ErrorState / LoadingSkeleton / LiveRegion ----

export function notice(text) {
  return h("p", { class: "sqlp-notice", role: "note" }, h("b", { text: "注意" }), text);
}
export function stateView({ title, text, actions, alert }) {
  return h("div", { class: "sqlp-state", role: alert ? "alert" : null }, screenTitle(title), hint(text), actionBar({ buttons: actions }));
}
export function skeleton() {
  return h("div", { class: "sqlp-skel", "aria-busy": "true" },
    h("span", { class: "sqlp-vh", text: "載入題庫中" }),
    h("i", { class: "sqlp-skel-kw" }),
    h("div", { class: "sqlp-skel-q" },
      h("div", { class: "sqlp-skel-side" }, h("i"), h("i"), h("i"), h("i")),
      h("div", { class: "sqlp-skel-tiles" }, h("i"), h("i"), h("i"), h("i"))));
}
export function liveRegion() {
  return h("p", { id: "sqlp-live", class: "sqlp-vh", "aria-live": "polite" });
}
