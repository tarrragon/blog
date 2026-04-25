---
title: "Pattern：DOM attribute idempotency 標記"
date: 2026-04-25
weight: 50
description: "用 `:not([data-x])` 過濾 + 處理後 `setAttribute('data-x', 'true')` 保證每元素只處理一次 — 是 production apply 函式的預設 idempotency 工具。本文展開命名、生命週期、跟 framework 共處的設計細節。"
tags: ["report", "pattern", "JavaScript", "DOM"]
---

## 核心做法

```js
shell.querySelectorAll('.pagefind-ui__result:not([data-scoped])').forEach(function (el) {
  // ... 處理
  el.setAttribute('data-scoped', 'true');
});
```

apply 函式入口用 `:not([data-x])` 過濾掉已處理元素、處理完後設 attribute 標記。下次 apply 被觸發時、已處理的元素不會被命中。

---

## 這個做法存在的價值

把「保證只處理一次」的責任從**呼叫端**（要記得只呼叫一次）轉到**元素本身**（看自己有沒有被處理過）。

apply 函式可能被多個源觸發：

- 初始化時呼叫
- MutationObserver 偵測到變動觸發
- 使用者事件觸發
- Framework 重繪後重新呼叫

任一個源多呼叫就重複處理 — 無法靠呼叫端紀律避免。Idempotency 標記讓 apply 自己防護。

---

## 適合的情境

| 情境 | 為什麼合理 |
|------|----------|
| Production apply 函式、可能被多源觸發 | 標記在元素上、不依賴呼叫紀律 |
| 處理動作有副作用（綁 listener、改 class） | 重複觸發會疊加副作用 |
| 元素生命週期跟 attribute 同步（不會被 reset） | 標記跟著元素走、自然清理 |
| Devtools debug 友善 | attribute 在 inspector 可見 |

**核心特徵**：元素的 attribute 跟著元素 DOM 生命週期、元素移除時標記自動消失。

---

## 不適合的情境

| 情境 | 為什麼不夠 | 改用 |
|------|---------|------|
| 寫第三方 library | 在使用者 DOM 加自家 attribute、有命名衝突風險 | [WeakMap 紀錄](pattern-weakmap-idempotency-record/) |
| Framework 重繪會清掉 attribute | 標記消失、防護失效 | 配合 disconnect/observe 或改 WeakMap |
| 需要週期性 reset 標記 | attribute 改回需要遍歷所有元素 | WeakMap 可整批 `new WeakMap()` |
| 多種獨立的 idempotency 維度 | DOM 上多 attribute 互相干擾 | WeakMap 各別管理 |

---

## 設計細節

### Attribute 命名規範

```js
// 好：明確 namespace + 用途
el.setAttribute('data-search-scoped', 'true');
el.setAttribute('data-myapp-processed', 'true');

// 較差：通用名、容易跟其他程式撞
el.setAttribute('data-processed', 'true');
el.setAttribute('processed', 'true');  // 不是 data-* 開頭、可能不被 HTML spec 接受
```

預設用 `data-{appname}-{purpose}` 格式 — 即使引入第三方 library 加 attribute、也不會撞名。

### Attribute 值的選擇

```js
// 用法 1：固定 'true'（最簡）
el.setAttribute('data-scoped', 'true');

// 用法 2：紀錄處理時間 / 版本（debug 友善）
el.setAttribute('data-scoped', String(Date.now()));
el.setAttribute('data-scoped', 'v2');

// 用法 3：boolean attribute（無值）
el.setAttribute('data-scoped', '');
// CSS 用 [data-scoped] 即可選中
```

預設用 `'true'`、debug 困難時改 timestamp 看處理順序。

### 跟 framework 重繪共處

Svelte / React / Vue 重繪元素時、**自家 attribute 通常會被保留**（framework 只管自己的 attribute）— 但有例外：

| 情境 | 行為 |
|------|------|
| Framework re-render 整段 DOM | 元素被替換、新元素沒標記 → apply 重跑、合理 |
| Framework patch 既有元素 attribute | 自家 attribute 保留 |
| Framework `replaceWith` / `innerHTML` 重設 | 元素被替換 → 標記消失、apply 重跑、合理 |

**核心觀察**：自家 attribute 跟著元素走 — 元素還在就有、元素被換就沒。這是「正確」行為、不是 bug。

### 例外：framework 主動清自家 attribute

少數 framework 會 strict 清非預期的 attribute（例如某些 Web Component lib）。檢查方式：

```js
el.setAttribute('data-scoped', 'true');
// ... 等 framework patch 一次後
console.log(el.getAttribute('data-scoped'));  // 還在嗎？
```

如果消失、改用 [WeakMap 紀錄](pattern-weakmap-idempotency-record/)。

---

## 跟其他 idempotency 做法的關係

[#14 Selector 精準度](dom-selector-precision/) 的「過濾」維度有三種做法：

| 做法 | 比較 |
|------|------|
| 本卡片：DOM attribute 標記 | production 預設、devtools 可見、有命名衝突風險 |
| [WeakMap 紀錄](pattern-weakmap-idempotency-record/) | 不污染 DOM、適合 library、debug 不便 |
| 依賴外部呼叫者保證 | 反模式、無防護、不可靠 |

預設用本卡片、第三方 library / framework 衝突情境升級到 WeakMap。

---

## 應用範例：完整 apply

```js
function apply(shell) {
  var newResults = shell.querySelectorAll(
    '.pagefind-ui__result:not([data-search-scoped])'
  );

  newResults.forEach(function (el) {
    bindClickHandler(el);
    addCustomBadge(el);
    el.setAttribute('data-search-scoped', 'true');
  });
}

// 多源觸發都安全
init.addEventListener('click', () => apply(shell));
observer.observe(shell, ...);  // 觀察到變動觸發 apply
apply(shell);  // 初始化時跑一次
```

三個觸發點任一個多跑、`:not([data-search-scoped])` 都會過濾掉已處理元素。

---

## 應用範例：多維度標記

```js
// 三個獨立 idempotency 維度、各自 attribute
el.setAttribute('data-search-scoped', 'true');     // scope filter 處理過
el.setAttribute('data-search-bound', 'true');      // event listener 綁過
el.setAttribute('data-search-decorated', 'true');  // 視覺裝飾加過

// 各 apply 函式只看自己的 attribute
function applyScope(shell) {
  shell.querySelectorAll('.x:not([data-search-scoped])').forEach(...)
}
function applyBindings(shell) {
  shell.querySelectorAll('.x:not([data-search-bound])').forEach(...)
}
```

每個 idempotency 維度獨立 — 互相不干擾。

---

## 判讀徵兆

| 訊號 | 該套用本 pattern 嗎？ |
|------|----------|
| Apply 被多源觸發、產生重複處理 bug | 是 — 直接對應使用情境 |
| 寫第三方 library / 不能污染 DOM | 否 — 改 [WeakMap](pattern-weakmap-idempotency-record/) |
| Framework 會清自家 attribute | 否 — 改 WeakMap |
| 想在 devtools inspector 直接看處理狀態 | 是 — attribute 可見性是優點 |
| 同元素多種 idempotency 維度 | 是 — 多 attribute 各自管理 |

**核心原則**：把 idempotency 責任從呼叫端搬到元素本身、attribute 是「便宜可見的旗標」。Production apply 預設用本 pattern、特殊情境（library / framework 衝突）才升級到 WeakMap。
