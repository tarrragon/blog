---
title: "Canary Release"
date: 2026-06-23
description: "分批把流量導向新版本、用 stop condition 控制 blast radius 的部署策略"
weight: 236
tags: ["canary", "deployment"]
---

Canary release 的核心概念是「先把小比例流量導向新版本、觀察行為、再決定是否擴大」。它把版本切換從一次性決策變成連續多批決策，每批都有明確的觀察窗口與停損條件。可先對照 [Rolling Update](/backend/knowledge-cards/rolling-update/)。

## 概念位置

Canary release 位在 [rolling update](/backend/knowledge-cards/rolling-update/) 與 [release gate](/backend/knowledge-cards/release-gate/) 之間。Rolling update 是逐批替換實例的機制，canary 是在替換過程中加入「先驗證再擴批」的決策層。Release gate 是每批擴大前的放行條件。可先對照 [Canary Perf Check](/backend/knowledge-cards/canary-perf-check/)。

## 可觀察訊號

系統需要 canary release 的訊號是「版本切換需要控制 [blast radius](/backend/knowledge-cards/blast-radius/)」。判讀要維持 per-version 視角——只看整體平均值會掩蓋新版本的局部退化。常見 stop condition 包含 per-version error rate 偏離、p95/p99 latency 惡化、依賴 timeout 連續超門檻、[draining](/backend/knowledge-cards/draining/) 未完成。

## 設計責任

Canary release 要定義三件事：切換單位（比例 / 區域 / 租戶 / 路由規則）、每批觀察窗口與停損條件、回退路徑（舊版本是否仍能承接回退流量）。效能退化的檢查見 [Canary Perf Check](/backend/knowledge-cards/canary-perf-check/)。Canary 決策的 evidence 格式見 [Evidence Package](/backend/knowledge-cards/evidence-package/)。
