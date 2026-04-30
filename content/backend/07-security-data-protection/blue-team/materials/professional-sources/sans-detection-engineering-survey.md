---
title: "SANS Detection Engineering Survey：偵測工程職能素材"
tags: ["SANS", "Detection Engineering", "Security Operations"]
date: 2026-04-30
description: "把 SANS detection engineering survey 轉成藍隊偵測工程與協作流程素材"
weight: 72517
---

SANS Detection Engineering Survey 的素材責任是提供偵測工程職能與流程成熟度觀察。它適合支撐「藍隊需要把偵測規則當成可維護工程資產」的論點。

## 來源定位

[2025 SANS Detection Engineering Survey](https://www.sans.org/white-papers/2025-sans-detection-engineering-survey-evolving-practices-modern-security-operations) 適合支撐 detection engineering 在現代 security operations 中持續演進的論點。[2026 SANS detection engineering webcast](https://www.sans.org/webcasts/state-detection-engineering-2026-what-data-reveals-accuracy-automation-ai-adoption) 則顯示 accuracy、automation 與 AI adoption 已經成為偵測工程討論重點。

## 可引用論點

| 可引用論點                       | 藍隊轉譯                                           |
| -------------------------------- | -------------------------------------------------- |
| Detection engineering 是持續職能 | 7.B2 規則維護需要 owner、review cadence 與測試     |
| Accuracy 與 automation 是重點    | 7.B3 驗證要包含誤報、漏報與自動化邊界              |
| 協作流程影響偵測品質             | 7.B4 演練要納入 analyst、engineer 與 service owner |

## 後端服務轉譯

後端服務引用這張卡時，重點是把偵測工程放進服務交付流程。每個高風險服務變更都可以同步檢查 log schema、rule coverage、alert routing、owner 與回寫節奏。

## 引用限制

SANS 適合支撐職能趨勢與流程討論，具體偵測策略仍要回到服務事件資料、攻擊面與既有工具能力。
