---
title: "Pattern：跨 slot 同節點搬遷"
date: 2026-04-25
weight: 54
description: "Stateful UI 在兩個 slot 之間用 `appendChild` 搬同一個 DOM 節點、不複製兩份 — 避免 state 分歧。本文展開搬遷 pattern 的設計細節與適用邊界。"
tags: ["report", "pattern", "JavaScript", "DOM", "Responsive Design"]
---

## 核心做法

```js
var mql = window.matchMedia('(min-width: 1400px)');
function place() {
  if (mql.matches) {
    desktopSlot.appendChild(filter);
  } else {
    drawer.insertBefore(filter, drawer.firstChild);
  }
}
mql.addEventListener('change', place);
place();  // 初始化
```

同一個 DOM 節點在兩個 slot 之間搬移、不複製成兩份。

---

## 這個做法存在的價值

Stateful UI（內含 checkbox 勾選、表單值、scroll 位置等 state）跨兩個顯示位置切換時、複製兩份會造成 state 分歧 — 使用者在 desktop 勾的 filter、切到 mobile 看不到勾選狀態。

搬同一份節點 = state 永遠跟著節點走 = 切換無感。

---

## 適合的情境

| 情境 | 為什麼合理 |
|------|----------|
| Filter UI 跨 viewport 切換顯示位置 | checkbox state 跟著節點 |
| Modal 內容 vs 側邊抽屜 | 同一份表單在兩種展示方式間 |
| Tab UI 跨 desktop / mobile 重新組織 | 各 tab 內 state 不重置 |
| 任何「同 UI、不同位置」的 responsive 切換 | 不需要 state 同步邏輯 |

**核心特徵**：UI 內含 state、兩個位置展示的是「同一個邏輯單位」、不是「兩個獨立元件」。

---

## 不適合的情境

| 情境 | 為什麼不夠 | 改用 |
|------|---------|------|
| 兩個位置展示的是不同元件（雖然視覺類似） | 搬遷會把錯誤元件搬到錯位置 | 各自獨立掛載、不搬 |
| UI 純 stateless（純圖示、純文字） | 複製兩份成本低、無 state 風險 | CSS-only 雙顯示 + display 切換 |
| Framework 管的節點 | 整節點搬安全、但複製不安全（id duplicate / framework 困惑） | 必須搬整節點、不複製 |
| 兩個位置視覺差異大 | 搬遷後 UI 不適配新位置 | 各自獨立元件 |

---

## 設計細節

### `appendChild` 是搬遷、不是複製

```js
parentA.appendChild(node);  // node 從原位置消失、出現在 parentA
```

DOM API 的 `appendChild` / `insertBefore` 是 move、不是 copy — 同一個節點不能同時存在於多個位置。這個特性正是搬遷 pattern 的基礎。

### 初始放在哪

```html
<!-- 預設位置（mobile / fallback）-->
<div class="pagefind-ui">
  <div class="drawer">
    <div class="filter-panel">...</div>  <!-- 初始在這 -->
  </div>
</div>

<!-- 桌面 slot（空、等待搬入）-->
<aside class="desktop-filter-slot"></aside>
```

預設放在 fallback 位置 — 當 JS 失敗時仍可見。

### 跨 slot 切換的時機

`matchMedia` event 是 viewport 跨過 breakpoint 的瞬間：

```js
var mql = window.matchMedia('(min-width: 1400px)');
mql.addEventListener('change', place);
place();  // 初始也跑一次
```

不要用 resize event — 太頻繁、會在 breakpoint 邊界震盪。`matchMedia` 只在 cross 的瞬間觸發。

### 搬遷時 framework 的 reactivity

如果搬遷的節點是 framework 管的（如 Pagefind 的 svelte 元件）— 整節點搬通常安全、framework 在下次 patch 時看到節點還在、繼續更新內部。

