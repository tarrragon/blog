---
title: "Selector 精準度：讓 query 只命中你想要的元素"
date: 2026-04-25
weight: 14
description: "JS 的 DOM query 是 sanity 防線、不是優化選項。從『起點 / 範圍 / 過濾』三層收斂、避免誤命中、避免未來頁面結構變動讓 query 撈到不該撈的東西。本文是 selector 設計的完整指引。"
tags: ["report", "事後檢討", "JavaScript", "DOM", "工程方法論"]
---

## 核心原則

**JS 的 DOM query 從具體開始、發現不夠用再放寬。** Selector 涵蓋「最少必要範圍」、避免誤命中其他元素、避免未來頁面結構變動讓 query 撈到不該撈的東西。精準度有三個收斂維度：起點（從哪開始找）、範圍（找多深）、過濾（哪些不要）— 三者一起設計才完整。

---

## 為什麼精準度是 default

### 商業邏輯

DOM selector 的範圍越寬、被誤命中的可能性越高。寬泛 selector 像「網撈」 — 當下頁面只有一個目標元素時看不出問題、未來頁面結構變動（加第二個同類元件、加 demo 區塊、加 widget）就壞。

精準度的成本是「寫 selector 時多想一點」、收益是「行為可預測、不會被未來變動打破」。**這不是優化、是 sanity 防線**。

### 寬泛 selector 的失敗模式

| 失敗模式           | 表現                             | 根因                         |
| ------------------ | -------------------------------- | ---------------------------- |
| 跨元件誤命中       | 該動的動了、不該動的也動了       | 沒指定 ancestor scope        |
| 同名 class 誤命中  | demo 區塊 / 文檔截圖也被處理     | 沒過濾「處於展示用途」的元素 |
| 未初始化元素被處理 | 元件還沒 mount 完就被操作        | 沒過濾「狀態未就緒」的元素   |
| 已處理元素重複處理 | apply 被 observer 觸發又處理一次 | 沒標記「已處理」             |

四種失敗都來自「query 範圍 > 真實需要的範圍」。從具體開始就避免。

---

## 三層收斂維度

Selector 精準度不是單一參數、是三個維度的組合。每個維度都該設計、不能只想其中一個。

### 維度 1：起點（從哪個 root 開始找）

**核心定義**：query 的起點決定「最大可能範圍」。從 `document` 起 = 全頁面；從元件根起 = 子樹內。

```js
// 寬：全頁面搜尋
document.querySelector('.pagefind-ui__result');

// 收斂：從元件根開始
var shell = document.querySelector('.search-shell');
shell.querySelector('.pagefind-ui__result');
```

從元件根開始等於把 selector 的作用範圍收斂到「我管的子樹」 — 即使未來頁面其他地方出現同名元素、跟我無關。

**起點選擇的決策**：

| 起點                    | 適用情境                                 |
| ----------------------- | ---------------------------------------- |
| `document`              | 確定全頁只有一個目標、且未來不會增加同類 |
| 元件根（變數存好）      | 一般情境（推薦預設）                     |
| 函式參數傳入根          | 同頁面有多個元件實例、各自獨立 setup     |
| 事件 `closest` 反向找根 | 動態多實例、用事件驅動                   |

**多元件 setup pattern**：

```js
function setupSearchShell(shell) {
  var ui     = shell.querySelector('.pagefind-ui');
  var input  = shell.querySelector('.pagefind-ui__search-input');
  var drawer = shell.querySelector('.pagefind-ui__drawer');
  // ... 其他 setup
}

document.querySelectorAll('.search-shell').forEach(setupSearchShell);
```

頁面有 N 個 shell、自動 setup N 次、各自獨立。當前只一個也適用、未來加更多無痛 — 這是「起點當參數」帶來的擴展性。

**例外處理**：當目標元素不在元件子樹內（例如同層的 sibling），保留 `document.querySelector` 但加註解說明：

