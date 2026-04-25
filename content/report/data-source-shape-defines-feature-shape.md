---
title: "資料源的形狀決定 feature 的形狀"
date: 2026-04-26
weight: 63
description: "Feature 設計要服從資料源的形狀（一次性 / 分批 / streaming / cached）— 不能憑 UI 想要的形狀去倒推資料層。憑 UI 倒推 = 在錯誤的層解錯誤的問題、產生 #55 層錯位類 bug。"
tags: ["report", "事後檢討", "工程方法論", "Architecture"]
---

## 核心原則

**Feature 的設計受資料源的形狀約束、不能憑 UI 想要的形狀去倒推**。

| 資料源形狀                      | 對 feature 的硬約束                      |
| ------------------------------- | ---------------------------------------- |
| 一次性 fetch（靜態 / API 全集） | Filter / sort / count 都安全可在任意層做 |
| 分批 fetch（pagination）        | Filter / sort 必須跟 source 同層         |
| Streaming（SSE / iterator）     | 結果可能無上限、count 是不確定值         |
| Cached + revalidate             | 兩個 dataset 並存、要決定哪個 winning    |

憑 UI 倒推資料層 =「我希望畫面這樣呈現、所以資料層應該這樣」 → 多半會在錯誤的層做錯誤的操作（見 #55 [層錯位](../view-layer-filter-vs-source-layer/)）。

---

## 為什麼會憑 UI 倒推

### UI 設計通常先動

設計師畫 wireframe、PM 描述體驗、執行者看到的是「畫面該長什麼樣」 — 資料層的限制不在 wireframe 裡。

### UI 形狀對資料層假設過強

UI 上「filter 拉桿」這個元件、隱含假設「資料能立即過濾」 — 但如果資料是分批 fetch、立即過濾在資料層不成立。執行者按 UI 寫 → view 層 post-filter → 撞上層錯位。

### 「能用」訊號早於「對齊資料形狀」

寫完 view 層 filter、手動測一次能用、覺得對 — 但能用的範圍是「已載入子集」、不是「完整 dataset」。資料形狀的限制要刻意對照才看得到。

---

## 多面向：資料源形狀的不同類型

### 形狀 1：一次性給完整 dataset

範例：靜態 JSON、SSR 完整渲染、API 一次回全集（< 1MB）。

| Feature 設計  | 安全與否 |
| ------------- | -------- |
| 任意層 filter | 安全     |
| 任意層 sort   | 安全     |
| Count         | 安全     |
| Pagination    | 不需要   |

這類 source 是「最寬容」的、UI 想怎麼設計都行。

### 形狀 2：分批 fetch（pagination）

範例：pagefind、infinite scroll、cursor-based API。

| Feature 設計     | 限制                                      |
| ---------------- | ----------------------------------------- |
| Filter           | 必須跟 source 同層（A）或自動續抓（B）    |
| Sort             | 必須是 server-side sort、不能 client 重排 |
| Count            | 通常需要 source 提供 total（pagefind 有） |
| 「跳到最後一頁」 | 需要 cursor / offset 支援                 |

UI 設計時要避開：「立即 filter」「立即 sort」「Show all」 — 這些假設 dataset 已 materialize。

### 形狀 3：Streaming / async iterator

範例：SSE、WebSocket push、async iterator from generator、log tail。

| Feature 設計 | 限制                                   |
| ------------ | -------------------------------------- |
| Filter       | 可在 stream 裡做（透明）               |
| Sort         | 不能 — stream 沒終點、無法 sort        |
| Count        | 「目前累計」、不是「總數」             |
| 進度條       | 只能顯示「已收 N 筆」、不能 % progress |

UI 設計時要避開：「sort by 任意欄位」「總共 X 筆」「進度條 50%」 — 這些假設有限終點。

### 形狀 4：Cached + revalidate

範例：service worker cache、SWR、HTTP cache、IndexedDB cache。

| Feature 設計     | 限制                                       |
| ---------------- | ------------------------------------------ |
| Filter           | 哪個 dataset 在 filter？cache 還是 fresh？ |
| 「最新狀態」訊號 | 需要 UI 區分 stale vs fresh                |
| 衝突處理         | Cache 跟 fresh 結果不同時、誰 winning？    |

UI 設計時要決定：cache-first（快但 stale）還是 fresh-first（慢但新）。Filter 跟其他操作要對齊這個選擇。

---

## 寫 feature 前的形狀對照表

寫第一行之前、先填這張表：

| 維度                          | 答案                    |
| ----------------------------- | ----------------------- |
| Source 是什麼形狀（1-4）      | ?                       |
| Total cardinality 是多少      | ?（10? 1萬? 10萬?）     |
| 是否分批 / 限額 / streaming   | ?                       |
| Source 支援哪些 filter / sort | ?                       |
| Cache 策略（如果有）          | ?                       |
| Match 密度預期                | ?（密集 / 中等 / 稀疏） |

填完後評估：UI 設計需求跟資料形狀有沒有衝突？衝突就重設計 UI、或調整資料層、或退到誠實 UX（D）。

---

## 設計取捨：UI 還是 Source 先服從

### A：UI 服從 source 形狀（推薦）

- **機制**：先看 source 給什麼形狀、UI 設計成「這個形狀能呈現的」
- **適合**：source 已存在（vendor library、legacy API、無法改）
- **代價**：UI 可能比設計理想中簡單

### B：Source 服從 UI 需求（重設計 source）

- **機制**：UI 設計理想化、為了支援 UI、改 source（重 index、加欄位、換 SDK）
- **跟 A 的取捨**：B 工程量大、但 UX 上限高
- **B 才合理的情境**：source 能控、改 source 的成本 < 長期 UX 收益

### C：兩邊妥協、用誠實 UX 補縫

- **機制**：UI 設計理想、source 不重做、用 #62 誠實進度 UX 把資料形狀的限制告訴使用者
- **跟 A 的取捨**：C 比 A 顯眼、比 B 工程量小、是常見的中間方案
- **C 才合理的情境**：使用者能接受顯眼的「掃描範圍」UX

### D：UI 假裝 source 形狀符合、silent 失敗

- **D 成本特別高的原因**：使用者基於錯誤訊號決策、信任損失
- **D 才合理的情境**：實務上幾乎不存在

---

## 判讀徵兆

| 訊號                                                       | 該做的行動                         |
| ---------------------------------------------------------- | ---------------------------------- |
| 拿到 wireframe 開始實作前、沒看過資料源 API doc            | 先看 — 確認資料形狀                |
| UI 含「立即 filter」「sort by 任意欄位」但 source 是分批的 | 衝突 — 重設計 UI 或重 index source |
| UI 顯示 progress bar 但 source 是 streaming                | 衝突 — 改成「已收 N 筆」、不寫 %   |
| Cache 策略沒設定就開始寫 feature                           | 先設定 — cache-first / fresh-first |
| 內心 OS：「資料層之後處理、先把 UI 寫出來」                | 停 — 形狀對照表先填                |

**核心原則**：資料源的形狀是 feature 的硬約束。UI 設計可以理想化、但實作要看 source 給什麼。憑 UI 倒推資料層的實作 = 在錯誤的層解錯誤的問題、最終產生層錯位類 bug。
