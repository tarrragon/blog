---
title: "以 class toggle 取代 inline `display: none !important`"
date: 2026-04-25
weight: 28
description: "JS 用 `el.style.setProperty('display', 'none', 'important')` 是低層次 hack。在 CSS Layers 環境下、用語意化 class + JS toggle 可以更乾淨、更易 debug。"
tags: ["report", "事後檢討", "CSS", "JavaScript", "Refactor", "工程方法論"]
---

## 核心原則

**JS 改 DOM 元素的視覺狀態、用 class toggle、不用 inline style.setProperty important hack。** Class toggle 的好處：CSS 規則集中可讀、devtools 看到語意化的 class 名而非神秘 inline style、未來改視覺只動 CSS 不動 JS。

---

## 為什麼 class toggle 比 inline style 好

### 商業邏輯

兩種方式都能達成「JS 控制視覺」、差別在「視覺規則的家在哪」：

| 方式                                                                | 視覺規則住址 | 維護成本                     |
| ------------------------------------------------------------------- | ------------ | ---------------------------- |
| `el.style.display = 'none'`                                         | 散在 JS 各處 | 高 — 改視覺要找 JS、不在 CSS |
| `el.classList.toggle('is-hidden')` + `.is-hidden { display: none }` | 集中在 CSS   | 低 — 改視覺改 CSS            |

集中在 CSS = 設計系統的單一來源、devtools Element 面板看 class 知道狀態、code review 容易理解。

`!important` 的需求消失：只要 CSS Layers 把 vendor CSS 包進低權層、自家 unlayered CSS 自然贏、不需要 important。

### 何時 inline style 是必要的

| 情境                           | inline style 必要                       |
| ------------------------------ | --------------------------------------- |
| 動態值（隨 runtime 計算）      | 是 — 如 `el.style.top = scrollY + 'px'` |
| 動畫起點 / 終點                | 是 — `el.style.transform = ...`         |
| 切換 boolean 狀態（顯示/隱藏） | 否 — 用 class toggle                    |
| 套用設計系統一致樣式           | 否 — 用 class toggle                    |

「狀態切換」是 class toggle 的場景、不是 inline style 的場景。

---

## 這次任務的重構機會

### 觀察

Scope filter 用：

```js
items.forEach(function (el) {
  var show = scope === 'title' ? re.test(title) : re.test(excerpt);
  if (show) {
    el.style.removeProperty('display');
  } else {
    el.style.setProperty('display', 'none', 'important');
  }
});
```

`setProperty important` 是為了壓過 Svelte 重繪可能 reset 的 inline style。CSS Layers 之後、important 不再必要。

### 判讀

改用 class toggle + layered CSS：

```css
/* assets/search.css，unlayered（pagefind 在 layer(pagefind) 內） */
.pagefind-ui__result.is-scope-filtered {
  display: none;
}
```

```js
items.forEach(function (el) {
  var show = scope === 'title' ? re.test(title) : re.test(excerpt);
  el.classList.toggle('is-scope-filtered', !show);
});
```

更乾淨：

- CSS 規則集中
- DevTools Element 面板看到 `.is-scope-filtered` 就知道為什麼隱藏
- JS 邏輯簡化（`classList.toggle` 一行解兩種狀態）
- 不需要 `!important`

### 執行 prerequisite

要這個 refactor 生效、先做 #24（CSS Layers）：

```css
@import url("/blog/pagefind/pagefind-ui.css") layer(pagefind);

/* unlayered，自動勝過 pagefind 的所有 specificity */
.pagefind-ui__result.is-scope-filtered { display: none; }
```

否則 layered 的 pagefind CSS 可能用 specificity 30 蓋過 `.is-scope-filtered`（specificity 20）。

---

## 內在屬性比較：四種 JS 控制視覺方式

| 方式                                                      | 維護成本               | DevTools 可讀性           | Important 需求          |
| --------------------------------------------------------- | ---------------------- | ------------------------- | ----------------------- |
| `el.style.display = 'none'`                               | 中 — 規則散在 JS       | 中 — 看到 inline style    | 否                      |
| `el.style.setProperty('display','none','important')`      | 高 — important 散在 JS | 中                        | 是 — 跟 framework 競爭  |
| `el.classList.toggle('is-hidden')` + CSS                  | 低 — 規則在 CSS        | 高 — 看 class 知狀態      | 否（CSS Layers 環境下） |
| `el.dataset.state = 'hidden'` + `[data-state=hidden]` CSS | 低 — 規則在 CSS        | 高 — attribute 也表達狀態 | 否                      |

