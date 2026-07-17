---
title: "6.15 Environment Parity 與漂移控制"
date: 2026-05-01
description: "把 staging / preprod / prod 之間的差異視為一級風險，按漂移來源分類偵測與治理"
weight: 15
tags: ["backend", "reliability"]
---

## 概念定位

Staging 通過但 production 上線失敗 — 這類事故的根因常常是環境差異。Environment parity 把 staging 與 production 的差異視為一級風險，要求會影響行為的差異被識別與管理。

三個環境完全相同既不可能也不必要，但未被追蹤的差異會讓測試結論與真實服務脫鉤。

## 核心判讀

Parity 漂移最先暴露的訊號是差異是否可見，接著決定差異是否會改變驗證結果。

判讀時看四件事：

- config drift 是否有清單與責任人
- data shape 是否接近 production
- infra parity 是否涵蓋 network、storage、identity
- release 前是否知道哪些差異會影響判讀

## 漂移來源分類

Parity 漂移按來源分類，不同來源的風險特徵與偵測手段不同。

### Config drift

環境變數、[timeout](/backend/knowledge-cards/timeout/)、[connection pool](/backend/knowledge-cards/connection-pool) size、retry config、feature flag 在 staging 與 prod 不同步。這是最常見的漂移來源，因為 config 變更頻率高且通常不走完整 review 流程。

典型暴露時機：staging 測試通過，但 prod 上線後 timeout 觸發或 pool 耗盡，根因是 staging 的 timeout 設定比 prod 寬鬆。偵測手段：定期 config snapshot diff，標註差異項目與 owner。

### Scale drift

Staging 用單機或少量 replica，prod 用多區多 replica。query plan 在小資料集走 index scan、在大資料集走 table scan；[connection pool](/backend/knowledge-cards/connection-pool) 在低併發下不飽和、在高併發下排隊；load balancer 在少 replica 時的路由行為跟多 replica 時不同。

典型暴露時機：壓測在 staging 通過，但 prod 出現 connection pool 耗盡或 load balancer 的 least-connection 策略在高 replica 數下行為不同。偵測手段：對照 staging 與 prod 的 replica count、resource quota、auto-scaling 設定。

### Data drift

Staging 資料量遠小於 prod，資料分佈也不同。index scan vs table scan 的切換點跟資料量直接相關；cache hit ratio 跟 key 分佈與資料量相關；pagination 行為在千筆與百萬筆資料下差異顯著。

典型暴露時機：staging 的查詢 < 50ms，prod 同一查詢 > 2s，根因是 staging 資料量不足以觸發 full table scan。偵測手段：比較 staging 與 prod 的資料表 row count 與 key 分佈統計。

### Dependency drift

Staging 跟 prod 使用不同版本的 [database](/backend/knowledge-cards/database/) engine、cache、[broker](/backend/knowledge-cards/broker/) 或 cloud service。版本差異的行為差異通常在 edge case 才暴露：不同版本的 SQL dialect、cache eviction policy、message ordering guarantee 可能不同。

典型暴露時機：DB engine 小版本升級改變了 query optimizer 行為，staging 早已升級但 prod 延遲升級，兩邊 query plan 不同。偵測手段：維護 dependency version matrix，每次版本變更時檢查跨環境一致性。

### Infra drift

Network topology、DNS 解析路徑、TLS 配置、identity provider 設定在不同環境不同。跨服務通訊路徑的差異最難偵測，因為這些差異通常在正常流量下不可見，只在跨區切換、failover 或 mTLS 驗證時才暴露。

典型暴露時機：staging 用同區呼叫、prod 跨區呼叫，latency 差異導致 timeout 觸發條件不同。偵測手段：infra-as-code diff 與定期 topology audit。

## 漂移偵測機制

偵測環境漂移需要多種手段組合，單一手段無法覆蓋所有漂移來源。

### Automated config diff

定期比較 staging 與 prod 的 config snapshot，輸出差異清單並標註 owner。diff 結果按風險等級分類：會影響行為的差異（timeout、pool size、retry policy）標為高風險；只影響標籤或描述的差異標為低風險。高風險差異在 release review 時必須被討論。

### Contract + parity test

[Contract test](/backend/06-reliability/contract-testing/) 驗證 API 邊界（schema、欄位、狀態碼）在不同環境的一致性。Parity test 更進一步，驗證同一請求在 staging 與 prod 的行為結果是否相同。兩者互補：contract test 抓結構差異，parity test 抓行為差異。

### Shadow traffic

用 prod 流量的副本打 staging，比較回應差異。shadow traffic 能偵測 data drift 和 dependency drift，因為它用真實請求觸發真實查詢路徑。限制是寫入操作需要隔離處理（shadow write 不能影響 prod 資料），且 staging 需要有足夠容量承接 prod 流量副本。跟 [6.2 load testing](/backend/06-reliability/load-testing/) 的 synthetic traffic 限制互補 — synthetic traffic 偵測不到的環境差異，shadow traffic 通常能暴露。

### Canary 作為中間層

Canary 環境處於 staging 與 prod 之間，用少量真實流量驗證變更。parity 差異在 canary 階段暴露的成本遠低於在 prod 全量暴露。canary 的偵測價值在於它跑在 prod infra 上但只承接部分流量，能暴露 scale drift 和 infra drift。

