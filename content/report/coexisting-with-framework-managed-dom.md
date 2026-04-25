---
title: "與 framework-managed DOM 共處的隔離原則"
date: 2026-04-25
weight: 5
description: "Svelte / React 等框架對自己管轄的 DOM 子樹有完整渲染週期 — 客製 UI 注入這個子樹會被框架重繪清掉。本文以 scope UI 注入 .pagefind-ui 失敗為例，展開『客製 UI 留在框架邊界外、用 CSS 控制視覺位置』的原則。"
tags: ["report", "事後檢討", "Svelte", "JavaScript", "工程方法論"]
---

## 核心原則

**框架管轄的 DOM 子樹是框架的領地 — 客製 UI 注入這個子樹會被框架的渲染週期清掉。** 客製 UI 留在框架邊界外、用 CSS（grid / absolute / margin spacer）控制視覺位置；必要的 DOM 移動只搬「框架管的節點本身」、不修改節點內部。

---

## 為什麼框架管轄區不能塞東西

### 商業邏輯

Svelte / React 等框架透過「component tree → DOM tree」的 reconciliation 機制保持 UI 與 state 同步。框架在 patch 時只認得自己 create 的節點；外來節點要嘛被視為差異而清掉、要嘛被忽略並擋住框架的更新。

外來節點的命運由框架的 reconciliation 策略決定 — 不可預測，且不在我們的控制範圍。

### 兩種 DOM 區域、兩種策略

| 區域                 | 框架管轄程度                   | 客製策略                    |
| -------------------- | ------------------------------ | --------------------------- |
| 框架邊界外           | 不管                           | 自由加 / 改 / 移除          |
| 框架邊界內，節點本身 | 框架認得這個節點，但不檢查內部 | 可整節點 reparent、不改內部 |
| 框架邊界內，節點內部 | 完全管轄                       | 不要動 — 等框架自己更新     |

---

## 這次任務的實際情境

### 觀察

要把搜尋範圍切換 UI（scope radio group）放在「pagefind 搜尋輸入框與結果之間」 — 視覺上希望它就在 form 與 drawer 中間。

第一次嘗試：JS 把 scope element 用 `form.insertAdjacentElement('afterend', scopeEl)` 注入 `.pagefind-ui` 內部。

結果：使用者打字後 scope 消失。

### 判讀

Pagefind 用 svelte 構建 UI、reactivity 監聽 search query 變動。Query 改變時 svelte 會 patch `.pagefind-ui` 的子樹 — 我們注入的 scope 不是 svelte 認得的節點、被視為差異清掉。

這不是 bug、是 svelte reconciliation 的正常行為：框架要保證 DOM 與 component state 一致，外來節點屬於不一致的部分。

### 執行

策略改為「scope 留在 `.search-shell` 裡（框架邊界外）、用 CSS absolute 浮在 form 上」：

```html
<div class="search-shell">
  <h1>...</h1>
  <div class="search-scope">...</div>      <!-- 框架邊界外 -->
  <div id="search">...</div>               <!-- pagefind 進來這裡 -->
</div>
```

```css
.search-shell { position: relative; }
.search-scope {
  position: absolute;
  top: calc(var(--search-title-h) + var(--search-form-h) + 4px);
  /* ... */
}
.search-shell .pagefind-ui__drawer {
  margin-top: calc(var(--search-scope-h) + 8px);  /* 為 scope 讓位 */
}
```

scope 不在 svelte 管轄區、永遠不被清；視覺位置靠 absolute + drawer 的 margin-top 共同決定。

---

## 必要的 DOM 移動：搬整節點

某些情境需要把框架管的節點移到別處（例如 filter sidebar 切換）— 移動時遵守「只搬節點、不修改節點內部」。

### 為什麼搬整節點是安全的

框架的 reconciliation 通常以「節點 identity」為依據 — 同一個節點在哪裡不重要、節點存不存在才重要。把 `.pagefind-ui__filter-panel` 從 drawer 移到外部 aside、節點本身與內部子樹保持完整、框架在下次 patch 時看到節點還在、就繼續更新。

### 不可動的：節點內部

| 操作                                            | 是否安全                  |
| ----------------------------------------------- | ------------------------- |
| `aside.appendChild(filterPanel)` 整節點搬       | 安全 — 節點 identity 不變 |
| 在 filterPanel 內部 `appendChild` 加東西        | 不安全 — 框架會清掉       |
| 改 filterPanel 內部子節點的 attribute           | 不安全 — 框架可能 revert  |
| 改 filterPanel 自己的 attribute（class、style） | 多半安全 — 看框架實作     |

---

## 內在屬性比較：客製 UI 的位置選擇

| 位置                      | 依賴前提                   | 升級風險            | 視覺控制                  |
| ------------------------- | -------------------------- | ------------------- | ------------------------- |
| 框架邊界外 + CSS 視覺定位 | 框架元素的 class / id 穩定 | 低                  | 中 — CSS 能達成多數位置   |
| 框架邊界外 + JS 量測位置  | DOM measurable             | 低                  | 高 — runtime 算出精確位置 |
| 框架邊界內注入            | 框架不重繪這部分           | 高 — 框架更新即失效 | 高 — 直接放在想要的位置   |
| Fork 框架 source          | 整個框架原始碼             | 最高 — 升級必衝突   | 最高                      |

優先選擇前兩種。框架邊界內注入只在「該子樹確認不會被 reconcile」時可用 — 多數情境難以保證。

---

## 正確概念與常見替代方案的對照

### 客製 UI 與框架 UI 各自有自己的 DOM 邊界

**正確概念**：客製 UI 放在框架邊界外，用 CSS / 量測算出視覺位置。框架 UI 維持原樣。兩者透過 CSS 共存、不透過 DOM 巢狀。

**替代方案的不足**：把客製 UI 注入框架 DOM 內 — 看似省事（節省一層 wrapper），實際讓客製 UI 的命運綁在框架的 reconciliation 策略上。

### 整節點 reparent 是安全的；改節點內部不安全

**正確概念**：框架以節點 identity 追蹤元素。整節點搬到別處不影響 identity。改內部則進入框架管轄區。

**替代方案的不足**：在框架管的節點內加東西（即使只是一個 span）— 框架不認得這個 span、可能清掉；即使這次沒清，下次更新還是會。

### CSS spacer 取代 DOM 注入

**正確概念**：要在框架元素之間插入客製內容，用 CSS `margin-top` 推開框架元素、把客製內容絕對定位在讓出的空間。

**替代方案的不足**：硬要把客製 DOM 塞到框架 DOM 之間 — 跟框架的渲染競爭、bug 不可預測。

---

## 判讀徵兆

| 訊號                                     | 可能的根因                       | 第一個該嘗試的動作                                            |
| ---------------------------------------- | -------------------------------- | ------------------------------------------------------------- |
| 注入框架 DOM 的元素在使用者互動後消失    | 框架 reconciliation 清掉外來節點 | 把該元素搬出框架邊界、用 CSS 控制視覺位置                     |
| 整節點搬到別處後框架行為異常             | 改了節點內部、不只搬位置         | 確認搬節點時沒動內部子樹                                      |
| 客製 UI 在框架更新後 attribute 被 revert | 框架重新套 attribute             | 不要改框架管的節點 attribute、用 wrapper 元素套自家 attribute |
| 看不出哪些 DOM 是框架管的                | 缺少邊界辨識                     | 讀框架的 mount root，從那裡往內都是管轄區                     |

**核心原則**：客製 UI 的存活壽命 = 「離框架管轄區多遠」。最遠 = 永遠不被清；最近（注入內部） = 隨時可能消失。