優先選 class toggle（或 dataset） — CSS-first、可讀、可維護。

---

## Class toggle 的命名慣例

### 用 `is-X` / `has-X` 表狀態

```css
.is-scope-filtered { display: none; }
.is-loading { opacity: 0.5; }
.has-error { border-color: red; }
```

`is-` / `has-` 前綴讓「狀態 class」跟「結構 class」（如 `.search-shell`）視覺區分、code review 一眼看出哪些是動態狀態。

### 用 BEM modifier

```css
.search-result--filtered { display: none; }
```

BEM 風格也可以、看專案 convention。重點是有規律、不要混雜。

---

## DevTools 可讀性的具體差異

### Inline style 視角

```html
<div class="pagefind-ui__result svelte-j9e30" style="display: none !important;">
```

DevTools 顯示「inline style 設了 important」 — 但不知道為什麼。要 grep JS 找出哪段邏輯設的。

### Class toggle 視角

```html
<div class="pagefind-ui__result svelte-j9e30 is-scope-filtered">
```

DevTools 顯示「有 `.is-scope-filtered` class」 — class 名本身解釋為什麼隱藏。CSS 面板也直接顯示對應規則。

---

## 設計取捨：JS 控制視覺狀態的策略

四種做法、各自機會成本不同。這個專案選 A（class toggle）當預設、其他做法在特定情境合理。

### A：Class toggle + CSS 規則（這個專案的預設）

- **機制**：`el.classList.toggle('is-scope-filtered')`、CSS 內定義 `.is-scope-filtered { display: none }`
- **選 A 的理由**：CSS 規則集中、devtools 看 class 知狀態、改視覺只動 CSS、配 CSS Layers 不需 `!important`
- **適合**：布林狀態切換（顯示 / 隱藏 / 啟用 / 停用）
- **代價**：需要在 CSS 預先定義 class 規則（多一份 CSS）

### B：Inline `style.X = ...`

- **機制**：`el.style.display = 'none'`
- **跟 A 的取捨**：B 一行 JS、A 需要 CSS 規則；但 B 規則散在 JS 各處、devtools 看到 `display: none` inline 不知道為什麼
- **B 比 A 好的情境**：runtime 計算的動態值（`el.style.top = scrollY + 'px'`）— 這類值無法預先寫進 CSS

### C：Inline + `setProperty('important')`

- **機制**：`el.style.setProperty('display', 'none', 'important')`
- **跟 A/B 的取捨**：C 比 B 多 important、為了壓過 framework 重繪 reset 的 inline；但 C 進入 `!important` 戰、未來新 important 對撞 debug 困難
- **C 才合理的情境**：framework 強制 reset 自家 inline style、且不能用 layered CSS（極罕見）
- **更好的解**：用 [#24 CSS Layers](../css-layers-over-specificity/) 解 specificity 戰、本卡片 A 即可

### D：Dataset attribute + CSS attribute selector

- **機制**：`el.dataset.state = 'hidden'`、CSS `[data-state="hidden"] { display: none }`
- **跟 A 的取捨**：D 用 attribute 表狀態、A 用 class；D 在「狀態值多種」時更合適（例如 `data-state="loading|ready|error"`）
- **D 比 A 好的情境**：狀態有多個值（不只 boolean）、需要 CSS attribute selector 表達多分支

---

## 判讀徵兆

| 訊號                                        | Refactor 動作                                               |
| ------------------------------------------- | ----------------------------------------------------------- |
| JS 用 `style.setProperty(..., 'important')` | 改用 class toggle、用 CSS Layers 解決 specificity           |
| `el.style.display = 'none'` 散落多處        | 集中為 `.is-X` class、JS 只 toggle                          |
| DevTools 看到 inline style 不知為什麼       | 改用語意化 class、devtools 看 class 自帶解釋                |
| 視覺改動要改 JS（不是 CSS）                 | Refactor 為 class toggle、視覺改動只動 CSS                  |
| 改視覺需要對抗 framework reset              | 用 CSS Layers 把 framework 規則降層、自家規則不需 important |

**核心原則**：CSS 是視覺規則的家、JS 控制狀態 - 兩者透過 class toggle 介面共處、不互相侵入。
