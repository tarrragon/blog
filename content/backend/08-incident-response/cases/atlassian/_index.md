---
title: "Atlassian"
date: 2026-05-01
description: "Atlassian 多租戶事故時間線與架構脈絡"
weight: 5
---

Atlassian 2022 的 14 天事故是多租戶誤刪 + 跨團隊協作的教學標竿。事故 post-mortem 公開度極高、揭露 IR 內部運作細節（incident commander 輪值、跨團隊溝通、客戶補償政策），是少數能完整看到大型事故 IR 流程的公開素材。

## 規劃重點

- 多租戶資料模型：跨產品 tenant ID 的 cascading delete 風險
- Recovery 順序：885 個 tenants 為何不能平行恢復、需要排序
- 跨團隊協作：incident commander 輪值、24x7 支援、客戶溝通分軌
- Stakeholder 通訊：customer impact 量化、補償政策、合約衝擊
- Postmortem 文化：Atlassian Incident Management Handbook 公開內容

## 預計收錄事故

| 年份 | 事故            | 教學重點                                |
| ---- | --------------- | --------------------------------------- |
| 2022 | 14 天多租戶誤刪 | 大規模 IR 協作、長尾 recovery、客戶溝通 |
| 2023 | 較小規模事故    | 對比 14 天事故的 IR 流程演化            |

## 案例定位

Atlassian 這個案例在講的是多租戶 SaaS 在發生誤刪後，復原與對外通訊如何一起構成事故本體。讀者先看懂 PIR、status update 與 restore path 的責任，再把 2022 事件當成跨團隊協作與復原節奏的範例。

## 判讀重點

當事故牽涉到客戶資料或多個內部系統時，復原速度取決於能否把依賴關係一層一層還原。當事故持續時間拉長時，對外更新的節奏也要固定，讓客戶能知道哪些功能先恢復、哪些風險仍在。

## 可操作判準

- 能否把誤刪後的復原步驟寫成明確順序
- 能否把 status update 與內部復原節奏對齊
- 能否說明哪些服務先恢復、哪些依賴後恢復
- 能否在 PIR 中把流程缺口轉成可追蹤的改善項

## 與其他案例的關係

Atlassian 和 Microsoft 365 都在講企業 SaaS 的客戶通訊問題，但 Atlassian 更像是把復原流程完整攤在桌上。它也適合和 GitHub 一起看，因為兩者都能說明長時間事故裡，時間線、責任與客戶影響如何一起被管理。

## 代表樣本

- 2022 年 14 天 outage 代表多租戶誤刪後的長尾復原。
- PIR 與對外 update 的節奏，讓客戶能知道哪些服務先回來。
- incident commander 輪值與跨團隊協作是這類事故的核心樣本。
- 補償政策與客戶溝通會直接影響事故收斂速度。
- 885 個 tenants 的排序恢復讓復原順序本身成為事故管理的一部分。
- customer impact quantification 讓補償與優先恢復有可執行依據。
- multi-tenant data model 讓單一誤刪能直接跨產品擴散。
- stakeholder communication 會和技術復原一起構成事故處理流程。

## 引用源

- [Post-Incident Review on the Atlassian April 2022 outage](https://www.atlassian.com/blog/atlassian-engineering/post-incident-review-april-2022-outage)：Atlassian 2022 年大規模誤刪事件的完整 PIR。
- [Update on the Atlassian outage affecting some customers](https://www.atlassian.com/blog/atlassian-engineering/april-2022-outage-update)：對外更新版本，適合對照復原節奏。
