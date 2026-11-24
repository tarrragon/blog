// SQL 的排版與上色：練習頁的選項磚與資料表結構用它把 SQL 畫成「一行一個完整子句」的程式碼。
// 契約在 scripts/sql-practice/ui/components.md 的 SqlBlock；題庫全部選項的排版結果由
// scripts/sql-practice/ui/check_sql_format.mjs 檢查（token 順序不變、每行長度）。
//
// 排版規則：
// - 子句關鍵字（SELECT、FROM、WHERE、GROUP BY、各種 JOIN、UNION…）各自起一行。
// - 一個子句排成一行超過 WIDTH 時才拆：清單類子句（SELECT、GROUP BY、ORDER BY、SET、VALUES…）
//   每個項目一行；條件類子句（WHERE、HAVING、ON）在最外層的 AND／OR 前斷行；JOIN 先在 ON 前斷行。
// - 括號裡是子查詢（以 SELECT 或 WITH 開頭）時，內容縮排一層另起幾行；其餘括號排成一行，
//   超過 WIDTH 而且有逗號時，每個項目一行（CREATE TABLE 的欄位定義就走這條）。
// - 分號結束一個陳述式，下一個陳述式另起一行。
// 原文已經有換行的 SQL（schema.sql 切出的片段）不重排，只上色。

export const WIDTH = 72;

const KEYWORDS = new Set(("SELECT FROM WHERE GROUP BY HAVING ORDER LIMIT OFFSET UNION ALL INTERSECT EXCEPT WITH AS " +
  "JOIN LEFT RIGHT FULL INNER OUTER CROSS NATURAL ON USING AND OR NOT IN IS NULL LIKE ILIKE GLOB BETWEEN EXISTS " +
  "CASE WHEN THEN ELSE END DISTINCT INSERT INTO VALUES UPDATE SET DELETE RETURNING CONFLICT DO NOTHING CREATE " +
  "TABLE INDEX UNIQUE PRIMARY KEY FOREIGN REFERENCES CHECK DEFAULT CONSTRAINT VIEW TRIGGER BEGIN COMMIT ROLLBACK " +
  "TRANSACTION OVER PARTITION ROWS RANGE PRECEDING FOLLOWING CURRENT ROW UNBOUNDED ASC DESC NULLS FIRST LAST " +
  "FOR SKIP LOCKED NOWAIT SHARE GRANT REVOKE TO ROLE POLICY ENABLE ROW LEVEL SECURITY ALTER ADD DROP COLUMN " +
  "RECURSIVE MATERIALIZED LATERAL FILTER WITHIN TRUE FALSE STRICT WITHOUT ROWID INTEGER TEXT REAL NUMERIC BLOB " +
  "BIGINT INT VARCHAR CHAR BOOLEAN TIMESTAMP TIMESTAMPTZ DATE JSONB JSON SERIAL CASCADE RESTRICT IF REPLACE " +
  "EXPLAIN QUERY PLAN ANALYZE COLLATE NOCASE ESCAPE CAST EXCLUDE GIST INCLUDE CONCURRENTLY TEMP TEMPORARY " +
  "SAVEPOINT RELEASE ISOLATION LEVEL SERIALIZABLE READ COMMITTED REPEATABLE ONLY OF EACH NEW OLD BEFORE AFTER " +
  "INSTEAD EXECUTE FUNCTION PROCEDURE RAISE ABORT IGNORE FAIL LOCK MODE EXCLUSIVE VACUUM PRAGMA ATTACH DETACH").split(" "));

// 子句起點：多字關鍵字放前面，比對時取最長
const CLAUSES = [
  "INSERT INTO", "DELETE FROM", "GROUP BY", "ORDER BY", "PARTITION BY", "UNION ALL", "ON CONFLICT", "DO UPDATE SET",
  "LEFT OUTER JOIN", "RIGHT OUTER JOIN", "FULL OUTER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL JOIN", "INNER JOIN",
  "CROSS JOIN", "NATURAL JOIN", "JOIN", "SELECT", "FROM", "WHERE", "HAVING", "LIMIT", "OFFSET", "UNION", "INTERSECT",
  "EXCEPT", "WITH", "VALUES", "UPDATE", "SET", "RETURNING", "WINDOW", "FOR UPDATE", "FOR SHARE",
].map((c) => c.split(" "));
const LIST_CLAUSES = new Set(["SELECT", "GROUP BY", "ORDER BY", "PARTITION BY", "SET", "DO UPDATE SET", "VALUES", "RETURNING", "WITH"]);
const COND_CLAUSES = new Set(["WHERE", "HAVING"]);

