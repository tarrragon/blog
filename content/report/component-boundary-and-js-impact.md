---
title: "元件邊界與 JS 操作的影響範圍"
date: 2026-04-25
weight: 13
description: "JS 操作前界定『此次動的是哪個元件、邊界在哪、state 由誰維護』 — 邊界不清楚就會誤動到框架管的部分、引發超乎預期的副作用。本文展開元件邊界的契約思考。"
tags: ["report", "事後檢討", "JavaScript", "DOM", "工程方法論"]
---

## 核心原則

**JS 操作前先界定「動的是哪個元件、邊界在哪、state 由誰維護」 — 邊界 = 契約。** 沒列清楚邊界就 patch DOM，等於跨進別人領地，副作用來自意料之外的責任歸屬。動的範圍越小越安全。

---

## 為什麼邊界要先列清楚

### 商業邏輯

每個元件（自家或 framework 提供）都有「對外契約」與「內部實作」。對外契約包括：

| 契約類型     | 內容                                 |
| ------------ | ------------------------------------ |
| DOM identity | 哪些 class / id / attribute 是穩定的 |
| State 來源   | 元件內部 state 由誰寫 / 何時改       |
| 渲染週期     | 元件何時重繪、重繪時影響哪些 DOM     |
| 對外介面     | 提供哪些 props / events / API hooks  |

JS 操作前不知道這些 = 黑箱操作。動了什麼、會觸發什麼、誰會被影響、不可預測。

### 邊界宣告的格式

開始 JS 操作之前、寫一段註解或 mental note：

```text
動什麼：filter-panel 的 parent
邊界：filter-panel 整個節點 OK，內部子節點屬於 pagefind 管
State：checkbox 勾選狀態存在 panel 子節點上、由 pagefind 維護
動作：appendChild 整節點 reparent
```

這段宣告把「動什麼」「不能動什麼」「為什麼安全」說清楚。

---

## 這次任務的邊界辨識

### 觀察

四個 JS 操作場景、各有不同邊界：

| 場景                                   | 動的對象                    | 邊界                                                   |
| -------------------------------------- | --------------------------- | ------------------------------------------------------ |
| 把 filter-panel 從 drawer 搬到 sidebar | 整節點 reparent             | filter-panel 是 pagefind 管的、整節點搬 OK，內部不動   |
| reorder type / tag filter              | filter 子節點順序           | 子節點順序是「展示順序」、pagefind 不依賴順序          |
| 注入 scope UI                          | 自家新元件                  | scope 是自家元件、放在 search-shell 內、不動 framework |
| Filter 結果 hide / show                | pagefind 結果元素的 display | 元素由 pagefind 維護、改 inline style 是邊界灰區       |

### 判讀

第一三個場景邊界明確：

- filter-panel reparent：搬整節點 = 不動內部 = 安全。
- scope UI 注入 search-shell：自家領域、自由操作。

第二個有風險：reorder filter 子節點 = 動 framework 內部。但因為 pagefind 的渲染週期不會 reset filter 順序（filter 順序不是 reactive 屬性、只在初次 mount 時生成），實際安全。

第四個是灰區：pagefind 沒明確說「結果元素的 display 不可改」、但 svelte 可能在重繪時 reset。實作上加 `setProperty('display', 'none', 'important')` + MutationObserver 補打、是因應這個灰區的 workaround。

### 執行原則

操作前的決策樹：

```text
動的是誰的元件？
├── 自家：自由操作
└── Framework 管的：
    ├── 整節點 reparent → 安全（節點 identity 不變）
    ├── 動內部子節點 → 風險高（框架可能 reconcile）
    │   └── 確認該屬性是否 reactive（讀框架 source）
    └── 動節點 attribute / inline style → 灰區
        └── 加防禦性策略（important / observer 補打）
```

---

## 內在屬性比較：四種 JS DOM 操作的安全度

| 操作類型                                  | 安全度                   | 適用情境                           |
| ----------------------------------------- | ------------------------ | ---------------------------------- |
| 自家元件內所有操作                        | 最高                     | 自由                               |
| Framework 元件整節點 reparent             | 高                       | DOM 移動                           |
| Framework 元件內部子節點順序調整          | 中 — 視 framework 而定   | reorder 等不影響 reactivity 的操作 |
| Framework 元件的 attribute / inline style | 低 — 框架隨時可能 revert | 加防禦性 observer / important      |
| Framework 元件 source 修改                | 不適用 — fork 級操作     | 升級時必衝突                       |

選擇順序：**先試最高安全度的方式達成需求；成本太高再降級**。

---

## 邊界宣告的實踐

### 寫成 JSDoc 或 inline 註解

```js
/**
 * 把 .pagefind-ui__filter-panel 從 drawer 搬到外部 sidebar。
 *
 * 邊界：
 *   - 動：filter-panel 整節點的 parent
 *   - 不動：filter-panel 內部子節點（由 pagefind 管）
 *   - State：checkbox 勾選由 pagefind 維護、跟著節點走
 *
 * 為什麼安全：節點 identity 不變、pagefind 在下次 patch
 * 時看到節點還在、繼續更新內部。
 */
function place() {
  if (mql.matches) sidebar.appendChild(filter);
  else drawer.insertBefore(filter, drawer.firstChild);
}
```

註解是給未來的自己 / 同事看的「契約備忘」 — 看到操作時知道為什麼安全。

### 邊界違反時的 fail-safe

對「灰區」操作（如改 framework 元素 inline style）加防禦：

```js
// 防 svelte 重繪時 reset display
el.style.setProperty('display', 'none', 'important');
new MutationObserver(reapply).observe(parent, { childList: true, subtree: true });
```

`setProperty('important')` 把 inline style 提升優先度、observer 補打 reset 後的元素 — 即使 framework 介入、結果仍維持。

---

## 正確概念與常見替代方案的對照

### 邊界先界定、操作後執行

**正確概念**：JS 操作前列清楚「動什麼、邊界在哪、state 誰管」、確認操作不跨界。

**替代方案的不足**：直接 querySelector + 改 — 不知道改的是誰的領地、bug 出現時不知道從哪查起。

### 整節點 reparent 比改內部安全

**正確概念**：要影響 framework 元件的位置，整節點搬到別處（identity 不變）、不要在內部 appendChild 加東西（框架不認得）。

**替代方案的不足**：在 framework 元件內 appendChild 加 wrapper — 看似省事、framework 重繪時清掉。

### 灰區操作要加 fail-safe

**正確概念**：對 framework 元素的 attribute / inline style 操作是灰區、加 observer 監聽變動、被 reset 時補打。

**替代方案的不足**：寫 `el.style.display = 'none'`、不加 observer — framework 一 patch 就 revert、行為間歇性失效難以重現。

---

## 判讀徵兆

| 訊號                                  | 邊界問題                        | 第一個該檢查的事                          |
| ------------------------------------- | ------------------------------- | ----------------------------------------- |
| JS 操作後 framework 行為異常          | 動到內部子節點                  | 確認操作只動「整節點 identity」、不動內部 |
| Inline style 在某些互動後消失         | 動到 framework 管的 attribute   | 加 observer 補打、或改用 CSS class toggle |
| reparent 後 framework state 重置      | 整節點移動但 framework 看作刪除 | 確認框架對節點 identity 的追蹤機制        |
| 某些 querySelector 命中不該命中的元素 | Selector 範圍超過自家元件       | 把 query 限縮到 self 元件根節點下         |

**核心原則**：JS 動 DOM 前，邊界先列清楚。邊界 = 契約 = 安全範圍 = 出 bug 時可追責的範圍。
