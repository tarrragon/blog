// 拿題庫全部選項的 SQL 跑 assets/js/sql-format.js 的排版，檢查兩件事：
// 1. token 順序不變：排版前後去掉空白的 token 序列逐一相同（排版只動空白與換行）
// 2. 行長：列出超過 WIDTH 的行數與最長的幾行，供調整規則時對照
// 用法：node scripts/sql-practice/ui/check_sql_format.mjs [--show <variantId>]
// 結尾印 `checked N option(s), M token mismatch(es), K line(s) over WIDTH`；M 不是 0 時 exit 1。
import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const { formatSql, lineText, tokenize, WIDTH } = await import(join(here, "../../../assets/js/sql-format.js"));
const qdir = join(here, "../questions");
const show = process.argv.includes("--show") ? process.argv[process.argv.indexOf("--show") + 1] : null;

let n = 0, mismatch = 0, over = 0, prose = 0;
const longest = [];
for (const f of readdirSync(qdir).filter((x) => x.endsWith(".json") && x !== "manifest.json")) {
  for (const q of JSON.parse(readFileSync(join(qdir, f), "utf8"))) {
    for (const o of q.options) {
      n += 1;
      const lines = formatSql(o.sql);
      const before = tokenize(o.sql).filter((t) => t.k !== "ws").map((t) => t.t);
      const after = tokenize(lines.map(lineText).join("\n")).filter((t) => t.k !== "ws").map((t) => t.t);
      if (before.join("\u0001") !== after.join("\u0001")) {
        mismatch += 1;
        console.log(`MISMATCH ${q.variantId}/${o.key}`);
      }
      // 整段是 -- 註解的選項是文字描述的設計方案，練習頁用一般文字顯示，不算行長
      if (/^\s*--/.test(o.sql) && !o.sql.trim().includes("\n")) { prose += 1; continue; }
      for (const l of lines) {
        const t = lineText(l);
        if (t.length > WIDTH) { over += 1; longest.push([t.length, `${q.variantId}/${o.key}`, t]); }
      }
      if (show && q.variantId === show) {
        console.log(`--- ${o.key}`);
        console.log(lines.map(lineText).join("\n"));
      }
    }
  }
}
longest.sort((a, b) => b[0] - a[0]);
for (const [len, id, t] of longest.slice(0, 12)) console.log(`${len}\t${id}\t${t}`);
console.log(`checked ${n} option(s), ${prose} prose option(s), ${mismatch} token mismatch(es), ${over} line(s) over ${WIDTH}`);
process.exit(mismatch ? 1 : 0);