```js
// slot 是 main 的子節點、跟 shell 同層、不能從 shell 找
var slot = document.querySelector('.search-filter-slot');
```

註解讓未來維護者知道這是「明知故為」的例外、不是疏忽。

### 維度 2：範圍（找多深）

**核心定義**：起點確定後、要找直接子、特定層、還是任意深度。

`querySelector` 預設找任意深度 — 大部分情況沒問題、但結構穩定時可以更精準：

```js
// 預設：任意深度
shell.querySelector('.pagefind-ui');

// 限縮：只找直接子
shell.querySelector(':scope > .pagefind-ui');

// 限縮：只找特定層
shell.querySelector(':scope > div > .pagefind-ui');
```

`:scope` 在 querySelector 內表示 query 的起始元素 — 配合 `>` 就能精準匹配「直接子」。

**範圍選擇的決策**：

| 範圍                      | 適用情境                           |
| ------------------------- | ---------------------------------- |
| 任意深度（預設）          | 結構可能變動、目標可能搬位置       |
| 直接子 `:scope > X`       | 結構穩定、避免深層誤命中           |
| 特定路徑 `:scope > A > B` | 結構非常穩定、想要結構變動立即察覺 |

選太寬未來誤命中、選太窄未來結構微調就壞 — 預設選任意深度、結構穩定的關鍵 query 才用 `:scope >`。

### 維度 3：過濾（哪些元素不要）

**核心定義**：起點 + 範圍確定後、可能還是命中過多 — 用 attribute filter 與否定 selector 排除不要的。

```js
// 寬：所有 result
shell.querySelectorAll('.pagefind-ui__result');

// 過濾：只取已 rank 過的（排除初始化中的）
shell.querySelectorAll('.pagefind-ui__result[data-pagefind-rank]');

// 過濾：排除已處理過的
shell.querySelectorAll('.pagefind-ui__result:not([data-scoped])');
```

**過濾技巧**：

| 技巧             | 用法                                                         |
| ---------------- | ------------------------------------------------------------ |
| Attribute filter | `[data-state="ready"]` 只取狀態就緒的                        |
| `:not()` 排除    | `:not([data-scoped])` 排除已處理                             |
| Attribute exists | `[data-pagefind-rank]` 只取有特定屬性的                      |
| 處理後標記       | 處理完 `el.setAttribute('data-scoped', 'true')` 避免重複處理 |

**「處理後標記」是 idempotency 工具**：apply 函式可能被多次呼叫（observer 觸發、event 觸發），標記 + `:not()` 過濾確保每個元素只處理一次。

---

## 三維度的組合範例

完整的精準 selector 設計：

```js
var shell = document.querySelector('.search-shell');           // 維度 1：起點
if (!shell) return;

var results = shell.querySelectorAll(                          // 維度 2：任意深度
  '.pagefind-ui__result[data-pagefind-rank]:not([data-scoped])'  // 維度 3：過濾
);

results.forEach(function (el) {
  // ... 處理
  el.setAttribute('data-scoped', 'true');                      // 處理後標記
});
```

每個維度都有意識地選擇 — 不是把所有預設值疊一起。

---

## 內在屬性比較：四種 selector 設計

| 設計                                 | 誤命中風險 | 未來結構變動的容忍度    | 多元件支援       |
| ------------------------------------ | ---------- | ----------------------- | ---------------- |
| `document.querySelector('.x')`       | 高         | 低 — 任何同名出現就壞   | 否（只取第一個） |
| `shell.querySelector('.x')`          | 低         | 中 — shell 內變動才影響 | 部分             |
| `shell.querySelector(':scope > .x')` | 最低       | 低 — 結構微調就壞       | 部分             |
| 起點當參數 + 過濾 + 標記             | 最低       | 高 — 顯式聲明所有假設   | 完整             |

