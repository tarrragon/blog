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

## 正確概念與常見替代方案的對照

### 視覺狀態用 class、值動態用 inline

**正確概念**：「顯示 / 隱藏」「啟用 / 停用」這類布林狀態用 class toggle；動態值（座標、尺寸）用 inline style。

**替代方案的不足**：所有 JS 改視覺都用 inline — 規則散在 JS、CSS 失去設計系統的角色。

### CSS Layers 後不再需要 important

**正確概念**：CSS Layers 把 vendor CSS 包進低權層、自家 unlayered 自動贏 — `!important` 不再有用武之地。

**替代方案的不足**：保留 `!important` 作 defensive 寫法 — important 之間沒層級、未來其他 important 對撞時 debug 困難。

### Class 名要語意化

**正確概念**：Class 名表達「為什麼這狀態」（`is-scope-filtered`）、不表達「視覺結果」（`is-display-none`）。

**替代方案的不足**：用 `is-hidden` / `is-display-none` 等視覺結果命名 — 改視覺實作（從 display:none 改 visibility:hidden）時 class 名不再貼切、要重命名。

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
