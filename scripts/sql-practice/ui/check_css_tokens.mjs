// 檢查練習頁的 CSS 只透過 token 取值，擋住這幾種寫法：
// 1. !important：用提高優先度蓋掉別的規則，下一次調整時又要再蓋一次
// 2. font-size／line-height 寫 px、rem 或 pt，以及 font 簡寫裡寫 px、rem 或 pt 的字級：
//    字級要用功能字級 --sqlp-t-*／--sqlp-lh-*（em 這類相對值可以）
// 3. 寫死的顏色：色碼、色彩函式（rgb()、hsl()、hwb()、lab()、lch()、oklab()、oklch()、color()、color-mix()），
//    以及顏色屬性裡的色名（white、black……；transparent、currentColor、inherit 這類關鍵字放行）。顏色要用 --sqlp-* 顏色 token
// 4. 選擇器裡、:where() 以外的 id（#sql-practice 這類）：id 的特定性高過所有 class 規則，
//    只替部分規則加 id 會打亂元件內部的勝負。包在 :where() 裡的 id 特定性是 0，不擋
// 5. 字級的兩層：tokens.css 以外直接引用尺寸階 var(--sqlp-size-*)（元件只引用功能字級 --sqlp-t-*），
//    以及功能字級 --sqlp-t-* 的值不是引用尺寸階（寫成字面值時，整階調整改不到它）
// 6. tokens.css 以外定義自訂屬性時寫字面值（.a { --x: #123; color: var(--x) } 會繞過 1–3）：
//    tokens.css 以外的自訂屬性只能引用別的 token（值裡有 var()）
// 自訂屬性（--…: 值）的宣告就是 token 的定義，不套 1–3（token 定義裡的 !important 也不擋），另外計數。
// tokens.css 的豁免（第 5、6 項）看檔名，所以傳暫存檔進來的呼叫端（pre-commit）要讓暫存檔保留原檔名。
// 例外寫在同一行的註解裡，兩種，都要在後面寫出它對到哪一種例外：
//   `sqlp-lint: allow <原因>`：這一行的宣告不套 1–3（讀不到 token 的位置，例如 #sql-practice 外面的 body）；第 5、6 項照樣檢查
//   `sqlp-lint: allow-id <原因>`：這一行的選擇器不套 4（練習區根元素自己的規則，例如在根元素上定義 token）
//   沒寫原因的允許註解本身算一處違規。每一處允許註解都逐行印出（`allowed: …`），數量印在結尾，
//   豁免增加時讀輸出的人看得到。
// 限制：逐行讀，每一行只把最後一個 { 之前當成選擇器、之後當成宣告；一行寫兩條以上規則、
// 選擇器清單跨行、壓縮過的 CSS、Sass 原始檔都讀不完整（at-rule 與一條規則寫在同一行時，取 at-rule 的 { 之後當選擇器）。
// 只讀 CSS 檔，模板的 style 屬性與 JavaScript 設定的樣式不在範圍內。
// 沒有量過的寫法：var() 的 fallback 裡的色名、filter 函式裡的顏色、COLOR_PROP 以外屬性的色名、系統色、px／rem／pt 以外的絕對單位。
// 用法：node scripts/sql-practice/ui/check_css_tokens.mjs [檔案...]
//（預設檢查 assets/sql-practice/ 的 tokens.css、practice.css、callout.css 與 assets/practice/hub.css）
// 結尾印 `checked N declaration(s), T token definition(s), S selector line(s), A allowed line(s), M violation(s)`；
// M 不是 0 時 exit 1；有檔案讀不到，或有一份檔案一個宣告與 token 定義都沒讀到時 exit 2。
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const assets = join(here, "../../../assets");
const files = process.argv.slice(2).length ? process.argv.slice(2)
  : ["sql-practice/tokens.css", "sql-practice/practice.css", "sql-practice/callout.css", "practice/hub.css"].map((f) => join(assets, f));

