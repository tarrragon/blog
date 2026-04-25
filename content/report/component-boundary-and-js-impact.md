---
title: "JS 操作 framework 元件：邊界辨識與安全規則"
date: 2026-04-25
weight: 13
description: "操作 framework 管的 DOM 前先界定『動什麼、邊界在哪、state 由誰維護』。本文展開邊界辨識的決策樹、整節點 reparent 的具體 do/don't 規則、灰區操作的 fail-safe 設計。"
tags: ["report", "事後檢討", "JavaScript", "DOM", "工程方法論"]
---

## 核心原則

**JS 操作 framework 元件前先界定邊界、選對應的安全規則執行。** 邊界 = 契約 = 安全範圍。整節點搬遷安全、改節點內部不安全、改節點 attribute 是灰區。每類操作有對應的安全規則 — 不是「能不能動」、是「動了之後 framework 會不會 revert」。

> 本篇焦點：**framework 元件本身需要動時的安全規則**。「客製 UI 該放哪」由 [#5 客製 UI 留 framework 邊界外](coexisting-with-framework-managed-dom/) 處理 — 預設應該完全不動 framework、需要動時才參考本篇。

---

## 為什麼邊界要先界定

### 商業邏輯

每個元件（自家或 framework 提供）有「對外契約」與「內部實作」。對外契約包括：

| 契約類型 | 內容 |
|---------|------|
| DOM identity | 哪些 class / id / attribute 是穩定的 |
| State 來源 | 元件內部 state 由誰寫、何時改 |
| 渲染週期 | 元件何時重繪、重繪時影響哪些 DOM |
| 對外介面 | 提供哪些 props / events / API hooks |

JS 操作前不知道這些 = 黑箱操作。動了什麼、會觸發什麼、誰會被影響、不可預測。

### 邊界宣告的格式

開始 JS 操作之前、寫一段註解或 mental note：

```text
動什麼：filter-panel 的 parent
邊界：filter-panel 整個節點 OK，內部子節點屬於 pagefind 管
State：checkbox 勾選狀態存在 panel 子節點上、由 pagefind 維護
動作：appendChild 整節點 reparent
為什麼安全：節點 identity 不變、pagefind 在下次 patch 時看到節點還在
```

這段宣告把「動什麼」「不能動什麼」「為什麼安全」說清楚 — 不是儀式、是強迫自己想清楚再動。

---

## 三類操作的安全度

從最安全到最不安全：

### 1. 整節點 reparent（安全）

把 framework 管的整個節點搬到別處 — 節點 identity 不變、framework 在下次 patch 時仍認得它。

```js
// 安全 — 整節點搬位置
sidebar.appendChild(filterPanel);
drawer.insertBefore(filterPanel, drawer.firstChild);
```

### 2. 改節點內部子節點（不安全）

在 framework 管的節點內 appendChild / removeChild / 改子節點屬性 — framework 會 revert。

```js
// 不安全 — 在 framework 子樹內加東西
filterPanel.appendChild(myCustomDiv);
filterPanel.querySelector('.x').setAttribute('data-y', 'z');
```

### 3. 改節點自身的 attribute / inline style（灰區）

改 framework 管的節點本身的 attribute、看 framework 是否認為這屬於 reactive：

```js
// 灰區 — 看 framework 怎麼處理
el.style.display = 'none';
el.classList.add('my-state');
el.setAttribute('aria-hidden', 'true');
```

下節展開三類各自的設計細節。

---

## 整節點 reparent：為什麼安全、怎麼做才安全

### 為什麼安全

Framework 的 reconciliation 通常以「節點 identity」為依據 — **同一個節點在哪裡不重要、節點存不存在才重要**。

把 `.pagefind-ui__filter-panel` 從 drawer 移到外部 aside：

| Framework 看到 | 反應 |
|---|---|
| 節點還在（identity 沒變） | 繼續更新它的內部 |
| 節點的 parent 變了 | Framework 不關心 — parent 不在 component tree 內 |
| 節點內的 children 不變 | Framework 不需要重建 |

reconciliation 不會因為「位置變了」而重建節點 — 重建只發生在「節點消失了 + 新節點出現」的情境。

### 安全 reparent 的 do / don't

| Do | Why |
|----|-----|
| `parent.appendChild(node)` 整節點搬 | identity 保留 |
| `parent.insertBefore(node, ref)` 整節點搬到特定位置 | identity 保留 |
| 搬之前 `node.cloneNode(true)` 為複本（如果要保留原位） | 複本是新 identity、原節點仍由 framework 管 |
| 搬完後不動 node 內部 | framework 繼續正常更新 |

| Don't | Why |
|----|-----|
| `parent.appendChild(node.firstChild)` 搬 framework 子節點 | 把節點抽出原 parent、framework 認為消失了 |
| `node.innerHTML = node.innerHTML` 重設內部 | 創造一堆新 identity、framework 認不得 |
| 搬完後在 node 內 appendChild 加東西 | 加的東西不在 framework 認知中、被清 |
| 搬完後改 node 內子節點的 text / attribute | framework 在下次 patch 時 revert |

**核心規則**：搬節點 = 操作 node 本身；不要操作 node 的 children。

### 跟 framework reactivity 的對齊

某些 framework 對節點的「內部值」是 reactive 的（例如 `<input>` 的 `value`），改了會被 reconcile 回來。對這類屬性：

| 屬性類型 | 操作策略 |
|---------|---------|
| Reactive value（input.value、textContent） | 透過 framework API 改、不要直接改 DOM |
| 純展示 attribute（class、aria-* 多數情境） | 直接改 DOM 通常 OK、但仍是灰區（見下節） |
| Layout-relevant style（display、position） | 直接改 DOM 通常 OK、可能需要 fail-safe |

不確定某屬性是否 reactive：讀框架 source / 文件確認、或加 fail-safe 防意外。

---

## 改節點內部：為什麼不安全、有什麼例外

### 為什麼不安全

在 framework 管的節點內 appendChild / removeChild — framework 不認得這些操作的結果、下次 patch 時：

1. Framework 比對 component tree 的目標狀態
2. 看到 DOM 多了不該有的節點 → 移除
3. 或看到 DOM 少了該有的節點 → 重建

我們手動加的節點屬於前者、被移除。我們手動移除的子節點屬於後者、被重建（且重建的 identity 不同）。

### 唯一的例外：靜態元件 + 確認 patch 不重設

如果該 framework 子樹「初次 mount 後不再 patch」、改內部可能安全。但這是**框架實作細節、隨版本可能變動**。

例：當前 pagefind 的 filter 順序在初次 mount 時生成、後續 patch 不重排 — 所以 reorder filter 子節點實際安全。但這是「當前版本碰巧」、不是「框架保證」。

**操作規則**：不要依賴「碰巧安全」。如果必須改內部、加 MutationObserver 監聽 framework 是否 revert、必要時補打。

---

## 改節點 attribute / inline style：灰區的 fail-safe 設計

### 為什麼是灰區

Framework 通常**不主動管理節點的 inline style 與非 reactive attribute** — 但「通常」不是「永遠」。某些 framework 會在 patch 時把 inline style 重設、或把 attribute 跟 component state 強制同步。

### Fail-safe 工具 1：`!important` 提升優先級

```js
el.style.setProperty('display', 'none', 'important');
```

`important` 把 inline style 的優先級提升 — 即使 framework 套了同屬性的低優先 style、也蓋不過。

### Fail-safe 工具 2：MutationObserver 補打

```js
function reapply() {
  el.style.setProperty('display', 'none', 'important');
}
reapply();
new MutationObserver(reapply).observe(parent, {
  childList: true, subtree: true,
});
```

Framework 在重繪後可能把 element 替換成新的 — observer 監聽到變動、立刻補套 style。

詳細設計（observer 範圍 / 觸發頻率 / self-mutation 處理）由 [#29 MutationObserver 範圍與觸發頻率](mutation-observer-scope/) 處理。

### Fail-safe 工具 3：CSS class toggle 取代 inline style

```js
// 不用 inline style
el.classList.toggle('is-hidden');
```

```css
/* CSS 內定義行為、layered CSS 不需要 important */
@layer base {
  .is-hidden { display: none; }
}
```

詳細展開由 [#28 class toggle 取代 important](class-toggle-over-important/) 處理。

**選擇順序**：能用 class toggle 就用（最乾淨）；framework 會清 class 才用 inline + important + observer。

---

## 這次任務的邊界辨識實例

四個 JS 操作場景、各有不同邊界：

| 場景 | 動的對象 | 操作類別 | 安全度 | 處理 |
|---|---|---|---|---|
| 把 filter-panel 從 drawer 搬到 sidebar | 整節點 reparent | 1（安全） | 高 | 直接搬、不動內部 |
| Reorder type / tag filter | filter 子節點順序 | 2（不安全） | 中 — 視 framework 而定 | 確認框架不 reset 順序、加 observer 防護 |
| 注入 scope UI | 自家新元件 | N/A（自家領域） | 高 | 放 framework 邊界外（[#5](coexisting-with-framework-managed-dom/)） |
| Filter 結果 hide / show | pagefind 結果元素的 display | 3（灰區） | 中 | inline + important + observer 補打 |

每個場景操作前的 mental check：「這是哪一類？該用什麼安全規則？」

---

## 設計取捨：操作 framework 元件的策略

四種策略、各自機會成本不同。預設追求「最高安全度的方式達成需求」、成本太高再降級。

### A：完全不動 framework、客製留邊界外（這個專案的預設）

- **機制**：把客製 UI 放在 framework sibling 位置、用 CSS 達成視覺效果
- **選 A 的理由**：跟 framework 完全解耦、命運自主
- **適合**：需求是「在 framework 旁加東西」（多數情境）
- **代價**：CSS 定位可能複雜
- **詳細**：[#5 客製 UI 留 framework 邊界外](coexisting-with-framework-managed-dom/)

### B：整節點 reparent

- **機制**：把 framework 管的節點搬位置、不動內部
- **跟 A 的取捨**：A 不動 framework、B 搬 framework 元件本身；B 換到的是「能改變 framework 元件位置」、付出的是「節點內部仍由 framework 管、外部行為仍可能變」
- **B 比 A 好的情境**：framework 元件位置決定權需要奪回（例如 sidebar 切換）

### C：改節點 attribute + fail-safe

- **機制**：改 inline style / class、加 important + observer 補打
- **跟 A/B 的取捨**：A 不碰 framework、C 介入 framework 元件本身的視覺行為；C 比 A 侵入性高、但比直接改內部安全
- **C 比 B 好的情境**：需要的不是搬位置、是改顯隱 / 顏色 / state

### D：改節點內部（最後手段）

- **機制**：在 framework 子樹內 appendChild、改子節點屬性
- **成本特別高的原因**：跟 framework reconciliation 直接競爭、bug 不可預測、升級可能徹底打破
- **D 才合理的情境**：當前 framework 確認「該子樹不 reconcile」+ 升級時會重新驗證 — 通常不值得

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

---

## 跟其他原則的關係

| 抽象層原則 | 關係 |
|---------|------|
| [#45 跟外部組件合作的層次](external-component-collaboration-layers/) | 本篇是「邊界內 DOM 層」操作的具體規則 — 接受要進入這層、用本篇規則限制傷害 |
| [#43 最小必要範圍](minimum-necessary-scope-is-sanity-defense/) | 操作範圍越小越安全 — 整節點 reparent 比改內部範圍小、改 attribute 比改子樹範圍小 |
| [#5 客製 UI 留邊界外](coexisting-with-framework-managed-dom/) | 互補關係 — #5 處理「不動 framework 的策略」、本篇處理「必須動 framework 時的安全規則」 |

---

## 判讀徵兆

| 訊號 | 邊界問題 | 第一個該檢查的事 |
|------|--------|-------------|
| JS 操作後 framework 行為異常 | 動到內部子節點 | 確認操作只動「整節點 identity」、不動內部 |
| Inline style 在某些互動後消失 | 動到 framework 管的 attribute | 加 observer 補打、或改用 CSS class toggle |
| reparent 後 framework state 重置 | 整節點移動但 framework 看作刪除 | 確認框架對節點 identity 的追蹤機制（少數框架不靠 identity） |
| 某些 querySelector 命中不該命中的元素 | Selector 範圍超過自家元件 | 把 query 限縮到 self 元件根節點下（[#14 selector 精準度](dom-selector-precision/)） |
| 「再加一段防禦邏輯應該就好了」第 2 次 | 整體策略可能該換層級（從 D 升到 C 或 B） | [#42 2 次門檻](two-occurrence-threshold/)、考慮換策略 |

**核心原則**：JS 動 framework 元件前、邊界先界定、選對應的安全規則。預設追求「完全不動 framework」(A)、必須動時用層級遞減的策略（B / C / D）— 每往下一層付的是「跟 framework 競爭」的成本。
