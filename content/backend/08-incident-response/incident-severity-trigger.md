---
title: "8.1 事故分級與啟動條件"
date: 2026-04-23
description: "建立統一分級標準與事故啟動門檻"
weight: 1
---

## 概念定位

[incident severity](/backend/knowledge-cards/incident-severity/) 與 trigger 是把事故從「有問題」變成「需要開始協作」的門檻。incident severity 定義的是這次事故應該用多大規模的協作來處理，trigger 定義的是什麼訊號足以啟動這個協作。當兩者被分開寫清楚，團隊就不會把所有異常都當成同一種事件，也不會在影響面已經擴大後才開始反應。

這個節點先處理啟動，再處理升級。先定義什麼情況要 page、要不要拉 [incident command system](/backend/knowledge-cards/incident-command-system/)、要不要進 status update，然後才處理 severity 分級的細節。這樣讀，會比先背 severity level 再找案例更接近真實事故運作。

## 大綱

- [incident severity](/backend/knowledge-cards/incident-severity/) criteria
- user impact signals
- trigger thresholds
- [escalation policy](/backend/knowledge-cards/escalation-policy/) handoff

## 判讀訊號

- 事故啟動延遲於擴散、影響面已擴大才升級
- severity 分級靠 [incident command system](/backend/knowledge-cards/incident-command-system/) 直覺、無 user impact 量化
- 升級條件不清、跨團隊重複 page 同事故
- 同類事件不同 [incident command system](/backend/knowledge-cards/incident-command-system/) 給不同 severity
- 啟動門檻過高（漏判）或過低（噪音）、無校準流程

## 核心判讀

[incident severity](/backend/knowledge-cards/incident-severity/) 的責任是把影響面說清楚。當服務開始退化時，先看使用者是否真的受影響，再看影響是否跨產品、跨 region、跨 tenant，最後才決定 severity。這個順序很重要，因為它決定了團隊是先止血還是先爭論標籤。

啟動條件的責任是把協作拉起來。當 trigger 被觸發時，團隊應該立刻知道誰要接手、誰要記錄、誰要對外通訊，以及下一次檢視的時間點。這種節奏不需要等事故結束才討論，因為事故本身就是路由。

## 案例對照

AWS S3 適合用來看控制面事故如何把區域級影響迅速擴大，因為這類事件最容易讓 severity 上升到需要更大範圍協作。GitHub 適合用來看 replication 與 split-brain 的分級，因為資料一致性問題會直接拉長復原時間。Slack 與 Discord 則提供通訊平台事故的視角，讓我們看到「通訊工具本身失效」時 trigger 與 communication 是怎麼一起被啟動的。

Atlassian 的長尾復原、GCP 的全球控制面失效、Azure AD 的 identity cascading 也都能回扣到同一件事：severity 不是根據直覺標註，而是根據 [impact scope](/backend/knowledge-cards/impact-scope/)、擴散速率與協作成本來路由。這樣的分級，才會讓後續的止血、通訊與復盤有一致的起點。

## 交接路由

- 04.6 SLI/SLO：burn rate 對應 severity 門檻
- 08.14 multi-incident：跨事故優先序判準
- 08.17 security vs operational：分流影響 severity 計算
