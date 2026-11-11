---
title: "Readiness / Health Check"
date: 2026-05-06
description: "說明服務存活與可接流量判斷在部署中的不同責任"
tags: ["CD", "readiness", "health-check", "knowledge-card"]
weight: 12
aliases: ["/ci/knowledge-cards/readiness-health-check/"]
---

Readiness / Health Check 的核心概念是「服務活著」與「服務可接流量」是兩個不同訊號。部署放行通常依賴 readiness 而非僅看 process alive，是 [Rollout Strategy](/devops/ci/knowledge-cards/rollout-strategy/) 決定是否擴大流量的判斷依據。

## 跟其他概念的關係

Readiness / Health Check 位在 rollout、load balancer 與 runtime platform 之間，是流量切換前的核心 gate，與 [Deployment Dry Run](/devops/ci/knowledge-cards/deployment-dry-run/) 同屬部署放行前的驗證機制。

## 可觀察訊號

- 部署後健康檢查綠燈但請求仍大量失敗。
- 新版啟動中就提早接到流量。
- rollout 失敗時缺少可觀測放行條件。

## 接近真實服務的例子

Kubernetes liveness 通過只代表 process 存活；readiness 通過才代表連線池、依賴服務與必要資料都已準備完成。

## 判斷條件與後果

Readiness check 的檢查內容決定 rollout 拿到的訊號是否可信。檢查只確認 process 還活著時，新版本在連線池、依賴服務或必要資料準備好之前就被判定可以接流量，部署後健康檢查綠燈而請求大量失敗。容錯窗口太短時，啟動較慢的實例在準備完成之前就被判定失敗而重啟；太長時，已經故障的實例要等更久才被移出流量。檢查失敗之後 rollout 怎麼走（暫停推進、回退，或只把那個實例移出）沒有事先寫定時，健康檢查變紅也不會改變 rollout 的走向。
