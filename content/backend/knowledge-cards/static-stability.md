---
title: "Static Stability"
tags: ["Static Stability", "Control Plane", "Data Plane", "可靠性"]
date: 2026-06-23
description: "控制面失效時資料面用快取的已知好配置繼續服務的設計模式"
weight: 320
---

Static stability 的核心概念是「資料面在 [control plane](/backend/knowledge-cards/control-plane/) 失效時仍能維持服務」。設計約束是資料面必須快取控制面最後已知的好配置，並在控制面不可用時用快取繼續運作，不依賴控制面即時回應。

## 概念位置

Static stability 位在 [control plane](/backend/knowledge-cards/control-plane/) 與 [blast radius](/backend/knowledge-cards/blast-radius/) 之間。它把控制面失效的影響限制在「新配置無法推送」，而非「現有服務中斷」。跟 [steady state](/backend/knowledge-cards/steady-state/) 的關係是：static stability 定義了控制面失效期間的 degraded steady state — 服務能力受限但仍在可接受範圍。

## 核心機制

Static stability 依賴三個機制：快取最後已知好配置（控制面失效時不嘗試重新取得）、預計算 fallback 路徑（控制面在線時就 build 好備用配置）、constant work pattern（失敗模式下的工作量跟正常時相同，避免 retry storm 放大負載）。

## 可觀察訊號與例子

需要 static stability 設計的訊號是控制面重啟或網路隔離時，資料面同時不可用。典型例子是 service mesh 的 control plane 掛掉後 sidecar 無法取得路由表、導致所有服務間通訊中斷；static stability 設計讓 sidecar 用快取的路由表繼續服務。

## 設計責任

Static stability 的責任是讓 [DR](/backend/knowledge-cards/rto/) 設計不依賴已故障的控制面。它跟 [readiness](/backend/knowledge-cards/readiness/) 的關係是：static stability 是 readiness review 的前置項 — 若資料面沒有控制面失效時的自主能力，readiness 就有結構性缺口。
