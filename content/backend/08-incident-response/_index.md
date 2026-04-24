---
title: "模組八：事故處理與復盤"
date: 2026-04-23
description: "整理事故分級、指揮流程、通訊節奏、止血回復與復盤改進"
weight: 8
---

事故處理模組的核心目標是把「事故發生時的臨場反應」轉成可演練、可交接、可復用的團隊流程。觀測平台負責看見訊號，部署平台負責交付與切換，可靠性模組負責事故前驗證；本模組負責事故中的決策與協作節奏。

## 暫定分類

| 分類                                                            | 內容方向                                                           |
| --------------------------------------------------------------- | ------------------------------------------------------------------ |
| [Incident severity](../knowledge-cards/incident-severity)       | 事故分級、影響判斷、啟動條件                                       |
| Command model                                                   | incident commander、角色分工、決策邊界                             |
| Containment and recovery                                        | 止血、隔離、[降級](../knowledge-cards/degradation)、回復、rollback |
| Incident communication                                          | 內部通報、外部溝通、狀態更新節奏                                   |
| Incident [runbook](../knowledge-cards/runbook)                  | 場景化 [playbook](../knowledge-cards/playbook)、查詢入口、停止條件 |
| [Post-incident review](../knowledge-cards/post-incident-review) | [RCA](../knowledge-cards/rca)、行動項、驗證與關閉流程              |
| [Readiness](../knowledge-cards/readiness) and drills            | 值班訓練、演練設計、[game day](../knowledge-cards/game-day)        |

## 選型入口

事故處理設計的核心判斷是先界定產品影響，再安排處置節奏。分級回答影響多大，指揮模型回答誰決策，止血回復回答先保護什麼結果，通訊流程回答誰需要知道什麼資訊，復盤流程回答下一次如何更快更準。

接近真實網路服務的例子包括付款成功率下降、[broker](../knowledge-cards/broker) [consumer lag](../knowledge-cards/consumer-lag/) 持續擴大、憑證過期導致 HTTPS 失效、資料回填錯誤造成查詢結果偏差。這些場景的共同問題是跨角色協作與時間壓力，因此需要明確分工與標準化流程。

## 與既有模組關係

1. [可觀測性平台](../04-observability/) 提供事故訊號與判讀資料。
2. [部署平台與網路入口](../05-deployment-platform/) 提供切換、回滾與流量控制能力。
3. [可靠性驗證流程](../06-reliability/) 提供事故前演練與風險驗證。
4. [資安與資料保護](../07-security-data-protection/) 提供權限、稽核與高風險操作約束。
5. [紅隊案例庫（7.R7）](../07-security-data-protection/red-team/cases/) 提供可引用事故案例與 workflow 檢查點來源。

## 與資安概念層的交接

本模組承接 07 模組的概念判讀，並把問題地圖轉成可執行事故節奏。交接基線如下：

- 來自 [7.2 身分與授權邊界](../07-security-data-protection/identity-access-boundary/)：承接身分事件分級與收斂順序。
- 來自 [7.3 入口治理與伺服器防護](../07-security-data-protection/entrypoint-and-server-protection/)：承接入口事件止血、隔離與驗證節奏。
- 來自 [7.4 資料保護與遮罩治理](../07-security-data-protection/data-protection-and-masking-governance/)：承接外送事件通報與影響盤點節奏。
- 來自 [7.7 稽核追蹤與責任邊界](../07-security-data-protection/audit-trail-and-accountability-boundary/)：承接證據結構與復盤責任閉環。

這個交接讓事故模組聚焦角色協作與決策節奏，同時保持與資安章節同一套語意。

## 章節大綱

| 章節 | 主題                           | 目標                                                                      |
| ---- | ------------------------------ | ------------------------------------------------------------------------- |
| 8.1  | 事故分級與啟動條件             | 建立統一分級與啟動門檻                                                    |
| 8.2  | 事故指揮與角色分工             | 定義 commander、owner、scribe、[on-call](../knowledge-cards/on-call) 協作 |
| 8.3  | 止血、降級與回復策略           | 把短期止血與正式回復拆成可執行步驟                                        |
| 8.4  | 事故通訊與狀態更新             | 建立內外部通訊節奏與格式                                                  |
| 8.5  | 復盤與改進追蹤                 | 把 RCA 與 action items 變成可驗證閉環                                     |
| 8.6  | 演練與值班能力建設             | 用 game day 與值班訓練提升反應品質                                        |
| 8.7  | 攻擊者視角（紅隊）事故弱點判讀 | 用擴散路徑、回復瓶頸與交接斷點檢查事故設計                                |
| 8.8  | 事故報告轉 workflow            | 把事故故事轉成可執行、可驗證、可演練的流程                                |

## 章節列表

- [8.1 事故分級與啟動條件](incident-severity-trigger/)
- [8.2 事故指揮與角色分工](incident-command-roles/)
- [8.3 止血、降級與回復策略](containment-recovery-strategy/)
- [8.4 事故通訊與狀態更新](incident-communication/)
- [8.5 復盤與改進追蹤](post-incident-review/)
- [8.6 演練與值班能力建設](drills-and-oncall-readiness/)
- [8.7 攻擊者視角（紅隊）事故弱點判讀](attacker-view-incident-risks/)
- [8.8 事故報告轉 workflow：從案例到日常流程](incident-report-to-workflow/)

## 既有可引用卡片

- [runbook](../knowledge-cards/runbook/)
- [alert runbook](../knowledge-cards/alert-runbook/)
- [runbook link](../knowledge-cards/runbook-link/)
- [on-call](../knowledge-cards/on-call/)
- [playbook](../knowledge-cards/playbook/)
- [game day](../knowledge-cards/game-day/)
- [symptom-based alert](../knowledge-cards/symptom-based-alert/)
- [alert fatigue](../knowledge-cards/alert-fatigue/)
- [downtime](../knowledge-cards/downtime/)
- [degradation](../knowledge-cards/degradation/)
- [failover](../knowledge-cards/failover/)
- [fallback plan](../knowledge-cards/fallback-plan/)
- [replay runbook](../knowledge-cards/replay-runbook/)

## 首批事故處理卡片

事故處理章節可直接引用以下原子卡片，避免每章重複定義同一套術語：

1. [incident severity](../knowledge-cards/incident-severity/)
2. [incident command system](../knowledge-cards/incident-command-system/)
3. [escalation policy](../knowledge-cards/escalation-policy/)
4. [incident timeline](../knowledge-cards/incident-timeline/)
5. [blast radius](../knowledge-cards/blast-radius/)
6. [rollback strategy](../knowledge-cards/rollback-strategy/)
7. [post-incident review](../knowledge-cards/post-incident-review/)
8. [RCA](../knowledge-cards/rca/)
9. [RTO](../knowledge-cards/rto/)
10. [RPO](../knowledge-cards/rpo/)
11. [MTTR](../knowledge-cards/mttr/)

## 下一步

本模組先建立分類入口與首批卡片。下一批建議先完成 8.1 與 8.2，再把 8.3 到 8.6 依場景拆成可演練 playbook。
