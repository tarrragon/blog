---
title: "Load Test"
date: 2026-04-23
description: "說明在預期流量下驗證容量、延遲與降級策略的測試"
weight: 159
---

Load test 的核心概念是「以接近真實流量模型驗證系統容量」。它用來發現瓶頸與評估擴容/降級策略。 可先對照 [Local Worker](/backend/knowledge-cards/local-worker/)。

## 跟其他概念的關係

常在活動前、重大發版前或架構調整後執行，並觀察延遲、錯誤率與資源使用。 可先對照 [Local Worker](/backend/knowledge-cards/local-worker/)。

## 判斷條件與後果

壓測沒有定義流量模型時，送出的請求組合與到達方式跟真實流量不同，找到的瓶頸可能不是正式環境先碰到的那一個。沒有成功標準（延遲與錯誤率的門檻）時，跑完只得到一組數字，判斷不了系統在活動的預期流量下延遲與錯誤率是否在可接受的範圍。沒有事先寫下各種結果對應的行動（擴容、降級、延後發版）時，結果出來之後才開始討論怎麼做，壓測沒有產出決策結論。壓測跑在共用主機或筆電上的 Docker 虛擬機裡時，量到的上限含有主機當下的負載，紀錄方式見 [共用主機的資源競爭](/devops/operations/05-capacity-planning/shared-host-contention/)〈容量估算〉。
