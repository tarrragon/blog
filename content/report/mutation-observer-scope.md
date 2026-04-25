---
title: "MutationObserver 範圍與觸發頻率：監聽最少必要的變動"
date: 2026-04-25
weight: 29
description: "MutationObserver 是非同步監聽工具、跟同步 selector 是不同議題。範圍寬會頻繁觸發、option 勾多會在不關心的變動上跑邏輯、apply 自己改 DOM 會觸發無限循環。本文是 observer 設計的完整指引。"
tags: ["report", "事後檢討", "JavaScript", "DOM", "工程方法論"]
---

## 核心原則

**MutationObserver 監聽最少必要的變動 — 從「監聽哪個 root」「觀察什麼類型」「多久觸發一次」三維度收斂。** 範圍寬會頻繁觸發、option 勾多會在不關心的變動上跑邏輯、apply 自己改 DOM 會引發無限循環。三維度都該顯式設計、不能只丟預設。

---

## 為什麼 observer 需要獨立議題

### 跟 selector 的差異

Observer 與 selector 都涉及「DOM 範圍」、機制完全不同：

| 維度     | Selector           | Observer                       |
| -------- | ------------------ | ------------------------------ |
| 時機     | 同步、當下查詢     | 非同步、回應未來變動           |
| 執行頻率 | 一次或顯式重呼叫   | 隨 DOM 變動自動觸發            |
| 失敗模式 | 撈太多 / 撈太少    | 觸發太頻繁 / 漏觸發 / 無限循環 |
| 設計重點 | 起點 + 範圍 + 過濾 | 監聽範圍 + option + 頻率       |

把 selector 與 observer 綁同一篇討論會混淆 — 兩者解決的是不同問題、有不同失敗模式、需要不同的設計工具。

### Observer 寬範圍的失敗模式

| 失敗模式   | 表現                             | 根因                        |
| ---------- | -------------------------------- | --------------------------- |
| 過度觸發   | 短時間觸發數十次                 | subtree 太深 + option 太多  |
| 在錯時機跑 | layout 還沒穩就跑 apply          | 沒等 framework patch 結束   |
| 無限循環   | apply 自己改 DOM 又觸發 observer | 沒 disconnect/observe 保護  |
| 漏掉變動   | 預期會觸發但沒觸發               | option 沒勾對、或 root 選錯 |

四種都來自「沒精細設計 observer 的監聽形狀」。

---

## 三維度收斂

### 維度 1：監聽哪個 root（範圍）

**核心定義**：observer 的 root 元素決定「哪些範圍內的變動會被看到」。

```js
// 寬：監聽整個 .pagefind-ui
new MutationObserver(apply).observe(ui, { childList: true, subtree: true });

// 收斂：只監聽結果列表
var results = shell.querySelector('.pagefind-ui__results');
new MutationObserver(apply).observe(results, { childList: true });
```

寬範圍把無關變動也帶進來 — pagefind 重繪 input、調整 filter、重排 chip 都會觸發 apply、但 apply 只關心結果變動。

**Root 選擇的決策**：找到「**包含所有目標變動、但不包含其他無關變動**的最小元素」。

- 太大 → 帶進無關變動、過度觸發
- 太小 → 漏掉真正關心的變動
- 剛好 → 只關心的變動觸發

問自己：「我關心的變動發生在哪些元素？這些元素的最小共同 ancestor 是誰？」答案就是 observer root。

### 維度 2：觀察什麼類型（option flag）

**核心定義**：MutationObserver 提供四種 option、每種對應不同類型變動：

```js
{
  childList: true,        // 子節點增 / 減 / 重排
  attributes: true,       // 屬性變動
  attributeFilter: ['data-state'],  // 只看特定屬性
  characterData: true,    // 文字內容變動
  subtree: true,          // 上面三種往子樹深處看
  attributeOldValue: true,  // 屬性變動時記錄舊值
  characterDataOldValue: true,
}
```

預設只勾需要的、不要全部 true：

| Option                         | 用途                 | 觸發頻率 |
| ------------------------------ | -------------------- | -------- |
| `childList: true`              | 子節點增減           | 中       |
| `childList + subtree`          | 任何深度的子節點增減 | 高       |
| `attributes` 全屬性            | 任何屬性變動         | 最高     |
| `attributes + attributeFilter` | 只特定屬性           | 低       |
| `characterData`                | 文字內容（少用）     | 低       |

**避免勾 subtree**：subtree 把監聽從「直接子」擴展到「整個子樹」、觸發頻率可能爆炸。只在「真的需要看深層變動」時用。

**避免無 filter 的 attributes**：DOM 屬性變動很頻繁（class 改、style 改、aria-* 改），不過濾會被淹沒。用 `attributeFilter: [...]` 縮到只看你關心的屬性。