// CSS Color Module Level 4 的色名（不含 transparent、currentcolor 這類關鍵字）
const NAMED = new Set(("aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue blueviolet brown " +
  "burlywood cadetblue chartreuse chocolate coral cornflowerblue cornsilk crimson cyan darkblue darkcyan darkgoldenrod " +
  "darkgray darkgreen darkgrey darkkhaki darkmagenta darkolivegreen darkorange darkorchid darkred darksalmon darkseagreen " +
  "darkslateblue darkslategray darkslategrey darkturquoise darkviolet deeppink deepskyblue dimgray dimgrey dodgerblue " +
  "firebrick floralwhite forestgreen fuchsia gainsboro ghostwhite gold goldenrod gray green greenyellow grey honeydew " +
  "hotpink indianred indigo ivory khaki lavender lavenderblush lawngreen lemonchiffon lightblue lightcoral lightcyan " +
  "lightgoldenrodyellow lightgray lightgreen lightgrey lightpink lightsalmon lightseagreen lightskyblue lightslategray " +
  "lightslategrey lightsteelblue lightyellow lime limegreen linen magenta maroon mediumaquamarine mediumblue mediumorchid " +
  "mediumpurple mediumseagreen mediumslateblue mediumspringgreen mediumturquoise mediumvioletred midnightblue mintcream " +
  "mistyrose moccasin navajowhite navy oldlace olive olivedrab orange orangered orchid palegoldenrod palegreen " +
  "paleturquoise palevioletred papayawhip peachpuff peru pink plum powderblue purple rebeccapurple red rosybrown " +
  "royalblue saddlebrown salmon sandybrown seagreen seashell sienna silver skyblue slateblue slategray slategrey snow " +
  "springgreen steelblue tan teal thistle tomato turquoise violet wheat white whitesmoke yellow yellowgreen").split(" "));
