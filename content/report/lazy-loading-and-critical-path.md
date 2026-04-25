---
title: "資源載入時序：lazy chunk 與 critical path"
date: 2026-04-25
weight: 36
description: "Pagefind 的 index 採 chunked lazy load — 首次互動延遲與 critical path 之間的取捨怎麼盤點。預載 entry chunk 的時機與不預載的代價。"
tags: ["report", "事後檢討", "Performance", "Pagefind", "工程方法論"]
---

## 核心原則

**資源載入時序的設計選擇是「首次渲染速度」與「首次互動延遲」的權衡 — 不是越早載越好。** 把不影響首次渲染的資源延後（lazy load）、首屏更快；但延後的資源在使用者真正需要時可能還沒到、互動延遲。盤點時兩者一起看。

---

## 為什麼載入時序需要設計

### 商業邏輯

每個資源都有兩個時點：

| 時點     | 含義                                                |
| -------- | --------------------------------------------------- |
| 開始下載 | 在 critical path（首屏）還是 lazy（首次互動才下載） |
| 可用     | 下載完 + parse + 執行完                             |

把資源放 critical path = 阻塞首屏渲染；放 lazy = 首屏更快但首次互動可能等。

對搜尋頁：使用者打開 `/search/` 但可能不立刻搜尋 — pagefind index lazy load 是合理選擇。但若打開後立刻打字、index 還沒載完、第一次搜尋有明顯延遲。

### Critical path vs lazy 的標準

| 資源類型                   | 通常的選擇              |
| -------------------------- | ----------------------- |
| 視覺主體 CSS（首屏看到的） | Critical path           |
| 互動 JS（事件處理）        | DOMContentLoaded 後即可 |
| 大型功能模組（搜尋 index） | Lazy、使用者觸發才載    |
| 圖片 / 影片                | Lazy 視可見性           |

選擇原則：**「首屏渲染需要嗎？」是 → critical；「使用者一定會用嗎？」否 → lazy**。

---

## 搜尋頁的具體風險點

### 風險 1：Pagefind index 下載延遲

**位置**：PagefindUI 在 mount 時開始下載 entry chunk、之後才能搜尋。

**判讀**：

- entry chunk（`pagefind-entry.json`）~ 10KB
- 下載 + parse 約 100-500ms（看網路）
- 使用者打開搜尋頁立刻打字時、第一個字可能還沒搜尋

**症狀**：使用者打開 /search/ 立刻打字、第一個字沒回應、過 200-500ms 才開始搜尋。

**第一個該查的**：DevTools Network 看 entry chunk 下載時間。> 500ms 考慮 preload 機制。

### 風險 2：個別 search chunk 的 lazy load

**位置**：使用者搜尋特定 term 時、pagefind 動態下載對應 chunk。

**判讀**：每個搜尋 term 對應一個 chunk（依 term 前綴分）。第一次搜尋某個 prefix 要下載對應 chunk、之後同 prefix 搜尋走 cache。

**症狀**：搜尋特定字時稍有延遲（200-500ms）、之後就快了。

**第一個該查的**：Pagefind 內建 cache 機制、多數情境表現可接受。若極慢可考慮 service worker preload chunk。

### 風險 3：Pagefind UI script 下載

**位置**：`<script src="/blog/pagefind/pagefind-ui.js">`。

**判讀**：

- ~ 50KB minified、需在使用者打字前載完
- 有 `defer` 不阻塞 HTML parsing、但仍占 critical path 寬度

**症狀**：搜尋頁初次載入比一般頁慢。

**第一個該查的**：確認 `<script>` 有 `defer` attribute、使用者開啟搜尋頁後背景下載、不阻塞 HTML 渲染。

### 風險 4：assets/search.css 與 pagefind-ui.css 載入順序

**位置**：兩個 stylesheet 都在 `<head>` 載入。

**判讀**：

- pagefind-ui.css 5-10KB、search.css（拆檔後）3-5KB
- 兩者都阻塞首屏渲染（CSS render-blocking）
- 加總 < 20KB、影響輕微

**症狀**：rare、僅在極慢網路下感受到。

**第一個該查的**：DevTools Network 看 CSS 下載時間。考慮：

- 把 critical CSS inline（首屏需要的部分）、其他 lazy
- 用 Hugo `resources.Get | minify | fingerprint` 確保最小化

---

## 內在屬性比較：四種載入策略

| 策略                     | 首屏速度              | 首次互動延遲          | 適用情境                    |
| ------------------------ | --------------------- | --------------------- | --------------------------- |
| 全 critical path         | 慢                    | 0（即可用）           | 小型站、所有資源都重要      |
| Lazy load 大型模組       | 快                    | 中 — 使用者觸發才下載 | 搜尋、富互動模組            |
| Critical path + lazy mix | 中                    | 低                    | 一般情境（pagefind 走這條） |
| Service Worker preload   | 中 — 首次載完後永久快 | 0 — 從 cache 取       | 高頻使用者、PWA             |

對搜尋頁的場景：**Lazy load 大型模組**是 pagefind 預設行為、合理；考慮再進一步可以 preload entry chunk 在 idle 時。

---

## Preload 的取捨

預先載入下一步可能需要的資源 — 加快互動、但浪費頻寬（若使用者最終沒用）。

```html
<link rel="preload" href="/blog/pagefind/pagefind-entry.json" as="fetch" crossorigin>
```

放 head、瀏覽器在 critical path 完成後 idle 時開始下載。

**值得做的條件**：

- 使用者進入此頁的明確意圖會觸發該資源（搜尋頁進入 = 會搜尋）
- 資源不大（entry chunk < 10KB OK）

**不值得**：

- 使用者可能只看不用（首頁載 search index 通常不值得）
- 資源很大（不要 preload 整個 search index）

---

## 正確概念與常見替代方案的對照

### 載入時序是設計、不是預設

**正確概念**：每個資源主動決定 critical path / lazy / preload — 看是否影響首屏、是否使用者必用。

**替代方案的不足**：所有資源預設 critical path（`<link>` / `<script>` 直接放 head）— 首屏慢、且多數資源使用者根本不用。

### Lazy load 不是「免費的」

**正確概念**：lazy load 把成本從首屏推到首次互動。要評估「首次互動的延遲使用者能接受嗎」、不是「lazy 一律好」。

**替代方案的不足**：把所有 JS lazy load — 互動延遲到使用者明顯感受到、體驗差。

### Preload 是「打賭使用者會用」

**正確概念**：preload 賭使用者會觸發這個資源、賭對省互動延遲、賭錯浪費頻寬。對「進入此頁 = 必用」的資源賭值得。

**替代方案的不足**：對所有 lazy 資源都 preload — 等於沒 lazy、首屏資源量回到全部 critical。

---

## 判讀徵兆

| 訊號                             | 該檢查的位置                                          |
| -------------------------------- | ----------------------------------------------------- |
| 使用者打開頁面立刻互動有明顯延遲 | 該互動依賴的資源是否 lazy、是否值得 preload           |
| 首屏渲染慢、CSS / JS 阻塞        | DevTools Network 找 critical path 中可拆 lazy 的資源  |
| Lazy 資源永遠不被觸發            | 該資源預設或許不必 lazy（不會 lazy 也不會貴）         |
| 慢網路 / 行動裝置使用者抱怨      | 用 DevTools Network throttling 模擬、量首屏與首次互動 |

**核心原則**：載入時序是設計決定、不是預設。每個資源「critical / lazy / preload」三選一明確選、不要全部丟 critical path。
