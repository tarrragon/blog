---
title: "動態 DOM 移動時的 focus 管理"
date: 2026-04-25
weight: 37
description: "Filter slot 跨 viewport 搬節點、scope filter 隱藏結果 — 這類 DOM 變動會讓鍵盤 focus 跑掉或停在不可見位置。本文盤點動態 DOM 對 focus 的影響與檢查方法。"
tags: ["report", "事後檢討", "Accessibility", "JavaScript", "工程方法論"]
---

## 核心原則

**JS 移動或隱藏 DOM 元素時、鍵盤 focus 的命運要主動處理 — 不處理會跑掉或停在不可見元素上、鍵盤使用者瞬間迷失方向。** 多數動態 UI 的 focus 問題不是「某個元素該 focusable」、是「某個變動沒考慮 focus 該去哪」。

---

## 為什麼 focus 管理需要主動處理

### 商業邏輯

鍵盤使用者依 focus 知道「現在在哪」。focus 變動有三種來源：

| 來源                             | 含義                                      |
| -------------------------------- | ----------------------------------------- |
| 使用者主動（Tab、Enter、方向鍵） | 預期、無需處理                            |
| Focus 元素被移除                 | focus 跳到 body — 使用者迷失              |
| Focus 元素被 reparent            | 看瀏覽器、可能 focus 仍在元素上、可能掉失 |

第二、三類是 JS 變動 DOM 引起的副作用、開發者要主動處理。

### 三類 DOM 變動對 focus 的影響

| 變動類型                       | Focus 行為                                     |
| ------------------------------ | ---------------------------------------------- |
| 整節點 reparent（appendChild） | 視瀏覽器、Chrome 多半保留 focus、Safari 可能掉 |
| 節點 remove                    | focus 跳到 body                                |
| 節點 display: none             | focus 跳到 body                                |
| 節點 visibility: hidden        | focus 仍在但元素不可見、使用者迷失             |

每類有對應的處理 — 主要是「事前 save、事後 restore」。

---

## 搜尋頁的具體風險點

### 風險 1：Filter slot 跨 viewport 切換

**位置**：matchMedia callback 的 `place()` 函式。

```js
function place() {
  if (mql.matches) slot.appendChild(filter);
  else drawer.insertBefore(filter, drawer.firstChild);
}
```

**判讀**：使用者鍵盤 focus 在 filter 內某個 checkbox、視窗 resize 跨過 1400px、`appendChild` 把 filter 整個搬到別處。理論上 focus 跟著節點走、實際視瀏覽器。

**症狀**：使用者按 tab 進到 filter checkbox、調視窗寬度跨 breakpoint、focus 突然在 body 或其他位置。

**第一個該查的**：

```js
function place() {
  var activeBefore = document.activeElement;
  if (mql.matches) slot.appendChild(filter);
  else drawer.insertBefore(filter, drawer.firstChild);
  // 嘗試還原 focus
  if (activeBefore && filter.contains(activeBefore)) {
    activeBefore.focus();
  }
}
```

`activeElement` 在 reparent 前後仍指向同一個 DOM 節點（如果 focus 在 filter 內）。明確 `.focus()` 確保視覺一致。

### 風險 2：Scope filter 隱藏當前 focus 元素

**位置**：scope filter 的 `apply()`。

```js
items.forEach(function (el) {
  el.classList.toggle('is-scope-filtered', !show);
});
```

**判讀**：若使用者 focus 在某個 result（例如標題連結）、切換 scope 後該 result 被隱藏（display: none）— focus 跳到 body。

**症狀**：使用者 tab 到 result、切 scope、focus 不見了。

**第一個該查的**：

```js
function apply() {
  var activeBefore = document.activeElement;
  // ... 套用 scope filter
  if (activeBefore && getComputedStyle(activeBefore).display === 'none') {
    // 該元素被隱藏、focus 移到下一個可見的同類元素
    var nextResult = findNextVisibleResult(activeBefore);
    if (nextResult) nextResult.focus();
    else input.focus();   // 沒有下一個就回到 search input
  }
}
```

明確處理「focus 元素被隱藏時去哪」、不留給瀏覽器預設行為。

### 風險 3：Pagefind 重繪結果時 focus 流失

**位置**：使用者改 query 時、pagefind 重新渲染結果列表。

**判讀**：若使用者 tab 到第 1 個結果、修改 query、pagefind 替換整個結果列表 — 第 1 個結果被 remove、focus 跳到 body。

**症狀**：使用者打字過程中、tab 順序時不時被打回起點。

**第一個該查的**：這個情境較難解 — 框架管的 DOM 我們不能干預。可行的做法：

