---
title: "Filter × Source 的合成策略五選一"
date: 2026-04-26
weight: 59
description: "Filter 跟 paginated / streaming source 合成的五種策略、各自機會成本不同：A 推進 query / B 自動續抓 / C 預先 index / D 誠實 UX / E 接受語意縮小。沒有絕對最佳、看 source capabilities、match 密度、UX 容忍度而定。"
tags: ["report", "事後檢討", "工程方法論", "Architecture", "Data Flow"]
---

## 核心原則

**Filter 跟分批 source 的合成有五種策略、各自機會成本不同**。沒有絕對最佳 — 選哪個取決於三個變數：

1. Source 是否支援 server-side filter（capabilities）
2. Match 密度（稀疏 vs 密集）
3. UX 容忍度（要不要誠實顯示「掃描範圍」）

本文是 #55 [Filter 與 Source 的層錯位](../view-layer-filter-vs-source-layer/) 的解法展開、列出五個合理選項與適用情境。

---

## 五策略對照表

| 策略 | 一句話                                           | 對 source 的需求              | 對 UX 的影響   | 工程量 |
| ---- | ------------------------------------------------ | ----------------------------- | -------------- | ------ |
| A    | 把 filter 推進 source 的 query                   | 必須支援該 filter 條件        | 透明（無感）   | 中-高  |
| B    | 自動續抓直到湊滿 N 個 match                      | 任何分批 source               | 透明（稍慢）   | 中     |
| C    | 預先建獨立 index（每種 mode 一份）               | 能控 source 的 build pipeline | 透明（最快）   | 高     |
| D    | 誠實 UX 顯示「已掃 N / 命中 K」                  | 任何 source                   | 顯眼（多按鈕） | 低     |
| E    | 接受「filter 範圍 = 已載入」、不承諾 source 全集 | 任何 source                   | 隱性語意縮小   | 最低   |

---

## 策略 A：推進 query

### 機制

把 filter 條件變成 source 的 query 參數。Source 直接回符合的、client 不再 post-filter。

```js
// 反例：post-filter
const all = await pagefind.search(query);
const filtered = all.results.filter(r => r.type === 'post');

// 對例：推進 query
const filtered = await pagefind.search(query, { filters: { type: 'post' } });
```

### 適合

- Source 已索引該欄位（pagefind filter API、SQL `WHERE`、ES bool query）
- 條件能在 source 端表達（=, BETWEEN, IN, full-text match）

### 不適合

- Source 不支援該 filter（如 pagefind 的 title-only vs content 區分、需要重 index）
- 條件需要 client 計算（隨機抽樣、依 viewport 計算）

---

## 策略 B：自動續抓直到湊滿

### 機制

抓一批 → filter → 不夠就再抓 → 直到湊滿目標數或 source 結束。

```js
async function loadFiltered(targetCount) {
  let collected = [];
  while (collected.length < targetCount && hasMore()) {
    const batch = await fetchNext();
    collected.push(...batch.filter(matches));
  }
  return collected;
}
```

### 適合

- Source 不支援 server-side filter
- Match 密度可預期（不會稀疏到要拉光整個 dataset）
- 使用者期望「filter 後自動湊夠」

### 不適合

- 稀疏 match（拉光 dataset 才湊到 N 個 → 浪費頻寬）
- 沒有上限保護（拉到無限）
- Source cardinality 大（10 萬筆全拉一遍）

### 必要的保護

| 保護         | 必要性                       |
| ------------ | ---------------------------- |
| 最大續抓次數 | 必要 — 避免稀疏時拉爆        |
| 最大時間     | 必要 — 避免 UX 凍住          |
| 已掃進度顯示 | 推薦 — 使用者看到正在工作    |
| 可中斷       | 必要 — 使用者改 query 時能停 |

---

## 策略 C：預先建獨立 index

### 機制

Build time 為每種 filter mode 各建一份 source / index。Runtime 切換 mode = 切 source。

