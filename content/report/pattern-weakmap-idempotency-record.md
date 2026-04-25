---
title: "Pattern：WeakMap idempotency 紀錄"
date: 2026-04-25
weight: 51
description: "用 `WeakMap` 紀錄已處理的元素 — 不污染 DOM、適合第三方 library、跟 framework 衝突場景。本文展開 GC 行為、debug 替代方案、跟 attribute 標記的取捨。"
tags: ["report", "pattern", "JavaScript", "DOM"]
---

## 核心做法

```js
var processed = new WeakMap();

shell.querySelectorAll('.pagefind-ui__result').forEach(function (el) {
  if (processed.has(el)) return;
  // ... 處理
  processed.set(el, true);
});
```

把「已處理」狀態紀錄在 JS 的 WeakMap 裡、不寫到 DOM 上。WeakMap key 是元素本身、元素被 GC 時自動清理。

---

## 這個做法存在的價值

兩件事 [DOM attribute 標記](pattern-attribute-idempotency-marker/) 做不到：

1. **不污染 DOM**：使用者 DOM 不會被加自家 attribute、適合第三方 library
2. **跟 framework 完全解耦**：framework 怎麼操作 DOM 都不影響 WeakMap 紀錄

代價是 debug 不便（看不到狀態）、紀錄跟 JS context 綁定（換頁就消失）。

---

## 適合的情境

| 情境 | 為什麼合理 |
|------|----------|
| 寫第三方 library / npm package | 不在使用者 DOM 加 attribute、避免命名衝突 |
| Framework 會清非預期的 attribute | WeakMap 不在 DOM、framework 動不到 |
| 需要週期性 reset 紀錄 | `processed = new WeakMap()` 一行重置全部 |
| 紀錄複雜資料、不只是 boolean | WeakMap value 可以是任何物件 |

**核心特徵**：紀錄獨立於 DOM 之外、跟 JS 物件 lifetime 綁定。

---

## 不適合的情境

| 情境 | 為什麼不夠 | 改用 |
|------|---------|------|
| 自家 application、devtools debug 重要 | 看不到狀態、debug 困難 | [DOM attribute 標記](pattern-attribute-idempotency-marker/) |
| 跨頁面 / 跨 session 的 idempotency | WeakMap 在 JS context 內、換頁就消失 | LocalStorage / 後端紀錄 |
| 元素生命週期短、頻繁 GC | WeakMap 自動清理可能比預期早 | 改用 Map（但要手動清理） |
| 紀錄要跟 SSR 同步 | WeakMap 只活在 client | 結合 attribute（SSR 階段標記） |

---

## 設計細節

### 為什麼用 WeakMap 不用 Map / Set

```js
// WeakMap：key 是元素、元素被 GC 時 entry 自動消失
var processedW = new WeakMap();
processedW.set(el, true);
// el 從 DOM 移除 + 沒其他 reference → GC → WeakMap entry 消失

// Map / Set：強引用、阻止 GC
var processedS = new Set();
processedS.add(el);
// el 從 DOM 移除、但 Set 還抓著 → 永久 leak
```

DOM 元素可能動態移除（filter、SPA 路由切換、framework 重繪）— Map / Set 會造成 memory leak。**處理 DOM 元素 idempotency 預設用 WeakMap**。

### Value 的設計

```js
// 用法 1：純 boolean（最簡）
processed.set(el, true);

// 用法 2：紀錄處理版本（升級時偵測 stale 紀錄）
processed.set(el, { version: 2, time: Date.now() });
if (processed.has(el) && processed.get(el).version === currentVersion) return;

// 用法 3：紀錄相關 metadata（避免重複查詢）
processed.set(el, {
  bindingsId: registerListener(el),
  initialClass: el.className,
});
```

WeakMap value 可以儲任何資料 — 比 attribute（只能存字串）更彈性。

### Debug 替代方案

attribute 標記可以在 devtools inspector 直接看；WeakMap 看不到。debug 時的替代：

```js
// 開發模式同步寫一份 attribute（production build 時拿掉）
function markProcessed(el) {
  processed.set(el, true);
  if (DEV_MODE) {
    el.setAttribute('data-debug-processed', 'true');
  }
}
```

或暴露到 console：

```js
window.__debug_processed = processed;
// console: __debug_processed.has($0)  // 檢查當前選中元素
```

這些都是 workaround、不如 attribute 標記直觀。**選 WeakMap 的人通常已經接受這個 debug 成本**。

### Reset 紀錄

```js
// WeakMap 整批 reset
processed = new WeakMap();

// 對比 attribute 整批 reset 要遍歷
shell.querySelectorAll('[data-scoped]').forEach(el => {
  el.removeAttribute('data-scoped');
});
```

需要週期性 reset（例如 user 切換 mode、所有元素該重新處理）— WeakMap 一行解決、attribute 要遍歷。

---

## 跟其他 idempotency 做法的關係

[#14 Selector 精準度](dom-selector-precision/) 的「過濾」維度有三種做法：

| 做法 | 比較 |
|------|------|
| [DOM attribute 標記](pattern-attribute-idempotency-marker/) | production 預設、devtools 可見、有命名衝突風險 |
| 本卡片：WeakMap 紀錄 | 不污染 DOM、適合 library、debug 不便 |
| 依賴外部呼叫者保證 | 反模式、無防護 |

選擇順序：**自家 application** → attribute；**library / framework 衝突** → WeakMap；**反模式不選**。

---

## 應用範例：library 設計

```js
// 第三方 library export 的 init 函式
function initSearchEnhancement(shell) {
  var processed = new WeakMap();

  function apply() {
    shell.querySelectorAll('.search-result').forEach(function (el) {
      if (processed.has(el)) return;
      enhanceResult(el);
      processed.set(el, true);
    });
  }

  apply();
  new MutationObserver(apply).observe(shell, { childList: true, subtree: true });
}

// 使用者：
initSearchEnhancement(document.querySelector('.my-search'));
// 不會在使用者 DOM 上加任何 data-* attribute
```

使用者 DOM 完全乾淨、library 行為內聚。

---

## 應用範例：版本化處理

```js
var processed = new WeakMap();
var CURRENT_VERSION = 3;

function apply() {
  shell.querySelectorAll('.x').forEach(function (el) {
    var record = processed.get(el);
    if (record && record.version === CURRENT_VERSION) return;

    // 升級到新版本（可能需要清舊綁定）
    if (record) cleanup(el, record);
    enhance(el, CURRENT_VERSION);
    processed.set(el, { version: CURRENT_VERSION, time: Date.now() });
  });
}
```

版本變動時 — 不需要遍歷 DOM 清舊 attribute、直接用 WeakMap value 比對。

---

## 判讀徵兆

| 訊號 | 該套用本 pattern 嗎？ |
|------|----------|
| 寫第三方 library / npm package | 是 — 不污染使用者 DOM |
| Framework 會 strict 清自家 attribute | 是 — WeakMap 跟 framework 解耦 |
| 紀錄需要儲複雜資料（不只 boolean） | 是 — WeakMap value 可任意 |
| 自家 application、debug 重要 | 否 — [attribute 標記](pattern-attribute-idempotency-marker/) 在 inspector 可見 |
| 紀錄要跨頁面持久化 | 否 — 改用 storage / 後端 |

**核心原則**：WeakMap idempotency 是 attribute 標記的「不污染 DOM 替代品」 — 在 library / framework 衝突情境必要、在自家 application 通常用 attribute 即可。GC 自動清理是 WeakMap 的特性、預設不用 Map / Set 是因為它們會 memory leak。
