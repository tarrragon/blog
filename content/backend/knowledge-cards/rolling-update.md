---
title: "Rolling Update"
date: 2026-04-23
description: "說明逐批替換服務版本的發版策略與風險控制"
weight: 153
---

Rolling update 的核心概念是「逐批替換舊版本實例，維持服務持續可用」。它可降低一次性切換風險。 可先對照 [Readiness](/backend/knowledge-cards/readiness/)。

## 跟其他概念的關係

常搭配 [readiness](/backend/knowledge-cards/readiness/)、[graceful shutdown](/backend/knowledge-cards/graceful-shutdown/) 與 [service discovery](/backend/knowledge-cards/service-discovery/)。

## 判斷條件與後果

Rolling update 的四個參數（每批比例、健康檢查門檻、回滾條件、流量切換節奏）各自決定新版本有缺陷時，影響擴散到多少實例才停下。每批比例越大，替換越快，新版本有缺陷時一次受影響的實例也越多，比例接近全部時等於一次性切換；健康檢查門檻（[readiness](/backend/knowledge-cards/readiness/)）太寬時，還沒準備好的實例就開始接流量，請求在替換過程中失敗。沒有回滾條件時，錯誤率上升也不會停下替換，壞版本照樣推進到最後一批。流量切換的節奏快過 [graceful shutdown](/backend/knowledge-cards/graceful-shutdown/) 時，舊實例在處理完手上的請求之前就被移除，進行中的請求被中斷。
