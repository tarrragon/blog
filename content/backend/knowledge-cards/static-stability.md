---
title: "Static Stability"
tags: ["Static Stability", "Control Plane", "Data Plane", "可靠性"]
date: 2026-06-23
description: "控制面失效時資料面用快取的已知好配置繼續服務的設計模式"
weight: 321
---

Static stability 的核心概念是「資料面在 [control plane](/backend/knowledge-cards/control-plane/) 失效時仍能維持服務」。設計約束是資料面必須快取控制面最後已知的好配置，並在控制面不可用時用快取繼續運作，不依賴控制面即時回應。

## 跟其他概念的關係

Static stability 位在 [control plane](/backend/knowledge-cards/control-plane/) 與 [blast radius](/backend/knowledge-cards/blast-radius/) 之間。它把控制面失效的影響限制在「新配置無法推送」，而非「現有服務中斷」。跟 [steady state](/backend/knowledge-cards/steady-state/) 的關係是：static stability 定義了控制面失效期間的 degraded steady state — 服務能力受限但仍在可接受範圍。

## 核心機制

Static stability 依賴三個機制：快取最後已知好配置（控制面失效時不嘗試重新取得）、預計算 fallback 路徑（控制面在線時就 build 好備用配置）、constant work pattern（失敗模式下的工作量跟正常時相同，避免 retry storm 放大負載）。

## 可觀察訊號與例子

需要 static stability 設計的訊號是控制面重啟或網路隔離時，資料面同時不可用。典型例子是 service mesh 的 control plane 掛掉後 sidecar 無法取得路由表、導致所有服務間通訊中斷；static stability 設計讓 sidecar 用快取的路由表繼續服務。

## 判斷條件與後果

判斷的對象是資料面處理每一個請求時，是否需要控制面即時回應。需要的話，控制面重啟或被網路隔離時資料面跟著停止服務，影響從「新配置推不出去」擴大成「現有服務中斷」。[DR](/backend/knowledge-cards/rto/) 計畫把控制面當成可用的前提時，在控制面一起故障的事故裡執行不了，原因是計畫依賴的元件正是故障的那一個。資料面已經快取最後已知的好配置、fallback 路徑在控制面在線時就預先算好的話，控制面失效只讓配置更新停下來，現有的服務照常運作。所以 [readiness](/backend/knowledge-cards/readiness/) review 把資料面的這種自主能力列為前置項：缺了它，其他項目通過之後，控制面一故障服務仍然中斷。
