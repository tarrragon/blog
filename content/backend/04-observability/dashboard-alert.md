---
title: "4.4 dashboard 與 alert 設計"
date: 2026-06-22
description: "讓 dashboard 與 alert 對應 runbook 與容量趨勢"
weight: 4
tags: ["backend", "observability"]
---

## 大綱

- [Dashboard](/backend/knowledge-cards/dashboard/) 設計原則：SLI 導向 vs 指標堆疊
- [Alert](/backend/knowledge-cards/alert/) 設計：symptom-based vs cause-based
- Alert noise control 與 [alert fatigue](/backend/knowledge-cards/alert-fatigue/)
- [Runbook](/backend/knowledge-cards/runbook/) linkage
- Dashboard / alert 的生命週期與 ownership
- 反模式

## 概念定位

[Dashboard](/backend/knowledge-cards/dashboard/) 與 [alert](/backend/knowledge-cards/alert/) 是把觀測訊號轉成操作入口的控制面，責任是讓團隊在正常巡檢與事故響應時看到同一組事實。

Dashboard 讓人理解狀態，alert 讓人採取行動。兩者的設計問題不同：dashboard 的問題是「資訊太多、焦點不明」；alert 的問題是「通知太多、行動不明」。兩者都需要 [ownership](/backend/knowledge-cards/ownership/)、生命週期管理與 [runbook](/backend/knowledge-cards/runbook/) 連結。

## Dashboard 設計

### SLI 導向 vs 指標堆疊

Dashboard 的常見失敗模式是「把所有能拿到的指標都放上去」。二十個 panel、五十條曲線、無法在 3 秒內回答「服務現在健康嗎」。

SLI 導向的 dashboard 從使用者體驗出發：第一排 panel 回答「使用者感受到的健康狀態」（availability、latency percentile、error ratio），第二排回答「健康狀態的原因」（dependency latency、queue depth、resource utilization），第三排回答「趨勢與容量」（traffic growth、storage usage、capacity headroom）。

每個 panel 都應該能回答一個具體問題。如果團隊看了某個 panel 後的反應是「所以呢？」，這個 panel 不是放錯位置就是不該存在。

### Dashboard 層級

不同使用者看不同層級的 dashboard。把所有資訊擠在同一個 dashboard 會讓每個角色都找不到自己要的。

**Service overview**：on-call 工程師的第一個入口。5-8 個 panel，回答「這個服務現在有沒有問題」。SLI 指標（error rate、latency p99、availability）、最近的 alert、dependency 健康。

**Debug dashboard**：事故中的深入診斷入口。按 dependency 分組（database panel group、cache panel group、downstream API panel group），每組顯示延遲、錯誤率、連線數。Panel 數量多但按需展開。

**Capacity dashboard**：容量規劃用。週到月級的趨勢圖 — traffic growth、storage usage、connection pool saturation、cost trends。刷新頻率低（每小時或每天），panel 讀 [recording rule](/backend/knowledge-cards/recording-rule/) 或 [rollup](/backend/knowledge-cards/rollup/) 資料。

**Business dashboard**：給非工程角色看。轉換率、使用者活躍度、營收指標。資料來源可能不只是觀測訊號，還包括 analytics 跟 business metrics。

### Dashboard 的查詢效能

Dashboard 是觀測查詢設計中「聚合趨勢」模式的主要消費者（見 [4.23](/backend/04-observability/observability-query-design/)）。每個 panel 每 30 秒刷新一次，十個團隊各自有 dashboard 就是每分鐘數百個背景查詢。

Panel 設計時要注意查詢成本：時間範圍越長、raw series 越多、聚合越複雜，query-time cost 越高。長時間趨勢 panel 應該讀 recording rule 或 rollup series，而非每次刷新都掃描 raw data。

## Alert 設計

### Symptom-based vs cause-based

[Symptom-based alert](/backend/knowledge-cards/symptom-based-alert/) 觸發在使用者可感知的症狀上 — error rate 升高、latency p99 超過閾值、availability 下降。Cause-based alert 觸發在內部原因上 — CPU > 90%、disk usage > 85%、connection pool exhausted。

Symptom-based 是 alert 設計的起點。原因是：cause-based alert 容易產生大量「系統在忙但使用者沒受影響」的 false alarm。CPU 短暫衝到 95% 然後回落，如果 latency 跟 error rate 都正常，這個 alert 不需要人類介入。

Cause-based alert 的價值是預防性告警 — disk usage 趨勢在兩天後會滿、connection pool 使用率在高峰時逼近上限。這類 alert 不需要立即行動，但需要在工作時間排入 task。把 cause-based alert 設成 warning（不 page）、symptom-based alert 設成 critical（page on-call），能降低 noise。

