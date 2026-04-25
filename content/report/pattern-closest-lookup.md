---
title: "Pattern：closest 反向找根"
date: 2026-04-25
weight: 49
description: "事件處理時用 `e.target.closest('.shell')` 從事件目標反向找元件根 — 適合動態元件、SPA 路由切換、事件委派場景。本文展開反向定位 pattern 的應用邊界。"
tags: ["report", "pattern", "JavaScript", "DOM", "事件處理"]
---

## 核心做法

```js
document.addEventListener('click', function (e) {
  var shell = e.target.closest('.search-shell');
  if (!shell) return;
  // 在這個 shell 內處理
  handleSearchClick(shell, e);
});
```

不在初始化時綁定 listener、而是頁面層級委派事件、事件處理時從 `e.target` 反向找元件根。

---

## 這個做法存在的價值

把「找元件根」從「初始化時綁定」延後到「事件發生時動態判斷」 — 換到三個能力：

1. **元件動態增減免處理**：新加的元件不需要重新綁 listener
2. **多實例不需要 forEach setup**：所有實例共用一個 listener
3. **記憶體效率**：N 個元件只綁 1 個 listener、不是 N 個

代價是事件處理邏輯多一層（每次都要 closest 反向找）。

---

## 適合的情境

| 情境 | 為什麼合理 |
|------|----------|
| SPA 路由切換、元件動態 mount/unmount | 不需要在 mount 時重綁 listener |
| 元件數量大（>10 個實例） | 事件委派比每實例綁 listener 省記憶體 |
| 元件透過 AJAX 動態注入 | 注入後不需要任何 setup 動作 |
| 第三方 widget、不能控制元件生命週期 | listener 綁在 document、跟 widget 解耦 |

**核心特徵**：元件的 mount 時機 / 數量 runtime 才知道、不是初始化時固定。

---

## 不適合的情境

| 情境 | 為什麼過度工程 | 改用 |
|------|------------|------|
| 元件靜態 mount、生命週期跟頁面一樣 | 委派多一層、收益不明顯 | [起點當參數](pattern-root-as-parameter/) |
| 一個元件實例、永不變動 | 完全沒必要 | [元件根變數](pattern-component-root/) |
| 需要在元件 mount 時就跑邏輯（不只回應事件） | closest 只在事件發生時跑、無法當 init hook | [起點當參數](pattern-root-as-parameter/) + MutationObserver |

---

## 設計細節

### Closest 失敗的處理

```js
document.addEventListener('click', function (e) {
  var shell = e.target.closest('.search-shell');
  if (!shell) return;  // 點擊不在任何 shell 內
  // ...
});
```

`closest` 找不到時回 `null`、提早 return 是必要防護。**沒這個 check 會在頁面其他地方點擊時報錯**。

### 從 closest 結果再往下 query

```js
var shell = e.target.closest('.search-shell');
var input = shell.querySelector('.pagefind-ui__search-input');
```

`closest` 找到 shell 後、可以從 shell 往下 query 同元件內的其他元素 — 這是「事件 + closest + 局部 query」的組合。

### 事件類型的選擇

| 事件 | 適合 |
|------|------|
| `click` | 點擊互動 |
| `input` | 輸入框文字變動（需要 bubble） |
| `change` | 選項變動（select / radio / checkbox） |
| `keydown` | 鍵盤快捷鍵 |
| `focus` / `blur` | 焦點移動（不 bubble、要用 `focusin` / `focusout`） |

注意 `focus` / `blur` 不會 bubble — 事件委派要用 `focusin` / `focusout`。

### 委派的根節點選擇

```js
// 選項 1：document（最寬）
document.addEventListener('click', handler);

// 選項 2：特定容器（縮範圍）
var pageContainer = document.querySelector('main');
pageContainer.addEventListener('click', handler);
```

縮範圍的好處是「跟其他頁面區域的 listener 不互相干擾」。預設用 document、有干擾風險才縮。

---

## 跟其他起點做法的關係

[#14 Selector 精準度](dom-selector-precision/) 的「起點」維度有四種做法：

| 做法 | 比較 |
|------|------|
| [document query](pattern-document-query/) | 靜態、簡潔、無多實例支援 |
| [元件根變數](pattern-component-root/) | 靜態、shell 唯一假設 |
| [起點當參數](pattern-root-as-parameter/) | 靜態多實例、forEach 一次設定 |
| 本卡片：closest 反向找根 | 動態、事件驅動、無 init 時機綁定 |

複雜度遞增、能處理的動態程度也遞增。最動態的場景才用本 pattern。

---

## 應用範例：跨多 shell 的 scope filter

```js
function setupGlobalScopeFilter() {
  document.addEventListener('change', function (e) {
    var shell = e.target.closest('.search-shell');
    if (!shell) return;

    var scope = e.target.closest('.search-scope');
    if (!scope) return;  // 不是 scope 控制的 change

    applyScope(shell, scope);
  });
}
setupGlobalScopeFilter();
```

一個 listener 處理所有 shell 的 scope 變動 — 不論 shell 是初始 mount 的、還是 runtime 注入的。

---

## 應用範例：與 [起點當參數](pattern-root-as-parameter/) 組合

```js
// 初始化階段：對已存在的 shell 做 setup
document.querySelectorAll('.search-shell').forEach(setupSearchShell);

// 事件階段：用 closest 處理可能新加的 shell
document.addEventListener('click', function (e) {
  var shell = e.target.closest('.search-shell');
  if (!shell) return;
  // 處理事件、不論 shell 是初始的還是後加的
});

// MutationObserver：捕捉新加的 shell 做 setup
new MutationObserver(function (mutations) {
  mutations.forEach(function (m) {
    m.addedNodes.forEach(function (node) {
      if (node.matches && node.matches('.search-shell')) {
        setupSearchShell(node);
      }
    });
  });
}).observe(document.body, { childList: true, subtree: true });
```

三個 pattern 組合：「靜態 setup」+「事件動態」+「mount 時 setup」 — 各 pattern 補不同時間點的需求。

---

## 判讀徵兆

| 訊號 | 該套用本 pattern 嗎？ |
|------|----------|
| 元件 SPA 路由動態切換 | 是 — 直接對應使用情境 |
| 元件數量大、每實例都要綁 listener | 是 — 委派省記憶體 |
| AJAX / Web Component runtime 注入 | 是 — 不需要重綁 |
| 確定元件靜態、生命週期固定 | 否 — [起點當參數](pattern-root-as-parameter/) 已夠 |
| 邏輯不是事件驅動（init 時就要跑） | 否 — closest 只在事件發生時跑 |

**核心原則**：closest 反向找根把「定位元件」從綁定時延後到事件發生時 — 換到動態能力、付出的是事件處理多一層判斷。靜態場景用更簡單的做法、動態場景才升級到本 pattern。
