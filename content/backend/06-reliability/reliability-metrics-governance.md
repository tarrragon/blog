---
title: "6.18 Reliability Metrics Governance"
date: 2026-05-01
description: "DORA / SPACE 指標的選用、量測陷阱、anti-gaming 與團隊階段適配"
weight: 18
tags: ["backend", "reliability"]
---

## 概念定位

Reliability metrics governance 確保團隊量測到的指標能反映真實的可靠性狀態。指標的價值在於引導討論與暴露趨勢，一旦指標被直接當成目標，治理就開始退化。

## 核心判讀

指標是否對準使用者感受、是否能驅動工程決策 — 這兩個問題決定 metrics governance 的有效性。

判讀的核心問題：

- SLI 是否有明確觀測窗口與採樣邊界
- SLO 是否能轉成 release / alert / incident 決策
- DORA / SPACE / CFR 是否被混用成單一成績單
- metric drift 是否被記錄與校正

## DORA 四指標

DORA 量測的是交付與可靠性流程的效率，四個指標各自回答不同問題。

**Deploy frequency** 量測交付節奏 — 團隊多頻繁把變更送到 production。高頻 deploy 通常代表小批次、低風險；但判讀陷阱是拆碎 deploy 只為衝頻率。辨別方式是同時看 deploy size distribution — 若平均 deploy 的變更量持續縮小但 frequency 持續上升，gaming 的可能性高。deploy frequency 要搭配 change failure rate 一起看，頻率高但 CFR 也高代表品質沒跟上。

**Lead time for changes** 量測從 commit 到 production 的時間。長 lead time 通常指向 [CI pipeline](/backend/06-reliability/ci-pipeline/) bottleneck、approval queue 或 staging 排隊。判讀陷阱是把 lead time 壓短但跳過驗證步驟 — 縮短的時間可能來自移除 slow path 測試，表面效率提升但風險轉移到 production。改善 lead time 的投資方向先看 CI 分層（6.1）是否合理，再看 review queue 是否成為瓶頸。

**Change failure rate (CFR)** 量測 deploy 後需要 rollback 或 hotfix 的比率。CFR 是 [release gate](/backend/06-reliability/release-gate/) 健康度的直接指標 — gate 有效時 CFR 應該維持穩定或下降。判讀陷阱是團隊避免標記 rollback 來壓低 CFR，或把 hotfix 歸類為「正常 deploy」。偵測方式是把 CFR 跟 customer complaint rate 做相關性分析 — 若 CFR 持續下降但客訴未減，代表量測漏洞存在。

**[MTTR](/backend/knowledge-cards/mttr/)** 量測從故障到恢復的時間。MTTR 的量測邊界需要明確定義：從 alert 觸發開始算、從 customer impact 開始算、到 recovery complete 還是到 root cause 修復。不同定義會產出完全不同的數字。判讀陷阱是延遲標記 incident 起始時間來壓低 MTTR。連到 [08 incident response](/backend/08-incident-response/) 的事故分級與復盤流程。

## SPACE 補充維度

DORA 偏重 delivery 效率，SPACE 補人因與協作維度。五個面向各捕捉 DORA 看不到的訊號。

| 維度          | 量測重點                                                                    | 判讀價值                                         |
| ------------- | --------------------------------------------------------------------------- | ------------------------------------------------ |
| Satisfaction  | 團隊對工具、流程、[on-call](/backend/knowledge-cards/on-call/) 負擔的滿意度 | 滿意度下降常先於效能指標退化                     |
| Performance   | code review 品質、bug escape rate                                           | 補 DORA 缺的品質維度                             |
| Activity      | commit / PR / deploy 頻率                                                   | activity 是描述性指標，不等於 productivity       |
| Communication | 跨團隊協作效率、incident communication 品質                                 | 協作瓶頸在 DORA 中完全看不到                     |
| Efficiency    | flow state time、context switch frequency                                   | 高 context switch 會拖慢 lead time 但原因不在 CI |

SPACE 同樣需要 governance。Satisfaction 被 KPI 化後團隊會避免誠實回饋；Activity 被當成 productivity 量測後會鼓勵 commit 拆碎。治理原則跟 DORA 相同：指標是討論的起點，不是績效的終點。

## 指標選用與團隊階段

指標投資的 ROI 跟團隊規模正相關。團隊小時指標治理成本高，應集中在最少的關鍵指標。

| 階段               | 建議指標               | 理由                                                    |
| ------------------ | ---------------------- | ------------------------------------------------------- |
| Startup（< 10 人） | deploy frequency + CFR | 兩個指標足以判讀交付節奏與品質平衡，其他指標 noise 太大 |
| Scale（10-100 人） | 完整 DORA              | 加入 lead time + MTTR，開始治理跨團隊 baseline          |
| Mature（100+ 人）  | DORA + SPACE + trend   | 完整框架加趨勢分析，composite metrics 需要專人維護      |

baseline 對齊的判準是跟自己的歷史趨勢比，而非抄業界數字。DORA 報告的 elite / high / medium / low 分類提供方向參考，但直接套用會忽略產業、架構與團隊結構的差異。

## Anti-gaming 與 Goodhart's law

