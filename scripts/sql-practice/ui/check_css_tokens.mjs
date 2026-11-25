// 檢查練習頁的 CSS 只透過 token 取值，擋住三種寫法：
// 1. !important：用提高優先度蓋掉別的規則，下一次調整時又要再蓋一次
// 2. font-size／line-height 寫 px、rem 或 pt：字級要用功能字級 --sqlp-t-*／--sqlp-lh-*（em 這類相對值可以）
// 3. 色碼與 rgb()／rgba()／hsl()：顏色要用 --sqlp-* 顏色 token
// 自訂屬性（--sqlp-…: 值）的宣告就是 token 的定義，不檢查。讀不到 token 的位置（例如 #sql-practice 外面的 body）
// 在同一行加註解 `sqlp-lint: allow`，並在註解裡寫原因。
// 用法：node scripts/sql-practice/ui/check_css_tokens.mjs [檔案...]（預設 assets/sql-practice/practice.css）
// 結尾印 `checked N declaration(s), M violation(s)`；M 不是 0 時 exit 1，沒有讀到任何宣告時 exit 2。
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const files = process.argv.slice(2).length ? process.argv.slice(2) : [join(here, "../../../assets/sql-practice/practice.css")];

let checked = 0;
const violations = [];
for (const file of files) {
  const lines = readFileSync(file, "utf8").split("\n");
  let inComment = false;
  let prop = null; // 跨行的值（多行的 background）沿用上一行的屬性名稱
  lines.forEach((raw, i) => {
    const allow = raw.includes("sqlp-lint: allow");
    // 去掉註解，保留程式碼部分
    let code = "";
    for (let j = 0; j < raw.length; j++) {
      if (inComment) {
        if (raw.startsWith("*/", j)) { inComment = false; j++; }
      } else if (raw.startsWith("/*", j)) {
        inComment = true; j++;
      } else {
        code += raw[j];
      }
    }
    // 選擇器與 @media 條件在最後一個 { 之前，宣告在它之後
    const body = code.includes("{") ? code.slice(code.lastIndexOf("{") + 1) : code;
    if (code.includes("{")) prop = null;
    for (const seg of body.split(/[;}]/)) {
      const s = seg.trim();
      if (!s) continue;
      const m = s.match(/^([-a-z]+)\s*:(.*)$/);
      let value;
      if (m) { prop = m[1]; value = m[2]; } else if (prop) { value = s; } else { continue; }
      if (prop.startsWith("--")) continue;
      checked += 1;
      if (allow) continue;
      const where = `${file.replace(/^.*?assets\//, "assets/")}:${i + 1}`;
      if (/!\s*important/.test(value)) violations.push(`${where}: !important in ${prop}`);
      if (/^(font-size|line-height)$/.test(prop) && /\d(px|rem|pt)\b/.test(value)) violations.push(`${where}: ${prop} uses a raw length (${value.trim()}); use --sqlp-t-* / --sqlp-lh-*`);
      if (/#[0-9a-fA-F]{3,8}\b|\b(rgba?|hsla?)\(/.test(value)) violations.push(`${where}: ${prop} uses a raw color (${value.trim()}); use a --sqlp-* color token`);
    }
    if (body.includes("}")) prop = null;
  });
}
for (const v of violations) console.log(v);
console.log(`checked ${checked} declaration(s), ${violations.length} violation(s)`);
process.exit(checked === 0 ? 2 : violations.length ? 1 : 0);
