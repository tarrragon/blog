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
| 待補 | 其他公開 PIR          | 比對 AWS post-incident report 的格式變化 |

## 引用源

待補（AWS post-incident report URL、相關 status page snapshot）。
