---
title: "Pattern：自動續抓直到湊滿 quota"
date: 2026-04-26
weight: 60
description: "Pattern 卡片：分批 source + post-filter 時、自動續抓直到湊滿 N 個 match。含上限保護、進度顯示、可中斷三個必要元件。對應 #59 策略 B 的具體實作。"
tags: ["report", "Pattern", "工程方法論", "Data Flow"]
---

## Pattern 一句話

抓一批 → filter → 不夠就再抓 → 湊滿 N 個 match 或 source 結束。

對應 #59 [Filter × Source 合成策略](../filter-source-composition-strategies/) 的策略 B。

---

## 何時用、何時不用

### 用

- Source 不支援 server-side filter（不能用策略 A）
- 不能控 build pipeline 重 index（不能用策略 C）
- Match 密度可預期、不會稀疏到要拉光整個 dataset
- 使用者期望「filter 後自動湊夠 N 個」、不要手動續抓

### 不用

- Source 支援 server-side filter（直接用策略 A）
- Match 稀疏、可能拉光整個 dataset 才湊到 N（換 D 誠實 UX）
- Source cardinality 大（10 萬筆）、不能拉太多次

---

## 必要元件

### 元件 1：Quota 跟上限

```js
const TARGET = 10;       // 期望湊滿的 match 數
const MAX_BATCHES = 20;  // 最多續抓次數（保護）
const MAX_TIME_MS = 5000; // 最大時間（保護）
```

**沒有上限 = 稀疏時拉爆**。兩個上限缺一不可。

### 元件 2：Loop with break conditions

```js
async function fetchUntilQuota(matches, target = TARGET) {
  const collected = [];
  const start = Date.now();
  let batchCount = 0;

  while (
    collected.length < target &&
    hasMore() &&
    batchCount < MAX_BATCHES &&
    Date.now() - start < MAX_TIME_MS
  ) {
    const batch = await fetchNext();
    collected.push(...batch.filter(matches));
    batchCount++;
  }

  return {
    collected,
    reachedQuota: collected.length >= target,
    exhaustedSource: !hasMore(),
    hitLimit: batchCount >= MAX_BATCHES || Date.now() - start >= MAX_TIME_MS,
  };
}
```

返回值含三個 flag、UI 用來判斷該顯示哪個狀態（湊滿 / 抓完無更多 / 撞到上限）。

### 元件 3：可中斷

```js
async function fetchUntilQuota(matches, target, signal) {
  // ...
  while (...) {
    if (signal?.aborted) throw new DOMException('aborted', 'AbortError');
    const batch = await fetchNext({ signal });
    // ...
  }
}

// 使用
const ctrl = new AbortController();
input.addEventListener('input', () => {
  ctrl.abort();
  ctrl = new AbortController();
  fetchUntilQuota(matches, 10, ctrl.signal);
});
```

使用者改 query / filter 時能立刻取消舊的續抓。**沒有可中斷 = 競態 bug**（舊 query 的結果晚到、覆蓋新 query 的）。

---

## UX 配套

### 載入中顯示進度

```html
<div class="loading">已掃 <strong>24</strong> 筆 / 已命中 <strong>3 / 10</strong></div>
```

不顯示進度 = 使用者不知道是在等還是卡住。

### 結束時顯示原因

| 結束原因          | 顯示                                   |
| ----------------- | -------------------------------------- |
| `reachedQuota`    | 「找到 10 個結果」                     |
| `exhaustedSource` | 「全部掃完、共找到 K 個」              |
| `hitLimit`        | 「已掃 N 筆、找到 K 個。要繼續找嗎？」 |

不區分原因 = 使用者不知道為什麼停（同 #57 三狀態問題）。

---

## 反例

### 反例 1：沒上限

```js
while (collected.length < target && hasMore()) {
  collected.push(...(await fetchNext()).filter(matches));
}
// 稀疏 match → 拉光整個 source
```

### 反例 2：沒 abort signal

```js
input.addEventListener('input', async () => {
  const r = await fetchUntilQuota(matches);
  render(r);  // 舊 query 的結果可能覆蓋新 query
});
```

### 反例 3：每批序列化等

```js
for (let i = 0; i < MAX; i++) {
  const batch = await fetchNext();  // 序列、慢
  // ...
}
```

如果 source 支援平行 fetch（多個 page 同時抓） → 改成平行更快：

```js
const batches = await Promise.all([fetch(0), fetch(1), fetch(2)]);
```

但平行有 over-fetch 風險（湊滿後其他批白抓） — 適合 match 密度高的情境。

---

## 跟其他 Pattern 的關係

- 跟 #61 [Pattern：推進 query](../pattern-query-side-pushdown/)（待補）：A 是最優、B 是 source 不支援時的退路
- 跟 #62 [Pattern：誠實進度 UX](../pattern-honest-progress-ui/)（待補）：B 撞到上限後 fallback 到誠實 UX

---

## 判讀徵兆

| 訊號                                     | 該做的事                     |
| ---------------------------------------- | ---------------------------- |
| Source 不支援 filter、要湊滿 N 個結果    | 用本 pattern                 |
| 寫了 while loop 但沒上限                 | 補 MAX_BATCHES + MAX_TIME_MS |
| Input 改變時舊的續抓還在跑               | 補 AbortController           |
| 結束時不知道是「湊滿」「掃完」「撞上限」 | 補三個 flag、UI 分支顯示     |
| Match 稀疏、續抓 50 次才湊到 1 個        | 換策略 — B 不適合稀疏 case   |

**核心原則**：自動續抓的價值在「使用者透明」、但成本是「上限保護必要」。沒上限的 B 比 silent post-filter 更糟（會拉爆）。
