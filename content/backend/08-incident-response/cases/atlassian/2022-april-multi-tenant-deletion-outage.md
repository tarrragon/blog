---
title: "Atlassian 2022 April Multi-tenant Deletion Outage"
date: 2026-05-07
description: "2022-04 Atlassian 因維運腳本誤刪多租戶站點造成長時間事故的解析：恢復分批、跨團隊指揮與對外通訊節奏。"
weight: 1
tags: ["backend", "incident-response", "case-study", "atlassian"]
---

Atlassian 2022 事故的核心教訓是：在多租戶 SaaS 中，誤刪不只是一個資料問題，而是恢復編排、客戶通訊與跨團隊協調同時失效的系統級事件。

## 事故摘要

Atlassian 官方 PIR 指出，2022-04-05 起有 775 客戶受影響，部分恢復歷時長達 14 天。事故起因是維運腳本使用了錯誤識別資訊，導致站點被刪除，後續需要多工作流並行恢復與驗證。

事件特徵是「影響客戶數有限，但每一個客戶的恢復成本高」，因此恢復策略必須分批與分層。

## 判讀訊號

| 訊號                         | 事故中代表什麼                 | 第一波決策價值                       |
| ---------------------------- | ------------------------------ | ------------------------------------ |
| 客戶站點直接不可用           | 已是 tenant 級資料生命週期事件 | 立即升級 major incident              |
| 恢復進度呈現長尾分布         | 不同租戶恢復難度差異大         | 改分批恢復與分層追蹤                 |
| 初期通訊管道壓力高           | 客戶影響與資訊需求同步上升     | 固定通訊節奏，區分已知事實與待確認項 |
| 後續發現部分資料恢復點不一致 | 恢復策略與資料一致性治理待補   | 增加恢復後審核與補救流程             |

## 事故路徑

1. 維運腳本操作錯誤導致多租戶站點被刪除。
2. 客戶無法存取產品並建立支援事件。
3. 事故升級後成立跨職能指揮團隊，24x7 推進恢復。
4. 恢復以分批方式進行，並持續更新 status 與客戶通訊。
5. 事後回寫到 soft delete、恢復自動化與通訊流程改善。

## 可回寫控制面

| 控制面                             | 這次事故暴露的缺口                   | 回寫方向                                   |
| ---------------------------------- | ------------------------------------ | ------------------------------------------ |
| Script safety guardrail            | 腳本輸入與刪除對象校驗不足           | 高風險刪除操作增加雙重驗證與範圍確認       |
| Multi-tenant restore orchestration | 大規模租戶恢復缺少標準化分批流程     | 建立恢復編排工具與租戶優先序模型           |
| Data restoration consistency       | 恢復點一致性在早期流程中不穩         | 增加恢復後一致性審核與回補流程             |
| Incident communication resilience  | 長事故中的客戶通訊節奏與聯絡資料治理 | 固定 cadence、改善受影響客戶聯絡資訊可得性 |

## 下一步路由

- 事故通訊： [8.4 Incident Communication](/backend/08-incident-response/incident-communication/)
- 客戶影響評估： [8.20 Customer Impact Assessment](/backend/08-incident-response/customer-impact-assessment/)
- 事中決策紀錄： [8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)
- 證據回寫流程： [8.22 Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/)
- 穩態與恢復完成： [6.22 Steady State Definition](/backend/06-reliability/steady-state-definition/)

## 引用源

- [Post-Incident Review on the Atlassian April 2022 outage](https://www.atlassian.com/blog/atlassian-engineering/post-incident-review-april-2022-outage)
- [Update on the Atlassian outage affecting some customers](https://www.atlassian.com/blog/atlassian-engineering/april-2022-outage-update)