### SLO-based alerting

SLO-based alerting 用 [burn rate](/backend/knowledge-cards/burn-rate/) 取代固定閾值。不是「error rate > 1% 就告警」，而是「error budget 的消耗速度超過預期就告警」。

Burn rate alerting 的好處是自動適應基線。低流量時段的 1% error rate 可能只是幾筆錯誤、不值得 page；高流量時段的 0.5% error rate 可能代表大量使用者受影響。Burn rate 用「相對於 SLO 允許的錯誤量，目前消耗速度有多快」來判斷嚴重性，比固定閾值更能反映使用者影響。

SLO-based alert 的實作通常用 multi-window burn rate — 短視窗（5 分鐘）抓急性問題、長視窗（1 小時）抓慢性問題。兩個視窗都超過 burn rate 閾值時才觸發，減少單一 spike 造成的 false alarm。

SLI/SLO 訊號的詳細設計見 [4.6](/backend/04-observability/sli-slo-signal/)。

### Alert 的必要欄位

每個 alert rule 應該帶以下 metadata，讓收到 page 的 on-call 工程師在 30 秒內知道下一步：

- **Severity**：critical（立即行動）/ warning（工作時間處理）/ info（記錄但不通知）
- **Runbook link**：對應的 [runbook](/backend/knowledge-cards/runbook/) URL，描述診斷步驟跟可能的修復動作
- **Owner**：負責這個 alert 的團隊或服務
- **Dashboard link**：點進去直接看相關 panel，不用自己找 dashboard
- **Summary**：一句話描述發生了什麼（`checkout error rate > 2% for 5 minutes`），而非只有 alert rule 名稱

缺少 runbook link 的 alert 等於「通知了但不告訴你做什麼」。On-call 工程師收到不認識的 alert 時，第一反應是 ack 然後繼續觀察 — 這就是 [alert fatigue](/backend/knowledge-cards/alert-fatigue/) 的起點。

## Alert Noise Control

### 什麼是 noise

Alert noise 是「觸發了但不需要人類行動」的 alert。包括：

- **False positive**：條件觸發但實際沒問題（短暫 spike 觸發固定閾值、maintenance 期間的預期 error）
- **Redundant alert**：同一個問題觸發多個 alert（database 慢 → query timeout alert + error rate alert + latency alert 同時觸發）
- **Stale alert**：條件已經不適用（服務改版後舊 alert rule 沒更新、abandoned service 的 alert 還在）

### Noise rate 量測

Noise rate = 不需要行動的 alert / 總 alert。追蹤方式是讓 on-call 工程師在 ack alert 時標記「actionable」或「noise」。月度彙整 noise rate，超過 30% 的 alert rule 進入治理流程（業界常用的基線閾值，Google SRE Workbook 建議 actionable rate 維持在 70% 以上；團隊可依自身容忍度調整）。

### 降噪手段

**Grouping**：把同一個根因觸發的多個 alert 合併成一則通知。Alertmanager 的 `group_by` 讓同服務、同 alert name 的 alert 只發一次。

**Inhibition**：高嚴重性 alert 抑制低嚴重性。Database down 觸發時，所有依賴該 database 的 query timeout alert 被抑制 — 根因已知、不需要每個症狀都通知。

**Silence / maintenance window**：已知的維護活動期間暫停特定 alert。Silence 需要有過期時間，避免永久靜默掩蓋真實問題。

**Hysteresis**：alert 觸發需要條件持續 N 分鐘（`for: 5m`），避免瞬間 spike 觸發。恢復也需要條件持續 N 分鐘，避免「反覆觸發 → 恢復」的 flapping。

## Runbook 設計

[Runbook](/backend/knowledge-cards/runbook/) 是 alert 的行動指南。每個 critical alert 應該連到一份 runbook，描述「收到這個 alert 時該做什麼」。

Runbook 的有效結構：

1. **症狀描述**：這個 alert 代表什麼（「checkout error rate 超過 SLO burn rate」）
2. **影響評估**：誰受影響、嚴重程度（「付款功能受影響、影響所有 checkout 流程」）
3. **診斷步驟**：先看哪個 dashboard、查哪些 log、跑哪些 query
4. **可能的修復動作**：restart service、scale up、rollback deployment、failover to backup
5. **升級路徑**：如果 15 分鐘內無法解決，通知誰

Runbook 的維護責任跟 alert 的 owner 一致。Alert rule 改了但 runbook 沒更新是常見的退化 — 把 runbook 的 last-reviewed date 作為 alert 治理的審計項目。

## Dashboard 與 Alert 的生命週期

