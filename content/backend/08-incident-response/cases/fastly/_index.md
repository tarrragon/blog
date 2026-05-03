---
title: "Fastly"
date: 2026-05-01
description: "Fastly 全球配置 push 事故時間線"
weight: 7
---

Fastly 2021-06 的全球分鐘級配置 push 事故是 edge platform 的客戶配置觸發供應商 bug 的教學標竿。事件揭露了「客戶觸發供應商 bug」這類 IR 議題的特殊性、跟 Cloudflare 配置事故有對照價值。

## 規劃重點

- 客戶配置觸發供應商 bug：誰負責、誰補償、誰公開
- 全球 edge 分鐘級擴散：為何 edge platform 出事規模特別大
- Recovery 機制：客戶配置回退 vs 供應商 hotfix 的取捨
- 通訊責任：上下游服務（Reddit、Amazon、政府網站）受影響時的 status 揭露

## 預計收錄事故

| 年份    | 事故                     | 教學重點                                 |
| ------- | ------------------------ | ---------------------------------------- |
| 2021-06 | 全球分鐘級配置 push 失效 | 客戶配置觸發、edge platform blast radius |

## 案例定位

Fastly 這個案例在講的是一個小型配置錯誤如何透過 edge 網路快速放大。讀者先看懂配置驗證、全球推送與回滾的責任，再把這類事故視為 control-plane 失誤，而不是單點節點故障。

## 判讀重點

當壞配置進入全球推送鏈時，真正關鍵的步驟不是事後修補，而是能否快速阻斷傳播。當回復開始時，還要同時確認快取、路由與客戶流量是否已回到預期狀態。

## 可操作判準

- 能否在推送前把配置驗證到足夠高的信心
- 能否即時看見錯誤配置的擴散跡象
- 能否把 rollback 做成高優先序動作
- 能否把 global propagation 與客戶影響對齊

## 與其他案例的關係

Fastly 和 Cloudflare 是最接近的一組對照頁，兩者都在講 edge 網路上的配置擴散。Fastly 更適合用來看「客戶配置觸發供應商 bug」這個特殊模式，和 AWS S3 的區域控制面事故放在一起時，會更容易分辨不同層級的 blast radius。

## 代表樣本

- 2021-06 全球分鐘級配置 push 失效是最典型的 edge propagation 樣本。
- 這類事故強調回滾速度與配置驗證必須先於全球擴散。
- 客戶配置觸發供應商 bug 是 edge 平台最難處理的模式之一。
- Fastly 的樣本能和 Cloudflare、AWS S3 一起看 blast radius。
- CDN 邊緣層的壓力會把一個小錯誤迅速推成全球事件。
- rollback 與 status 通訊必須同步，否則客戶只會看到更長的黑箱。
- deploy tool misconfiguration 讓工具本身變成事故起點。
- edge runtime 的錯誤驗證不充分時，影響會直接落到全球流量。

## 引用源

- [Summary of June 8 outage](https://www.fastly.com/blog/summary-of-june-8-outage)：Fastly 2021-06 全球 outage 的官方回顧。
