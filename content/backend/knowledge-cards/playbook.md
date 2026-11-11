---
title: "Playbook"
tags: ["處置手冊", "Playbook"]
date: 2026-04-23
description: "說明場景化處置腳本如何降低事故處理不確定性"
weight: 163
---

Playbook 的核心概念是「針對特定故障場景提供可直接執行的處置腳本」。它比通用 [runbook](/backend/knowledge-cards/runbook/) 更聚焦，通常對應單一風險模式或單一系統路徑。

## 跟其他概念的關係

Playbook 位在 [incident command system](/backend/knowledge-cards/incident-command-system/)、[rollback-strategy](/backend/knowledge-cards/rollback-strategy/) 與 [post-incident-review](/backend/knowledge-cards/post-incident-review/) 之間。復盤後的改進常會沉澱成新的 playbook。

## 可觀察訊號與例子

系統需要 playbook 的訊號是某類事故反覆出現且處置步驟可預期。consumer lag 持續擴大、數位憑證即將過期、單區域流量異常等場景都適合建立專用 playbook。

## 判斷條件與後果

Playbook 是事故當下照著執行的腳本，可不可用看值班者拿到它時缺不缺觸發條件、必要查詢、操作步驟、停止條件與回復驗證。沒有觸發條件時，值班者無法確認眼前的狀況是不是這份 playbook 處理的那一種；沒有必要查詢時，他要臨場決定看哪些指標；沒有停止條件時，步驟做下去沒有依據判斷何時該停、何時該升級；沒有回復驗證時，步驟做完也確認不了服務是否恢復。內容寫長時，事故壓力下讀不完，所以保持短而可執行；步驟對應的系統會改變，演練或真實事故之後沒有更新的 playbook，下一次照做時步驟可能已經對不上系統。
