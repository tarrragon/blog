---
title: "CSS 變數定義位置統一"
date: 2026-04-25
weight: 26
description: "CSS 變數一次定義在離 root 最近的合適位置、其他地方只引用、不重複宣告。改 token 只動一處、避免散落多處難同步。"
tags: ["report", "事後檢討", "CSS", "Refactor", "工程方法論"]
---

## 核心原則

**CSS 變數的定義位置只能有一處。** 一次定義在離 root 最近的合適 selector（`:root` 或頁面層級的 body class），其他地方只用 `var()` 引用、不重複宣告。改 token 只動一處、所有引用點自動跟上。

---

## 為什麼定義位置要單一

### 商業邏輯

CSS 變數的價值是「單一來源、多處引用」。把定義散在多個 selector：

```css
:root           { --search-title-h: 64px; }
.search-shell   { --pagefind-ui-scale: 1.0; }
body.page-search { --search-form-h: 68px; }
```

每個變數的「真相」分散在不同位置 — 改一個 token 要先 grep 找到定義位置、可能漏改。

更嚴重：同名變數在不同 selector 重複定義時、值依 cascade 順序決定 — 維護者不易看出哪個值生效。

### 統一定義的位置選擇

| 位置              | 適用情境                | 影響範圍          |
| ----------------- | ----------------------- | ----------------- |
| `:root`           | 全站適用的 design token | 全站              |
| `body.page-X`     | 特定頁面類型適用        | 該類型頁面        |
| `.component-name` | 特定 component 內適用   | 該 component 子樹 |

選擇原則：**定義在「跟使用範圍最匹配的最高層級」selector**。全站用 `:root`、頁面類型用 body class、組件內用組件 class。

---

## 這次任務的散落問題

### 觀察

`search.html` 內 CSS 變數定義散在三處：

```css
body.page-search {
  --search-title-h: 64px;
  --search-form-h: 68px;
  --search-gap: 20px;
}

:root {
  --search-scope-h: 60px;   /* JS 量測會覆寫 */
}

.search-shell {
  --pagefind-ui-scale: 1.0;
}
```

三處定義 — 雖然各有理由（body 範圍、JS 寫入點、cascade 給 pagefind），但維護者要知道「改 search-form-h 在哪改」需要全文 grep。

### 判讀

整理後集中在 `body.page-search`（搜尋頁的 root selector）：

```css
body.page-search {
  /* 設計 token：寫死值 */
  --search-title-h: 64px;
  --search-form-h: 68px;
  --search-gap: 20px;

  /* JS 量測寫入 fallback：JS 會用 setProperty 覆寫到 :root */
  --search-scope-h: 60px;

  /* 給 pagefind cascade 的 scale */
  --pagefind-ui-scale: 1.0;
}
```

一個 selector 看到所有 search 相關 token、cascade 到子樹生效。

### 執行

JS 量測寫入 scope-h 時、寫到 `body.page-search` 而非 `:root`：

```js
function syncScopeHeight() {
  var h = scopeEl.offsetHeight || 56;
  document.body.style.setProperty('--search-scope-h', h + 'px');
}
```

寫到 body.style 直接覆蓋 body.page-search 的 fallback 值。Cascade 到所有後代生效。

---

## 變數命名與分類

### 命名前綴標明範圍

| 前綴                 | 範圍                                             |
| -------------------- | ------------------------------------------------ |
| `--token-*` 或無前綴 | 全站設計 token（顏色、字型）                     |
| `--page-search-*`    | 搜尋頁專用                                       |
| `--pagefind-ui-*`    | Pagefind 提供的 hook（不是我們命名、是組件預期） |

前綴讓維護者一眼看出變數的「歸屬」、不會誤改別處變數。

### 分類定義

```css
body.page-search {
  /* === 對齊 token === */
  --search-title-h: 64px;
  --search-form-h: 68px;
  --search-gap: 20px;
  --search-scope-h: 60px;     /* JS 寫入 */

  /* === 響應式 breakpoint === */
  /* (CSS 變數無法用在 @media query、breakpoint 寫死在 query 內) */

  /* === 對組件的 hook === */
  --pagefind-ui-scale: 1.0;
}
```

分類註解讓維護者知道「我要改哪類 token」、找對位置。

---

## 內在屬性比較：四種變數定義方式

| 方式                          | 維護成本         | 可見性             |
| ----------------------------- | ---------------- | ------------------ |
| 散在多個 selector 定義        | 高 — grep 找定義 | 低 — 不知哪個生效  |
| 集中在一個 selector           | 低 — 改一處      | 高 — 全部變數一覽  |
| 集中 + 分類註解               | 低               | 最高 — 結構化      |
| 集中 + JS 寫入用同一 selector | 低               | 最高 + JS 動態同步 |

優先選「集中 + 分類 + JS 寫入同 selector」。

---

## 變數的 fallback 策略

JS 量測寫入的變數、CSS 應該有 fallback 值供 JS 還沒跑完時用：

```css
body.page-search {
  --search-scope-h: 60px;   /* fallback、JS 會覆寫 */
}

.search-shell .pagefind-ui__drawer {
  margin-top: calc(var(--search-scope-h) + 8px);  /* JS 跑完前用 60px */
}
```

或用 `var()` 第二參數：

```css
margin-top: calc(var(--search-scope-h, 60px) + 8px);
```

兩種寫法效果相近 — 第一種讓 token 集中在 body.page-search 內、推薦使用。

---

## 正確概念與常見替代方案的對照

### 變數定義集中、引用分散

**正確概念**：所有變數在一個 selector 集中定義、其他地方只 `var()` 引用、不重複定義。

**替代方案的不足**：每個 component 各自定義需要的變數 — 同名 token 散落多處、cascade 順序決定值、不直觀。

### 定義位置 = 使用範圍的 root

**正確概念**：選定義位置時、找「使用範圍的最高層 selector」。全站用 `:root`、頁面用 body class、組件用組件 class。

**替代方案的不足**：所有變數都丟 `:root` — 不在乎 scope、可能跟其他組件變數命名衝突。

### JS 寫入用同一 selector

**正確概念**：JS 用 `setProperty` 寫入變數時、寫到「定義 fallback 的同一 selector」上、保持來源一致。

**替代方案的不足**：JS 寫到 element.style、CSS 在 body 定義 — 兩套機制、cascade 衝突難 debug。

---

## 判讀徵兆

| 訊號                               | Refactor 動作                 |
| ---------------------------------- | ----------------------------- |
| 同名變數在多個 selector 定義       | 集中到一個 selector、移除其他 |
| 改一個 token 要 grep 找定義位置    | 集中 + 分類註解               |
| Token 命名沒前綴、跟其他組件變數混 | 加範圍前綴（`--page-X-*`）    |
| JS 寫入變數的位置跟 CSS 定義不同   | 對齊到同一 selector           |
| 變數值在 cascade 中被另一處覆蓋    | 找出兩處、決定哪一處保留      |

**核心原則**：CSS 變數是設計 token 系統的基礎、定義位置就是 token 的「住址」。住址一個就好、不要一物多址。
