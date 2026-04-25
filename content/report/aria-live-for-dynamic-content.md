---
title: "Screen reader 與動態內容變動的 live region 設計"
date: 2026-04-25
weight: 38
description: "Scope filter 切換、結果數量變動 — screen reader 使用者看不到視覺變動、需要 aria-live region 主動朗讀。本文盤點 live region 的設計選擇與適用情境。"
tags: ["report", "事後檢討", "Accessibility", "ARIA", "工程方法論"]
---

## 核心原則

**動態內容變動對螢幕報讀軟體使用者預設不可見 — 要主動透過 aria-live region 把變動「廣播」給輔助技術。** 沒 live region 的 UI 在視覺使用者眼裡很流暢、在 screen reader 使用者眼裡是「靜悄悄變了什麼但我不知道」。

---

## 為什麼動態內容需要主動廣播

### 商業邏輯

Screen reader 的工作模式：

| 動作                      | screen reader 行為                     |
| ------------------------- | -------------------------------------- |
| 頁面載入                  | 朗讀整個 main 內容（或使用者導航位置） |
| 使用者按 tab              | 朗讀新 focus 元素                      |
| 使用者按方向鍵            | 朗讀附近元素                           |
| **DOM 變動但 focus 沒動** | **預設不朗讀**                         |

第四種是動態 UI 的常見情境 — 使用者在 search input 上、結果列表變動 — screen reader 預設不知道。

`aria-live` 屬性告訴 screen reader「這個區域內容變動時、主動朗讀變動」。沒 aria-live、變動就沉默。

### 三類動態變動

| 變動類型                     | 是否需要廣播                    |
| ---------------------------- | ------------------------------- |
| 使用者主動觸發、focus 跟著走 | 否（focus 變動會朗讀新位置）    |
| 使用者主動觸發、focus 沒動   | 是 — 用 `aria-live="polite"`    |
| 重要警示（錯誤訊息、警告）   | 是 — 用 `aria-live="assertive"` |

`polite` 等使用者當前朗讀完才宣告、`assertive` 立刻打斷 — 多數場景用 polite。

---

## 搜尋頁的具體風險點

### 風險 1：Scope filter 切換後沒提示

**位置**：scope filter 的 `apply()` — 改變 result 顯示後沒有 aria 提示。

**判讀**：使用者切換 scope（標題 / 內文 / 全部）、UI 上結果數量變了 — screen reader 完全不知道。使用者可能繼續以為「189 筆結果」、實際只剩 4 筆。

**症狀**：screen reader 使用者切 scope 後、tab 到結果區、發現跟剛才不同、困惑。

**第一個該查的**：加 aria-live region 在 scope UI 旁邊、apply 後寫入訊息。

```html
<div class="search-scope" role="radiogroup" aria-label="搜尋範圍">
  <!-- radios... -->
</div>
<div class="search-scope-status" aria-live="polite" aria-atomic="true"></div>
```

```js
function apply() {
  // ... filter 邏輯
  var visible = items.filter(el => !el.classList.contains('is-scope-filtered')).length;
  document.querySelector('.search-scope-status').textContent = '篩選後 ' + visible + ' 筆結果';
}
```

`aria-atomic="true"` 確保整個訊息每次都完整朗讀（而非只朗讀差異）。

### 風險 2：搜尋結果載入完成沒提示

**位置**：使用者打字、pagefind 載入結果 — UI 上 result 出現、但 screen reader 不知道載入完成。

**判讀**：使用者打字結束、預期「結果出來了」— 但需要主動 tab 過去確認、不像視覺使用者一眼看到。

**症狀**：使用者打字後不知道結果是否準備好、不知道是否該 tab 過去。

**第一個該查的**：pagefind 自身可能已實作 aria-live；若未、加一個 region 在結果區上方。

```html
<div class="search-results-status" aria-live="polite"></div>
```

```js
new MutationObserver(function () {
  var count = items.length;
  status.textContent = count + ' 筆結果符合搜尋';
}).observe(resultsRoot, { childList: true });
```

### 風險 3：Filter 變動後沒提示

**位置**：使用者勾選 / 取消 filter checkbox、pagefind 自動更新結果。

**判讀**：勾選某個 tag、結果列表變動 — screen reader 看不到變動、若 focus 還在 checkbox 也沒朗讀。

**症狀**：螢幕報讀軟體使用者勾 filter、不知道有沒有效果。

**第一個該查的**：同上、aria-live region 反映「N 筆結果符合篩選」。

### 風險 4：「無結果」訊息

**位置**：搜尋字找不到任何結果。

**判讀**：頁面顯示「找不到 X 相關內容」、screen reader 若 focus 還在 input 不會朗讀。

**症狀**：screen reader 使用者打字後沒任何回應、不知道是「無結果」還是「還在搜尋」。

**第一個該查的**：把「無結果」訊息放 aria-live region 內、變動時自動朗讀。

