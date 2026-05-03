---
title: "Roblox"
date: 2026-05-01
description: "Roblox 73 小時事故時間線與架構脈絡"
weight: 6
---

Roblox 2021 的 73 小時事故是 Consul 流量模式 + long-tail recovery 的教學標竿。事故 post-mortem 詳細揭露根因發現過程、適合作為「為何根因難找」「為何 recovery 比預期慢」的敘事範本。

## 規劃重點

- Consul 流量模式：streaming + 大量 watch 的非預期行為
- 根因發現延遲：72 小時內為何無法定位 streaming 是兇手
- Long-tail recovery：服務恢復後為何效能未恢復、cache cold start 影響
- 廠商協作：HashiCorp 介入時機、第三方協助的 IR 流程
- Postmortem 公開度：Roblox 罕見的詳細工程敘事

## 預計收錄事故

| 年份 | 事故           | 教學重點                               |
| ---- | -------------- | -------------------------------------- |
| 2021 | 73 小時 outage | 根因難尋、long-tail recovery、廠商協作 |

## 案例定位

Roblox 這個案例在講的是長時間事故如何把基礎設施依賴顯性化。讀者先看懂控制面、配置與服務恢復的順序，再把 73 小時這類事件當成 prolonged recovery 的範例。

## 判讀重點

當核心依賴出現問題時，恢復不只是在某台機器上按下重啟，而是要讓整個服務依賴鏈按順序回來。當事件持續多天時，修復與驗證的節奏要穩定，否則使用者面恢復會反覆抖動。

## 可操作判準

- 能否說明哪個基礎設施層先恢復
- 能否把長尾恢復拆成可驗證的階段
- 能否在控制面回穩前避免過早開流量
- 能否把 prolonged recovery 的每一步對外說清楚

## 與其他案例的關係

Roblox 和 Discord、Heroku 一起讀時，最能看出長連線與多租戶基礎設施的恢復難度。它也能對照 AWS S3，因為兩者都在說明基礎層恢復順序一旦錯了，後面的使用者體感就會反覆抖動。

## 代表樣本

- 73 小時 outage 是長尾恢復與根因難尋的代表案例。
- Return to Service 文件則提供了從事故到結構性改善的完整敘事。
- Consul 的流量模式揭露了意外的 session 壓力。
- 廠商協作是 prolonged recovery 的重要組件。
- streaming / watch traffic 讓非預期的控制面壓力浮出來。
- infrastructure efficiency 改善是事故之後的結構性回應。
- streaming / watch traffic 讓非預期的控制面壓力浮出來。
- infrastructure efficiency 改善是事故之後的結構性回應。

## 引用源

- [An Update on Our Outage](https://corp.roblox.com/newsroom/2021/10/update-recent-service-outage/)：Roblox 73 小時 outage 的初始對外說明。
- [Roblox Return to Service](https://corp.roblox.com/fr/salledepresse/2022/01/roblox-return-to-service-10-28-10-31-2021)：完整 return-to-service 與技術復盤。
- [How We’re Making Roblox’s Infrastructure More Efficient and Resilient](https://corp.roblox.com/de/newsroom/2023/12/making-robloxs-infrastructure-efficient-resilient)：後續的結構性改善與 cell 化方向。
