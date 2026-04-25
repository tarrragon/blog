---
title: "JS query 範圍限定在元件內"
date: 2026-04-25
weight: 29
description: "JS 操作 DOM 用 `shell.querySelector(...)` 從元件根節點往下找、避免 `document.querySelector` 全文件搜。本文展開 query 縮範圍的方法與好處。"
tags: ["report", "事後檢討", "JavaScript", "DOM", "Refactor", "工程方法論"]
---

## 核心原則

**JS 的 DOM query 從「元件已知根節點」開始、不從 `document` 開始。** 限縮範圍避免未來同頁有第二個同類元件時失控、也避免無關的同名 class 元素被誤命中。

---

## 為什麼縮範圍是 default

### 商業邏輯

`document.querySelector` 是「全頁面搜尋」 — 未來頁面任何地方有同名 class 都可能命中。當前頁面只有一個 pagefind 實例時看不出問題、未來加第二個就壞。

從元件根節點 query = 把 selector 的作用範圍限縮到「我管的子樹」 — 即使未來有同名元素出現在頁面其他地方、也跟我無關。

縮範圍的成本是「多一個變數存元件根」、收益是「未來改頁面結構不影響當前邏輯」。

### Query 範圍的層級

| 範圍   | Selector 寫法                       | 適用情境                 |
| ------ | ----------------------------------- | ------------------------ |
| 全文件 | `document.querySelector(...)`       | Debug、確定全頁只一個    |
| 元件根 | `shell.querySelector(...)`          | 一般情境（推薦預設）     |
| 直接子 | `shell.children[0]` 或 `:scope > X` | 結構穩定、避免深層誤命中 |

`document` 是「便利優先」、元件根是「精準優先」 — 預設選後者。

---

## 這次任務的範圍問題

### 觀察

`search.html` 內多處 query：

```js
var slot   = document.querySelector('.search-filter-slot');
var filter = document.querySelector('.pagefind-ui__filter-panel');
var drawer = document.querySelector('.pagefind-ui__drawer');
var input  = document.querySelector('.pagefind-ui__search-input');
var ui     = document.querySelector('.pagefind-ui');

document.querySelectorAll('.pagefind-ui__result').forEach(...);
```

全部 `document` 開始。當前頁面只有一個 pagefind 實例、可運作；但若未來：

- 同頁加「相關搜尋」widget 也用 pagefind → 多個 `.pagefind-ui` 存在、`document.querySelector` 取到第一個（不一定是我們要的）
- 加 demo 區塊展示「另一個搜尋頁的截圖」帶有 `.pagefind-ui__result` class → query 命中 demo 內容、不該動的被動到

### 判讀

把所有 query 改從 `shell` 根節點開始：

```js
var shell = document.querySelector('.search-shell');
if (!shell) return;

var slot   = document.querySelector('.search-filter-slot');  // slot 在 shell 外、保持 document
var ui     = shell.querySelector('.pagefind-ui');
var filter = shell.querySelector('.pagefind-ui__filter-panel');
var drawer = shell.querySelector('.pagefind-ui__drawer');
var input  = shell.querySelector('.pagefind-ui__search-input');

shell.querySelectorAll('.pagefind-ui__result').forEach(...);
```

`shell` 是 `.search-shell` 元素本身、`shell.querySelector(...)` 只在 shell 子樹內找。

### 例外處理

`.search-filter-slot` 在 `.search-shell` 外（是 main 的另一個直接子）、不能從 shell 找。對這類例外、保留 `document.querySelector` 但加註解：

```js
// slot 是 main 的子節點、跟 shell 同層、不能從 shell 找
var slot = document.querySelector('.search-filter-slot');
```

註解讓維護者知道為什麼這個是例外。

---

## Query 範圍縮減的具體技巧

### 1. 把元件根存成變數一次

```js
var shell = document.querySelector('.search-shell');
if (!shell) return;
// 之後的 query 都從 shell 開始
```

### 2. 用 `:scope` 限縮 querySelector

```js
shell.querySelector(':scope > .pagefind-ui');
// 只找 shell 的直接子、不找深層
```

`:scope` 在 querySelector 裡指 query 的起始元素、可以做「只找直接子」這類精準匹配。

### 3. 函式接受元件根參數

```js
function setupScopeFilter(shell) {
  var input = shell.querySelector('.pagefind-ui__search-input');
  // ...
}
```

把元件根當參數傳入、函式內所有 query 從這個根開始 — 函式可重用於不同元件實例。

### 4. 用 closest 反向查 ancestor

```js
function getShell(el) {
  return el.closest('.search-shell');
}
```

事件處理時、從事件目標反向找元件根 — 多元件實例時各自綁定不會互相干擾。

---

## 內在屬性比較：四種 query 範圍策略

| 策略                            | 隔離度 | 維護成本        | 多元件支援                     |
| ------------------------------- | ------ | --------------- | ------------------------------ |
| `document.querySelector` 全文件 | 低     | 低 — 寫法簡單   | 否 — 只取第一個                |
| 從元件根 `shell.querySelector`  | 中     | 中 — 多一個變數 | 部分 — 一個 shell 用一份 setup |
| 函式接受元件根參數              | 高     | 中              | 是 — 可呼叫多次 setup          |
| 事件 + closest 反向找根         | 最高   | 中              | 是 — 動態多元件                |

優先選「函式接受元件根參數」 — 多元件支援好、未來擴展容易。

---

## 多元件實例的 setup pattern

```js
function setupSearchShell(shell) {
  var ui     = shell.querySelector('.pagefind-ui');
  var input  = shell.querySelector('.pagefind-ui__search-input');
  var drawer = shell.querySelector('.pagefind-ui__drawer');
  // ... 其他 setup
}

document.querySelectorAll('.search-shell').forEach(setupSearchShell);
```

頁面有 N 個 search-shell、自動 setup N 次、各自獨立。當前頁面只一個也適用、未來加更多無痛。

---

## 正確概念與常見替代方案的對照

### Query 從元件根、不從 document

**正確概念**：所有 query 從「我管的元件根節點」開始、限縮範圍。`document.querySelector` 只在「跨元件邊界」時用。

**替代方案的不足**：所有 query 都從 `document` — 未來頁面結構變動可能讓 query 命中不該命中的元素。

### 元件根存成變數重用

**正確概念**：把元件根 query 一次存成變數、之後所有 query 都從這個變數開始。

**替代方案的不足**：每個 query 都從 `document` 找一次 — 重複的 query、效能浪費（雖小）、且範圍仍然是全文件。

### 函式接受元件根參數

**正確概念**：把元件根當函式參數、函式內所有 query 從這個根開始 — 函式可重用於多個元件實例。

**替代方案的不足**：函式內 hardcode `document.querySelector('.shell')` — 只能處理頁面第一個 shell、多實例時其他被忽略。

---

## 判讀徵兆

| 訊號                                        | Refactor 動作                           |
| ------------------------------------------- | --------------------------------------- |
| JS 內多處 `document.querySelector` 同類元素 | 把元件根存變數、之後 query 從變數開始   |
| 同頁加第二個元件實例後行為錯亂              | 改用「函式接受根參數」pattern           |
| Selector 命中了不該命中的元素               | 縮範圍到元件內、加 `:scope` 必要時      |
| 事件處理時不知道是哪個元件實例觸發的        | 用 `event.target.closest(...)` 反向找根 |

**核心原則**：JS query 的範圍是 sanity 防線。從元件根開始、即使當前只有一個元件、未來擴展也不需要重寫。
