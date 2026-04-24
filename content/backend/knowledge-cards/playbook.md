---
title: "Playbook"
date: 2026-04-23
description: "說明場景化處置腳本如何降低事故處理不確定性"
weight: 162
---

Playbook 的核心概念是「針對特定故障場景提供可直接執行的處置腳本」。它比通用 [runbook](../runbook/) 更聚焦，通常對應單一風險模式或單一系統路徑。

## 概念位置

Playbook 位在 [incident command system](../incident-command-system/)、[rollback-strategy](../rollback-strategy/) 與 [post-incident-review](../post-incident-review/) 之間。復盤後的改進常會沉澱成新的 playbook。

## 可觀察訊號與例子

系統需要 playbook 的訊號是某類事故反覆出現且處置步驟可預期。consumer lag 持續擴大、憑證即將過期、單區域流量異常等場景都適合建立專用 playbook。

## 設計責任

Playbook 要定義觸發條件、必要查詢、操作步驟、停止條件與回復驗證。內容應保持短而可執行，並在每次演練或真實事故後更新。

## 英文術語對照
- Playbook
- Response playbook
