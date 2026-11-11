---
title: "Steady State"
tags: ["Steady State", "Chaos Engineering", "穩態"]
date: 2026-05-07
description: "說明可靠性實驗與事故恢復如何定義系統應維持的可接受狀態"
weight: 320
---

Steady state 的核心概念是「系統在正常或受控退化期間仍應維持的服務能力」。它連接 [SLI / SLO](/backend/knowledge-cards/sli-slo/)、[chaos test](/backend/knowledge-cards/chaos-test/) 與 [degradation](/backend/knowledge-cards/degradation/)，讓實驗與事故共用同一組成功條件。

## 跟其他概念的關係

Steady state 位在 [error budget](/backend/knowledge-cards/error-budget/)、[blast radius](/backend/knowledge-cards/blast-radius/) 與 [RTO](/backend/knowledge-cards/rto/) / [RPO](/backend/knowledge-cards/rpo/) 之間。它把可靠性承諾轉成可量測訊號，並說明故障期間哪些能力要維持、哪些能力可以受控退化。

## 可觀察訊號與例子

系統需要 steady state 的訊號是 chaos、failover 或 DR drill 只描述故障動作，缺少成功判斷標準。常見例子是節點被關閉後 health check 仍為綠燈，但 checkout success、queue lag 或 client-side error rate 已經偏離使用者可接受範圍。

## 判斷條件與後果

Steady state 的門檻缺了哪一項，實驗或事故的判斷就在那一項上沒有依據。只訂 success rate 與 latency、沒有 queue lag 門檻時，節點關閉後請求照常成功而積壓持續增加，實驗仍判成通過；沒有 data correctness 門檻時，failover 後寫入成功而資料不一致，判斷上看不出來；沒有 customer impact 門檻時，內部指標都在範圍內、client-side error rate 已經偏離，結論仍是正常；沒有 recovery complete 門檻時，事故何時算恢復由當下的人決定，[incident decision log](/backend/knowledge-cards/incident-decision-log/) 記下的恢復時間沒有可以對照的條件。[evidence package](/backend/knowledge-cards/evidence-package/) 與 [game day](/backend/knowledge-cards/game-day/) 判斷實驗是否通過時，都拿這組門檻對照量到的值，所以門檻在實驗或演練開始之前寫下；事後才補的門檻是看過結果之後訂的，判斷不出實驗本身是否通過。