- 使用者打字時通常在 input 上、focus 不在結果列表 — 影響面小
- 若真有需要、用 tabindex / aria-activedescendant 模擬 focus 但不實際 focus DOM

### 風險 4：載入 pagefind UI 時 focus 行為

**位置**：頁面載入後 PagefindUI mount 約 200-500ms。

**判讀**：使用者開啟搜尋頁、瀏覽器把 focus 放 body、使用者按 tab — 應該到搜尋輸入框。

**症狀**：使用者開頁面立刻按 tab、focus 跳到網站其他部分（nav、其他 link）、不是搜尋框。

**第一個該查的**：考慮頁面載入後自動 focus 搜尋輸入框（auto-focus）— 對搜尋頁是合理 UX、不是干擾。

```js
waitForElement(searchRoot, '.pagefind-ui__search-input', function (input) {
  input.focus();
});
```

---

## 內在屬性比較：四種 focus 處理策略

| 策略                                           | 維護成本 | 涵蓋情境             | 風險               |
| ---------------------------------------------- | -------- | -------------------- | ------------------ |
| 不處理（瀏覽器預設）                           | 低       | 簡單情境             | focus 掉失常見     |
| Save / restore activeElement                   | 中       | DOM 移動、隱藏       | 大多有效           |
| 用 tabindex / aria-activedescendant 模擬 focus | 高       | 框架管的 DOM         | 較複雜、視框架行為 |
| Auto-focus 關鍵元素                            | 低       | 頁面載入、modal 開啟 | 使用者預期才適用   |

選擇順序：**簡單變動用 save / restore；framework 管的 DOM 用模擬 focus；關鍵元素用 auto-focus**。

---

## 盤點 focus 影響的具體步驟

對每個 JS 變動 DOM 的位置、列三個問題：

1. **這個變動會 reparent / remove / hide 哪些元素？**
2. **這些元素有可能是當前 focus 嗎？** （form input、checkbox、link 都是常見 focusable）
3. **若是、focus 該去哪？** （restore / next sibling / 預設位置）

回答完三題、變動前後加 save / restore 邏輯。

---

## 設計取捨：DOM 變動時的 focus 處理策略

四種做法、各自機會成本不同。這個專案選 A（save / restore activeElement）當預設、其他做法在特定情境合理。

### A：Save / restore activeElement（這個專案的預設）

- **機制**：JS 變動 DOM 前 `var activeBefore = document.activeElement`、變動後 `activeBefore.focus()`
- **選 A 的理由**：跨瀏覽器一致、簡單元件移動 / 顯隱都涵蓋
- **適合**：自家管的 DOM 變動（reparent、display: none、remove）
- **代價**：每個變動位置要顯式加 save / restore 邏輯（用 helper 包裝可一行）

### B：不處理（依瀏覽器預設）

- **機制**：JS 變動 DOM、不主動處理 focus
- **跟 A 的取捨**：B 簡單、A 有額外邏輯；但 B 結果不一致（Chrome / Safari 不同）、多數預設是「focus 跳 body」、使用者迷失
- **B 才合理的情境**：純展示元素變動（沒有 focusable 子元素）— 不會發生 focus 掉失

### C：用 tabindex / aria-activedescendant 模擬 focus

- **機制**：focus 物理上不動、用 attribute 標記「邏輯 focus」
- **跟 A 的取捨**：C 比 A 複雜、但能處理 framework 管的 DOM（無法 save / restore）
- **C 比 A 好的情境**：framework 持續重繪元素 identity、save / restore 失敗 — 用 attribute 表達 focus

### D：Auto-focus 關鍵元素

- **機制**：頁面載入後 / modal 開啟後自動 focus 預期的第一個元素
- **跟 A 的取捨**：D 不依變動觸發、A 對應變動處理；D 適合「使用者預期」的初始 focus
- **D 比 A 好的情境**：搜尋頁載入 → focus search input、modal 開啟 → focus 第一個 input — 使用者預期的場景才用

---

## 判讀徵兆

| 訊號                               | 該檢查的位置                            |
| ---------------------------------- | --------------------------------------- |
| 鍵盤使用者 tab 中途 focus 突然跳走 | 該時點是否有 JS 變動 DOM                |
| Resize 視窗後 focus 不見           | matchMedia callback 內加 save / restore |
| 切 filter / mode 後 focus 在 body  | apply 函式內處理被隱藏元素的 focus      |
| 開頁面立刻按 tab 跳到不對位置      | 評估是否該 auto-focus 主要互動元素      |

**核心原則**：JS 變動 DOM = focus 副作用。每個變動位置都該回答「focus 該去哪」、不留給瀏覽器預設。
