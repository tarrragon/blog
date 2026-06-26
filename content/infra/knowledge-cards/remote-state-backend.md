---
title: "Remote State Backend"
date: 2026-06-26
description: "把 Terraform state 從本地搬到團隊共享儲存的機制，同時滿足持久保存、並行鎖與敏感值保護"
weight: 17
tags: ["infra", "knowledge-cards"]
---

Remote state backend 是 IaC 工具用來存放 [state](/infra/knowledge-cards/state/) 的共享儲存機制。它要同時滿足三件事：持久保存（不會因為某台筆電故障而遺失）、防止並行寫入衝突（兩個人不能同時 apply）、以及保護敏感內容（state 內含資源的真實屬性，可能包含密碼或 key）。

## 概念位置

State 是 [IaC](/infra/knowledge-cards/iac/) 工具對現實的唯一記憶。把它放在本地檔案系統等於把整個基礎設施的記憶綁在一台機器上——換人接手、換台電腦、或兩人同時 apply，記憶就分裂了。Remote state backend 解決的是「讓 state 變成團隊共用的、有保護的事實來源」。

典型的自管組合是 S3（存放 state 檔、開 versioning 和加密）加上 DynamoDB（提供 apply 時的並行鎖）。託管服務（Terraform Cloud、Spacelift）把存放、鎖和加密包在一起，用月費換掉配置和維運負擔。

## 可觀察訊號

本地 state 的失敗訊號是：跑 `terraform plan` 時出現「想刪掉」明知存在的資源——通常代表本地 state 跟雲端實際狀態已經脫節。另一個訊號是兩個人同時跑 apply 但沒有任何鎖機制阻擋——結果是互相覆蓋對方的變更，state 進入不一致狀態。

Remote backend 設定後，如果 `terraform init` 提示 state 遷移確認，代表正在從本地搬到遠端——這是正確的一次性操作，但搬遷過程中不能有其他人在 apply。

## 設計責任

選擇 remote state backend 時要決定：自管還是託管（取決於團隊規模和維運餘裕）、state bucket 的加密與存取控制（誰能讀 state 等於誰能看到所有資源的敏感屬性）、versioning 是否開啟（是 state 回捲的唯一退路）、以及鎖表的設定（DynamoDB 的表名和 partition key）。

State 絕不能進 git——它含明文敏感值，推進版控等於把密碼寫進每個 clone 的歷史裡。Backend 設定本身（bucket name、region、鎖表名稱）寫在 HCL 裡進 git，state 檔本身只存在 backend 裡。

## 鄰卡

- [State](/infra/knowledge-cards/state/) — remote backend 存放的對象
- [Drift](/infra/knowledge-cards/drift/) — state 與現實不一致時的現象
- [IaC](/infra/knowledge-cards/iac/) — remote state backend 是 IaC 工具的基礎設施
