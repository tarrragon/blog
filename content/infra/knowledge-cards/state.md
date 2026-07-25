---
title: "State（IaC 狀態檔）"
date: 2026-06-26
description: "IaC 工具用來記錄每個納管資源在雲端真實樣貌的快照，是比對差異與排定操作順序的依據"
weight: 2
tags: ["infra", "knowledge-cards", "state", "terraform"]
---

State 是 [IaC](/infra/knowledge-cards/iac/) 工具用來記錄「上一次 apply 之後，每個資源在雲端長什麼樣」的快照。它的作用是讓工具能算出「程式碼描述的目標」與「雲端上的現況」之間的最小差異。沒有 state，工具每次都得把所有資源重新查一遍才知道該不該動，而且無法分辨「這個資源是我建的、該由我管」還是「別人手動建的、不歸我管」。

State 裡通常含有資源的真實 ID、相依關係，以及部分敏感屬性（例如資料庫的初始密碼、private key 的輸出值）。這帶來兩條硬邊界：state 不能進 git（含敏感值，推進版控等於把密碼寫進每個 clone 的歷史）、state 不能只放本地（本地 state 的失敗模式是記憶綁在一台筆電上，多人並行 apply 會互相覆蓋）。

## 概念位置

State 是 [IaC](/infra/knowledge-cards/iac/) 的記憶機制。[模組一：最小可行 IaC](/infra/01-minimal-iac/iac-tool-state-backend/) 的核心主題就是怎麼把 state 管好——remote backend、加密、鎖機制。State 管不好，後續所有 IaC 操作都建立在不可靠的記憶上。

## 可觀察訊號

State 出問題的訊號包括：`terraform plan` 顯示大量非預期的變更（state 與現實不一致）、兩個人同時 apply 後環境出現矛盾狀態、`state list` 的資源數與 Console 上看到的不一致。

## 設計責任

管理 state 時要決定：

- 存放位置：S3 + DynamoDB（自管）vs Terraform Cloud（託管），取捨在維運負擔 vs 控制權
- 加密：state 含敏感值，落地加密（S3 SSE）是底線
- 版本保留：bucket versioning 讓 state 損壞時能回捲到上一個正確版本
- 鎖機制：防止兩個人同時 apply 互相覆蓋
- 分割策略：一個大 state vs 多個小 state，取捨在引用便利性 vs 影響範圍控制

## 鄰卡

- [IaC](/infra/knowledge-cards/iac/) — state 是 IaC 工具的核心依賴
- [Drift](/infra/knowledge-cards/drift/) — state 與現實的落差
