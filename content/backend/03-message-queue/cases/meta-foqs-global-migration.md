---
title: "3.C1 Meta：FOQS 從區域到全域佇列遷移"
date: 2026-05-07
description: "佇列架構如何在不中斷下升級成 disaster-ready 模式。"
weight: 1
tags: ["backend", "message-queue", "case-study"]
---

這個案例的核心責任是說明 queue 轉換不只換 broker，還包含路由與可用性模型重整。

## 觀察

FOQS 從區域安裝轉為全域架構，目標是讓災害期間佇列資料仍可被存取，並控制遷移期間的延遲與可用性風險。

## 判讀

當 queue 成為跨區關鍵路徑，轉換焦點是 discoverability、routing freshness 與 tenant 遷移節奏。

## 策略

1. 先建立全域路由層，再分批搬遷租戶。
2. 針對 stale routing 做補貨延遲治理。
3. 用零停機遷移策略保留客戶端連續性。

## 下一步路由

回 [3.1 broker basics](/backend/03-message-queue/broker-basics/) 與 [3.2 durable queue](/backend/03-message-queue/durable-queue/)。

## 引用源

- [FOQS disaster-ready migration](https://engineering.fb.com/2022/01/18/production-engineering/foqs-disaster-ready/)
