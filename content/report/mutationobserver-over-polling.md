---
title: "setTimeout 輪詢換 MutationObserver"
date: 2026-04-25
weight: 30
description: "等元素出現的場景、用 MutationObserver 監聽 DOM 變化、看到目標就 disconnect — 沒延遲、CPU 不被輪詢吃。本文展開兩種等待機制的差異。"
tags: ["report", "事後檢討", "JavaScript", "Refactor", "工程方法論"]
---

## 核心原則

**等待元素出現用 MutationObserver、不用 setTimeout 輪詢。** Observer 是 event-driven、元素出現的瞬間觸發、無延遲；輪詢是 time-based、最快回應時間 = 輪詢間隔、且 CPU 一直跑。

輪詢只在「沒有事件可監聽」時才用。

---

## 為什麼 observer 比輪詢好

### 商業邏輯

「等待某個 DOM 元素出現」這件事的本質是「監聽 DOM 變化、出現時觸發」 — 完全是 event-driven 場景。

`setTimeout` 輪詢的特徵：

- 每隔 N ms 檢查一次、最快 N ms 才能回應
- 即使元素已經出現、要等到下次檢查才知道
- CPU 持續被佔用（即使元素永遠不出現）

`MutationObserver` 的特徵：

- 元素出現的瞬間觸發 callback
- 0 延遲
- DOM 沒變動時 observer 不耗 CPU

兩者效能差異在現代設備上不明顯、但設計上 observer 才是「適合這個場景」的工具。

### 何時輪詢是必要的

| 情境                       | 輪詢必要                     |
| -------------------------- | ---------------------------- |
| 等待 DOM 元素出現          | 否 — 用 MutationObserver     |
| 等待元素尺寸變化           | 否 — 用 ResizeObserver       |
| 等待元素進入 viewport      | 否 — 用 IntersectionObserver |
| 等待外部 API 結果          | 否 — 用 promise / async      |
| 等待全局變數出現（無事件） | 是 — 必要時輪詢              |

「無事件可監聽」時才輪詢 — 這類場景在現代 Web 開發少見。

---

## 這次任務的輪詢

### 觀察

`search.html` 用 setTimeout 等 pagefind UI mount：

```js
function waitAndInit() {
  filter = document.querySelector('.pagefind-ui__filter-panel');
  drawer = document.querySelector('.pagefind-ui__drawer');
  if (!filter || !drawer) {
    setTimeout(waitAndInit, 100);
    return;
  }
  // 找到了、開始 setup
  place();
  reorderFilters();
  setupScopeFilter();
  mql.addEventListener('change', place);
}
waitAndInit();
```

每 100ms 檢查一次、有延遲、CPU 一直跑（雖然輕）。

### 判讀

改用 MutationObserver 監聽 `#search`（pagefind mount target）的子節點變化：

```js
function waitForPagefind(searchRoot, onReady) {
  // 已經存在則立即觸發
  if (searchRoot.querySelector('.pagefind-ui__drawer')) {
    onReady();
    return;
  }
  // 否則 observe DOM 變動
  var observer = new MutationObserver(function () {
    if (searchRoot.querySelector('.pagefind-ui__drawer')) {
      observer.disconnect();
      onReady();
    }
  });
  observer.observe(searchRoot, { childList: true, subtree: true });
}

waitForPagefind(document.getElementById('search'), function () {
  filter = document.querySelector('.pagefind-ui__filter-panel');
  drawer = document.querySelector('.pagefind-ui__drawer');
  place();
  reorderFilters();
  setupScopeFilter();
  mql.addEventListener('change', place);
});
```

特性：

- pagefind 渲染完瞬間觸發、無延遲
- `disconnect()` 後 observer 不再耗資源
- 已存在時 fast path 直接觸發

### 執行：通用 helper

```js
/**
 * 等待 selector 在 root 內出現、觸發 callback。
 * 已存在則 sync 觸發；不存在則用 MutationObserver 等待。
 */
function waitForElement(root, selector, callback) {
  var existing = root.querySelector(selector);
  if (existing) {
    callback(existing);
    return;
  }
  var observer = new MutationObserver(function () {
    var el = root.querySelector(selector);
    if (el) {
      observer.disconnect();
      callback(el);
    }
  });
  observer.observe(root, { childList: true, subtree: true });
}

// 用法
waitForElement(searchRoot, '.pagefind-ui__drawer', function (drawer) {
  // 開始 setup
});
```

