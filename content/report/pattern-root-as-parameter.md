---
title: "Pattern：起點當函式參數"
date: 2026-04-25
weight: 48
description: "把元件根當函式參數傳入 — `function setup(shell) { shell.querySelector(...) }`、外部呼叫 `forEach(setup)` 處理多實例。本文展開純函式設計與多實例支援的取捨。"
tags: ["report", "pattern", "JavaScript", "DOM", "Refactor"]
---

## 核心做法

```js
function setupSearchShell(shell) {
  var ui     = shell.querySelector('.pagefind-ui');
  var input  = shell.querySelector('.pagefind-ui__search-input');
  var drawer = shell.querySelector('.pagefind-ui__drawer');
  // ... 所有 query 從參數 shell 開始
}

document.querySelectorAll('.search-shell').forEach(setupSearchShell);
```

元件根不在函式內 query、由呼叫者傳入。函式支援任意數量的元件實例。

---

## 這個做法存在的價值

兩件事：

1. **多實例支援免費**：`forEach(setup)` 自動處理多個 shell
2. **純函式特性**：函式行為只依賴參數、不依賴外部狀態 — 可單獨測試、可重用、副作用集中

跟[元件根變數](../pattern-component-root/)的關鍵差異：那個 pattern 假設「shell 唯一」、本 pattern 把這個假設外移到呼叫端、函式本身不假設。

---

## 適合的情境

| 情境                                       | 為什麼合理                    |
| ------------------------------------------ | ----------------------------- |
| 同頁面有多個元件實例（多語切換、相關搜尋） | `forEach` 自動覆蓋全部        |
| 元件設計成可被重用到其他頁面               | 沒有 hardcoded 依賴、容易移植 |
| 寫成函式庫 / 第三方 component              | 使用者可以對任意根節點呼叫    |
| 想單元測試函式行為                         | 傳入 mock root 即可測試       |

**核心特徵**：把「shell 從哪來」這個責任明確交給呼叫端、函式自己不關心。

---

## 不適合的情境

| 情境                           | 為什麼過度工程                       | 改用                                           |
| ------------------------------ | ------------------------------------ | ---------------------------------------------- |
| 確定全站只有一個元件實例       | 每函式多一個參數、收益不明顯         | [元件根變數](../pattern-component-root/)       |
| 元件動態增減、生命週期不可預測 | forEach 只跑一次、無法捕捉後加的元件 | [closest 反向找根](../pattern-closest-lookup/) |
| 一次性探索程式碼               | 純函式設計成本不值得                 | [document query](../pattern-document-query/)   |

---

## 設計細節

### 函式簽名的設計

```js
// 好：shell 是必填參數
function setupSearchShell(shell) { ... }

// 較差：依賴外部變數
var shell;  // module scope
function setupSearchShell() {
  // 用了外部 shell
}

// 更差：mega object
function setupSearchShell(allElements) {
  var shell = allElements.shell;  // 不知道實際依賴什麼
  // ...
}
```

明確參數 = 明確依賴 = 容易測試、容易讀。

### 內部子函式也接受 shell

```js
function setupSearchShell(shell) {
  syncScopeHeight(shell);
  setupFilterSlot(shell);
  setupScopeFilter(shell);
}

function syncScopeHeight(shell) {
  var scope = shell.querySelector('.search-scope');
  // ...
}
```

每層都明確接受 shell — 不依賴外層 closure。整套函式族都是純函式。

### 預先抓子節點 vs 每次重 query

```js
// 方式 A：函式入口抓所有子節點
function setupSearchShell(shell) {
  var els = {
    ui:     shell.querySelector('.pagefind-ui'),
    input:  shell.querySelector('.pagefind-ui__search-input'),
    drawer: shell.querySelector('.pagefind-ui__drawer'),
  };
  // 後續用 els.ui / els.input / els.drawer
}

// 方式 B：各子函式自己 query
function setupSearchShell(shell) {
  syncScopeHeight(shell);  // 內部自己 querySelector
  setupFilterSlot(shell);
}
```

A 比較有效率（只 query 一次）、B 比較解耦（子函式自包含）。**選 B 為預設、效能瓶頸時才考慮 A**。

---

## 跟其他起點做法的關係

[#14 Selector 精準度](../dom-selector-precision/) 的「起點」維度有四種做法：

| 做法                                           | 比較                                |
| ---------------------------------------------- | ----------------------------------- |
| [document query](../pattern-document-query/)   | 比本卡片簡潔、無多實例支援          |
| [元件根變數](../pattern-component-root/)       | 比本卡片少一個參數、無多實例支援    |
| 本卡片：起點當參數                             | 多實例支援、純函式、設計成本前移    |
| [closest 反向找根](../pattern-closest-lookup/) | 比本卡片更動態、不依賴 forEach 時機 |

升級階梯：document → 元件根變數 → 起點當參數 → closest。複雜度遞增、能處理的情境也遞增。

---

## 應用範例：多實例 setup

```js
// 頁面有 N 個 search-shell（例如多語版面切換）
document.querySelectorAll('.search-shell').forEach(setupSearchShell);

// 跑完之後：每個 shell 各自獨立 setup、互不干擾
```

當前頁只一個 shell、上面這行也適用 —`forEach` 對 1 個元素跑一次、跟 hardcode 單例沒差。**做了多實例設計、未來不需要重寫**。

---

## 應用範例：單元測試

純函式可以對 mock DOM 測試：

```js
test('setupSearchShell 把 filter 移到 sidebar', function () {
  var shell = createMockShell();  // 建立測試用 DOM
  setupSearchShell(shell);

  expect(shell.querySelector('.search-filter-slot').children.length).toBe(1);
});
```

不需要全頁面 mount、只需要 mock 一個 shell — 測試成本低。

---

## 判讀徵兆

| 訊號                           | 該套用本 pattern 嗎？                              |
| ------------------------------ | -------------------------------------------------- |
| 同頁要支援多個元件實例         | 是 — 直接的好處                                    |
| 想對函式寫單元測試             | 是 — 純函式才好測                                  |
| 函式內讀 module scope 變數     | 是 — 改成參數讓依賴顯式                            |
| 確定永遠只一個實例、且不寫測試 | 否 — [元件根變數](../pattern-component-root/) 已夠 |
| 元件實例 runtime 動態增減      | 否 — 升級到 [closest](../pattern-closest-lookup/)  |

**核心原則**：本 pattern 把「我從哪取得 shell」的答案從函式內搬到呼叫端 — 換到「函式可重用」+「測試容易」+「多實例免費」三個收益、代價是函式簽名多一個參數。當前情境只一個實例也適用、未來擴展不需重寫。
