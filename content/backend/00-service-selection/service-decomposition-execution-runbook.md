---
title: "0.20 服務拆分執行 Runbook（Strangler Fig / 雙寫期 / 切流 / 回退）"
date: 2026-05-27
description: "0.18 決定該拆之後、實際怎麼動手拆 — Strangler Fig pattern、雙寫期管理、切流策略、回退條件設計"
weight: 20
tags: ["backend", "service-selection", "microservice", "runbook"]
---

[0.18 服務拆分與邊界判讀](/backend/00-service-selection/service-decomposition-boundaries/) 處理「該不該拆」、本章處理「決定拆之後實際怎麼動手」。拆服務不是一次性大爆炸（big bang）動作、而是漸進演進。[Strangler Fig pattern](/backend/knowledge-cards/strangler-fig/) 是這層的工程基底 — 用「新功能在新服務、舊功能慢慢搬」的方式、把整個 monolith 包圍、逐步替換。

## Strangler Fig Pattern 的工程含義

Strangler Fig（絞殺榕）是 Martin Fowler 對漸進拆分的命名比喻：榕樹依附在宿主樹上、慢慢長大、最終取代宿主。應用到服務拆分：

- **舊系統繼續運作**：拆分過程中、monolith 仍是 source of truth、新服務從旁長出
- **流量逐步遷移**：用 routing layer（API gateway、proxy、feature flag）控制哪些 request 走新服務、哪些走舊
- **驗證 → 擴大**：每個遷移的功能先小流量驗證、確認新舊一致後再加流量比例
- **舊系統最終下架**：當所有功能都遷出後、monolith 才被退役

Strangler Fig 跟 big bang 拆分的本質差異是「失敗代價可控」— 大爆炸拆分失敗就整個服務掛、Strangler 拆分失敗只影響該功能、且可即時切回 monolith。

## 拆分執行的四階段

把 Strangler 細化成可操作的四階段：

### 階段 1：邊界冷凍 + Adapter 抽出

動手拆之前、先在 monolith 內部把「將要拆出去」的功能用 adapter / interface 封起來。所有外部呼叫該功能都走 adapter、不直接呼叫實作。

這層動作的責任：

- **強制 dependency 清楚**：哪些功能依賴它、哪些功能被它依賴、必須變成顯式 interface 而非分散在 codebase
- **資料邊界明示**：該功能用到哪些 table / column、用 repository / DAO 封裝、不讓其他功能直接 access
- **變更頻率冷凍**：拆分期間原則上不接受該功能的新需求、避免「拆到一半新需求又進來」

階段 1 在 monolith 內完成、不動部署、不動資料。完成後、拆分的「邊界」已經在 codebase 顯現、是 prerequisite。

### 階段 2：新服務 + 雙寫期

新服務 spin up、實作 adapter 同樣的介面。寫入路徑進入「雙寫期」：所有寫入同時寫 monolith 跟新服務、讀取仍從 monolith 取。

雙寫期的設計關鍵：

- **寫入順序**：先寫 monolith 還是先寫新服務？通常先寫 monolith（保持 source of truth 一致性）、新服務寫失敗時記 error 但不影響業務
- **跨服務一致性**：兩邊寫入用 [outbox pattern](/backend/knowledge-cards/outbox-pattern/) 或 [saga](/backend/knowledge-cards/saga/) 保證最終一致、不能容忍長期不一致
- **資料對賬機制**：每天 / 每小時跑對賬 job、找出兩邊不一致的 row、修正 + 統計差異率
- **雙寫期長度**：通常 1-4 週、視差異率收斂速度決定。差異率穩定在 0.01% 以下、可進階段 3

雙寫期的失敗訊號：差異率持續高於 1%、代表資料模型對應有 gap、不該進切流階段。

### 階段 3：切流（讀路徑遷移）

雙寫期穩定後、讀路徑開始從 monolith 切到新服務。切流策略選擇：

- **按 user / tenant ID hash 分流**：取 user_id mod 100、x% 走新服務、其餘走 monolith。漸進 ramp up（1% → 5% → 25% → 100%）
- **按 endpoint 分流**：read endpoint A 全切、endpoint B 跟 C 還在 monolith。適合「不同 endpoint 風險不同」的場景
- **Dark launch**：每個 request 同時打兩邊、用 monolith 結果回應、log 兩邊差異。是 shadow read、不是真實切流、但能在切流前找出 edge case

切流期間的觀測重點：

- **錯誤率對比**：新服務 vs monolith 同 endpoint 的 5xx / 4xx 比例
- **延遲分布對比**：P50 / P95 / P99 latency
- **業務指標對比**：轉換率、跳出率、訂單成功率 — 確認沒有「技術指標看起來正常、業務指標掉」的隱形 regression

任一指標惡化、切回 monolith、不繼續推進。

### 階段 4：寫路徑遷移 + Monolith 退役

讀路徑 100% 切完、且穩定觀察一段時間後（建議至少 2 週）、寫路徑才從「雙寫」變成「只寫新服務」。

寫路徑切換的步驟：

1. **雙寫變成「新服務 + 異步 backfill 到 monolith」**：以新服務為主、monolith 變成 standby
2. **觀察期 1-2 週**：確認新服務寫入路徑穩定、無資料遺失或不一致
3. **停止 backfill**：monolith 不再被寫入、變成 read-only
4. **Monolith 該功能下架**：等確認所有 dependency 都已遷移後（通常還要再 1-4 週觀察）、刪掉 monolith 對應 code 跟 table

階段 4 是 point of no return — 過了寫路徑切換、回 monolith 的成本變得很高（要把新服務累積的寫入 backfill 回去）。這個 checkpoint 必須有明確的 go/no-go 決策、不是「順勢推進」。