當指標直接變成目標，量測的行為會改變被量測的對象。這就是 Goodhart's law 在工程指標上的實現。

常見 gaming 模式與偵測方式：

| Gaming 模式                       | 偵測方式                                                                                                      |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| 拆碎 deploy 衝 frequency          | deploy size distribution 出現異常小的 cluster                                                                 |
| 延遲標記 incident 降 MTTR         | incident 起始時間 vs alert 觸發時間的 gap 分析                                                                |
| 避免 rollback 降 CFR              | CFR vs customer complaint rate 的相關性斷裂                                                                   |
| 跳過 slow path 測試縮短 lead time | lead time 下降同時 CFR 上升                                                                                   |
| 壓下同類 incident 不報            | incident recurrence rate 與 [post-incident review](/backend/knowledge-cards/post-incident-review/) 數量不匹配 |

治理原則：指標是診斷工具，用來發現問題方向與引導團隊討論。指標跨團隊強制排名會讓 gaming 成為理性選擇 — 團隊會優化數字而非優化系統。有效做法是把指標用在團隊自身的趨勢追蹤，跨團隊只分享經驗與改善策略。

## 跟 SLO 的差異

SLO 是面向使用者的服務承諾 — 量測的是「我的服務給使用者什麼品質」。6.18 metrics 是面向團隊的工程能力量測 — 量測的是「我的交付與可靠性流程效率如何」。

兩者的消費者不同：SLO 的消費者是 product / business stakeholder 與 on-call 團隊；DORA / SPACE 的消費者是工程管理與團隊自身。治理節奏也不同：SLO 跟 [error budget](/backend/knowledge-cards/error-budget/) 政策綁定，burn rate 驅動即時決策；DORA 趨勢按月或按季 review。

混用的風險是 SLO 失去商業對齊的價值。當 SLO 被當成工程 KPI 而非使用者承諾，團隊會開始縮小 SLI 範圍或放寬目標來讓數字好看，SLO 政策的放行判讀也跟著失真。

## 案例對照

- [Google：Error Budget 與 Release Gating](/backend/06-reliability/cases/google/error-budget-policy-and-release-gating/)：SLO 與 DORA 的邊界在這個案例中最清楚 — error budget 是服務承諾的消耗量測，DORA 是交付流程的效率量測，兩者在 release gate 交會但責任不同。
- [Honeycomb：Burn Rate 驅動可靠性](/backend/06-reliability/cases/honeycomb/burn-rate-driven-reliability-operations/)：用觀測資料驅動判讀，而非先設定指標再找資料。這個案例說明指標治理的起點是觀測能力，指標是觀測的摘要，觀測是指標的來源。
- [Datadog](/backend/08-incident-response/cases/datadog/_index.md)：指標平台的可靠性直接影響事故判讀品質。當指標平台本身不穩定，所有基於它的 DORA / SLO 量測都會失真。

## 判讀訊號

| 訊號                               | 判讀條件                                                                                   | 行動建議                                    |
| ---------------------------------- | ------------------------------------------------------------------------------------------ | ------------------------------------------- |
| 指標數字持續改善、客戶投訴未減     | 量測覆蓋不足或 gaming — 先檢查 CFR vs complaint 相關性                                     | 把 complaint 率加入 dashboard 交叉比對      |
| 跨團隊強制排名                     | gaming 風險高 — 改為團隊自身趨勢追蹤                                                       | 取消排名、改為各團隊獨立看自身 trend        |
| DORA 採集靠人工、滯後超過一個月    | 指標失去即時性 — 自動化採集連到 CI / deploy pipeline                                       | 串接 CI/CD pipeline 自動產出 DORA 資料      |
| 指標無 owner、半年無人 review      | 治理已停擺 — 指定 owner 與季度 review 節奏                                                 | 指定 metrics owner + 排入季度 review 議程   |
| deploy frequency 上升同時 CFR 上升 | 速度與品質失衡 — 先補 [release gate](/backend/06-reliability/release-gate/) 再追 frequency | 暫停追 frequency、先讓 CFR 回到 baseline    |
| MTTR 定義跨團隊不一致              | 量測不可比 — 先統一量測邊界（alert → recovery complete）                                   | 發布 MTTR 量測定義文件、統一 start/end 判準 |

## 交接路由

- [6.1 CI pipeline](/backend/06-reliability/ci-pipeline/)：lead time 的主要改善入口
- [6.6 SLO / error budget](/backend/06-reliability/slo-error-budget/)：商業承諾層的指標，跟 DORA 互補但責任不同
- [6.8 release gate](/backend/06-reliability/release-gate/)：CFR 是 gate 健康度訊號
- [6.21 reliability debt backlog](/backend/06-reliability/reliability-debt-backlog/)：指標趨勢揭露的可靠性債
- [04.6 SLI/SLO 訊號層](/backend/04-observability/sli-slo-signal/)：指標的觀測來源
- [08.5 post-incident review](/backend/08-incident-response/post-incident-review/)：MTTR 計算的事件來源、指標漂移通常先在復盤裡被看見
- [08.11 觀測 / 可靠性 / 事故閉環](/backend/08-incident-response/observability-reliability-incident-loop/)：指標治理回寫到三模組閉環
