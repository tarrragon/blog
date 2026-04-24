---
title: "7.R7 事故案例庫（可引用）"
date: 2026-04-24
description: "把公開事故拆成可引用案例：事件摘要、失效控制面、可落地 workflow 檢查點"
weight: 717
---

這個分類把紅隊案例整理成可重用素材。每個案例都回答同一組問題：發生了什麼、哪個控制面失效、如果工作流程少做哪一步會重演、後續章節應該引用哪裡。

## 分類入口

| 分類 | 內容 |
| --- | --- |
| [Identity & Access](identity-access/) | 身分、認證流程、支援流程、社交工程 |
| [Supply Chain](supply-chain/) | 第三方整合、CI/CD、軟體供應鏈 |
| [Edge Exposure](edge-exposure/) | 邊界設備、外網入口、零時差攻擊 |
| [Data Exfiltration](data-exfiltration/) | 資料外送、備份風險、營運衝擊 |
| [案例引用地圖](case-reference-map/) | 服務主題對應事故案例與 workflow 檢查點 |

## 使用方式

1. 在服務章節先描述需求與風險。
2. 連到對應案例，指出「若缺少哪個流程步驟會重演」。
3. 連到 [事故處理 workflow 參考](../../../../08-incident-response/incident-report-to-workflow/) 落地成 runbook 或演練項目。