```bash
# Build 階段
pagefind --source public --output-subdir _pagefind-all
pagefind --source public/title-extract --output-subdir _pagefind-title
```

```js
// Runtime
const pf = mode === 'title' ? pagefindTitle : pagefindAll;
const r = await pf.search(query);
```

### 適合

- 能控 source 的 build pipeline
- Filter mode 數量有限（< 5）
- 兩個 mode 都重要、流量大、值得分開

### 不適合

- Filter 維度多（每個維度組合都建 index 會爆炸）
- Index 大小敏感（多份 index = 多份 size）
- Build pipeline 不能控（外部 API source）

---

## 策略 D：誠實 UX

### 機制

保留 view 層 filter、UI 顯示「已掃 N 筆 / 命中 K 筆 / 共 M 筆 / 再掃一批」、使用者手動續抓。

```html
<div class="filter-status">
  已掃 <strong>24</strong> 筆 / 命中 <strong>3</strong> 筆 / 共 <strong>~150</strong> 筆
  <button>再掃一批</button>
</div>
```

### 適合

- Filter 是次要功能、預設模式不用 filter
- 使用者願意手動互動
- 工程量限制、無法做 A / B / C

### 不適合

- Filter 是主要互動模式
- 使用者期望「自動全找完」

### 跟策略 B 的差別

B 是「自動」、D 是「半自動」（使用者觸發每一輪）。B 透明、D 顯眼。

---

## 策略 E：接受語意縮小

### 機制

明示或隱性把 filter 的語意定為「在已載入子集裡」、不承諾包含 source 全集。

```text
"Filter results"
  ↓
（隱性語意：filter 已載入的、不續抓）
```

### 適合

- Source 一次給完整 dataset（沒分批 → 沒層錯位）
- 使用者明確知道「先載入更多再 filter」是分開動作
- 原型 / MVP 階段、不解決完美

### 不適合

- Source 分批、但使用者預期 filter 是「全集」
- 使用者沒被告知語意縮小

### 跟策略 D 的差別

D 用 UI 顯式告訴使用者「掃描範圍」。E 不告訴 — 接受使用者可能誤解。E 通常是「來不及做 D」的退而求其次。

---

## 選擇規則：決定矩陣

| 條件                                  | 建議策略              |
| ------------------------------------- | --------------------- |
| Source 支援 server-side filter        | A（最優）             |
| Source 不支援、match 密度高、自動較好 | B                     |
| Source 不支援、能控 build、mode 有限  | C                     |
| Source 不支援、稀疏、要避免拉爆       | D                     |
| 原型期、不解決完美                    | E（明示語意縮小）     |
| Source 一次性給完、無分批             | view 層 filter 直接寫 |

---

## 多策略並用

實務上常見組合：

- **A + D fallback**：query 推進失敗（如使用者用 source 不支援的條件）→ fallback 到 D
- **B + 上限 → D**：自動續抓到上限後切 D（顯示「已掃 N 筆、再掃？」）
- **C + B 補強**：預先 index 解一般 case、B 解 index 沒覆蓋的組合

並用通常比單選有效、但複雜度也最高。

---

## 判讀徵兆

| 訊號                                                    | 該選的策略起點                  |
| ------------------------------------------------------- | ------------------------------- |
| Source 是 SQL / ES / pagefind 且 filter 條件已索引      | A                               |
| Source 是 pagefind 且 filter 是「title vs content」     | C（重 index 兩份）              |
| Source 不支援、預期 match 密集、要無感                  | B                               |
| 工程量限制、能接受顯眼 UX                               | D                               |
| 原型 / MVP、能接受語意縮小但要明示                      | E（含語意聲明）                 |
| 使用者意圖明確要「全部命中」、source 不支援、match 稀疏 | A 或 C 重設計、不要 B（會拉爆） |

**核心原則**：Filter × Source 沒有最佳解、只有「對齊三變數（capabilities / 密度 / UX）的取捨」。識別三變數、選對策略 → 比寫漂亮的程式重要。
