---
title: "Request Routing"
date: 2026-04-24
description: "說明入口流量如何依規則被導向不同服務或處理路徑"
weight: 132
---

Request Routing 的核心概念是「根據 request 的特徵，決定它應該被送到哪個服務或哪條處理路徑」。它處理的是入口層的分派規則，而不是訊息 broker 內部的 routing rule。

## 概念位置

Request Routing 位在 client、[API Gateway](api-gateway/)、[Load Balancer](load-balancer/) 與 application 之間。它通常依 host、path、header、method、tenant、版本或地區決定流量走向。

## 可觀察訊號

系統需要 request routing 的訊號是：

- 同一個對外入口要支援多個服務或版本
- 不同路徑需要不同安全政策、觀測欄位或後端處理
- 需要在不改 client 的情況下調整入口分派

## 接近真實網路服務的例子

`/api/v1` 與 `/api/v2` 導向不同版本服務、依 tenant 送到不同區域、依 path 導向不同內部服務，或把健康流量從一組 instance 切到另一組，都屬於 request routing。

## 設計責任

設計時要定義匹配條件、優先順序、預設路徑與回復方式。Request Routing 本身不應承擔業務邏輯，只應負責把入口流量穩定送到正確目標。