// ---- token ----

export function tokenize(sql) {
  const out = [];
  let i = 0;
  const n = sql.length;
  while (i < n) {
    const c = sql[i];
    const rest = sql.slice(i);
    let m;
    if (/\s/.test(c)) {
      m = /^\s+/.exec(rest);
      out.push({ t: m[0], k: "ws" });
    } else if (rest.startsWith("--")) {
      m = /^--[^\n]*/.exec(rest);
      out.push({ t: m[0], k: "cmt" });
    } else if (rest.startsWith("/*")) {
      const end = sql.indexOf("*/", i + 2);
      const s = end < 0 ? rest : sql.slice(i, end + 2);
      out.push({ t: s, k: "cmt" });
    } else if (c === "'") {
      m = /^'(?:[^']|'')*'?/.exec(rest);
      out.push({ t: m[0], k: "str" });
    } else if (c === '"' || c === "`") {
      const re = c === '"' ? /^"(?:[^"]|"")*"?/ : /^`[^`]*`?/;
      m = re.exec(rest);
      out.push({ t: m[0], k: "id" });
    } else if (/[0-9]/.test(c) || (c === "." && /[0-9]/.test(sql[i + 1] || ""))) {
      m = /^[0-9]*\.?[0-9]+(?:[eE][+-]?[0-9]+)?/.exec(rest);
      out.push({ t: m[0], k: "num" });
    } else if (/[A-Za-z_\u0080-￿]/.test(c)) {
      m = /^[A-Za-z_\u0080-￿][A-Za-z0-9_$\u0080-￿]*/.exec(rest);
      out.push({ t: m[0], k: "word" });
    } else if (c === "?" || c === "$" || c === ":" && /[A-Za-z_]/.test(sql[i + 1] || "")) {
      m = /^(?:\?|\$[0-9]+|:[A-Za-z_][A-Za-z0-9_]*)/.exec(rest) || { 0: c };
      out.push({ t: m[0], k: "param" });
    } else {
      m = /^(?:<=|>=|<>|!=|\|\||::|->>|->|[(),;.*+\-/%=<>&|~^!\[\]{}@#])/.exec(rest) || { 0: c };
      out.push({ t: m[0], k: m[0] === "(" ? "open" : m[0] === ")" ? "close" : m[0] === "," ? "comma" : m[0] === ";" ? "semi" : "op" });
    }
    i += m[0].length;
  }
  // 分類字詞：關鍵字、函式（後面緊接左括號且不是關鍵字）、識別字
  const sig = out.filter((x) => x.k !== "ws");
  sig.forEach((x, j) => {
    if (x.k !== "word") return;
    const up = x.t.toUpperCase();
    const next = sig[j + 1];
    if (KEYWORDS.has(up)) x.k = "kw";
    else if (next && next.k === "open") x.k = "fn";
    else x.k = "id";
  });
  return out;
}

// ---- 樹：括號成組 ----

