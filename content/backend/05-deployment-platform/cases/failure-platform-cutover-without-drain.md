---
title: "5.C9 反例：平台切流未先 Draining"
date: 2026-05-07
description: "切流時忽略連線清退造成請求錯誤與重試風暴。"
weight: 9
tags: ["backend", "deployment", "case-study"]
---

這個反例的核心責任是說明部署平台切換失敗常在 connection lifecycle 管理。

## 事故長相

平台切流一開始看似成功，新的 instance 也通過 readiness，但長連線、背景工作與 load balancer 仍把流量送到即將下線的節點。使用者看到的是短時間大量 5xx、重連風暴與 timeout。

## 為什麼會擴大

部署平台的切換不是只看 pod 或 VM 是否 ready。若 draining、idle timeout、health check、client retry 沒有同一節奏，平台會同時製造連線中斷與重試放大。

## 回退判讀

這類事故的回退要先恢復穩定流量路徑，而不是立刻重啟所有服務。若長連線仍在震盪，重啟會讓重連潮更大。比較可靠的做法是先停止下一批切流，恢復舊入口權重，等待連線數與錯誤率回到可控範圍。

## 部署專屬告警條件

- 切流批次內 5xx 突增
- 長連線重連率快速上升
- rollback time 超過既定 RTO

## 下一步路由

回 [5.3](/backend/05-deployment-platform/load-balancer-contract/) 與 [6.7](/backend/06-reliability/dr-rollback-rehearsal/)。