把 wait 抽成 helper、setup code 變得更簡潔。

---

## 內在屬性比較：四種等待機制

| 機制               | 延遲             | CPU 使用       | 適用情境        |
| ------------------ | ---------------- | -------------- | --------------- |
| `setTimeout` 單次  | 固定延遲         | 0              | 等已知時間      |
| `setTimeout` 輪詢  | 平均 = 間隔 / 2  | 持續低使用     | 沒事件可監聽    |
| `MutationObserver` | 0 — 變動瞬間     | DOM 變動時短暫 | 等待 DOM 元素   |
| Promise / async    | 0 — resolve 瞬間 | 0              | 等待 async 操作 |

優先順序：**event-driven > async > polling > timeout**。輪詢是最後選擇。

---

## MutationObserver 的細節

### Observe option 選對

```js
observer.observe(root, {
  childList: true,    // 直接子節點增減
  subtree: true,      // 包含深層子節點
  attributes: false,  // 不看 attribute 變動
  characterData: false,
});
```

只勾必要的、不要全部勾 — 觸發頻率影響效能。

### 找到目標後 disconnect

```js
var observer = new MutationObserver(function () {
  if (found) {
    observer.disconnect();   // 立刻停、不要繼續監聽
    callback();
  }
});
```

不 disconnect 的話、observer 一直 active、未來任何 DOM 變動都觸發 callback。

### 已存在的 fast path

```js
if (root.querySelector(selector)) {
  callback();   // 已存在則直接觸發、不需 observer
  return;
}
```

避免「元素已經存在但還是要等下次變動才觸發」的延遲。

---

## 設計取捨：等待 DOM 元素出現的策略

四種做法、各自機會成本不同。這個專案選 A（MutationObserver + fast path）當預設、其他做法在特定情境合理。

### A：MutationObserver + already-exists fast path（這個專案的預設）

- **機制**：先檢查目標是否已存在（直接觸發）、否則 observe DOM 變動、找到後 disconnect
- **選 A 的理由**：0 延遲、CPU 不被輪詢吃、找到後立即停
- **適合**：等待 framework / 第三方 library 動態 mount 的元素
- **代價**：需要寫 fast path + observer + disconnect 三段邏輯（用 helper 包裝即可一行調用）

### B：`setTimeout` 輪詢

- **機制**：每隔 N ms 檢查、找到就停
- **跟 A 的取捨**：B 寫法簡單、A 設計嚴謹；但 B 有最快回應 = N ms 的延遲、CPU 一直跑
- **B 比 A 好的情境**：等的不是 DOM 元素而是無事件可監聽的狀態（全局變數出現、外部 API 結果且無 promise 介面）

### C：Promise / async（如果 API 提供）

- **機制**：`await framework.ready()` 等 framework 提供的 promise
- **跟 A 的取捨**：C 是最乾淨的解、但需要 framework / library 提供 promise API
- **C 比 A 好的情境**：等的目標有官方 promise 介面（避免自行 observe 內部 DOM）

### D：`requestAnimationFrame` 迴圈

- **機制**：每個 frame 檢查一次
- **跟 B 的取捨**：D 跟著 frame、不會在 idle 時跑；但仍是輪詢、延遲 16ms
- **D 才合理的情境**：等待動畫 frame 相關狀態（罕見）— 純等 DOM 元素仍應用 A

---

## 判讀徵兆

| 訊號                                 | Refactor 動作                             |
| ------------------------------------ | ----------------------------------------- |
| `setTimeout` 用來等 DOM 元素         | 改 `MutationObserver` + disconnect        |
| `setInterval` 不停跑檢查元素狀態     | 改 `MutationObserver` 或 `ResizeObserver` |
| 等待邏輯有「最快 X ms 才回應」的延遲 | 改 event-driven 機制、消除延遲            |
| Observer 找到目標後沒 disconnect     | 加 disconnect、避免繼續觸發               |

**核心原則**：DOM 變動有對應的 event 機制可監聽 — 用對機制就有 0 延遲、無 CPU 浪費。輪詢是「沒辦法的辦法」、不是 default。
