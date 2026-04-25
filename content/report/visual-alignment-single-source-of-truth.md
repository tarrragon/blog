---
title: "視覺對齊用單一真實來源"
date: 2026-04-25
weight: 3
description: "視覺對齊的本質是『同一條基準線在多個元素上重現』 — 任何元素的尺寸沒有來源明確的數字，整條線都靠不住。本文說明 CSS 變數 + 必要時 ResizeObserver 寫回，讓多處引用同一個值。"
tags: ["report", "事後檢討", "CSS", "Layout", "工程方法論"]
---

## 核心原則

**多個元素要對齊，每個元素的尺寸都需要「來源明確的數字」 — 寫死的 token 或 runtime 量測寫回變數，二選一不要混搭。** 任何一個值含糊（猜的、估的、依字型自然渲染的），整條對齊基準就靠不住、修一處要找十處跟著改。

---

## 為什麼對齊需要單一來源

### 商業邏輯

對齊問題本質是**線性方程組**：每個參與對齊的元素貢獻一個未知數，要解出對齊的 padding / margin / position 等變數，所有未知數都要有確定值。任一個未知數憑感覺給，整組無解。

CSS 變數提供「一處定義、多處引用」的單一來源 — 改 token 只動一個值、所有引用點自動跟上。

### 兩種值來源、不要混搭

| 值的性質                  | 確定方式                         | 例子                             |
| ------------------------- | -------------------------------- | -------------------------------- |
| 設計可決定的固定值        | CSS 變數寫死                     | H1 height、icon size             |
| Runtime 依字型 / 內容變動 | ResizeObserver 量測寫回 CSS 變數 | 多行文字區塊高度、圖片自適應高度 |

混搭的後果：寫死值跟實際渲染不一致時，對齊只在某些字型 / 螢幕 / 瀏覽器下成立、其他情境壞掉、且難以重現。

---

## 這次任務的實際應用

### 觀察

搜尋頁有四處要共用同一組視覺 token：

| 元素                         | 為什麼需要這個值     |
| ---------------------------- | -------------------- |
| H1「搜尋」                   | 自身 height          |
| Pagefind search input        | 自身 height          |
| Filter sidebar `padding-top` | 對齊到 results 頂端  |
| Drawer `margin-top`          | 為 scope UI 讓出空間 |

### 判讀

H1 與 input 的 height 是設計可決定的固定值 — 用 CSS 變數寫死。Scope UI 的 height 受字型 / 換行影響、不可預測 — 用 ResizeObserver 量測寫回。

### 執行：CSS 變數定義

```css
body.page-search {
  --search-title-h: 64px;     /* 設計決定 */
  --search-form-h: 68px;      /* pagefind input 64 + border 4，鎖定 scale=1.0 */
  --search-gap: 20px;         /* drawer margin-top */
  /* --search-scope-h 由 JS 量測寫入 :root */
}
```

### 執行：JS 量測寫回

```js
function syncScopeHeight() {
  var h = scopeEl.offsetHeight || 56;
  document.documentElement.style.setProperty('--search-scope-h', h + 'px');
}
syncScopeHeight();
new ResizeObserver(syncScopeHeight).observe(scopeEl);
```

### 執行：多處引用

```css
.search-title { height: var(--search-title-h); }
.search-shell .pagefind-ui__drawer { margin-top: calc(var(--search-scope-h) + 8px); }
.search-filter-slot {
  padding-top: calc(
    var(--search-title-h) + var(--search-form-h)
    + var(--search-scope-h) + 8px + var(--search-gap)
  );
}
```

---

## 對齊問題的兩種失敗模式

| 失敗模式               | 表現                                | 根因                                |
| ---------------------- | ----------------------------------- | ----------------------------------- |
| 寫死值與實際渲染不一致 | 字型變動或 scale 改變後對不齊       | 沒控制渲染參數（如 pagefind scale） |
| 用估算值代替量測       | 邊界情境（短/長文字、特殊字型）壞掉 | 把不可預測的值當固定值處理          |

兩者共通的修法是：**確認每個值的性質、按性質選來源**。

---

## 鎖定渲染參數讓寫死值生效

當值「理論上可預測」但需要強制條件時，鎖定渲染參數。

**核心定義**：Pagefind input 高度 = `64px × --pagefind-ui-scale`。把 scale 設成 1.0、input 自然渲染為 64px、加 border 4px 共 68px、剛好等於我們的 `--search-form-h`。

```css
.search-shell { --pagefind-ui-scale: 1.0; }
```

把組件提供的 scale 變數拉進自家設計系統 — 組件配合我們、不是我們配合組件。

---

## 正確概念與常見替代方案的對照

### 對齊靠變數、不靠複製數字

**正確概念**：對齊基準寫成 CSS 變數，每個引用點都從變數計算。

**替代方案的不足**：在多處複製同一個 magic number（`padding-top: 152px` 寫好幾個地方）— 改一處要找全部、漏改一個就壞、code review 看不出哪些是「應該相等」。

### 寫死與量測二選一

**正確概念**：每個值依其可預測性，選擇 CSS 變數寫死或 ResizeObserver 量測寫回。**選定後不要混搭**。

**替代方案的不足**：對齊基準混合「猜的值」與「量測的值」 — 兩者在某些情境下不一致時，難以判斷哪個值錯了。

### 鎖渲染參數，把組件納入設計系統

**正確概念**：組件提供的尺寸變數（pagefind scale）拉到自家設計系統的 token 一起管理。

**替代方案的不足**：保留組件預設 scale（0.8）、再用 calc 適配 — 自己加一層轉換、未來改 scale 又要重算所有引用點。

---

## 判讀徵兆

| 訊號                                 | 可能的根因                     | 第一個該檢查的事                                 |
| ------------------------------------ | ------------------------------ | ------------------------------------------------ |
| 改一個 CSS 數字、要去 N 個地方跟著改 | 缺少單一來源                   | 找出複製的 magic number、提成 CSS 變數           |
| 設計稿對齊但實作對不齊               | 把可變值當固定值               | 量測該元素的真實 height、決定改用 ResizeObserver |
| 字型變動或 dark mode 後對齊壞掉      | 寫死值依賴某個沒鎖定的渲染參數 | 找出該渲染參數、用 CSS 變數鎖定                  |
| 對齊「大部分時候對」、邊界 case 壞掉 | 沒處理動態高度                 | 把該值用 ResizeObserver 量測寫回                 |

**核心原則**：對齊不是視覺問題，是「每個參與元素是否有確定尺寸」的問題。任何一個值不確定、整組對齊就脆弱。