canary 的限制是覆蓋時間：流量比例低時，low-frequency 的 edge case 可能在 canary 期間不出現。canary 時間越長覆蓋率越高，但拉長 canary 會延遲交付。這個 trade-off 要對齊變更風險等級 — 高風險變更拉長 canary，低風險變更可以縮短。

## Production-like data 策略

Staging 需要接近 prod 的資料才能讓驗證結果可信。三種策略各有 trade-off。

| 策略                      | 真實度 | 隱私風險 | 維護成本 | 適用場景                      |
| ------------------------- | ------ | -------- | -------- | ----------------------------- |
| Production sample（脫敏） | 高     | 中       | 高       | query plan 敏感、資料分佈關鍵 |
| Synthetic generation      | 中     | 低       | 中       | 功能驗證為主、分佈次要        |
| Schema-only + seed        | 低     | 低       | 低       | 早期開發、schema 驗證         |

Production sample 從 prod 抽樣後做 PII masking，資料分佈最接近真實，但需要遮罩管線且每次 schema 變更後要重新抽樣。Synthetic generation 用程式生成接近 prod 分佈的假資料，安全性高但分佈模型需要維護，偏移累積後資料特徵會跟 prod 脫鉤。Schema-only + seed 只複製 schema、用 seed 填少量資料，速度最快但跟 prod 差距最大，query plan 幾乎無法對齊。

選擇策略的判斷條件：如果系統的風險集中在 query performance 或 data-dependent 行為，production sample 是必要的；如果風險集中在功能正確性，synthetic generation 足夠；如果還在早期開發階段，schema-only + seed 可以先用，但上線前要升級。詳見 [6.16 test data management](/backend/06-reliability/test-data-management/)。

## Parity 治理流程

環境漂移是持續的，一次對齊不代表之後不會漂移。治理流程的責任是讓漂移保持可見且可決策。

**維護環境差異清單**：記錄所有已知的環境差異，每項標注 owner、風險等級與存在理由。有些差異是刻意的（staging 用較小 instance 節省成本），有些是遺忘的（某次 prod hotfix 沒同步到 staging）。區分刻意與遺忘的差異，才能知道哪些差異需要修復、哪些需要在判讀時考慮。

**Release 前 review 差異清單**：每次 release 前把差異清單跟變更內容交叉比對。如果本次變更涉及 connection pool 設定，但 staging 的 pool size 跟 prod 不同，這個差異就會影響驗證結論，必須在放行時被標記。連到 [6.19 reliability readiness review](/backend/06-reliability/reliability-readiness-review/) 的 pre-release checklist。

**Infra 變更同步**：新增 infra 變更時，同步更新 staging 或在差異清單中標記新增風險。infra-as-code 讓同步變得可自動化，但仍需要 review 確認 staging 的資源配額是否需要調整。

## 案例對照

- [Heroku](/backend/08-incident-response/cases/heroku/)：平台抽象越高，環境行為差異越不可見，漂移偵測需要更主動的手段。
- [GCP](/backend/08-incident-response/cases/gcp/)：區域、網路與權限設定差異會直接影響驗證結論，infra drift 在跨區場景最先暴露。
- [GitHub](/backend/08-incident-response/cases/github/)：大規模部署時，環境差異通常先變成事故放大器，漂移控制是降低放大倍數的前置工作。

## 判讀訊號

| 訊號                                                    | 判讀條件                                        | 行動建議                                       |
| ------------------------------------------------------- | ----------------------------------------------- | ---------------------------------------------- |
| staging 通過、prod 上線失敗，根因是 config / scale 差異 | parity 差異未被 release review 識別             | 把失敗根因加入環境差異清單 + release checklist |
| staging 跟 prod 用不同 DB engine 版本 / cache 配置      | dependency drift 未被 version matrix 追蹤       | 建 dependency version matrix、定期 diff        |
| shadow traffic 從未啟用、staging 流量靠手動測試         | data drift 和 dependency drift 沒有持續偵測機制 | 啟用 shadow traffic 或 canary 驗證             |
| prod-only bug 反覆出現、staging 無法重現                | 環境差異是 bug 的根因，差異清單可能遺漏關鍵項目 | 回查差異清單、補漏項 + owner                   |
| 環境差異無 owner、漂移無 review                         | parity 治理流程不存在或已停止運作               | 指定 parity owner、加入 release review 流程    |

## 交接路由

- [05 部署平台](/backend/05-deployment-platform/)：環境拓撲一致性與 canary 機制
- [6.2 load testing](/backend/06-reliability/load-testing/)：staging 壓測結果的可信度受 parity 影響
- [6.10 contract testing](/backend/06-reliability/contract-testing/)：契約覆蓋環境邊界
- [6.16 test data management](/backend/06-reliability/test-data-management/)：production-like data 來源與策略
- [6.19 reliability readiness review](/backend/06-reliability/reliability-readiness-review/)：release 前的 parity review
- [6.20 experiment safety boundary](/backend/06-reliability/experiment-safety-boundary/)：staging vs production 測試的安全邊界
- [8.5 post-incident review](/backend/08-incident-response/post-incident-review/)：parity 漂移作為事故根因類別
- [6.26 QA environment design](/backend/06-reliability/qa-environment-design/)：測試環境作為服務的消費者契約（刻意漂移如診斷欄位須登錄進差異清單）
