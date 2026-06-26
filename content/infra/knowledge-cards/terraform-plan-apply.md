---
title: "terraform plan / apply"
date: 2026-06-26
description: "IaC 的兩個核心操作：plan 只看不動（產出差異報告）、apply 真的動（執行差異）"
weight: 40
tags: ["infra", "knowledge-cards"]
---

`terraform plan` 和 `terraform apply` 是 Terraform 操作基礎設施的兩個核心指令。plan 比對三方（state 檔、雲端現況、HCL 描述）產出差異報告，告訴使用者「如果 apply 會發生什麼」，但不做任何改動。apply 執行 plan 算出的差異，在雲端建立、修改或刪除資源。

## 概念位置

plan/apply 的分離是 IaC 可審查性的基礎。模組七（PR 流程）的核心機制就是「PR 觸發 plan → plan 結果貼回 PR → reviewer 看 plan 再決定要不要 apply」。這個「先看再動」的流程跟手動操作（直接在 Console 改）的根本差別。

## 可觀察訊號

需要理解 plan/apply 的情境包括：第一次跑 Terraform、review 別人的 infra PR（看 plan 輸出）、排查 drift（plan 在沒有 code 變更的情況下顯示差異）、或決定一次 apply 是否安全。

## 設計責任

plan 輸出的三種動作標記：

| 標記  | 意義                           | 風險                                                     |
| ----- | ------------------------------ | -------------------------------------------------------- |
| `+`   | 新增資源                       | 低（新建不影響現有）                                     |
| `~`   | 修改資源（in-place update）    | 中（看改什麼，改 tag 低風險、改 instance type 可能重啟） |
| `-/+` | 先刪後建（forces replacement） | 高（stateful 資源如 RDS 代表資料遺失）                   |
| `-`   | 刪除資源                       | 高（不可逆）                                             |

review plan 時最需要警惕的是 `-/+`（forces replacement）——看起來只是改一個屬性，但某些屬性的修改會觸發資源重建（例如 RDS 的 `identifier` 改名）。

plan 與 apply 之間可能有時間差。如果 plan 之後、apply 之前有人手動改了雲端資源，apply 時的實際行為可能跟 plan 預期的不同。多數團隊在 apply 階段會重跑一次 plan 並要求結果一致。

## 鄰卡

- [State](/infra/knowledge-cards/state/)
- [Drift](/infra/knowledge-cards/drift/)
- [IaC](/infra/knowledge-cards/iac/)
