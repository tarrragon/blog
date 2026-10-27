---
title: "突發流量的分類"
date: 2026-06-20
description: "突發流量依能不能事前知道分成兩類：各自的來源、倍率與持續時間，可預期突發的準備要提前多久由什麼決定、collector 在活動前要準備的項目，以及 collector 遇到 error storm 時的資料保留"
weight: 1
tags: ["devops", "burst-traffic", "classification", "marketing", "error-storm"]
---

這篇把突發流量依能不能事前知道分成兩類，各列來源、流量倍率、持續時間與特徵。可預期的一類（行銷活動、新聞曝光）可以事前準備容量，這篇寫準備要從活動前多久開始由什麼決定，以及 collector 在活動前要準備的接收端台數與配額、寫入儲存層的壓測與 SDK 端的取樣設定；各項目排在活動前幾天的完整時程在 [9.11 高峰事件準備](/backend/09-performance-capacity/peak-event-readiness/)。不可預期的一類（病毒傳播、error storm）靠架構設計吸收衝擊，這篇寫 collector 遇到 error storm 時保留哪些資料。

## 可預期突發

事前知道流量會增加，有時間準備。

| 來源                           | 流量倍率 | 持續時間         | 特徵                                    |
| ------------------------------ | -------- | ---------------- | --------------------------------------- |
| 行銷活動（促銷、限時折扣）     | 5-50x    | 數小時～數天     | 流量集中在活動開始的前幾分鐘            |
| 新聞曝光（媒體報導、社群爆紅） | 10-100x  | 數小時           | 不可控的流量曲線、峰值在發佈後 1-2 小時 |
| 定時推播（每日報表、週報）     | 2-10x    | 分鐘級           | 短暫但可精確預測時間                    |
| 新版本推送（app store 更新）   | 3-10x    | 數天（逐漸擴散） | 流量緩慢上升、峰值在推送後 24-48 小時   |

可預期突發的應對核心是**容量預備** — 活動前擴容、活動後縮回。

### 容量預備的前置時間與 collector 在活動前要準備的項目

可預期突發能事前準備，而準備要從活動前多久開始，由各準備項目的產出交給誰、它發現的狀況要多久修好決定。容量估算、配額申請、壓力測試（[Load Test](/backend/knowledge-cards/load-test/)）、故障演練（[Game Day](/backend/knowledge-cards/game-day/)）與預先擴容各排在活動前幾天、為什麼排在那裡，以及準備時間不夠時被壓縮掉的是什麼，在 [9.11 高峰事件準備](/backend/09-performance-capacity/peak-event-readiness/)〈T-90 → T-0 準備時程〉與〈Event tier 分級〉。容量估算有兩種算法：平常的流量乘上歷史倍率、再加安全係數，在 [峰值估算](/operations/05-capacity-planning/peak-estimation/)〈用歷史倍率階梯推可預期峰值〉與〈安全係數的數學根據在飽和曲線〉；從業務預估經換算鏈與三點估計算出各層台數，連同活動的預算，在 [預知的大流量要加多大、編多少預算：從業務預估到擴容規格與費用區間的換算鏈、給決策者與會計的數字，以及每次活動之後的校準](/operations/05-capacity-planning/planned-peak-sizing-and-budget/)〈從業務預估到台數：換算鏈、換算係數的來源與三點估計〉。

