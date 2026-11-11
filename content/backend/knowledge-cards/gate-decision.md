---
title: "Gate Decision"
date: 2026-05-11
description: "說明 release gate 如何把證據轉成放行、暫停、回退或補證據的決策"
weight: 160
tags: ["backend", "knowledge-card", "reliability", "release-gate"]
---

Gate decision 的核心概念是「release gate 根據證據做出的明確下一步」。這類在明確時點做放行判斷的決策，業界慣稱 [go/no-go](/backend/knowledge-cards/go-no-go/) decision——發射體制、變更管理與 cutover 演練裡的 go/no-go 會議指的都是同一件事。它連接 [release gate](/backend/knowledge-cards/release-gate/)、[evidence package](/backend/knowledge-cards/evidence-package/) 與 [stop condition](/backend/knowledge-cards/stop-condition/)，讓 gate 不只寫檢查結果，也寫出能不能前進。

## 跟其他概念的關係

Gate decision 位在 [confidence](/backend/knowledge-cards/confidence/)、[rollback window](/backend/knowledge-cards/rollback-window/) 與 [incident decision log](/backend/knowledge-cards/incident-decision-log/) 之間。Checks 描述檢查結果，gate decision 把結果轉成放行、暫停、回退、fail-forward 或補證據。

## 可觀察訊號

系統需要 gate decision 的訊號是：

- CI、SLO、validation query 都有結果，但沒人知道下一步
- evidence 足以支持部分放行，但不足以支持完整 cutover
- 變更需要逐批 rollout、backfill、warmup 或 replay
- gate 要保留 owner 與 rollback window

## 接近真實網路服務的例子

資料庫 migration 的 gate decision 可以寫成 `allow next 10% backfill; block customer-visible read cutover`。這句話比 `migration pass` 更可操作，因為它同時說明允許前進的範圍與被擋住的風險面。

## 判斷條件與後果

Gate decision 的每一個成分缺席時，決策就少了一項事後回放得到的依據。只寫決策內容而沒有支撐的 checks 時，事後看不出當時依哪些結果放行；沒有 stop condition 時，放行之後指標變差也沒有事先約定的停止點；沒有 rollback window 時，發現異常的當下不知道是否還能退回；沒有 owner 時，放行之後出現異常由誰決定下一步沒有定論。這幾項寫在同一筆決策裡，並記進 [incident decision log](/backend/knowledge-cards/incident-decision-log/) 時，放行後出現異常能回放當時的依據，原因是決策與依據寫在同一筆紀錄裡。
