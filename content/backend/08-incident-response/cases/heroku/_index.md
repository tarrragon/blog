---
title: "Heroku"
date: 2026-05-01
description: "Heroku PaaS 事故與 router 層架構脈絡"
weight: 21
---

Heroku 是早期 PaaS 的代表、router 層事故揭露 multi-tenant 路由的失敗模式。Heroku status 與工程文章累積多年事故敘事。

## 規劃重點

- Router 層失效：多租戶 PaaS 的入口失效擴散
- Dyno scheduling：背景排程系統的 failure mode
- Add-on dependency：第三方服務嵌入 PaaS 後的責任邊界
- Salesforce 收購後的 IR 演化

## 預計收錄事故

| 年份 | 事故             | 教學重點               |
| ---- | ---------------- | ---------------------- |
| 2021 | Router incidents | 多租戶 PaaS 的入口失效 |
| 2022 | DB add-on 事故   | 第三方依賴的責任歸屬   |

## 案例定位

Heroku 這個案例在講的是 PaaS 入口路由如何成為多租戶事故的第一個放大點。讀者先抓 router、dyno scheduling 與 add-on dependency 的責任，再把 status 通訊視為事故管理的一部分。

## 判讀重點

當 router 或 keepalive 機制出現問題時，事故不只影響單一應用，而會直接影響入口流量與租戶隔離。當第三方 add-on 失效時，責任邊界也要一起說清楚，否則客戶會把平台與外部依賴視為同一個故障面。

## 可操作判準

- 能否區分 router 層與應用層問題
- 能否說明 add-on 依賴的責任邊界
- 能否把 incident 通訊路由到正確的 status channel
- 能否把多租戶入口失效視為平台級風險

## 與其他案例的關係

Heroku 比較像是 PaaS 世界裡的 AWS S3 或 Cloudflare，因為入口路由一出問題，很多 tenant 會一起受影響。它也能和 Datadog、Slack 對照，幫讀者理解平台本身與平台上的應用該怎麼切責任邊界。

## 代表樣本

- router incidents 顯示入口層是多租戶 PaaS 的第一個放大器。
- DB add-on 事故則讓第三方依賴的責任邊界變得很清楚。
- keepalive 與 internal routing 會直接影響租戶體感。
- status channel 的選擇也是事故管理的一部分。
- dyno scheduling 的問題會把平台內部失衡直接變成租戶可見故障。
- Salesforce Trust 作為主通路，改變了 Heroku 事故通訊的路由方式。
- multi-tenant routing 讓入口層成為最敏感的擴散點。
- third-party add-on 事故提醒平台必須清楚切出責任邊界。

## 引用源

- [Heroku Status](https://devcenter.heroku.com/articles/heroku-status)：Heroku incident 通訊與歷史紀錄的官方說明。
- [Salesforce Trust is now the primary channel for all Heroku incident and maintenance communications](https://devcenter.heroku.com/changelog-items/3422)：Heroku status 通訊的最新主通路。
- [Heroku Labs: Disabling Keepalives to Dyno for the Common Runtime Router](https://devcenter.heroku.com/articles/heroku-labs-disabling-keepalives-to-dyno-for-router-2-0)：Router / keepalive 的官方設計說明。
- [Internal Routing](https://devcenter.heroku.com/articles/internal-routing)：PaaS 內部路由與多租戶邊界。