套到 collector 上，活動前要準備的是三件事。接收端的台數與配額，從活動期間 SDK 送出的事件量估，事件量跟著使用者數與每人觸發的事件數變。壓力測試除了量接收端，也要量寫入儲存層的處理量：直接寫 PostgreSQL 的架構，背壓（[Backpressure](/monitoring/knowledge-cards/backpressure/)）常常先從寫入那一段出現（[規模分級應對表](/operations/07-burst-traffic/scale-tier-response/)〈Tier 3：大型（10000-100000 events/sec）〉）。SDK 端的動態取樣與事件優先級，在活動前設好觸發條件並演練一次；SDK 從 collector 回傳的 429 判斷要不要降低取樣率（[降級策略](/operations/07-burst-traffic/degradation-strategy/)〈觸發條件〉）。這一項的前置時間取決於設定怎麼送到客戶端：取樣設定由遠端設定下發時，活動前幾天改得到；編在 app 裡時，改設定要發新版，設定要比活動提早至少「發版審查加上使用者更新」所需的時間改好（新版本的流量峰值在推送後 24-48 小時，見上面〈可預期突發〉的來源表）。

配額申請被拒、或壓測測出的寫入瓶頸在活動前修不完時，collector 有兩種處置。一是超出容量的事件量由 queue 先接住、事後追趕（[Queue 緩衝](/operations/07-burst-traffic/queue-buffering/)），代價是排在 queue 裡的事件在活動期間看不到；錯誤與延遲這類要即時看的事件，依事件優先級走不排隊的路徑。二是由 SDK 降低取樣率，減少送進來的事件。

## 不可預期突發

事前不知道流量會增加，只能靠架構設計吸收。

| 來源                                  | 流量倍率        | 持續時間    | 特徵                                |
| ------------------------------------- | --------------- | ----------- | ----------------------------------- |
| 病毒傳播（社群分享爆量）              | 10-1000x        | 數小時      | 完全無法預測、可能超過任何預備容量  |
| DDoS 攻擊                             | 100-10000x      | 不定        | 惡意流量、需要 WAF / CDN 擋在前面   |
| Error storm（app bug 觸發大量 error） | 依 bug 影響範圍 | 直到 hotfix | 每個受影響的使用者都在送 error 事件 |
| 外部依賴復原（積壓請求一次湧入）      | 2-5x            | 分鐘級      | 依賴恢復後積壓的 retry 一起到達     |

依賴恢復時積壓請求一起到達的第二波湧入，以及它轉成停在失效的條件，見 [9.16 負載超過容量時服務的表現](/backend/09-performance-capacity/overload-outcomes/)。

不可預期突發的應對核心是**降級** — 系統在超載時自動犧牲非核心功能，保住核心功能。

### 監控系統的 error storm

Error storm 是監控系統特有的突發場景：被監控的 app 出了 bug，每個受影響的使用者都在送 error 事件。如果有 10 萬使用者同時遇到同一個 bug，collector 瞬間收到 10 萬筆 error 事件。

Error storm 的矛盾：error 事件是 debug 最需要的資料，但 storm 時的大量 error 可能塞滿 collector 的接收佇列，collector 開始回 429 或丟掉資料。處理策略是**保留前 N 筆完整 error（含 stack trace）、後續的 error 只計數不存原始資料**。第一筆 error 的 stack trace 足夠 debug，後續的 10 萬筆只是確認影響範圍。

## 下一步路由

- 突發時的降級策略 → [降級策略](/operations/07-burst-traffic/degradation-strategy/)
- 不可預期突發依來源（真人需求、應用層濫用流量、體積型攻擊）分流的處置，以及負載卸除、等候室與流量清洗 → [9.15 無預警瞬時大流量：流量來源辨識、擴展緩衝、請求優先等級、准入控制、體積型攻擊與退路](/backend/09-performance-capacity/unplanned-traffic-surge/)
- Queue 做 burst 緩衝 → [Queue 緩衝](/operations/07-burst-traffic/queue-buffering/)
- 可預期突發的擴容規格與預算怎麼從業務預估算出來、做成給決策者與會計的數字 → [預知的大流量要加多大、編多少預算：從業務預估到擴容規格與費用區間的換算鏈、給決策者與會計的數字，以及每次活動之後的校準](/operations/05-capacity-planning/planned-peak-sizing-and-budget/)
- 不同規模的應對方案 → [規模分級應對表](/operations/07-burst-traffic/scale-tier-response/)
