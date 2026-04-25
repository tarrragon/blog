---
title: "Init function 是 orchestrator、職責拆出獨立 function"
date: 2026-04-25
weight: 31
description: "一個 init function 同時做多件事 → 按職責拆成多個獨立函式、各自有清楚的 input / output、init 退化為組合各職責的 orchestrator。Debug 時知道哪個壞了、也容易單獨重用。"
tags: ["report", "事後檢討", "JavaScript", "Refactor", "工程方法論"]
---

## 核心原則

**單一函式做 ≥ 3 件無關的事就拆。** 每個函式只負責一個職責、有明確的 input / output、可以獨立 debug 與測試。Init function 變成「組合各職責 function 的 orchestrator」。

---

## 為什麼拆函式

### 商業邏輯

單一函式做多件事的成本：

| 規模                    | 維護痛點                          |
| ----------------------- | --------------------------------- |
| 一函式 50 行做 1 件事   | 低 — 容易讀、職責清楚             |
| 一函式 100 行做 3 件事  | 中 — 邏輯交織、debug 要分辨哪段   |
| 一函式 200 行做 5+ 件事 | 高 — 沒人想動、改一處可能影響別處 |

拆函式的成本是「多寫幾個函式名與簽名」、收益是「每個函式範圍小、debug 容易、可單獨重用」。

### 拆的依據是「職責」、不是行數

| 拆法                 | 結果                       |
| -------------------- | -------------------------- |
| 按行數機械拆         | 切出沒邏輯意義的片段、更亂 |
| 按職責拆             | 每個函式名能描述「做什麼」 |
| 按 input / output 拆 | 函式變得 testable、可組合  |

按職責拆的判斷：能不能用一個動詞片語描述函式做什麼？做不到 → 多個職責、該拆。

---

## 這次任務的拆分機會

### 觀察

`setupScopeFilter()` 現況做 5 件事：

```js
function setupScopeFilter() {
  // 1. 找元素
  var scopeEl = document.querySelector('.search-scope');
  var input   = document.querySelector('.pagefind-ui__search-input');
  // ...

  // 2. 量測 scope 高度寫回 CSS 變數
  function syncScopeHeight() { ... }
  syncScopeHeight();
  new ResizeObserver(syncScopeHeight).observe(scopeEl);

  // 3. 把 filter-panel 搬到 sidebar (position function)
  function place() { ... }

  // 4. 註冊 scope filter listener + apply
  function apply() { ... }
  scopeEl.addEventListener('change', apply);
  // ...

  // 5. Reorder filter blocks
  function reorderFilters() { ... }
  reorderFilters();
}
```

5 個職責塞在一個函式：找元素、量高度、搬 slot、scope filter、reorder filter。

### 判讀

按職責拆成獨立函式：

```js
function findSearchElements(shell) {
  return {
    shell:  shell,
    ui:     shell.querySelector('.pagefind-ui'),
    input:  shell.querySelector('.pagefind-ui__search-input'),
    drawer: shell.querySelector('.pagefind-ui__drawer'),
    filter: shell.querySelector('.pagefind-ui__filter-panel'),
    scope:  shell.querySelector('.search-scope'),
  };
}

function syncScopeHeight(scopeEl) {
  function update() {
    var h = scopeEl.offsetHeight || 56;
    document.body.style.setProperty('--search-scope-h', h + 'px');
  }
  update();
  new ResizeObserver(update).observe(scopeEl);
}

function setupFilterSlotSwap(filter, drawer, slot, breakpoint) {
  var mql = window.matchMedia('(min-width: ' + breakpoint + 'px)');
  function place() {
    if (mql.matches) slot.appendChild(filter);
    else drawer.insertBefore(filter, drawer.firstChild);
  }
  place();
  mql.addEventListener('change', place);
}

function reorderFilters(filterPanel, desiredOrder) {
  var blocks = filterPanel.querySelectorAll('.pagefind-ui__filter-block');
  var byKey = {};
  blocks.forEach(function (b) {
    var key = b.querySelector('.pagefind-ui__filter-name').textContent.trim().toLowerCase();
    byKey[key] = b;
  });
  desiredOrder.forEach(function (k) {
    if (byKey[k]) filterPanel.appendChild(byKey[k]);
  });
}

function setupScopeFilter(scopeEl, input, ui) {
  function getScope() { ... }
  function apply() { ... }
  function schedule() { ... }
  scopeEl.addEventListener('change', schedule);
  input.addEventListener('input', schedule);
  new MutationObserver(schedule).observe(ui, { childList: true, subtree: true });
}
```

`init()` 變成 orchestrator：