### 維度 3：多久觸發一次（頻率）

**核心定義**：observer 的回呼可能短時間內被連續呼叫、用 debounce 把多次合併成一次。

```js
var timer;
function schedule() {
  clearTimeout(timer);
  timer = setTimeout(apply, 80);
}
new MutationObserver(schedule).observe(root, { childList: true });
```

Debounce 80ms 表示「最後一次變動後 80ms 沒再變、才跑 apply」 — 把連續變動合併。

**Debounce vs Throttle**：

| 機制     | 行為         | 適合                             |
| -------- | ------------ | -------------------------------- |
| Debounce | 安靜後執行   | 等 framework 連續 patch 結束     |
| Throttle | 固定頻率執行 | UI 同步要立即反應、但限速        |
| 立即執行 | 每次都跑     | 變動頻率本來就低、且每次都要處理 |

大部分 observer 場景適合 debounce — framework patch 是突發性、不是持續的。

**Debounce 時間選擇**：

| 時間               | 適合                           |
| ------------------ | ------------------------------ |
| 16ms（一個 frame） | 跟 paint 同步、最即時          |
| 50-100ms           | 一般 UI 反應、肉眼感受不到延遲 |
| 200-300ms          | 等使用者輸入結束               |
| 1000ms+            | 後台處理、不影響 UI            |

預設 50-100ms — 比一個 frame 寬、又不會讓使用者感受延遲。

---

## Self-mutation 循環的處理

### 問題場景

apply 函式自己也改 DOM 時、會再次觸發 observer：

```js
function apply() {
  // 改了某個元素的 class（attribute 變動）
  someEl.classList.add('processed');
}
new MutationObserver(apply).observe(root, {
  attributes: true, subtree: true,
});
// → apply 改 class 觸發 observer → observer 又呼叫 apply → 無限循環
```

**這不是邏輯錯、是 observer 機制的特性**：observer 不會區分「是不是 apply 自己改的」。

### 解法：disconnect / observe 配對

```js
var observer = new MutationObserver(function () {
  observer.disconnect();      // 暫停監聽
  apply();                    // 自己改 DOM 不會觸發
  observer.observe(root, options);  // 恢復監聽
});
observer.observe(root, options);
```

apply 期間 observer 暫停、apply 結束後恢復 — 自己的改動不會觸發自己。

### 解法替代：用 attribute 標記區分

```js
function apply() {
  isApplying = true;
  someEl.classList.add('processed');
  isApplying = false;
}
new MutationObserver(function () {
  if (isApplying) return;
  apply();
}).observe(root, options);
```

但這個解法有時序風險 — observer 是非同步、`isApplying` 可能在錯時間被讀。**disconnect/observe 配對更穩**。

### 解法替代：root 與目標分離

如果 apply 改的是 A、observer 監聽的是 B（A 跟 B 沒交集），自然不循環：

```js
new MutationObserver(apply).observe(resultsEl, { childList: true });
function apply() {
  // 改的是 input 而不是 results — 不會觸發 observer
  inputEl.value = '...';
}
```

設計時讓 observer 看的範圍跟 apply 改的範圍**結構上分離** — 是最乾淨的解法、不需要 disconnect 配對。

---

## 觀察的時機問題

### Observer 跟 framework 渲染週期競爭

Observer 在 framework 連續 patch 中段觸發、可能在 layout 還沒穩時就跑 apply、造成短暫視覺錯位：

```js
// framework 連續 patch：
//   patch 1 → observer 觸發 → apply 跑 → 視覺 A
//   patch 2 → observer 觸發 → apply 跑 → 視覺 B
//   patch 3 → observer 觸發 → apply 跑 → 視覺 C（最終）
// 使用者看到 A → B → C 的閃爍
```

Debounce 是這個問題的解 — 讓 observer 等 patch 完成才跑 apply。

### 確認時機正確

寫 observer 時自問：

| 問題                               | 答案決定                 |
| ---------------------------------- | ------------------------ |
| Apply 跑的時候 layout 是否已穩定？ | 是否需要 debounce        |
| Apply 自己改 DOM 嗎？              | 是否需要 disconnect 配對 |
| 我關心的變動類型是什麼？           | option flag 怎麼勾       |
| 變動發生在哪一層？                 | 是否需要 subtree         |
| Framework 的渲染週期會干擾嗎？     | debounce 時間取多久      |

每個問題都該有顯式答案、不能丟預設。

---

## 內在屬性比較：四種 observer 設計

| 設計                                  | 觸發頻率 | Layout 穩定性       | 維護成本                     |
| ------------------------------------- | -------- | ------------------- | ---------------------------- |
| 全勾 + subtree + 無 debounce          | 最高     | 低 — patch 中段觸發 | 低（短期）/ 高（debug 噩夢） |
| 收斂 root + 必要 option + 無 debounce | 中       | 中                  | 中                           |
| 收斂 root + 必要 option + debounce    | 低       | 高                  | 中                           |
| 結構分離 + 收斂 + debounce            | 最低     | 最高                | 中（前期設計成本）           |

