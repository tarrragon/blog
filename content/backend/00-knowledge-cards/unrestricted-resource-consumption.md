---
title: "Unrestricted Resource Consumption"
date: 2026-04-23
description: "說明缺少資源限制如何讓 API 被濫用或拖垮"
weight: 116
---

Unrestricted resource consumption 的核心概念是「API 沒有對資源使用量設定足夠限制」。攻擊者或錯誤 client 可以用大量 request、大型 payload、昂貴查詢或大量匯出耗盡系統資源。

## 概念位置

資源消耗限制連接 rate limit、payload limit、timeout、pagination、query cost、queue quota 與 tenant quota。它同時是可靠性與資安問題。

## 可觀察訊號與例子

系統需要資源消耗限制的訊號是 API 支援搜尋、匯出、上傳、批次操作或複雜 filter。未限制日期範圍的報表匯出，可能讓單一 request 掃描多年資料。

## 設計責任

防護要定義大小限制、速率限制、分頁、查詢成本、timeout、租戶配額與告警。錯誤回應應告訴 client 如何縮小請求。