function buildTree(tokens) {
  const root = { kind: "group", items: [] };
  const stack = [root];
  for (const tk of tokens) {
    if (tk.k === "ws") continue;
    const top = stack[stack.length - 1];
    if (tk.k === "open") {
      const g = { kind: "group", items: [], open: tk };
      top.items.push(g);
      stack.push(g);
    } else if (tk.k === "close" && stack.length > 1) {
      top.close = tk;
      stack.pop();
    } else {
      top.items.push(tk);
    }
  }
  groupCase(root);
  return root;
}
// CASE … END 收成一組，太長時才能把 WHEN、ELSE 各排一行
function groupCase(g) {
  const out = [];
  let i = 0;
  const items = g.items;
  const take = () => {
    const c = { kind: "case", items: [items[i]] };
    i += 1;
    while (i < items.length) {
      const x = items[i];
      if (x.kind === "group") { groupCase(x); c.items.push(x); i += 1; continue; }
      const u = x.t.toUpperCase();
      if (x.k === "kw" && u === "CASE") { c.items.push(take()); continue; }
      c.items.push(x);
      i += 1;
      if (x.k === "kw" && u === "END") break;
    }
    return c;
  };
  while (i < items.length) {
    const x = items[i];
    if (x.kind === "group") { groupCase(x); out.push(x); i += 1; }
    else if (x.k === "kw" && x.t.toUpperCase() === "CASE") out.push(take());
    else { out.push(x); i += 1; }
  }
  g.items = out;
}
function isSub(g) {
  const first = g.items[0];
  return first && !first.kind && first.k === "kw" && /^(SELECT|WITH)$/i.test(first.t);
}
function up(x) {
  return x && !x.kind ? x.t.toUpperCase() : "";
}
function clauseAt(items, i) {
  for (const words of CLAUSES) {
    if (words.every((w, j) => up(items[i + j]) === w)) return words;
  }
  return null;
}

// ---- 排成文字（量長度用）與片段（上色用） ----

function noSpaceBefore(tk) {
  return tk.k === "comma" || tk.k === "semi" || tk.k === "close" || tk.t === "." || tk.t === "::";
}
function noSpaceAfter(tk) {
  return tk.k === "open" || tk.t === "." || tk.t === "::" || tk.k === "fn";
}
function flat(items) {
  const out = [];
  for (const x of items) {
    if (x.kind === "case") {
      out.push(...flat(x.items));
    } else if (x.kind === "group") {
      out.push(x.open || { t: "(", k: "open" });
      out.push(...flat(x.items));
      if (x.close) out.push(x.close);
    } else {
      out.push(x);
    }
  }
  return out;
}
function textOf(tokens) {
  let s = "";
  tokens.forEach((tk, j) => {
    if (j > 0 && !noSpaceBefore(tk) && !noSpaceAfter(tokens[j - 1])) s += " ";
    s += tk.t;
  });
  return s;
}
function hasSub(items) {
  return items.some((x) => (x.kind === "group" && (isSub(x) || hasSub(x.items))) || (x.kind === "case" && hasSub(x.items)));
}

// ---- 排版 ----

function Printer() {
  const lines = [];
  let cur = null;
  return {
    lines,
    start(indent) {
      if (cur && cur.tokens.length) lines.push(cur);
      cur = { indent, tokens: [] };
    },
    add(tokens) {
      if (!cur) cur = { indent: 0, tokens: [] };
      cur.tokens.push(...tokens);
    },
    get cur() { return cur; },
    end() {
      if (cur && cur.tokens.length) lines.push(cur);
      cur = null;
    },
  };
}

function splitTop(items, pred) {
  const parts = [[]];
  let between = false;
  items.forEach((x, j) => {
    const u = up(x);
    if (u === "BETWEEN") between = true;
    if (j > 0 && pred(x)) {
      if (u === "AND" && between) { between = false; parts[parts.length - 1].push(x); return; }
      // 逗號留在上一段的行尾；AND／OR 放在下一段的行首
      if (x.k === "comma") { parts[parts.length - 1].push(x); parts.push([]); return; }
      parts.push([]);
    }
    parts[parts.length - 1].push(x);
  });
  return parts.filter((p) => p.length);
}

// 把一串 items（不含子句關鍵字的換行判斷）接到目前這一行；子查詢與過長的括號另起幾行
// 一組放不下時，依序找切點：最外層的逗號 → AND／OR → 視窗與排序子句（PARTITION BY、ORDER BY、ROWS、RANGE）
function partsOf(items) {
  const byComma = splitTop(items, (y) => y.k === "comma");
  if (byComma.length > 1) return byComma;
  const byBool = splitTop(items, (y) => up(y) === "AND" || up(y) === "OR");
  if (byBool.length > 1) return byBool;
  return splitTop(items, (y, j) => {
    const u = up(y);
    return (u === "ORDER" || u === "PARTITION" || u === "ROWS" || u === "RANGE");
  });
}
function curLength(p, indent) {
  return p.cur && p.cur.tokens.length ? textOf(p.cur.tokens).length + p.cur.indent * 2 + 1 : indent * 2;
}