Dashboard 跟 alert 都有生命週期。建立時有用，但隨服務演進可能變得過時、冗餘或誤導。沒有生命週期管理的 dashboard / alert 系統會累積 debt — dashboard 數量膨脹但無人看、alert rule 堆疊但多數是 noise。

### Ownership

每個 dashboard 跟每個 alert rule 都需要明確的 owner。Owner 負責：維護 panel / rule 的正確性、定期審視 noise rate 跟使用率、在服務變更時更新對應的 dashboard / alert。

沒有 owner 的 dashboard 跟 alert 應該有過期機制 — 超過 N 天沒有人訪問的 dashboard 標記為候選淘汰、超過 N 天沒有觸發的 alert rule 審視是否仍有意義。

### 定期審視

Dashboard 跟 alert 的定期審視是 [4.8 signal governance loop](/backend/04-observability/signal-governance-loop/) 的一部分。每季或每次重大事故後，審視：

- 哪些 alert 的 noise rate 過高、需要調整或刪除
- 哪些 dashboard 沒人訪問、可以合併或淘汰
- 事故中是否有缺少的 alert 或 dashboard panel

Ownership 矩陣與 metadata 欄位的詳細設計見 [4.18 operating model](/backend/04-observability/observability-operating-model/)。

## 核心判讀

Dashboard 跟 alert 是否有效，最直接的訊號是 alert noise rate 跟 dashboard 訪問頻率 — noise rate 超過 30% 代表通知品質退化，dashboard 長期零訪問代表資訊跟決策脫節。

重點訊號包括：

- Alert 是否能對應到明確 [runbook](/backend/knowledge-cards/runbook/)、[ownership](/backend/knowledge-cards/ownership/) 與停止條件
- Dashboard 是否有固定使用者與更新責任
- Threshold 是否對齊 SLO、容量邊界或使用者影響
- Noise rate 是否被追蹤並回寫治理流程
- Dashboard panel 是否讀 recording rule 而非每次重算 raw data

## 判讀訊號

- Alert 跟 [runbook](/backend/knowledge-cards/runbook/) 沒連、收到 page 不知道做什麼
- Dashboard 數量爆量、無 owner、半年無人訪問
- 同一訊號多個 alert 重複觸發、無 grouping 或 inhibition
- Alert noise rate > 30%、ack 後無實際動作，形成 [alert fatigue](/backend/knowledge-cards/alert-fatigue/)
- Alert threshold 用直覺數字、沒對齊 SLO / 商業承諾
- Dashboard panel 載入慢、因為直接查 raw series 而非 recording rule
- Maintenance window 過後 silence 沒移除、真實問題被掩蓋

## 反模式

| 反模式                  | 表面現象                                 | 修正方向                                     |
| ----------------------- | ---------------------------------------- | -------------------------------------------- |
| 指標堆疊 dashboard      | 50 個 panel、看不出服務是否健康          | SLI 導向重構：第一排回答健康、第二排回答原因 |
| 全部 cause-based alert  | CPU / disk / memory alert 頻繁但服務正常 | 區分 symptom（page）跟 cause（warning）      |
| 固定閾值 alert          | 低流量時 false alarm、高流量時漏報       | 改用 SLO burn rate alerting                  |
| Alert 無 runbook        | On-call 收到 page 後自行摸索、MTTR 高    | 每個 critical alert 必附 runbook link        |
| Alert 無 owner          | 沒人維護的 alert rule 累積成 noise 來源  | 每個 alert rule 帶 owner metadata、定期審視  |
| Dashboard 無過期機制    | 三年累積 200 個 dashboard、多數沒人看    | 訪問頻率追蹤 + 定期淘汰審視                  |
| 同一問題觸發 N 個 alert | On-call 同時收到 5 則通知、不知道看哪個  | Alertmanager grouping + inhibition           |

## 交接路由

- [4.3 tracing](/backend/04-observability/tracing-context/)：trace waterfall 作為 dashboard 的診斷入口
- [4.6 SLI/SLO 訊號設計](/backend/04-observability/sli-slo-signal/)：alert 的訊號源頭、burn rate alerting 的 SLI 依據
- [4.8 訊號治理閉環](/backend/04-observability/signal-governance-loop/)：alert / dashboard 的生命週期維運
- [4.10 client-side / RUM](/backend/04-observability/client-side-monitoring/)：補 server-side 看不到的 dashboard 維度
- [4.14 anomaly detection](/backend/04-observability/anomaly-detection/)：rule-based alert 之外的統計訊號
- [4.18 operating model](/backend/04-observability/observability-operating-model/)：dashboard / alert 的 ownership 矩陣與 metadata 欄位
- [4.23 觀測查詢設計](/backend/04-observability/observability-query-design/)：dashboard 查詢的效能與 recording rule
