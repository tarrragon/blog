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
| 待補 | Router incidents | 多租戶 PaaS 的入口失效 |
| 待補 | DB add-on 事故   | 第三方依賴的責任歸屬   |

## 引用源

待補（Heroku status / Salesforce trust portal）。