```js
function init() {
  var shell = document.querySelector('.search-shell');
  if (!shell) return;

  waitForElement(shell, '.pagefind-ui__drawer', function () {
    var els = findSearchElements(shell);
    syncScopeHeight(els.scope);
    setupFilterSlotSwap(els.filter, els.drawer, document.querySelector('.search-filter-slot'), 1400);
    reorderFilters(els.filter, ['type', 'tag']);
    setupScopeFilter(els.scope, els.input, els.ui);
  });
}
init();
```

每個拆出的函式：

- 名字描述做什麼（動詞 + 名詞）
- 接受需要的元素當參數（不依賴全局）
- 不知道其他函式的存在（解耦）

---

## 內在屬性比較：四種函式拆分粒度

| 粒度                         | 維護成本            | Debug 範圍       | 可重用性             |
| ---------------------------- | ------------------- | ---------------- | -------------------- |
| 一個 mega init function      | 高 — 200+ 行交織    | 整個函式都要看   | 低 — 跟特定 setup 綁 |
| 按行數機械拆（每 30 行一份） | 中 — 切出無意義片段 | 中               | 低                   |
| 按職責拆                     | 低 — 每函式單一職責 | 函式內部、範圍小 | 高                   |
| 按職責拆 + class 包裝        | 低                  | 範圍小           | 最高 — 多實例        |

優先按職責拆 — 函式名表達 intent、debug 範圍小、單獨可測。

---

## 拆函式的具體技巧

### 1. 函式名是動詞片語

```js
syncScopeHeight()           // 動詞 + 對象
setupFilterSlotSwap()       // 動詞 + 對象
reorderFilters()            // 動詞 + 對象
findSearchElements()        // 動詞 + 對象
```

不要：

```js
filter()        // 動詞模糊（filter 是動詞還是名詞？）
handle()        // 太抽象
init()          // 只有 orchestrator 用、不要散在各處
```

### 2. 參數是該函式需要的、不傳一個 mega object

```js
// 好 — 函式知道它需要什麼
function syncScopeHeight(scopeEl) { ... }

// 較差 — 函式拿到一堆無關的東西、不清楚依賴
function syncScopeHeight(allElements) {
  var scope = allElements.scope;
  ...
}
```

明確參數 = 明確依賴 = 容易測試。

### 3. 副作用集中在一處

```js
function syncScopeHeight(scopeEl) {
  function update() {
    document.body.style.setProperty('--search-scope-h', scopeEl.offsetHeight + 'px');
  }
  update();
  new ResizeObserver(update).observe(scopeEl);
}
```

副作用（DOM 變動、event listener、observer）都在這個函式內。沒散到別處。

### 4. 不依賴外部變數

```js
// 好 — 純函式、依賴只在參數
function reorderFilters(filterPanel, desiredOrder) { ... }

// 較差 — 依賴外部全局變數
var desiredOrder = ['type', 'tag'];
function reorderFilters(filterPanel) {
  // 用了 desiredOrder
}
```

純函式 = 無隱式依賴 = 重用方便、測試方便。

---

## 正確概念與常見替代方案的對照

### 函式做一件事、init 做組合

**正確概念**：每個職責拆獨立函式、命名動詞 + 對象、明確參數。Init 函式是 orchestrator、組合各職責、不自己做事。

**替代方案的不足**：mega init function 把所有事塞一起 — 200+ 行、改一處要小心整體、debug 範圍大。

### 函式名表達 intent

**正確概念**：函式名讀起來像句子（`syncScopeHeight`、`setupFilterSlotSwap`）— 不看內容也大致知道做什麼。

**替代方案的不足**：抽象動詞（`handle`、`process`、`init`） — 看名字不知做什麼、要進去讀。

### 純函式優先

**正確概念**：能不依賴外部變數的就不要依賴、把依賴明確列在參數中。函式變 testable + reusable。

**替代方案的不足**：函式內隱式讀全局變數 — 依賴隱藏、未來改變數可能默默打破函式。

---

## 判讀徵兆

| 訊號                                        | Refactor 動作                     |
| ------------------------------------------- | --------------------------------- |
| 一個函式 100+ 行                            | 列出做的事、按職責拆              |
| 函式名抽象（`init` / `handle` / `process`） | 改名動詞 + 對象、表達 intent      |
| 函式內讀外部全局變數                        | 把依賴改為參數、純函式化          |
| Debug 時要 grep 整個函式找哪段邏輯          | 拆完後職責 = 函式 = grep 範圍縮小 |
| 同一段邏輯複製到別處                        | 拆成獨立函式、兩處引用            |

**核心原則**：函式是「做一件事」的單位。一個函式越多職責、debug 與重用越難。拆 = 投資、回報是未來的維護成本下降。
