---
title: "Deployment Contract"
date: 2026-04-23
description: "說明服務與部署平台之間的生命週期約定"
weight: 1
---

Deployment Contract 的核心概念是「application 與平台對啟動、存活、接流量與停止方式達成一致」。它把服務生命週期變成可預期的協作規則。 可先對照 [Draining](/backend/knowledge-cards/draining/)。

## 跟其他概念的關係

Deployment Contract 位在 application、container、Kubernetes、systemd 與 rollout control 之間。 可先對照 [Draining](/backend/knowledge-cards/draining/)。

## 可觀察訊號

系統需要 deployment contract 的訊號是發版、擴容、回滾或停止流程會影響流量與狀態保存。

## 接近真實網路服務的例子

readiness、shutdown、[draining](/backend/knowledge-cards/draining/) 與 [resource limit](/backend/knowledge-cards/resource-limit/) 都屬於 deployment contract。實際發版節奏與批次切換則交給 [rolling update](/backend/knowledge-cards/rolling-update/) 或 cutover 類卡片處理。

## 判斷條件與後果

Deployment Contract 少了哪一項約定，平台與 application 在那一段生命週期就各自照自己的假設行動。沒有約定何時可以接流量，平台會在 application 載入完成之前導入 request，第一批請求失敗；沒有約定何時停止接流量，instance 關閉時仍有新請求進來而被中斷；沒有約定資源不足時怎麼回應，呼叫端收到的可能是連線中斷，分不出這次失敗是否可以重試；沒有約定變更失敗時怎麼回復，失敗的發版停在新舊版本混雜的狀態，回復要靠人工判斷。原因是平台只照約定的訊號行動，約定沒寫到的那一段沒有任何一方負責。
