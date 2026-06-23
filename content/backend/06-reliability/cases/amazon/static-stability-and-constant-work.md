---
title: "Amazon：Static Stability 與 Constant Work Pattern"
date: 2026-06-23
description: "控制面失效時資料面如何維持服務：用快取、預計算與固定工作量避免恢復放大。"
weight: 32
tags: ["backend", "reliability", "case-study"]
---

[Static stability](/backend/knowledge-cards/static-stability/) 的責任是讓資料面在控制面故障時仍能維持服務。Constant work pattern 的責任是讓系統在失敗模式下的工作量與正常時相同。兩者共同保護系統在最需要穩定時不會因為自救動作而崩潰。

## 問題場景

控制面管理路由、配置推送、服務發現與 auto-scaling。當控制面本身失效，依賴控制面的資料面會同時進入未知狀態。最危險的放大路徑是：控制面掛掉後，資料面節點同時嘗試重新連線或重新取得配置，retry storm 把殘餘容量耗盡，資料面跟著崩潰。

這個問題在大規模平台上尤其嚴重。節點越多，控制面恢復時的同時 pull 量越大，恢復本身就會變成新的負載來源。

## 決策機制

| 機制                  | 核心問題                                   | 設計約束                                            |
| --------------------- | ------------------------------------------ | --------------------------------------------------- |
| Static stability      | 控制面不可用時資料面能否繼續服務           | 快取的配置必須是完整可用狀態，不能是 partial update |
| Constant work         | 失敗模式下的系統工作量是否跟正常時相同     | push-based 優於 pull-based：定時推全量，不靠拉取    |
| Pre-computed fallback | 控制面失效時是否有不需要即時計算的備援路徑 | fallback 路徑預先建好，切換動作本身不依賴控制面     |

Static stability 的實作核心是讓每個資料面節點持有控制面最後已知的好配置。當控制面恢復通訊時，節點用最新配置更新快取；當通訊中斷時，節點用快取繼續服務。這個設計要求配置快取是完整的（能獨立驅動服務），而不是差分的（需要跟控制面合併才能用）。

Constant work pattern 的核心是讓系統無論在正常或故障狀態下都執行相同的工作量。push-based config distribution 在每個週期推送全量配置給所有節點，不管配置是否有變更。這樣在控制面恢復時，不會因為所有節點同時 pull 而產生 thundering herd。相比之下，pull-based 在正常時流量低，但控制面恢復瞬間流量暴增。

## 可觀測訊號

| 訊號                           | 判讀重點                         | 對應章節                                                       |
| ------------------------------ | -------------------------------- | -------------------------------------------------------------- |
| control-plane health           | 控制面是否可用、是否在退化中     | [4.13](/backend/04-observability/service-topology/)            |
| cache staleness                | 快取配置距離最後更新多久         | [6.22](/backend/06-reliability/steady-state-definition/)       |
| recovery work amplification    | 恢復過程中負載是否比正常時更高   | [6.14](/backend/06-reliability/dependency-reliability-budget/) |
| data-plane autonomous duration | 資料面在無控制面時能獨立運作多久 | [6.7](/backend/06-reliability/dr-rollback-rehearsal/)          |

cache staleness 是 static stability 最關鍵的健康指標。當快取新鮮度超過預設門檻（取決於配置變更頻率），資料面仍能服務，但服務行為可能與最新意圖不一致。這個門檻決定了 degraded mode 的可接受時間窗。

## 常見陷阱

把控制面失效視為低概率事件而不做 static stability 設計，會在真正發生時暴露循環依賴。Meta 2021-10 事故中，BGP 配置變更導致控制面與資料面共用的網路路徑同時失效，而恢復工具本身也依賴這條路徑，恢復動作陷入循環等待。這個案例說明 static stability 的價值在事前設計，而非事後補救。

## 下一步路由

- [6.7 DR rollback rehearsal](/backend/06-reliability/dr-rollback-rehearsal/)：static stability 讓資料面在災難期間自主運作，是 DR by design
- [6.14 dependency reliability budget](/backend/06-reliability/dependency-reliability-budget/)：控制面是最高風險的內部依賴，budget 設計要先處理控制面失效
- [6.22 steady state definition](/backend/06-reliability/steady-state-definition/)：degraded mode 下的穩態需要包含「控制面不可用但資料面仍服務」的定義

## 引用源

- [Static stability using Availability Zones](https://aws.amazon.com/builders-library/static-stability-using-availability-zones/)
- [Avoiding insurmountable queue backlogs](https://aws.amazon.com/builders-library/avoiding-insurmountable-queue-backlogs/)