**推薦**：起點當參數 + 過濾。`:scope >` 只在「結構保證穩定」的關鍵 query 用。

---

## 進階技巧

### 1. 把元件根存成變數一次

```js
var shell = document.querySelector('.search-shell');
if (!shell) return;
// 之後所有 query 都從 shell 開始
```

避免每次 query 都重新從 document 找元件根 — 一是效能（小）、二是 query 範圍仍維持在 shell 內。

### 2. 用 closest 反向找根

```js
function getShell(el) {
  return el.closest('.search-shell');
}

document.addEventListener('click', function (e) {
  var shell = getShell(e.target);
  if (!shell) return;
  // 在這個 shell 內處理
});
```

事件委派 + closest 適合「多元件實例 + 動態事件處理」 — 各 shell 不需要各自綁 listener、共用一個 listener 用 closest 區分。

### 3. 起點不存在時提早 return

```js
var shell = document.querySelector('.search-shell');
if (!shell) return;
```

頁面可能沒有 shell（不是搜尋頁），所有後續 query 都會失敗。提早 return 比後續一連串 null check 乾淨。

### 4. WeakMap 替代 attribute 標記

當不想污染 DOM attribute 時、用 WeakMap 紀錄已處理的元素：

```js
var processed = new WeakMap();

shell.querySelectorAll('.pagefind-ui__result').forEach(function (el) {
  if (processed.has(el)) return;
  // ... 處理
  processed.set(el, true);
});
```

WeakMap 在元素 GC 時自動清理、不留下 DOM 痕跡。適合短生命週期的 idempotency。

---

## 設計取捨：起點選擇

Selector 的「起點」有四種做法、各自機會成本不同。這個專案選 B（元件根存變數）當預設、其他做法在特定情境也合理。每張卡片獨立展開該做法的設計細節。

### A：[`document.querySelector` 全文件搜](../pattern-document-query/)

- **機制**：每處 query 都從 document 開始、靠 class name 唯一性命中目標
- **適合**：原型階段、demo 程式碼、確定全頁只有一個目標且未來不會變
- **代價**：未來頁面結構變動（加同類 widget、加 demo 區塊）就壞、且失敗模式是安靜地操作錯元素、不報錯
- **選 A 的時機**：「快速看會不會動」的探索期

### B：[元件根存變數、之後從變數 query](../pattern-component-root/)（這個專案的預設）

- **機制**：`var shell = document.querySelector('.search-shell')` 一次、之後所有 query 用 `shell.querySelector(...)`
- **選 B 的理由**：當前頁面只有一個 shell、未來可能加（站內搜尋 widget、相關搜尋）— 用變數隔離成本低、提早預防
- **適合**：一般客製情境、預期未來結構可能擴展
- **代價**：多一個變數、多一次 query;函式內邏輯變得依賴外部變數

### C：[函式接受元件根當參數](../pattern-root-as-parameter/)

- **機制**：`function setup(shell) { shell.querySelector(...) }`、外部呼叫 `document.querySelectorAll('.shell').forEach(setup)`
- **跟 B 的取捨**：B 假設只有一個 shell、C 直接支援多 shell；C 的設計成本前期較高（每函式多一個參數）、但多實例支援是免費的
- **C 比 B 好的情境**：頁面同時有多個 shell（例如多語切換頁面）、或計劃中要重用組件到不同頁面

### D：[事件 + `closest` 反向找根](../pattern-closest-lookup/)

- **機制**：監聽全域事件、事件處理時 `e.target.closest('.shell')` 反向找元件根
- **跟 B/C 的取捨**：B/C 是「初始化時綁定」、D 是「事件發生時動態判斷」— D 適合元件動態出現 / 消失（SPA 路由切換、AJAX 注入）
- **D 比 C 好的情境**：元件實例在 runtime 動態增減、用 mutation observer 補打成本反而更高
- **代價**：事件委派的調試比直接綁定難（不知道事件實際從哪傳上來）

