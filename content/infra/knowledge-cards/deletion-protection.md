---
title: "Deletion Protection"
date: 2026-06-26
description: "雲端平台提供的防誤刪機制，開啟後刪除操作需要先顯式關閉保護才能執行"
weight: 19
tags: ["infra", "knowledge-cards"]
---

Deletion protection 是雲端平台在資源層級提供的防護機制：開啟後，任何刪除該資源的操作（Console 點按、CLI 指令、[IaC](/infra/knowledge-cards/iac/) 的 destroy）都會被擋下，必須先顯式關閉保護才能執行刪除。這個額外步驟的目的是防止手滑、批次操作誤傷、以及 Terraform plan 裡意外出現的 destroy。

## 概念位置

Deletion protection 是 [stateful 資源保護](/infra/05-core-services/stateful-protection-dependency/)的第一道防線。運算節點可以隨時重建，資料一旦遺失通常無法重來——這條分界線決定了哪些資源該開保護。對 stateful 資源（資料庫、持久化儲存）來說，這是 day-1 該開的設定，不是「等穩定再開」的選項。

不同 AWS 服務的保護機制名稱不同但行為一致：

| 服務                               | 屬性名稱                      | 保護對象        |
| ---------------------------------- | ----------------------------- | --------------- |
| [RDS](/infra/knowledge-cards/rds/) | `deletion_protection`         | 資料庫 instance |
| EC2                                | `disable_api_termination`     | 運算 instance   |
| S3                                 | MFA delete                    | bucket 版本控制 |
| DynamoDB                           | `deletion_protection_enabled` | 表格            |

## 可觀察訊號

需要開啟 deletion protection 的訊號是資源承載了不可重建的狀態。判斷方式是問一個問題：「這個資源被刪除後，能不能在 10 分鐘內從程式碼或備份完整恢復？」不能的就該開。

`terraform plan` 輸出裡出現 `destroy` 或 `forces replacement`（`-/+`）時，deletion protection 是阻擋意外資料遺失的最後一道閘門。有保護的資源在 apply 時會報錯而非直接刪除，讓操作者有機會停下來確認。

## 設計責任

用 [IaC](/infra/knowledge-cards/iac/) 描述 stateful 資源時，把 deletion protection 寫進程式碼而非手動在 Console 開啟——這讓保護策略本身成為可審查、可追蹤的設定。同時搭配 `skip_final_snapshot = false`（RDS）確保刪除前自動做最後一份快照。

Deletion protection 擋的是刪除操作，不擋資料覆寫或邏輯損壞——一段錯誤的 UPDATE 不會被 deletion protection 攔截。資料層的完整防線還需要備份保留與時間點還原（PITR），跟 deletion protection 正交。

## 鄰卡

- [State](/infra/knowledge-cards/state/) — deletion protection 在 [state](/infra/knowledge-cards/state/) 裡記錄為資源屬性，plan 會顯示保護狀態
- [IaC](/infra/knowledge-cards/iac/) — 保護策略寫進 IaC 讓它可審查
