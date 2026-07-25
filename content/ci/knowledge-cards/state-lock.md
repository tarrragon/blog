---
title: "State Lock"
date: 2026-05-21
description: "說明 IaC apply 如何用狀態鎖避免併發變更覆寫基礎設施狀態"
tags: ["CD", "IaC", "state", "knowledge-card"]
weight: 24
---

State Lock 的核心概念是「讓同一份基礎設施狀態一次只被一個 apply 修改」。它支撐 [Infrastructure Drift](/ci/knowledge-cards/infrastructure-drift/) 的治理，避免 CI job 或人工操作併發覆寫 state。

## 概念位置

State Lock 位在 [IaC state](/ci/knowledge-cards/infrastructure-drift/) backend、plan / apply workflow 與平台資源之間，常由 Terraform backend、Pulumi state 或平台鎖定機制提供。

## 可觀察訊號

- 多個 pipeline 同時 apply 同一個 workspace。
- state file 出現併發覆寫或 partial apply 後不一致。
- apply 長時間卡住需要判斷 lock 是否仍有效。

## 接近真實服務的例子

兩個 PR 同時修改 production network。第一個 workflow 取得 state lock 後進入 apply，第二個 workflow 等待或失敗，避免兩次變更同時寫入 state。

## 設計責任

State Lock 要定義 lock backend、timeout、人工解鎖條件、環境隔離與失敗處理，讓 IaC apply 保持序列化。
