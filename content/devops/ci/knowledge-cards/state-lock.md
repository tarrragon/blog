---
title: "State Lock"
date: 2026-05-21
description: "說明 IaC apply 如何用狀態鎖避免併發變更覆寫基礎設施狀態"
tags: ["CD", "IaC", "state", "knowledge-card"]
weight: 24
aliases: ["/ci/knowledge-cards/state-lock/"]
---

State Lock 的核心概念是「讓同一份基礎設施狀態一次只被一個 apply 修改」。它支撐 [Infrastructure Drift](/devops/ci/knowledge-cards/infrastructure-drift/) 的治理，避免 CI job 或人工操作併發覆寫 state。

## 跟其他概念的關係

State Lock 位在 [IaC state](/devops/ci/knowledge-cards/infrastructure-drift/) backend、plan / apply workflow 與平台資源之間，常由 Terraform backend、Pulumi state 或平台鎖定機制提供。

## 可觀察訊號

- 多個 pipeline 同時 apply 同一個 workspace。
- state file 出現併發覆寫或 partial apply 後不一致。
- apply 長時間卡住需要判斷 lock 是否仍有效。

## 接近真實服務的例子

兩個 PR 同時修改 production network。第一個 workflow 取得 state lock 後進入 apply，第二個 workflow 等待或失敗，避免兩次變更同時寫入 state。

## 判斷條件與後果

State lock 的設定決定兩種失敗情形下 state 處在什麼狀態。兩個 workflow 同時 apply 同一個 workspace、而 backend 不提供鎖定時，兩次變更都寫入 state，後寫的蓋掉先寫的，state 跟實際資源在 partial apply 之後對不上。持有鎖的 apply 中途被中斷、鎖沒有被釋放時，之後的 apply 全部卡在等鎖；這時的處置是人工解鎖，解鎖前先確認原本那次 apply 已經停止，原因是它還在執行時，解鎖等於重新允許併發寫入。不同環境共用同一份 state 與同一把鎖時，staging 的 apply 會擋住 production 的修復。