---

## Live region 的設計選擇

### `polite` vs `assertive`

| 屬性                    | 行為                     | 適用                 |
| ----------------------- | ------------------------ | -------------------- |
| `aria-live="polite"`    | 等使用者當前朗讀完才宣告 | 多數動態變動         |
| `aria-live="assertive"` | 立刻打斷使用者朗讀       | 錯誤、警告、緊急訊息 |

優先 polite — assertive 容易打斷使用者、感覺很突兀。

### `aria-atomic`

| 屬性                          | 行為                     |
| ----------------------------- | ------------------------ |
| `aria-atomic="false"`（預設） | 只朗讀變動的部分         |
| `aria-atomic="true"`          | 整個 region 內容完整朗讀 |

對「N 筆結果」這類固定格式訊息、用 `aria-atomic="true"` 確保使用者聽到完整脈絡（不只朗讀數字變動）。

### `aria-relevant`

預設只朗讀「新增 / 文字變動」、不朗讀「移除」。多數情境用預設即可。

---

## 內在屬性比較：四種動態內容廣播策略

| 策略                             | 涵蓋情境          | 維護成本                        | 適用                   |
| -------------------------------- | ----------------- | ------------------------------- | ---------------------- |
| 不處理（沉默）                   | 不適用            | 0                               | 不適用                 |
| `aria-live="polite"`             | 大多數動態變動    | 低 — 加 div 與 textContent 寫入 | 預設                   |
| `aria-live="assertive"`          | 緊急訊息          | 低                              | 錯誤 / 警告            |
| `role="status"` / `role="alert"` | semantic 角色明確 | 低                              | 純 status / alert 元素 |

優先選 `aria-live="polite"` + `aria-atomic="true"`、廣覆蓋且不打擾。

---

## Live region 的常見錯誤

### 1. 動態建立 region

```js
var status = document.createElement('div');
status.setAttribute('aria-live', 'polite');
status.textContent = '...';
document.body.appendChild(status);
```

不會生效 — screen reader 在 region 出現「之後」變動才朗讀、region 從無到有的瞬間不算。

正確：region 在 HTML 預先存在、JS 只更新內容。

### 2. 全頁加一個共用 region

可能導致訊息混淆 — 不同 source 的訊息共用同一個 region、難以追蹤。每個語意區域有自己的 region 較清楚。

### 3. 太頻繁的訊息

每次變動都廣播 — 使用者被 spam。Debounce + 重複內容跳過。

---

## 設計取捨：動態內容廣播策略

四種做法、各自機會成本不同。這個專案選 A（aria-live polite + aria-atomic）當預設、其他做法在特定情境合理。

### A：`aria-live="polite"` + `aria-atomic="true"`（這個專案的預設）

- **機制**：region 預先在 HTML、JS 寫入 textContent 觸發 polite 朗讀（等使用者當前朗讀完）
- **選 A 的理由**：覆蓋多數動態變動、不打擾使用者當前操作
- **適合**：搜尋結果數量變動、filter 切換、scope 改變等大多數 UI 變動
- **代價**：訊息要等使用者當前朗讀完才聽到（最多幾秒延遲）

### B：`aria-live="assertive"`

- **機制**：立刻打斷使用者當前朗讀、強制聽新訊息
- **跟 A 的取捨**：B 即時、A 禮貌；但 B 打斷感強、頻繁使用會讓使用者疲勞
- **B 比 A 好的情境**：真正緊急的訊息（錯誤 / 警告 / 安全提示）— 必須立刻知道

### C：`role="status"` / `role="alert"`

- **機制**：用 semantic role 取代 aria-live、語意更明確
- **跟 A 的取捨**：C 跟 A 行為類似（status = polite、alert = assertive）、但 role 表達意圖更清楚
- **C 比 A 好的情境**：region 本身就是 status 或 alert 元素（語意對齊）

### D：不處理（沉默）

- **機制**：DOM 變動不通知 screen reader
- **成本特別高的原因**：screen reader 使用者完全不知道有變動、UI 變得不可用
- **D 才合理的情境**：純視覺裝飾變動（背景動畫 / decorative）— 對 screen reader 使用者無意義

---

## 判讀徵兆

| 訊號                                           | 該檢查的位置                                    |
| ---------------------------------------------- | ----------------------------------------------- |
| Screen reader 使用者反映「不知道有沒有發生事」 | 找出該變動位置、加 aria-live region             |
| 動態 UI 沒任何 aria-live                       | 列出所有 focus 不跟著走的變動、各自評估是否需要 |
| Live region 朗讀但聽起來只有片段               | 加 `aria-atomic="true"`                         |
| 訊息太頻繁打擾                                 | Debounce、跳過重複                              |

**核心原則**：UI 上「使用者沒主動觸發但有變動」的位置、screen reader 預設沉默 — 用 aria-live region 把沉默變成可聽見。