**推薦**：收斂 root + 必要 option + debounce。`apply` 不改 DOM 時不需要 disconnect；改的話用結構分離優先、退而求其次用 disconnect。

---

## 進階技巧

### 1. 動態調整 observer 範圍

當監聽目標可能還沒 mount 時、用兩階段 observer：

```js
// 階段 1：等目標 mount
var bootstrap = new MutationObserver(function () {
  var target = shell.querySelector('.pagefind-ui__results');
  if (!target) return;
  bootstrap.disconnect();

  // 階段 2：mount 後監聽目標
  new MutationObserver(apply).observe(target, { childList: true });
});
bootstrap.observe(shell, { childList: true, subtree: true });
```

階段 1 用寬範圍找到目標、階段 2 切到精準範圍 — 把寬範圍的觸發限制在「找目標」這個短時間。

### 2. 用 `takeRecords` 主動取出累積變動

```js
var observer = new MutationObserver(function () { /* ... */ });
observer.observe(root, options);

// 之後某時間點、想立刻處理累積的變動
var records = observer.takeRecords();
processRecords(records);
```

`takeRecords` 取出尚未觸發回呼的變動記錄、主動處理 — 適合「我想在某時間點同步處理累積變動」場景。

### 3. 多 observer 各管一塊

不要用一個 observer 監聽全部、各分一個：

```js
new MutationObserver(applyA).observe(elA, { childList: true });
new MutationObserver(applyB).observe(elB, { attributes: true });
```

各自獨立 — 一個 observer 出錯不影響另一個、debug 範圍小、option 各自最佳化。

---

## 設計取捨：MutationObserver 的設計策略

四種做法、各自機會成本不同。這個專案選 A（收斂 root + 必要 option + debounce）當預設、其他做法在特定情境合理。

### A：收斂 root + 必要 option + debounce + 結構分離（這個專案的預設）

- **機制**：root 取最小共同 ancestor、option 只勾真正關心的變動、加 50-100ms debounce、apply 改的範圍跟 observer 看的範圍結構上分離
- **選 A 的理由**：觸發頻率最低、layout 穩定、無 self-mutation 循環風險
- **適合**：絕大多數 observer 設計
- **代價**：前期設計成本中（要思考 root / option / 結構）

### B：收斂 root + 必要 option（無 debounce）

- **機制**：縮範圍與 option、但不加 debounce
- **跟 A 的取捨**：B 即時反應、A 等 debounce；但 B 在 framework patch 中段觸發、layout 不穩時跑 apply 結果不可靠
- **B 比 A 好的情境**：apply 不依賴 layout（純改 attribute、不讀 bounding rect）

### C：寬範圍 + subtree + 全勾 option（預設配置）

- **機制**：observe(elem, { childList: true, subtree: true, attributes: true, ...})
- **跟 A 的取捨**：C 寫法簡單、A 顯式設計；但 C 觸發數十次、難 debug、效能下降
- **C 才合理的情境**：實務上幾乎不存在 — 「以防萬一全勾」是 anti-pattern

### D：disconnect / observe 配對處理 self-mutation

- **機制**：apply 前 disconnect、apply 後 reconnect
- **跟 A（結構分離）的取捨**：D 處理 callback 必須改 observer 監聽範圍的情境、A 從設計上避免；A 更乾淨
- **D 比 A 好的情境**：無法做結構分離（apply 必須改 observer 看的範圍）— 唯一情境

---

## 判讀徵兆

| 訊號                        | Observer 問題               | 修正動作                                  |
| --------------------------- | --------------------------- | ----------------------------------------- |
| 短時間觸發數十次            | 範圍 / option 太寬          | 縮 root、移除不需要的 option、加 debounce |
| Apply 跑時 layout 抖動      | 在 framework patch 中段觸發 | 加 debounce 50-100ms                      |
| Apply 內改 DOM 進入無限循環 | 沒處理 self-mutation        | 用結構分離 / disconnect 配對              |
| 預期變動沒觸發              | option 沒勾對、root 選錯    | 對照變動類型確認 option                   |
| Subtree 用了但只關心直接子  | 過度監聽深度                | 移除 subtree、改用直接子監聽              |
| 屬性監聽觸發太頻繁          | 沒用 attributeFilter        | 加 filter 限縮屬性                        |

**核心原則**：MutationObserver 是非同步監聽、跟同步 selector 設計工具完全不同。範圍 / option / 頻率三維度都要顯式設計 — 預設組合會在 framework 環境中過度觸發、且難以 debug。
