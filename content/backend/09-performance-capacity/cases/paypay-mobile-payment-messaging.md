---
title: "9.C26 PayPay：行動支付每日 3 億訊息的 DynamoDB 後端"
date: 2026-05-12
description: "日本最大行動支付 PayPay 每日 3 億訊息、用 DynamoDB 處理通知與訊息功能、支撐次秒級反應"
weight: 26
tags: ["backend", "performance", "capacity", "case-study", "db-kv", "aws", "sustained-growth"]
---

這個案例的核心責任是說明「行動支付類 SaaS」的訊息工作負載特性。PayPay 是日本最大行動支付（pre-IPO 估值 70 億美金級）、訊息功能需要在每筆交易後即時通知（付款成功、收款、優惠券）、單一用戶每天可能收到數十條訊息、加總到平台級別就是每日上億訊息。

## 觀察

PayPay 在 DynamoDB 的關鍵敘述（引自 [DynamoDB Customers](https://aws.amazon.com/dynamodb/customers/)）：

| 指標         | 數字                                          |
| ------------ | --------------------------------------------- |
| 每日訊息量   | 3 億訊息                                      |
| 主要工作負載 | 行動支付通知 + 訊息功能                       |
| 可靠性敘述   | 「Super reliable and performed consistently」 |
| 服務組合     | Amazon DynamoDB                               |
| 服務地理     | 日本                                          |

## 判讀

PayPay 案例揭露三個行動支付訊息系統的工程重點。

1. **支付通知是「不可丟失 + 不可延遲」雙重需求**：用戶付完款 30 秒沒收到通知會懷疑系統壞了、會打客服 / 重複扣款。這層需求比 OTA 推播嚴格、必須有 durable queue + retry + 重複偵測。對應 [03 訊息佇列模組](/backend/03-message-queue/) 的 idempotency 設計。
2. **DynamoDB 在「訊息事件」這類負載特別適合**：每則訊息有獨立 message_id（partition key 天然均勻）、TTL 機制可以自動清理過期訊息（避免 storage 爆炸）。對應 [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/) 的 partition 均勻優勢、跟 [02.4 cache copy freshness boundary](/backend/02-cache-redis/cache-copy-freshness-boundary/) 的 TTL 議題。
3. **3 億 / 天 ≈ 3,500 訊息 / 秒平均**：聽起來不大、但這是 *平均*。月底、雙 11 類大促、新年紅包等場景、單秒峰值可能達 10x-50x。對應 [9.2 Workload Modeling](/backend/09-performance-capacity/) 的峰均比評估。

需要警惕：「super reliable」是行銷語言、不是工程承諾。讀此類短篇案例要把行銷敘述折扣、重點看 *服務組合* 與 *規模量級*。

## 策略

可重用的工程做法：

1. **訊息系統設計區分「通知」跟「訊息」**：通知（payment received）是 transactional、不可丟失；訊息（marketing）可以丟失部分、重點是 throughput。兩者用不同 SLO、不同 storage。對應 [03 訊息佇列模組](/backend/03-message-queue/) 的訊息分類。
2. **TTL 自動清理避免 storage 成本爆炸**：3 億 / 天 × 30 天 = 90 億筆記錄、不清理會撐死 storage 預算。對應 [02 快取模組](/backend/02-cache-redis/) 的 TTL 設計。
3. **訊息推送的下游（APNs、FCM、SMS gateway）是隱性瓶頸**：DynamoDB 寫入可以撐 3K msg/sec、但 APNs 一天的 quota 是有限的。對應 [9.5 瓶頸定位流程](/backend/09-performance-capacity/) 的依賴鏈分析。

跨平台等效：GCP Firestore + Cloud Messaging、Azure Cosmos DB + Notification Hubs 都是對等架構。差異是 vendor 整合度跟全球分發能力。

## 下一步路由

- 想設計行動支付訊息 → [03 訊息佇列模組](/backend/03-message-queue/) + [9.5 瓶頸定位流程](/backend/09-performance-capacity/)
- 對照其他 KV 高吞吐 → [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/) / [9.C18 Zoom](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/)
- 想做訊息系統容量規劃 → [9.6 容量規劃模型](/backend/09-performance-capacity/) + [9.2 Workload Modeling](/backend/09-performance-capacity/)

## 引用源

- [Amazon DynamoDB Customers](https://aws.amazon.com/dynamodb/customers/)
- [PayPay on AWS](https://aws.amazon.com/solutions/case-studies/paypay/)
