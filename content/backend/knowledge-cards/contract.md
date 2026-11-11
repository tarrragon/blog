---
title: "Boundary Contract"
date: 2026-04-23
description: "說明跨邊界約定如何維持相容與可驗證"
weight: 1
---

Boundary Contract 的核心概念是「邊界兩端共同承認的約定」。它描述不同系統、元件或流程在互相協作時，需要遵守的共同規則。 可先對照 [Draining](/backend/knowledge-cards/draining/)。

## 跟其他概念的關係

Boundary Contract 位在 client 與 service、service 與 service、程式與平台之間。當兩端都需要依同一份規則運作時，就需要 contract 來避免含糊地帶。 可先對照 [Draining](/backend/knowledge-cards/draining/)。

## 可觀察訊號

系統需要 boundary contract 的訊號包括：不同團隊共同整合、版本需要相容、欄位變更可能影響下游、健康檢查與接流量條件要明確。

## 接近真實網路服務的例子

API contract 會定義欄位名稱、必要欄位、錯誤格式與相容版本；deployment contract 會定義 readiness、shutdown、[draining](/backend/knowledge-cards/draining/) 與 [resource limit](/backend/knowledge-cards/resource-limit/)；queue contract 會定義 ack、重試與重複投遞行為；load balancer contract 會定義流量切換、[health check](/backend/knowledge-cards/health-check/) 與排空行為。

## 判斷條件與後果

Boundary contract 沒有寫清楚的部分，由邊界兩端各自解讀。版本沒有定義時，client 說不出自己依賴的是哪一版行為；相容性與破壞性變更沒有界定時，一端改了欄位，另一端到上線後才發現整合失敗；沒有驗證方式時，實作偏離 contract 也沒有任何檢查會失敗；沒有回復流程時，破壞性變更上線之後只能往前修。contract 經常變動、兩端常對不上時，contract test 與 [Release Gate](/backend/knowledge-cards/release-gate/) 讓偏離在合併或發佈之前就被擋下，文件化的變更規則讓兩端對「什麼算破壞性變更」用同一個標準。
