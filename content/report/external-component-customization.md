---
title: "在外部組件上加客製功能：以邊界為中心的方法選擇"
date: 2026-04-25
weight: 1
description: "客製外部組件穩定的程度取決於『離組件邊界多近』。本文用 Pagefind 整合到 Hugo theme 的三個情境（索引邊界、重置邊界、specificity 邊界）展開：在邊界上客製為什麼穩、各種替代方案的不足、以及下次提早辨識的訊號。"
tags: ["report", "事後檢討", "Pagefind", "CSS", "Svelte", "工程方法論"]
---

## 核心原則

**客製外部組件的穩定性與「離組件邊界多近」成正比。** 組件作者維護組件內部的一致性；客製貼著組件的對外介面（CLI 參數、CSS reset 邊界、CSS layer）做，組件升級不會打到客製。深入組件內部（注入子節點、改 source 行為）的客製則仰賴組件的內部實作，作者不保證下個版本還相容。

這條原則對應到 Pagefind 整合時的三個具體情境，本文逐一拆解。

---

## 邊界概念：為什麼用「邊界」看外部組件

### 這類問題的本質（商業邏輯）

組件 = 一組對外契約 + 內部實作。對外契約是作者保證的東西（CLI 參數、CSS class name、CSS variable hooks），內部實作是達成契約的手段、可能在版本之間變動。

客製貼著對外契約做，等於跟作者站在同一邊；客製動到內部實作，等於跟作者每個版本對抗。

「邊界」這個概念把組件分成「契約面」與「實作面」 — 客製選位置時，依離邊界遠近排序：

| 客製位置        | 跨越時的依賴                         |
| --------------- | ------------------------------------ |
| 組件對外介面    | 介面契約（穩定）                     |
| 組件 DOM 邊界外 | 邊界元素的 class / id 名稱（半穩定） |
| 組件 DOM 邊界內 | 內部 DOM 結構（隨框架渲染週期變動）  |
| 組件內部邏輯    | source code（升級時必衝突）          |

### 這次任務涉及的邊界（CASE）

Pagefind 提供三條值得辨識的邊界：

| 邊界名稱         | 介面形式                       | 範圍                 |
| ---------------- | ------------------------------ | -------------------- |
| 索引邊界         | `--root-selector` 參數         | 「組件看到什麼資料」 |
| 重置邊界         | `.pagefind-ui--reset` class    | 對 UA 樣式的覆寫範圍 |
| specificity 邊界 | svelte hash class（雙寫到 30） | 組件 CSS 的權重起點  |

每條邊界各有對應的客製介面 — 緊貼這些介面比繞道進內部安全得多。

---

## 索引邊界：用 root-selector 限縮搜尋範圍

**核心定義**：Pagefind 的索引流程透過 `--root-selector` 參數控制「哪些 HTML 進索引」。這是組件預期的客製介面。

**這次的觀察**

theme 的 site header 包含 `<h1>{{ .Site.Title }}</h1>`，每一頁 DOM 上的第一個 h1 都是站名「Tarragon」。Pagefind 預設取頁面第一個 h1 當搜尋結果 title — 結果所有結果都顯示「Tarragon」。

**判讀**

第一個 h1 是站名而非文章名 — 索引「看到」的範圍跟我們以為的不同。要修的不是 theme（影響其他頁面），是 Pagefind 的 input 範圍。

**執行**

```bash
npx -y pagefind --site public --root-selector main
```

`<main>` 內才包含文章 h1；site header 在 `<body>` 直接子節點、不在 `<main>` 內，自然被排除。

**完成標準**：每一筆結果的 title 顯示文章 h1，而非站名。

---

## 重置邊界：在落腳處重建 UA 樣式

**核心定義**：CSS reset 的有效範圍與 ancestor class 綁定。元素換位置就換 reset context — 這是 CSS 的基本機制，不是 bug。

**這次的觀察**

Filter UI（`.pagefind-ui__filter-panel`，本質是 `<fieldset>`）需要從 `.pagefind-ui` 搬到外部 aside（左側 sidebar）。搬完後 fieldset 的瀏覽器預設邊框冒出來。

**判讀**

`.pagefind-ui--reset` 用 `all: unset` 重置所有後代元素的 UA 樣式。fieldset 搬出 `.pagefind-ui` 後，這個 ancestor 不在了，UA 樣式（包括 fieldset 預設邊框）回到原樣。

**執行**

在 fieldset 落腳處（aside 內）重新關掉 UA 樣式：

```css
.search-filter-slot fieldset {
  border: 0;
  padding: 0;
  margin: 0;
}
```

**完成標準**：fieldset 在新位置看起來跟在 `.pagefind-ui` 內一樣 — 沒有多餘邊框。

---

## specificity 邊界：跳出線性比較戰場

**核心定義**：當組件透過 hash class 把 specificity 拉高到一般客製寫法蓋不過時，邊界落在 CSS 樣式分層機制 — 不在個別 selector 數字。

