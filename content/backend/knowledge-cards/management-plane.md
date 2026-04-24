---
title: "Management Plane"
tags: ["管理平面", "Management Plane"]
date: 2026-04-24
description: "說明管理平面如何與業務流量平面分離，避免高權限入口擴散"
weight: 264
---

Management plane 的核心概念是「承載高權限控制操作的系統平面」。它通常包含管理介面、配置變更入口、平台控制 API 與維運工具。

## 概念位置

Management plane 位在 [admin-endpoint](../admin-endpoint/)、[trust-boundary](../trust-boundary/)、[runtime-config](../runtime-config/) 與 [audit-log](../audit-log/) 之間。它需要和業務流量平面維持清楚邊界。

## 可觀察訊號與例子

系統需要管理平面治理的訊號是管理入口可由一般流量路徑到達，或管理操作缺少獨立稽核。邊界設備、雲端控制台、平台管控 API 都屬於管理平面。

## 設計責任

管理平面要定義存取邊界、操作審核、變更時序與責任鏈。事件發生時要能快速鎖定高風險操作入口，避免控制能力被橫向擴散。
