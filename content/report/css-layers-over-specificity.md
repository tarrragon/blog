---
title: "CSS Layers 取代 specificity 戰"
date: 2026-04-25
weight: 24
description: "用 @import url('vendor.css') layer(vendor) 把外部組件 CSS 包進低權層、自家 CSS 留在 unlayered 自動贏 — 不論 specificity 數值。本文展開取代 !important 與雙寫的方法。"
tags: ["report", "事後檢討", "CSS", "Refactor", "工程方法論"]
---

## 核心原則

**CSS Layers 把樣式覆寫從「線性 specificity 數字戰」改成「分組權重順序」。** 把外部組件 CSS `@import` 進一個 layer、自家 CSS 留在 unlayered，自家規則自動贏 — 不論個別 selector specificity 數值。一次設定、所有 `!important` 與 `.x.x` 雙寫 hack 可以拿掉。

---

## 為什麼 specificity 戰沒有贏家

### 商業邏輯

CSS specificity 是線性數字比較。組件作者用 `.x.svelte-yyy.svelte-yyy` 雙寫 specificity 30 → 自家用 `.search-shell .x` specificity 20 蓋不過 → 加 `.x.x` 雙寫到 30 → 還是看 source order → 加 `!important` → 跟其他 important 對撞 → 寫死多層 fallback。

每加一層覆寫成本累積、未來 debug 越來越難。每個 `!important` 都是一個 future debugging burden、`!important` 之間沒有層級可言。

### CSS Layers 的解法

CSS `@layer` 提供「分組權重」 — unlayered CSS > layered CSS（layer 越早宣告越低權）、跟 selector specificity 無關：

```text
unlayered { ... }              ← 最高權
@layer high { ... }
@layer medium { ... }
@layer low { ... }             ← 最低權
```

把組件 CSS 整包丟進某個 layer、自家 CSS 留 unlayered、自家規則自動贏所有組件規則 — **不論 specificity**。

---

## 這次任務的覆寫戰場

### 觀察

現在 `search.html` 內為了蓋過 pagefind specificity 30 的寫法：

```css
.pagefind-ui__filter-block { border-bottom: 0 !important; }
.pagefind-ui__filter-panel { display: none !important; }
.search-filter-slot fieldset { border: 0; padding: 0; margin: 0; }
```

每條都靠 `!important` 或 source order 取勝。可維護性低。

### 判讀

把 pagefind-ui.css 用 `@import` 包進 layer：

```css
@import url("/blog/pagefind/pagefind-ui.css") layer(pagefind);
```

自家 CSS 不加 layer 宣告、留 unlayered。自家規則優先級自動高於 layer(pagefind)。

### 執行：refactor 步驟

```css
/* search.html / assets/search.css */

/* 把 pagefind 的整包 CSS 包進 layer */
@import url("/blog/pagefind/pagefind-ui.css") layer(pagefind);

/* 自家 CSS 留 unlayered、自動贏 */
.pagefind-ui__filter-block {
  border-bottom: 0;            /* 不需要 !important */
}
.pagefind-ui__filter-panel {
  display: none;               /* 不需要 !important */
}
@media (min-width: 1400px) {
  .pagefind-ui__filter-panel { display: none; }
}
```

原本的 `<link href="...pagefind-ui.css" rel="stylesheet">` 改成上方 `@import` 寫法、確保 import 在自家 CSS 之前發生（layered CSS 不會阻擋 unlayered CSS 的優先級）。

---

## 內在屬性比較：四種 specificity 應對

| 方法                                 | 維護成本                         | 可讀性                      | 升級兼容性                            |
| ------------------------------------ | -------------------------------- | --------------------------- | ------------------------------------- |
| `!important` 對抗                    | 高 — 每加一條未來 debug 成本上升 | 低 — 不知為什麼要 important | 中 — 組件變更可能讓 important 用錯    |
| 雙寫 class（`.x.x`）                 | 中 — selector 看起來奇怪         | 低 — 維護者不知為什麼       | 中 — 組件改 class 名就失效            |
| Inline style + setProperty important | 高 — 散落在 JS 各處              | 最低 — 不在 CSS 找不到      | 低 — JS 規則容易被 framework 重繪打破 |
| CSS Layers                           | 低 — 一次設定、規則簡單          | 高 — 結構化分層             | 高 — 跟組件升級無關                   |