**這次的觀察**

Pagefind 透過 svelte 把 class name 加 hash 重複寫進 selector（`.x.svelte-y.svelte-y`），把 specificity 從 10 提升到 30。一般客製 CSS specificity 10-20、蓋不過去。

**判讀**

Specificity 是線性數字比較 — 跟組件作者比 specificity 是無贏的軍備競賽。要真正解這類覆寫戰、需要跳出「線性比較」這個維度本身。

**執行**

具體做法（`@import url(...) layer(...)`）與升級兼容性、其他外部組件的 layer 策略，由 [#24 CSS Layers 取代 specificity 戰](../css-layers-over-specificity/) 完整展開。在邊界辨識上、本篇要記住的是：**遇到 specificity 30+ 的覆寫戰、不要往 `!important` / `.x.x` 雙寫的方向加碼、改去看 layer 維度**。

**完成標準**：所有原本需要 `!important` 或 `.x.x` 雙寫的覆寫，可以用單純的 class selector 寫。

---

## 客製深度的內在屬性比較

選擇客製位置時，用三個**內在屬性**比較 — 不用「實作要多久」這類時間維度：

| 位置                      | 依賴前提                 | 升級風險                  | 可逆性                      |
| ------------------------- | ------------------------ | ------------------------- | --------------------------- |
| 組件對外介面              | 介面 stable across 版本  | 低 — 介面是公開契約       | 高 — 改一個參數即可還原     |
| DOM 邊界外（class hooks） | 邊界元素 class / id 穩定 | 中 — class 改名才打破     | 中 — 改選擇器即可           |
| DOM 邊界內                | 內部 DOM 結構穩定        | 高 — 框架重繪可能即時打破 | 低 — 客製跟內部結構深度耦合 |
| 內部邏輯（fork / patch）  | 整個組件 source          | 最高 — 升級必衝突         | 最低 — 重新 merge           |

**選擇順序**：先試最外層；不夠用再往內推一層。每往內一層、依賴前提增加、升級風險上升、可逆性下降。

---

## 設計取捨：客製位置的層次選擇

四種做法、各自機會成本不同。預設選最外層（A）、不夠用才往內推一層。

> 本篇是 [#45 跟外部組件合作的層次](../external-component-collaboration-layers/) 抽象原則在「客製位置選擇」這個面向的應用。

### A：組件公開介面層（最佳）

- **機制**：用組件提供的 CLI 參數、props、CSS variable hook、event API 客製
- **選 A 的理由**：作者保證跨版本相容、客製跟組件升級無關
- **適合**：能被介面覆蓋的客製需求（多數常見場景）
- **代價**：受介面範圍限制、超出範圍只能往內推

### B：鄰接層（class hooks、reset 邊界）（這個專案的次選）

- **機制**：用組件邊界元素的 class / id / data attribute 寫客製 CSS、注意 CSS reset 邊界
- **跟 A 的取捨**：B 介面外但仍貼著組件邊界、A 在介面內；B 在 class 名穩定時 OK、改名就壞
- **B 比 A 好的情境**：組件未提供對應介面、但有穩定的 class 邊界可掛勾

### C：邊界內 DOM 操作

- **機制**：JS 改組件內部 DOM 結構 / 節點屬性 / 注入元素
- **跟 A/B 的取捨**：C 直接操控、跟 framework reconciliation 競爭；風險顯著上升
- **C 才合理的情境**：A/B 都無法達成、且能容忍每次升級重做（[#13](../component-boundary-and-js-impact/) 的安全規則必看）

### D：Fork / patch 組件 source

- **機制**：fork 整個組件、改 source code、自家維護版本
- **成本特別高的原因**：每次升級都要 merge upstream、客製永久綁在 fork
- **D 才合理的情境**：客製需求超過所有其他選項、且願意承擔 fork 維護成本

---

## 判讀徵兆

下次遇到組件整合任務、看到這些訊號就走「找邊界」的路：

| 訊號                            | 對應邊界類型     | 第一個該嘗試的動作                                             |
| ------------------------------- | ---------------- | -------------------------------------------------------------- |
| 組件抓到的資料超過你想要的範圍  | 索引邊界         | 找組件的 `root` / `scope` / `selector` 參數                    |
| 同一段 CSS 在不同位置表現不一致 | 重置邊界         | 比對兩個位置的 ancestor class、看 reset 是否還在               |
| `!important` 寫了還是沒蓋過     | specificity 邊界 | 看組件 CSS 是否用 hash class 提升 specificity；考慮 CSS Layers |
| 組件渲染後客製 UI 消失          | DOM 結構邊界     | 把客製 UI 搬出組件、用 CSS 控制視覺位置                        |
| 組件升級後客製失效              | 內部邏輯邊界     | 把客製重寫到組件介面層                                         |

**使用順序**：訊號出現 → 對應邊界 → 嘗試該邊界提供的介面 → 介面不夠用、才考慮往內推一層。
