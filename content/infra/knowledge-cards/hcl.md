---
title: "HCL"
date: 2026-06-26
description: "Terraform 使用的宣告式設定語言，用 resource block 描述基礎設施的目標狀態，工具負責收斂差異"
weight: 39
tags: ["infra", "knowledge-cards"]
---

HCL（HashiCorp Configuration Language）是 [Terraform](/infra/knowledge-cards/terraform-plan-apply/) 和 OpenTofu 使用的設定語言。它用宣告式的 resource block 描述「環境應該長什麼樣」，由工具負責比對現況與描述、算出差異再套用。寫 HCL 的人描述目標狀態，不描述達到目標的步驟。

## 概念位置

HCL 是 infra 系列中 [IaC](/infra/knowledge-cards/iac/) 程式碼的語言層。IaC 卡講的是「用程式碼管理基礎設施」的概念，HCL 是這個概念落地時最常用的語言。模組一到八的所有 HCL 範例都用這個語言寫成。

## 可觀察訊號

需要理解 HCL 的情境包括：第一次打開一份 `.tf` 檔案、要讀懂 Terraform 的 plan 輸出、要修改或新增一個 resource 定義、或要 review 別人的 infra PR。

## 設計責任

HCL 的基本結構：

```hcl
resource "aws_s3_bucket" "example" {
  bucket = "my-bucket"
  tags   = { env = "prod" }
}
```

- `resource`：宣告一個雲端資源
- `"aws_s3_bucket"`：資源類型（由 provider 決定）
- `"example"`：這個資源在程式碼裡的名稱（用來引用）
- `{}`：這個資源的屬性

跟其他格式的差別：

| 格式                | 特性                       | 適合場景                          |
| ------------------- | -------------------------- | --------------------------------- |
| JSON / YAML         | 純資料格式、沒有邏輯       | 設定值、資料交換                  |
| HCL                 | 支援變數、函式、條件、迴圈 | 基礎設施描述                      |
| TypeScript / Python | 通用程式語言、完整邏輯     | 複雜的 infra 抽象（CDK / Pulumi） |

HCL 的定位在 JSON 和通用語言之間——比 JSON 有表達力（能做迴圈和條件）、比通用語言好 review（diff 直觀、不需要在腦中「執行」程式碼才知道結果）。

## 鄰卡

- [IaC](/infra/knowledge-cards/iac/)
- [State](/infra/knowledge-cards/state/)