**Layers 的所有指標都最佳**。其他三種是 Layers 之前的 workaround、現在沒理由繼續用。

---

## Layers 的進階用法

### 多個外部組件分別 layer

```css
@import url("vendor-a.css") layer(vendor-a);
@import url("vendor-b.css") layer(vendor-b);

@layer vendor-a, vendor-b;   /* 後宣告的優先 */

/* 自家 unlayered */
.my-overrides { ... }
```

`@layer name1, name2;` 顯式宣告 layer 順序、後宣告的權重高。

### 自家 CSS 也分層

```css
@layer base, components, utilities;

@layer base {
  body { font-family: ... }
}
@layer components {
  .button { padding: ... }
}
@layer utilities {
  .text-center { text-align: center; }
}
```

自家 CSS 內部也分層、避免 utilities 被 components 蓋過。

### 跟 unlayered 並存

不是所有自家 CSS 都要分 layer。**最高優先的自家規則留 unlayered、其他規則可以分層**。

---

## 瀏覽器支援

CSS Layers 在所有主流瀏覽器（Chrome 99+、Firefox 97+、Safari 15.4+）支援、2022 年起。當前（2026）所有現代瀏覽器都支援。

對舊瀏覽器降級：不支援 `@layer` 的瀏覽器會把整個 `@layer { ... }` block 當作 invalid 跳過 — 自家 unlayered 規則仍然適用、效果一樣（但 vendor CSS 完全失效）。實務上不需要擔心。

---

## 設計取捨：覆寫外部組件 CSS 的策略

四種做法、各自機會成本不同。這個專案選 A（CSS Layers）當預設、其他做法在特定情境合理。

### A：CSS Layers（這個專案的預設）

- **機制**：`@import url(...) layer(vendor)` 把外部 CSS 包進低權層、自家 unlayered CSS 自動贏
- **選 A 的理由**：跨組件升級穩定、規則簡單、`!important` 完全不需要、跳出 specificity 線性比較戰場
- **適合**：所有現代瀏覽器（Chrome 99+ / Firefox 97+ / Safari 15.4+）的客製情境
- **代價**：需要重新引入 vendor CSS（從 `<link>` 改 `@import`）

### B：雙寫 class 提升 specificity

- **機制**：`.pagefind-ui__filter-block.pagefind-ui__filter-block` 寫兩次提升 specificity 從 10 到 20
- **跟 A 的取捨**：B 不需要改 vendor CSS 引入方式、A 需要；但 B 跟組件 specificity 競賽（組件作者改 hash 寫法就壞）、A 跳出競賽
- **B 是反模式**：跟組件 specificity 競賽（組件作者改 hash 寫法就壞） — 唯一例外是 vendor CSS 不能用 `@import` 引入（極罕見的 build pipeline 限制）

### C：`!important` 對抗

- **機制**：每條覆寫加 `!important`、用 importance 取勝
- **跟 A 的取捨**：C 短期有效、長期 important 之間沒層級可言；多個 important 對撞時 debug 困難
- **C 才合理的情境**：CSS Layers 不支援的舊瀏覽器（< 2022 的版本）、且確認沒其他 important 對撞

### D：Inline style + `setProperty('important')`

- **機制**：JS 用 `el.style.setProperty('display', 'none', 'important')`
- **成本特別高的原因**：規則散落在 JS 各處、devtools 看不出意圖、跟 framework 重繪競爭
- **D 才合理的情境**：動態值（runtime 算的位置 / 尺寸）必須用 inline 表達 — 但即使這樣、也建議用 class toggle + CSS 變數（[#28](../class-toggle-over-important/)）取代

---

## 判讀徵兆

| 訊號                                        | Refactor 動作                               |
| ------------------------------------------- | ------------------------------------------- |
| 為了蓋過組件規則寫了 `!important`           | 評估改用 CSS Layers                         |
| Selector 寫成 `.x.x` 雙寫只為了 specificity | 評估改用 CSS Layers                         |
| 覆寫邏輯散落在多個檔案 / inline style       | 集中到一份 CSS、用 layers 分層              |
| 組件升級後覆寫失效                          | 用 layers 隔離、跟組件 specificity 變動脫鉤 |

**核心原則**：跟組件 CSS 競爭 specificity 是不必要的戰爭。Layers 提供更高層的權重機制、把覆寫簡化成「自家 vs 別人」的二元決定。