// 把一串 items 接到目前這一行；子查詢、過長的括號與過長的 CASE 另起幾行
function emitInline(p, items, indent) {
  for (const x of items) {
    if (x.kind === "case") { emitCase(p, x, indent); continue; }
    if (x.kind !== "group") { p.add([x]); continue; }
    const tokensFlat = flat([x]);
    if (isSub(x)) {
      p.add([x.open]);
      emitBlock(p, x.items, indent + 1);
      p.start(indent);
      if (x.close) p.add([x.close]);
      continue;
    }
    const tooLong = curLength(p, indent) + textOf(tokensFlat).length > WIDTH;
    if (!tooLong && !hasSub(x.items)) { p.add(tokensFlat); continue; }
    p.add([x.open]);
    partsOf(x.items).forEach((part) => {
      p.start(indent + 1);
      emitInline(p, part, indent + 1);
    });
    p.start(indent);
    if (x.close) p.add([x.close]);
  }
}

function emitCase(p, c, indent) {
  const tokensFlat = flat([c]);
  if (curLength(p, indent) + textOf(tokensFlat).length <= WIDTH && !hasSub(c.items)) { p.add(tokensFlat); return; }
  // CASE 留在這一行，每個 WHEN 與 ELSE 各一行，END 回到這一層
  const items = c.items;
  p.add([items[0]]);
  let part = [];
  // WHEN 那一段太長時，在 AND／OR 前斷行，再縮一層
  const flush = () => {
    if (!part.length) return;
    p.start(indent + 1);
    if ((indent + 1) * 2 + textOf(flat(part)).length > WIDTH) {
      const bools = splitTop(part, (y) => up(y) === "AND" || up(y) === "OR");
      emitInline(p, bools[0], indent + 1);
      bools.slice(1).forEach((b) => { p.start(indent + 2); emitInline(p, b, indent + 2); });
    } else {
      emitInline(p, part, indent + 1);
    }
    part = [];
  };
  for (let i = 1; i < items.length; i++) {
    const u = up(items[i]);
    if (u === "WHEN" || u === "ELSE") flush();
    if (u === "END" && i === items.length - 1) { flush(); p.start(indent); p.add([items[i]]); return; }
    part.push(items[i]);
  }
  flush();
}

function emitClause(p, name, kwItems, rest, indent) {
  const all = kwItems.concat(rest);
  const fits = !hasSub(rest) && indent * 2 + textOf(flat(all)).length <= WIDTH;
  p.start(indent);
  if (fits) { p.add(flat(all)); return; }
  p.add(kwItems);
  if (LIST_CLAUSES.has(name)) {
    const parts = splitTop(rest, (y) => y.k === "comma");
    if (parts.length > 1) {
      parts.forEach((part) => { p.start(indent + 1); emitInline(p, part, indent + 1); });
      return;
    }
    emitInline(p, rest, indent);
    return;
  }
  if (/JOIN$/.test(name)) {
    const at = rest.findIndex((y) => up(y) === "ON" || up(y) === "USING");
    if (at > 0) {
      emitInline(p, rest.slice(0, at), indent);
      emitCond(p, rest.slice(at, at + 1), rest.slice(at + 1), indent + 1);
      return;
    }
  }
  if (COND_CLAUSES.has(name)) {
    const parts = splitTop(rest, (y) => up(y) === "AND" || up(y) === "OR");
    emitInline(p, parts[0], indent);
    parts.slice(1).forEach((part) => { p.start(indent + 1); emitInline(p, part, indent + 1); });
    return;
  }
  emitInline(p, rest, indent);
}

