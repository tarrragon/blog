---
title: "Reactive 監聽器的觸發頻率管理"
date: 2026-04-25
weight: 33
description: "MutationObserver / ResizeObserver / event listener 的觸發頻率決定 callback 跑的次數。範圍與 option 寬泛、debounce 不夠、callback 自身又改 DOM 形成循環 — 這幾類風險點怎麼盤點。"
tags: ["report", "事後檢討", "Performance", "JavaScript", "工程方法論"]
---

## 核心原則

**監聽器的「觸發頻率」是效能的第一道防線 — 比 callback 內部最佳化更重要。** 每次觸發都會跑整段 callback；範圍越寬、option 越多、觸發越頻繁、總成本線性放大。優先縮監聽範圍與 option，再考慮 callback 內部最佳化。

---

## 為什麼觸發頻率主導成本

### 商業邏輯

監聽器有三個獨立成本：

| 成本來源              | 單次量級        | 累積方式     |
| --------------------- | --------------- | ------------ |
| 觸發頻率              | 看範圍與 option | 倍數疊加     |
| Callback 內部運算     | 看實作          | 每次完整跑   |
| Callback 引發的副作用 | 看 DOM 變動     | 可能反向觸發 |

把單次 callback 從 5ms 優化到 2ms 是 2.5x；把觸發次數從 100 次 / 秒降到 10 次 / 秒是 10x。**觸發頻率優化的天花板更高**。

### 三類觸發頻率風險

| 類型        | 表現                                            |
| ----------- | ----------------------------------------------- |
| 範圍過寬    | observer 監聽 subtree、無關變動也觸發           |
| Option 全勾 | childList + attributes + characterData 同時觸發 |
| 自激迴圈    | callback 自己改 DOM、再次觸發 observer          |

每類都有對應的盤點方法、不需要等實際卡頓才查。

---

## 搜尋頁的具體風險點

### 風險 1：MutationObserver subtree 過寬

**位置**：`assets/search.js` 的 scope filter。

```js
new MutationObserver(schedule).observe(ui, { childList: true, subtree: true });
```

**判讀**：實際關心的是「結果列表變動」、不是整個 `.pagefind-ui` 的所有變動。pagefind 連續 patch 結果時、observer 在 results 區外的變動也觸發 — 浪費 schedule 跑次數。

**症狀**：使用者快速打字時、Performance 面板看到 schedule 在 1 秒內被排數十次。

**第一個該查的**：在 schedule 內加 `console.count()`、看一次搜尋輪到幾次。> 10 次表示範圍可縮。

### 風險 2：Observer option 全勾

**位置**：通常是「以防萬一」加的 option。

**判讀**：每個勾選的 option 增加觸發頻率。`subtree: true` 把監聽範圍從直接子放大到任意深度；`attributes: true` 加上每個屬性變動都觸發；`characterData: true` 連文字節點變動都觸發。

**症狀**：observer callback 觸發次數遠超預期、但 callback 內邏輯只關心一小部分變動。

**第一個該查的**：列出 callback 內實際會用到的變動類型、移除 observer 中沒用的 option。

### 風險 3：ResizeObserver 寫 CSS 變數造成自激

**位置**：scope-h 量測寫回。

```js
function syncScopeHeight() {
  document.documentElement.style.setProperty('--search-scope-h', scopeEl.offsetHeight + 'px');
}
new ResizeObserver(syncScopeHeight).observe(scopeEl);
```

**判讀**：寫 `--search-scope-h` 若間接影響 `scopeEl` 自身的尺寸（例如 calc 用到這個變數）— 寫入觸發 resize、resize 觸發 callback、callback 又寫入。

**症狀**：CPU 持續被佔、Performance 看到 ResizeObserver callback 連發。

**第一個該查的**：用 `console.count('resize')` 看 callback 一秒觸發幾次。> 60 / 秒表示進入循環。檢查寫入的變數是否反過來影響 scopeEl 尺寸。

### 風險 4：Debounce 沒覆蓋觸發點

**位置**：scope filter 的 schedule。

```js
function schedule() {
  clearTimeout(applyTimer);
  applyTimer = setTimeout(apply, 80);
}
scopeEl.addEventListener('change', schedule);
input.addEventListener('input', schedule);
```

**判讀**：Debounce 把 schedule 的多次觸發合併成一次 apply。但若 observer 觸發路徑沒走 schedule、或 debounce 時間太短、合併效果會打折。

**症狀**：apply 實際跑次數遠超「使用者操作次數」。

**第一個該查的**：每個觸發 apply 的路徑都看一次 — 是否都走 schedule、debounce 時間是否合適（80ms 對打字 OK；觀察 layout 變動可能需要更長）。

---

## 內在屬性比較：四種頻率管理策略

| 策略                                 | 縮減幅度          | 維護成本         | 適用情境            |
| ------------------------------------ | ----------------- | ---------------- | ------------------- |
| 縮 observer 範圍（subtree → 直接子） | 大 — 砍掉無關變動 | 低 — 改 selector | 預設                |
| 縮 observer option（移除沒用的）     | 中 — 視原本勾多少 | 低               | 預設                |
| Debounce / throttle                  | 中 — 合併連發     | 低               | 觸發本來就多的場景  |
| Disconnect / reconnect 配對          | 大 — 完全停掉     | 中               | callback 自己改 DOM |

優先順序：**先縮範圍、再縮 option、再加 debounce、最後考慮 disconnect 配對**。前兩項改一行、後兩項要寫額外邏輯。

---

## 盤點的標準格式

每個 reactive 監聽器寫成一段註解：

```js
/**
 * 監聽：.pagefind-ui 的子節點變動
 * 範圍：subtree（深層也看）
 * Option：childList only
 * Callback 是否改 DOM：是（toggle class）
 * 是否可能自激：否（class change 不觸發 childList）
 * Debounce：80ms
 */
new MutationObserver(schedule).observe(ui, { childList: true, subtree: true });
```

註解讓未來看到效能問題時、不需要重新理解 observer 的設計、可以直接從這份「設定卡」確認哪一項可以調整。

---

## 正確概念與常見替代方案的對照

### 觸發頻率優化先於 callback 內部優化

**正確概念**：優化監聽器先看「觸發次數」、再看「單次 callback 成本」。前者倍數收益、後者線性收益。

**替代方案的不足**：直接在 callback 內加快取、加 early return 等微觀最佳化 — 收益有限、callback 觸發 100 次優化到 90 次幫助不大、不如降到 10 次。

### Option 按需勾、不要全勾

**正確概念**：根據 callback 實際關心的變動勾 option（childList / attributes / characterData）。

**替代方案的不足**：「以防萬一」全勾 — 觸發頻率倍數放大、callback 跑很多次卻多數沒事做。

### 自激檢查列入 review

**正確概念**：每個 reactive 監聽器要回答「callback 是否改 DOM、會不會反向觸發 observer」。

**替代方案的不足**：寫完不檢查、上線後 CPU 100% 才發現是循環。

---

## 判讀徵兆

| 訊號                                 | 該檢查的位置                                    |
| ------------------------------------ | ----------------------------------------------- |
| 使用者操作後瀏覽器卡頓               | 該操作觸發了哪些 observer、各自觸發次數         |
| CPU 持續 100%                        | observer 自激迴圈                               |
| `setTimeout(0)` 也來不及處理         | observer / event 觸發頻率超過 schedule 處理速度 |
| Callback 內加 console.count 數字爆炸 | observer 範圍過寬                               |

**核心原則**：監聽器的成本不只在 callback、在「觸發了幾次」。盤點時把觸發頻率列為第一項、callback 內部最佳化是次要。