## 回退路徑設計

回退條件必須在拆分啟動前就定義、不是事故時臨時決策。常見回退路徑：

| 階段 | 失敗訊號                             | 回退動作                                         | 成本 |
| ---- | ------------------------------------ | ------------------------------------------------ | ---- |
| 1    | Adapter 抽出後 monolith 變慢 / 出錯  | revert PR、重新規劃 adapter 邊界                 | 低   |
| 2    | 雙寫期差異率 > 1% 持續               | 停雙寫、回 monolith 單寫、修資料模型對應         | 中   |
| 3    | 切流期間錯誤率 / 延遲 / 業務指標惡化 | 切流比例調回 0%、回 monolith 單讀、雙寫繼續      | 中   |
| 4    | 寫路徑切換後 1 週內出資料遺失        | 觸發 backfill from 新服務 → monolith、切回雙寫期 | 高   |
| 4+   | Monolith 已下架、新服務出事          | 災難級別、需要從備份重建 + 大規模事件公告        | 極高 |

階段 4 之後的回退代價是指數成長的。設計時要把 monolith 下架時點延後到「確信不需要回退」、寧可多保留 monolith 1-2 個月。

## 拆分執行的判讀訊號

| 訊號                                              | 判讀重點                                              | 對應動作                                               |
| ------------------------------------------------- | ----------------------------------------------------- | ------------------------------------------------------ |
| Adapter 抽出時發現難以封裝（dependency 散落各處） | 邊界其實沒形成、拆分判斷錯了                          | 回 0.18 重新評估、考慮先重構 monolith 再拆             |
| 雙寫期差異率不收斂                                | 資料模型對應有 gap、或業務邏輯有 monolith 隱式依賴    | 暫停拆分、做 data audit、找出隱式依賴點                |
| 切流比例增加後業務指標掉                          | 技術等價但業務行為不等價（例如 latency 微升影響轉換） | 切回 monolith、檢查 latency / 業務指標關聯             |
| 階段 4 出現「monolith 還有人在用」                | dependency 沒清乾淨、有隱藏的呼叫者                   | 延後 monolith 下架、用 access log audit 找出殘留呼叫者 |
| 拆分過程中 dev velocity 大幅下降                  | 拆分成本超過短期收益、可能拆錯時機                    | 評估暫停拆分、回到 modular monolith                    |

## 常見誤區

把拆分當成「直接把功能搬出去」、跳過階段 1 adapter 抽出。沒有 adapter 抽出、新服務跟 monolith 的 dependency 邊界不清楚、雙寫期會出現難以排查的隱式依賴問題。

把雙寫期當成「過渡而已、隨便寫」。雙寫期是拆分的 source of truth verification 階段、差異率沒收斂前不能進切流。隨便寫的結果是切流後出資料一致性事故。

把「monolith 下架」當成拆分成功訊號。Monolith 下架太早是常見事故來源 — 即使流量 100% 切完、可能仍有 batch job / report / 內部 tool 在用 monolith。下架前先用 access log audit 確認真實流量為 0。

## 定位邊界

本章專注「Strangler Fig 漸進拆分的執行流程」。當問題進入「該不該拆」的判讀、回 [0.18 服務拆分與邊界判讀](/backend/00-service-selection/service-decomposition-boundaries/)；進入跨服務通訊設計（同步 vs 異步、event-driven）、進 [03 message queue](/backend/03-message-queue/)；進入部署層的切流機制（feature flag、canary、blue/green）、進 [5.8 deployment rollout](/backend/05-deployment-platform/deployment-rollout-drain-rollback/)；進入資料庫遷移層的具體技術（dual write、shadow read、cutover），進 [1.6 資料庫轉換實作](/backend/01-database/database-migration-playbook/)。

## 案例回寫

09 / 05 案例庫中、Strangler 拆分案例不算多（多數案例是已拆完的狀態描述、而非拆分過程紀錄）。可用以下案例反向追問：

- [9.C23 Netflix Aurora consolidation](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) — Netflix 的故事是「拆完合回去」、隱含 strangler 反向。對照本章可問：合併過程是否也走了類似四階段、只是方向相反（雙寫期把多 DB 合到 Aurora、再切讀路徑、最後下架原 DB）？
- [5.C2 Condé Nast：EKS 平台整併](/backend/05-deployment-platform/cases/conde-nast-platform-modernization-eks/) — 平台層整併。本章在「服務層」、整併在「平台層」、邏輯類似但 surface 不同。

## 跨模組路由

1. 與 [0.18 服務拆分判讀](/backend/00-service-selection/service-decomposition-boundaries/) 的交接：0.18 給「該拆」的判讀、本章給「怎麼拆」的執行。
2. 與 [03 message queue + outbox](/backend/03-message-queue/) 的交接：雙寫期跟拆分後跨服務通訊都依賴 outbox / saga 保證一致性。
3. 與 [5.8 deployment rollout](/backend/05-deployment-platform/deployment-rollout-drain-rollback/) 的交接：階段 3 切流的技術機制（feature flag、canary）跟部署層的 rollout 同源。
4. 與 [1.6 資料庫轉換實作](/backend/01-database/database-migration-playbook/) 的交接：階段 2 雙寫期跟資料庫遷移的雙寫期是同一套機制、只是 surface 不同。

## 下一步路由

要看拆分判讀（該不該拆）、回 [0.18 服務拆分與邊界判讀](/backend/00-service-selection/service-decomposition-boundaries/)。要看拆分後跨服務通訊設計、進 [03 模組訊息佇列](/backend/03-message-queue/)。要看部署層的切流技術細節、進 [5.8 Deployment Rollout](/backend/05-deployment-platform/deployment-rollout-drain-rollback/)。
