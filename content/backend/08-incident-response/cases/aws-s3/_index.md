---
title: "AWS S3"
date: 2026-05-01
description: "AWS S3 重大事故時間線與架構脈絡"
weight: 1
---

AWS S3 是物件儲存的事實標準、區域控制面失效會大規模擴散到下游服務、是區域依賴 / blast radius / 控制面 vs 資料面分離的教學標竿。

## 規劃重點

- 區域依賴擴散：S3 us-east-1 失效會牽動 console、IAM、ECR、CloudFormation 等控制面
- Blast radius 範例：subsystem 失效如何意外擴散到看似無關服務
- 控制面 / 資料面分離設計：為何 S3 把兩者拆開、失效時表現差異
- Recovery 節奏：metadata service 重啟為何耗時、為何不能熱重啟

## 預計收錄事故

| 年份 | 事故                  | 教學重點                                 |
| ---- | --------------------- | ---------------------------------------- |
| 2017 | us-east-1 typo 4 小時 | 內部工具誤觸、區域依賴擴散               |
| 2021 | us-east-1 多服務退化  | 控制面與下游服務的隱性耦合               |
| 2023 | 其他 AWS 公開摘要     | 比對 AWS post-incident report 的格式變化 |

## 案例定位

AWS S3 這個案例在講的是區域控制面失效如何透過依賴鏈條放大成多服務事故。讀者先看懂控制面與資料面分離的責任，再把 us-east-1 這類事件當成 blast radius 與恢復節奏的教學範本。

## 判讀重點

當內部工具誤觸或控制面出現異常時，第一件事不是擴容，而是先切開受影響的依賴路徑。當服務恢復時，metadata service 與下游依賴通常不會同時回穩，所以恢復順序比單純重啟更重要。

## 可操作判準

- 能否分辨故障落在控制面還是資料面
- 能否指出哪個依賴把事故擴成區域事件
- 能否把恢復順序寫成可執行的 runbook
- 能否在復原後回頭檢查 blast radius 是否被正確限制

## 與其他案例的關係

AWS S3 是區域控制面事故的基準頁，和 Cloudflare、Fastly、GCP 一起讀時，最能看出「小變更如何變成大擴散」。這頁也能拿來對照 GitHub 與 Azure AD，因為它們同樣在處理共享依賴被一個節點拖垮後的恢復節奏。

## 代表樣本

- 2017 年 us-east-1 typo 事故顯示單一控制面誤觸可以牽動整個區域。
- 2021 年 us-east-1 多服務退化則示範了控制面與下游服務如何一起受影響。
- 其他公開 PIR 可以拿來對照 AWS 的回顧格式如何隨時間演化。
- S3 的案例也能對照控制面與資料面拆分後的恢復順序。
- metadata service 的恢復節奏常常比使用者看到的 outage 更長。
- region dependency 讓看似獨立的 AWS 服務一起進入失效鏈。
- blast radius 的核心不是單一服務，而是依賴鏈條被拉長後的擴散。
- post-incident report 的寫法能對照 AWS 如何對外說明與內部修復。

## 引用源

- [Summary of the Amazon S3 Service Disruption in the Northern Virginia (US-EAST-1) Region](https://aws.amazon.com/message/41926/)：2017 年 S3 us-east-1 事故的官方摘要與時間線。
- [Introducing The Amazon Builders’ Library](https://aws.amazon.com/about-aws/whats-new/2019/12/introducing-amazon-builders-library/)：S3 類事故所屬的大型系統操作與恢復脈絡。
- [Workload isolation using shuffle-sharding](https://aws.amazon.com/builders-library/workload-isolation-using-shuffle-sharding/)：補 blast radius 與隔離思路。
