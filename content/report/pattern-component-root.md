---
title: "Pattern：元件根變數 query"
date: 2026-04-25
weight: 47
description: "把元件根 `var shell = document.querySelector('.shell')` 一次存變數、之後所有 query 從 shell 開始 — 是 production 客製的預設起點。本文展開這個 pattern 的設計細節與邊界。"
tags: ["report", "pattern", "JavaScript", "DOM"]
---

## 核心做法

```js
var shell = document.querySelector('.search-shell');
if (!shell) return;

var input  = shell.querySelector('.pagefind-ui__search-input');
var drawer = shell.querySelector('.pagefind-ui__drawer');
// ... 之後所有 query 都從 shell 開始
```

把元件根 query 一次存變數、所有後續 query 都從這個變數開始。

---

## 這個做法存在的價值

把 selector 的作用範圍從「全頁面」收斂到「元件內部」。即使未來頁面其他地方出現同名元素、跟我無關。成本只多一行 query + 一個 null check、防護收益大。

---

## 適合的情境

| 情境                                         | 為什麼合理                     |
| -------------------------------------------- | ------------------------------ |
| Production 客製、預期長期存活                | 未來頁面結構可能變動、需要隔離 |
| 當前只有一個元件實例、未來可能加             | 提早預防、改造成本最低         |
| 元件根 mount 後不會被移除                    | 變數生命週期跟元件一致         |
| 程式跑在頁面 mount 後（DOMContentLoaded 後） | shell 可被找到                 |

**核心特徵**：寫的時候只有一個元件、但希望程式碼能容忍未來頁面結構變動。

---

## 不適合的情境

| 情境                         | 為什麼不夠                       | 改用                                           |
| ---------------------------- | -------------------------------- | ---------------------------------------------- |
| 同頁同時有多個元件實例       | 變數只存第一個 shell、其他被忽略 | [起點當參數](../pattern-root-as-parameter/)    |
| 元件動態增減（SPA 路由切換） | 變數指向 stale DOM               | [closest 反向找根](../pattern-closest-lookup/) |
| 一次性 / 探索期程式          | 過度工程                         | [document query](../pattern-document-query/)   |

---

## 設計細節

### Null check 的時機

```js
var shell = document.querySelector('.search-shell');
if (!shell) return;
```

頁面可能沒有 shell（不是搜尋頁），所有後續 query 都會 null pointer。提早 return 比後續一連串 `if (drawer)` 乾淨。

**等同於宣告**：「這段程式只在有 shell 的頁面執行」。

### 變數的宣告位置

| 位置                    | 適合                    |
| ----------------------- | ----------------------- |
| 函式內 local 變數       | 預設、scope 最小        |
| Module scope（IIFE 內） | 多函式共用同一 shell    |
| Class instance property | 元件本身用 class 包裝時 |

避免全域變數 — `window.shell` 容易跟其他 script 撞。

### 等待 shell mount 的處理

如果 script 跑得太早（shell 還沒 mount），shell 會是 null：

```js
// 解法 1：等 DOMContentLoaded
document.addEventListener('DOMContentLoaded', function () {
  var shell = document.querySelector('.search-shell');
  if (!shell) return;
  // ...
});

// 解法 2：MutationObserver 等 mount
var bootstrap = new MutationObserver(function () {
  var shell = document.querySelector('.search-shell');
  if (!shell) return;
  bootstrap.disconnect();
  // ...
});
bootstrap.observe(document.body, { childList: true, subtree: true });
```

**選擇取決於 shell 是 server-render 還是 client-render**：server-render 用 DOMContentLoaded、client-render 用 observer。

---

## 跟其他起點做法的關係

[#14 Selector 精準度](../dom-selector-precision/) 的「起點」維度有四種做法：

| 做法                                           | 比較                               |
| ---------------------------------------------- | ---------------------------------- |
| [document query](../pattern-document-query/)   | 比本卡片簡潔、不防護未來變動       |
| 本卡片：元件根變數                             | 多一行設定、隔離未來頁面變動       |
| [起點當參數](../pattern-root-as-parameter/)    | 比本卡片多支援多實例、設計成本前移 |
| [closest 反向找根](../pattern-closest-lookup/) | 適合動態元件、不依賴變數綁定的時間 |

預設用本卡片、需要多實例升級到「起點當參數」、需要動態升級到「closest」。

---

## 應用範例：完整 setup

```js
function init() {
  var shell = document.querySelector('.search-shell');
  if (!shell) return;

  var ui     = shell.querySelector('.pagefind-ui');
  var input  = shell.querySelector('.pagefind-ui__search-input');
  var drawer = shell.querySelector('.pagefind-ui__drawer');

  if (!input || !drawer) return;  // 元件未完整 mount

  syncScopeHeight(shell.querySelector('.search-scope'));
  setupFilterSlotSwap(shell, drawer);
  setupScopeFilter(shell, input);
}

document.addEventListener('DOMContentLoaded', init);
```

shell 取一次、各 setup 函式從 shell 派生需要的子節點。

---

## 判讀徵兆

| 訊號                               | 該換做法嗎？                                 |
| ---------------------------------- | -------------------------------------------- |
| 多函式共用同一 shell、各自重 query | 否 — 把 shell 提到 module scope 共用         |
| 同頁面要支援多個 shell 實例        | 是 — 升級到「起點當參數」                    |
| 元件可能在 runtime 動態出現 / 消失 | 是 — 升級到「closest 反向」                  |
| Shell 偶爾找不到（時序問題）       | 否 — 加 MutationObserver bootstrap、做法不變 |

**核心原則**：本 pattern 是 production 客製的預設、不是極致最佳化。當當前情境不複雜（一個元件、靜態 mount）、用本 pattern 即可；情境變複雜時再升級到對應做法。