---

## 設計取捨：範圍深度

`querySelector` 預設找任意深度、可以收緊到直接子。三種做法：

### A：任意深度（這個專案的預設）

- **機制**：`shell.querySelector('.target')` — 子樹任何深度都接受
- **選 A 的理由**：結構可能因 framework 升級微調、容忍微調換取維護彈性
- **代價**：深層結構意外多出同名元素時可能誤命中

### B：直接子 `:scope > X`

- **機制**：`shell.querySelector(':scope > .target')` — 只找直接子
- **跟 A 的取捨**：A 容忍結構微調、B 強制結構穩定 — B 帶來「結構變動立即報錯」的早期偵測
- **B 比 A 好的情境**：自家完全控制的結構、想用 selector 失敗當回歸測試訊號

### C：特定路徑 `:scope > A > B`

- **機制**：強制一條精確路徑
- **代價**：結構任何微調都壞、維護成本高
- **C 才合理的情境**：寫整合測試的結構斷言、不是 production query

---

## 設計取捨：過濾與 idempotency

apply 函式可能被多次觸發（observer / event / 初始化）、過濾保證每元素只處理一次。三種做法：

### A：[DOM attribute 標記](../pattern-attribute-idempotency-marker/)（這個專案的預設）

- **機制**：`:not([data-scoped])` 過濾 + 處理後 `el.setAttribute('data-scoped', 'true')`
- **選 A 的理由**：標記跟著 DOM 元素走、元素被移除時自動清理；標記在 devtools 可見、debug 直接
- **代價**：DOM 上多了一個自家用的 attribute（命名衝突風險小）

### B：[WeakMap 紀錄](../pattern-weakmap-idempotency-record/)

- **機制**：`var processed = new WeakMap(); processed.set(el, true)`
- **跟 A 的取捨**：B 不污染 DOM、適合「不想留 attribute 痕跡」的場景；A 在 devtools 可見、debug 較直接
- **B 比 A 好的情境**：寫成第三方函式庫、不想對使用者 DOM 加屬性

### C：依賴外部呼叫者保證只呼叫一次

- **機制**：apply 內不防護、依賴 init 時只綁一次 listener
- **成本特別高的原因**：observer 觸發 / 事件觸發 / 初始化任一處多呼叫、就產生重複處理 bug；錯誤難以追蹤
- **C 才合理的情境**：apply 本身是 idempotent 的（例如 set class 設成已是的值、無副作用）— 此時不需過濾

---

## 判讀徵兆

| 訊號                                   | Selector 精準度問題 | 修正動作                                 |
| -------------------------------------- | ------------------- | ---------------------------------------- |
| 多處 `document.querySelector` 同類元素 | 起點太寬            | 把元件根存變數、之後 query 從變數開始    |
| 同頁加第二個元件實例後行為錯亂         | 起點 hardcode       | 改「起點當參數」pattern                  |
| Selector 命中了不該命中的元素          | 範圍 / 過濾不足     | 加 ancestor scope、或加 attribute filter |
| Apply 被多次呼叫產生重複處理           | 沒 idempotency 防線 | 加 `:not([data-flag])` + 處理後標記      |
| 結構微調後 selector 失效               | `:scope >` 用得太死 | 換成任意深度（預設）                     |
| 事件處理時不知是哪個元件實例           | 沒反向找根機制      | 用 `closest`                             |

**核心原則**：Selector 精準度不是極致最佳化、是 sanity 防線。三維度（起點 / 範圍 / 過濾）一起設計、每個維度都顯式選擇 — 比從寬泛開始一路追 bug 容易得多。

寬 selector（`querySelectorAll('.title')`）是「便利位置」、窄 selector 是「對齊位置」 — 這個反相關的更高層原則見 [#67 寫作便利度跟意圖對齊反相關](../ease-of-writing-vs-intent-alignment/)。