// 值裡會出現顏色的屬性；其他屬性的值裡出現同一個字（例如字型名）不算色名
const COLOR_PROP = /^(color|background(-color|-image)?|border(-(top|right|bottom|left|block|inline)(-(start|end))?)?(-color)?|outline(-color)?|box-shadow|text-shadow|text-decoration(-color)?|column-rule(-color)?|caret-color|accent-color|fill|stroke|scrollbar-color)$/;
const COLOR_FN = /\b(rgba?|hsla?|hwb|lab|lch|oklab|oklch|color|color-mix)\(/;
const ALLOW = /sqlp-lint:\s*allow(-id)?\b(.*?)(\*\/|$)/g;

let checked = 0;
let selectorLines = 0;
const violations = [];
let tokenDefs = 0;
let emptyFile = false;
const allowed = [];
const isTokens = (f) => /(^|\/)tokens\.css$/.test(f);
for (const file of files) {
  let text;
  try { text = readFileSync(file, "utf8"); } catch (e) {
    console.log(`cannot read ${file}: ${e.code || e.message}`);
    process.exit(2);
  }
  const lines = text.split("\n");
  const before = checked + tokenDefs;
  let inComment = false;
  let prop = null; // 跨行的值（多行的 background）沿用上一行的屬性名稱
  lines.forEach((raw, i) => {
    const where = `${file.replace(/^.*?assets\//, "assets/")}:${i + 1}`;
    let allowDecl = false;
    let allowId = false;
    for (const m of raw.matchAll(ALLOW)) {
      const reason = m[2].replace(/^[\s:—–-]+/, "").trim();
      if (!reason) violations.push(`${where}: sqlp-lint: allow${m[1] || ""} without a reason`);
      else allowed.push(`allowed: ${where}: allow${m[1] || ""} ${reason}`);
      if (m[1]) allowId = true; else allowDecl = true;
    }
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
    if (code.includes("{")) {
      let head = code.slice(0, code.lastIndexOf("{")).trim();
      // `@media (…) { .a {` 寫在同一行時，at-rule 的 { 之後才是選擇器
      if (head.startsWith("@")) head = head.includes("{") ? head.slice(head.lastIndexOf("{") + 1).trim() : "";
      if (head) {
        selectorLines += 1;
        // :where(...) 的特定性是 0，拿掉之後還有 # 才算加權（:where 裡最多再巢狀兩層括號）；
        // 屬性選擇器的字串（a[href="#main"]）不是 id，先拿掉
        const weighted = head.replace(/\[[^\]]*\]/g, "").replace(/:where\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*\)/g, "");
        if (/#[A-Za-z_-]/.test(weighted) && !allowId) violations.push(`${where}: id selector outside :where() (${head}); drop the id or wrap it in :where() (both change which rule wins: re-run the computed-style snapshot diff), or add sqlp-lint: allow-id <reason>`);
      }
    }
    const body = code.includes("{") ? code.slice(code.lastIndexOf("{") + 1) : code;
    if (code.includes("{")) prop = null;
    for (const seg of body.split(/[;}]/)) {
      const s = seg.trim();
      if (!s) continue;
      const m = s.match(/^([-a-z]+)\s*:(.*)$/);
      let value;
      if (m) { prop = m[1]; value = m[2]; } else if (prop) { value = s; } else { continue; }
      if (prop.startsWith("--")) {
        tokenDefs += 1;
        if (/^--sqlp-t-/.test(prop) && !/var\(--sqlp-size-/.test(value)) violations.push(`${where}: ${prop} does not reference the size scale (${value.trim()}); use var(--sqlp-size-*)`);
        if (!isTokens(file) && !/var\(--/.test(value)) violations.push(`${where}: custom property ${prop} defined with a literal outside tokens.css (${value.trim()}); define the token in tokens.css or reference one with var()`);
        continue;
      }
      checked += 1;
      if (!isTokens(file) && /var\(--sqlp-size-/.test(value)) violations.push(`${where}: ${prop} references the size scale directly (${value.trim()}); use a --sqlp-t-* token`);
      if (allowDecl) continue;
      if (/!\s*important/.test(value)) violations.push(`${where}: !important in ${prop}`);
      if (/^(font-size|line-height)$/.test(prop) && /\d(px|rem|pt)\b/.test(value)) violations.push(`${where}: ${prop} uses a raw length (${value.trim()}); use --sqlp-t-* / --sqlp-lh-*`);
      if (prop === "font" && /\d(px|rem|pt)\b/.test(value)) violations.push(`${where}: font shorthand uses a raw size (${value.trim()}); set font-size / line-height from --sqlp-t-* / --sqlp-lh-*`);
      // url(#id) 的片段識別碼不是色碼，比對色碼之前先拿掉 url(...)
      if (/#[0-9a-fA-F]{3,8}\b/.test(value.replace(/url\([^)]*\)/g, "")) || COLOR_FN.test(value)) violations.push(`${where}: ${prop} uses a raw color (${value.trim()}); use a --sqlp-* color token`);
      if (COLOR_PROP.test(prop)) {
        const word = value.toLowerCase().replace(/var\([^)]*\)/g, "").replace(/url\([^)]*\)/g, "").match(/[a-z]+/g)?.find((w) => NAMED.has(w));
        if (word) violations.push(`${where}: ${prop} uses a color name (${word}); use a --sqlp-* color token`);
      }
    }
    if (body.includes("}")) prop = null;
  });
  if (checked + tokenDefs === before) {
    console.log(`${file}: no declarations or token definitions read`);
    emptyFile = true;
  }
}
for (const a of allowed) console.log(a);
for (const v of violations) console.log(v);
console.log(`checked ${checked} declaration(s), ${tokenDefs} token definition(s), ${selectorLines} selector line(s), ${allowed.length} allowed line(s), ${violations.length} violation(s)`);
process.exit(emptyFile ? 2 : violations.length ? 1 : 0);