詳細安全規則由 [#13 JS 操作 framework 元件：邊界辨識與安全規則](component-boundary-and-js-impact/) 處理。

### Focus 跟著搬

搬遷可能讓鍵盤 focus 暫時失去（視瀏覽器）— 加 save/restore：

```js
function place() {
  var activeBefore = document.activeElement;
  if (mql.matches) desktopSlot.appendChild(filter);
  else drawer.insertBefore(filter, drawer.firstChild);
  if (activeBefore && filter.contains(activeBefore)) {
    activeBefore.focus();
  }
}
```

詳細處理由 [#37 動態 DOM 移動時的 focus 管理](focus-management-on-dom-move/) 處理。

---

## 設計取捨：兩個 slot 的 stateful UI 共用

四種做法、各自機會成本不同。預設選 A（搬同節點）、其他做法在特定情境合理。

### A：搬同一節點（這個專案的預設）

- **機制**：`matchMedia + appendChild` 在兩 slot 間搬同一份節點
- **選 A 的理由**：state 跟著節點、切換無感、不需要 sync 邏輯
- **適合**：stateful UI、需要在兩個位置展示同樣內容
- **代價**：搬遷 callback 在 viewport 跨 breakpoint 時觸發、需要處理 focus / 動畫
- **詳細**：本卡片

### B：CSS-only 雙顯示 + display 切換

- **機制**：兩個位置都放同一份節點 (寫兩遍 HTML)、用 `@media + display: none` 切換顯示
- **跟 A 的取捨**：B 純 CSS 簡單、A 需要 JS；但 B 對 stateful UI 失敗（兩份 state 各自獨立）
- **B 比 A 好的情境**：UI 純 stateless（純圖示）、純 CSS 解就夠

### C：CSS-only + JS 同步 state

- **機制**：兩份節點 + JS 監聽 state 變動同步
- **跟 A 的取捨**：C 比 B 解 state 問題、但同步邏輯複雜（雙向更新、避免循環）
- **C 比 A 好的情境**：兩個位置的 UI 視覺需要差異（不只是位置不同）

### D：JS 完全重建 UI

- **機制**：viewport 變動時拆掉舊 UI、在新位置重建一份
- **成本特別高的原因**：state 在重建時遺失、UI 閃爍、輸入中斷
- **D 才合理的情境**：UI 是 stateless 的、且重建成本低

---

## 跟其他 pattern 的關係

[#14 Selector 精準度](dom-selector-precision/) 的「起點」維度有四種做法、本卡片是「跨 slot 搬遷」這個專門情境的補充：

| 議題 | 對應 pattern |
|------|------------|
| Query 的起點 | [#46 document](pattern-document-query/) / [#47 元件根變數](pattern-component-root/) / [#48 起點當參數](pattern-root-as-parameter/) / [#49 closest 反向](pattern-closest-lookup/) |
| Idempotency 過濾 | [#50 attribute 標記](pattern-attribute-idempotency-marker/) / [#51 WeakMap](pattern-weakmap-idempotency-record/) |
| 跨 slot 搬遷（本卡片） | 同節點 vs 雙節點 + state 同步 |

---

## 應用範例：跨 viewport filter 切換

```js
function setupResponsiveFilter(shell, breakpoint) {
  var filter = shell.querySelector('.pagefind-ui__filter-panel');
  var drawer = shell.querySelector('.pagefind-ui__drawer');
  var desktopSlot = document.querySelector('.search-filter-slot');

  if (!filter || !drawer || !desktopSlot) return;

  var mql = window.matchMedia('(min-width: ' + breakpoint + 'px)');

  function place() {
    var activeBefore = document.activeElement;

    if (mql.matches) {
      desktopSlot.appendChild(filter);
    } else {
      drawer.insertBefore(filter, drawer.firstChild);
    }

    if (activeBefore && filter.contains(activeBefore)) {
      activeBefore.focus();
    }
  }

  place();
  mql.addEventListener('change', place);
}
```

完整 pattern：取元件根 + matchMedia + 搬遷 + focus 處理。

---

## 判讀徵兆

| 訊號 | 該套用本 pattern 嗎？ |
|------|---------|
| 兩份節點各自 state、用 sync 邏輯保持一致 | 是 — 改成搬同節點、移除 sync |
| Stateful UI 在 mobile / desktop 兩種 layout 間 | 是 — 直接的應用 |
| 切換 viewport 時 UI 閃爍 / 重建 | 是 — 改成搬而非重建 |
| 兩個位置展示完全不同的 UI（不是同邏輯） | 否 — 各自獨立元件 |
| Framework 管的節點 | 是 — 整節點搬安全、但要遵守 [#13](component-boundary-and-js-impact/) 的規則 |

**核心原則**：Stateful UI 的兩個展示位置共用同一份節點、state 自然跟著走 — 比「兩份節點 + sync 邏輯」乾淨。複製兩份是「state 來源從一變二」的隱形多源（違反 [#44 SSoT](single-source-of-truth/)）。