function emitCond(p, kwItems, rest, indent) {
  const all = kwItems.concat(rest);
  p.start(indent);
  if (!hasSub(rest) && indent * 2 + textOf(flat(all)).length <= WIDTH) { p.add(flat(all)); return; }
  const parts = splitTop(rest, (y) => up(y) === "AND" || up(y) === "OR");
  p.add(kwItems);
  emitInline(p, parts[0], indent);
  parts.slice(1).forEach((part) => { p.start(indent + 1); emitInline(p, part, indent + 1); });
}

function emitBlock(p, items, indent) {
  // 依子句關鍵字與分號切段
  let i = 0;
  let pending = null; // { name, kw: [...], rest: [...] }
  const flush = () => {
    if (pending) emitClause(p, pending.name, pending.kw, pending.rest, indent);
    pending = null;
  };
  while (i < items.length) {
    const x = items[i];
    if (!x.kind && x.k === "semi") {
      if (pending) pending.rest.push(x);
      else { p.start(indent); p.add([x]); }
      flush();
      i += 1;
      continue;
    }
    const words = x.kind ? null : clauseAt(items, i);
    // AS ( 之後的 SELECT 在子查詢組裡，不會走到這裡；WITH 的 CTE 名稱跟在 WITH 後面
    if (words && !(words[0] === "SET" && pending && pending.name === "DO UPDATE SET")) {
      flush();
      const kw = items.slice(i, i + words.length);
      pending = { name: words.join(" "), kw, rest: [] };
      i += words.length;
      continue;
    }
    if (!pending) pending = { name: "", kw: [], rest: [] };
    pending.rest.push(x);
    i += 1;
  }
  flush();
}

// 回傳 [{ indent, tokens:[{t,k}] }]；原文已有換行時照原文的行切開
export function formatSql(sql) {
  const tokens = tokenize(sql);
  if (/\n/.test(sql.trim())) {
    const lines = [];
    let cur = [];
    tokens.forEach((tk) => {
      if (tk.k === "ws" && tk.t.includes("\n")) {
        const segs = tk.t.split("\n");
        cur.push({ t: segs[0], k: "ws" });
        lines.push(cur);
        for (let s = 1; s < segs.length - 1; s++) lines.push([]);
        cur = segs[segs.length - 1] ? [{ t: segs[segs.length - 1], k: "ws" }] : [];
      } else {
        cur.push(tk);
      }
    });
    lines.push(cur);
    return lines.map((toks) => ({ indent: 0, tokens: toks, raw: true }));
  }
  const p = Printer();
  emitBlock(p, buildTree(tokens).items, 0);
  p.end();
  return p.lines;
}

export function lineText(line) {
  return line.raw ? line.tokens.map((t) => t.t).join("") : "  ".repeat(line.indent) + textOf(line.tokens);
}

// 把排好的 SQL 畫進 <code>：每個 token 一個 span（class sqlp-k-<種類>），行尾換行
export function renderSql(codeEl, sql) {
  const doc = codeEl.ownerDocument;
  codeEl.textContent = "";
  formatSql(sql).forEach((line, li) => {
    if (li > 0) codeEl.appendChild(doc.createTextNode("\n"));
    if (line.raw) {
      line.tokens.forEach((tk) => codeEl.appendChild(span(doc, tk)));
      return;
    }
    if (line.indent) codeEl.appendChild(doc.createTextNode("  ".repeat(line.indent)));
    line.tokens.forEach((tk, j) => {
      if (j > 0 && !noSpaceBefore(tk) && !noSpaceAfter(line.tokens[j - 1])) codeEl.appendChild(doc.createTextNode(" "));
      codeEl.appendChild(span(doc, tk));
    });
  });
}
// 只上色、不重排：資料表結構表格裡的型別與約束這類短片段用它
export function highlightInline(el, sql) {
  const doc = el.ownerDocument;
  el.textContent = "";
  tokenize(sql).forEach((tk) => el.appendChild(span(doc, tk)));
}

function span(doc, tk) {
  if (tk.k === "ws") return doc.createTextNode(tk.t);
  const el = doc.createElement("span");
  el.className = "sqlp-k-" + (tk.k === "open" || tk.k === "close" || tk.k === "comma" || tk.k === "semi" ? "op" : tk.k);
  el.textContent = tk.t;
  return el;
}
