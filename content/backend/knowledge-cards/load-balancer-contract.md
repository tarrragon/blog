---
title: "Load Balancer Contract"
tags: ["負載平衡協議", "Load Balancer Contract"]
date: 2026-04-23
description: "說明服務與負載平衡器之間的流量與健康檢查約定"
weight: 1
---

Load Balancer Contract 的核心概念是「服務如何告訴流量入口自己能否安全接流量」。它描述 [health check](/backend/knowledge-cards/health-check/)、排空、切流與超時行為。

## 跟其他概念的關係

Load Balancer Contract 位在 application、load balancer、ingress 與 service discovery 之間。 可先對照 [Health Check](/backend/knowledge-cards/health-check/)。

## 可觀察訊號

系統需要 load balancer contract 的訊號是流量分散、rolling update、[draining](/backend/knowledge-cards/draining/) 或 [idle timeout](/backend/knowledge-cards/idle-timeout/) 直接影響使用者請求。

## 接近真實網路服務的例子

[health check](/backend/knowledge-cards/health-check/)、readiness、[draining](/backend/knowledge-cards/draining/) 與 [idle timeout](/backend/knowledge-cards/idle-timeout/) 都屬於 load balancer contract；[sticky session](/backend/knowledge-cards/sticky-session/) 則是另一種負載分派策略，應獨立理解。

## 判斷條件與後果

Load Balancer Contract 的某一項沒有定義時，那個時刻的行為由 load balancer 的預設值決定。可接新流量的條件沒有定義時，instance 的程序一啟動就被放進流量池，還沒準備好的 instance 收到請求而失敗。排空的條件沒有定義時，rolling update 關掉 instance 的那一刻，處理中的請求與長連線被切斷；切換的等待時間比最長的請求或 [idle timeout](/backend/knowledge-cards/idle-timeout/) 短時，[draining](/backend/knowledge-cards/draining/) 還沒結束連線就被關掉。健康檢查失敗後的處理（失敗幾次才移出、恢復後何時放回）沒有定義時，一次短暫失敗可能讓 instance 被移出，持續失敗的 instance 也可能遲遲沒被移出。
