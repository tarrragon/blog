---
title: "checkov 與 tfsec 規則配置"
date: 2026-06-26
description: "靜態掃描工具的規則選擇策略、自訂規則、豁免管理、false positive 處理與 CI 整合，讓掃描從噪音來源變成可信的品質關卡"
weight: 3
tags: ["infra", "ci-cd", "checkov", "tfsec", "security"]
---

checkov 和 tfsec 安裝後直接跑，通常會產出幾十到幾百條命中。全部修完不切實際、全部忽略又失去價值。這篇處理的是怎麼從「裝了工具」走到「工具的產出可信且可操作」——規則選擇、嚴重度過濾、豁免管理、自訂規則、CI 整合，以及 false positive 的處理流程。

## 規則選擇策略

兩個工具的內建規則集都超過數百條，涵蓋從加密設定到命名慣例。全開跑會讓命中清單長到沒人看。規則選擇的判準是「這條規則命中後，團隊會不會真的去修」——答案是不會的規則，開著只是製造噪音。

### 分層啟用

把規則分成三層逐步啟用，而非一次全開：

| 層次   | 規則類型               | 範例                                             | 啟用時機        |
| ------ | ---------------------- | ------------------------------------------------ | --------------- |
| 地基層 | 資料外洩與權限失控     | S3 public access、SG 0.0.0.0/0、IAM wildcard     | day 1           |
| 營運層 | 加密與備份             | RDS encryption、EBS encryption、backup retention | IaC 覆蓋率 >50% |
| 規範層 | 命名、tagging、logging | 缺 tag、缺 log group、resource naming            | 治理成熟後      |

地基層是即使其他規則都關掉也要開的——S3 bucket 對外公開（`CKV_AWS_19`、`CKV_AWS_53`）和 security group 全開（`CKV_AWS_24`、`CKV_AWS_25`）這類規則命中就是真問題。營運層在 IaC 覆蓋率夠高時啟用，否則會掃到大量不在 IaC 管理內的資源。規範層等團隊有能力消化命中量再開。

### checkov 的規則過濾

```bash
# 只跑地基層規則
checkov -d . --check CKV_AWS_19,CKV_AWS_53,CKV_AWS_24,CKV_AWS_25,CKV_AWS_40,CKV_AWS_145

# 或者用 framework 過濾（只掃 Terraform）
checkov -d . --framework terraform --compact --quiet
```

checkov 支援 `--check`（白名單，只跑這些）和 `--skip-check`（黑名單，跳過這些）。初期用 `--check` 白名單比較可控——明確列出要跑的規則，而非從全集去扣。隨著團隊消化能力提升再擴大白名單。

### tfsec 的嚴重度過濾

```bash
# 只報 CRITICAL 和 HIGH
tfsec . --minimum-severity HIGH

# 排除特定規則
tfsec . --exclude aws-s3-specify-public-access-block
```

tfsec 的嚴重度分 CRITICAL / HIGH / MEDIUM / LOW。初期設 `--minimum-severity HIGH` 把低嚴重度的過濾掉，減少噪音量。降低閾值的時機是 HIGH 以上的命中清零後。

## 豁免管理

不是每個命中都是錯——對外的 ALB 在 port 443 開 `0.0.0.0/0` 是設計意圖、不是漏洞。豁免的重點是讓例外顯式化、有理由、可被 review。

### 行內豁免

```hcl
resource "aws_security_group_rule" "alb_https" {
  type        = "ingress"
  from_port   = 443
  to_port     = 443
  protocol    = "tcp"
  cidr_blocks = ["0.0.0.0/0"]
  #checkov:skip=CKV_AWS_24:ALB 的 HTTPS 入站需要對外開放
}
```

tfsec 的行內豁免：

```hcl
resource "aws_security_group_rule" "alb_https" {
  #tfsec:ignore:aws-ec2-no-public-ingress-sgr -- ALB HTTPS listener requires public access
  cidr_blocks = ["0.0.0.0/0"]
}
```

行內豁免的好處是理由跟程式碼在一起，review 時一眼可見。壞處是散落在各檔案裡，盤點所有豁免要 grep。

### 集中式豁免

checkov 支援 `.checkov.yaml` 集中管理豁免：

```yaml
# .checkov.yaml
skip-check:
  - CKV_AWS_24  # ALB public-facing SG rules
  - CKV_AWS_19  # Legacy S3 buckets pending migration
```

集中式的好處是一個地方看到所有豁免，適合全域性的例外（如「這批 legacy S3 bucket 還沒遷完、暫時跳過 public access 檢查」）。壞處是理由離程式碼太遠，三個月後沒人記得為什麼跳過。

### 豁免紀律

每個豁免都要寫理由（`--` 之後的文字）。沒有理由的豁免等於靜默跳過——review 時看不出是故意的還是為了讓 CI 過而隨手加的。定期（每季度）跑一次豁免盤點：

```bash
# 盤點所有 checkov 豁免
grep -rn "checkov:skip" --include="*.tf" .

# 盤點所有 tfsec 豁免
grep -rn "tfsec:ignore" --include="*.tf" .
```

每個命中問一句：當初跳過的原因還成立嗎？legacy 遷移完了嗎？臨時的例外變成永久的了嗎？

## 自訂規則

內建規則覆蓋通用安全實踐，但專案特有的規範（如「所有 RDS 必須有 `cost-center` tag」「所有 S3 bucket 名稱必須以公司前綴開頭」）需要自訂。

### checkov 自訂規則（Python）

```python
# custom_checks/require_cost_center_tag.py
from checkov.terraform.checks.resource.base_resource_check import BaseResourceCheck
from checkov.common.models.enums import CheckResult, CheckCategories

class CostCenterTagRequired(BaseResourceCheck):
    def __init__(self):
        name = "Ensure cost-center tag is present"
        id = "CUSTOM_001"
        supported_resources = ["aws_instance", "aws_db_instance", "aws_s3_bucket"]
        categories = [CheckCategories.GENERAL_SECURITY]
        super().__init__(name=name, id=id, categories=categories,
                         supported_resources=supported_resources)

    def scan_resource_conf(self, conf):
        tags = conf.get("tags", [{}])[0]
        if isinstance(tags, dict) and "cost-center" in tags:
            return CheckResult.PASSED
        return CheckResult.FAILED

check = CostCenterTagRequired()
```

```bash
# 跑自訂規則
checkov -d . --external-checks-dir ./custom_checks
```

### tfsec 自訂規則（YAML）

```yaml
# .tfsec/custom_rules.yaml
- id: CUSTOM_001
  description: S3 bucket name must start with company prefix
  impact: Non-standard naming breaks cross-account policies
  resolution: Add company prefix to bucket name
  requiredTypes:
    - resource
  requiredLabels:
    - aws_s3_bucket
  severity: MEDIUM
  matchSpec:
    name: bucket
    action: startsWith
    value: acme-
```

自訂規則的數量保持精簡——每條規則都是維護成本。只有「違反後會在後續流程造成問題」的規範值得寫成自動化規則，純粹的風格偏好留給 review 時口頭提醒。

## CI 整合

把掃描接進 CI 的目標是「PR 合併前就攔下問題」，而非 apply 之後才發現。

### GitHub Actions 範例

```yaml
jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run checkov
        uses: bridgecrewio/checkov-action@v12
        with:
          directory: .
          check: CKV_AWS_19,CKV_AWS_53,CKV_AWS_24,CKV_AWS_25
          quiet: true
          compact: true
          soft_fail: false

      - name: Run tfsec
        uses: aquasecurity/tfsec-action@v1
        with:
          minimum_severity: HIGH
          soft_fail: false
```

`soft_fail: false` 讓掃描命中時 CI 失敗、阻擋合併。初期可以先設 `soft_fail: true`（掃描報告但不阻擋），讓團隊觀察命中量，確認規則集合理後再切成強制。

### 掃描結果回貼 PR

checkov 和 tfsec 的 GitHub Actions 都支援把結果以 PR comment 回貼。讓 reviewer 在 PR 頁面直接看到掃描結果，不用去翻 CI log。checkov-action 預設會回貼；tfsec-action 需要額外的 `github_token` 設定。

### 漸進式導入

```text
Week 1-2：soft_fail=true，觀察命中量和 false positive 率
Week 3：修完所有真問題，豁免所有合理的 false positive
Week 4：切 soft_fail=false，掃描變成強制 gate
```

這個節奏讓團隊在掃描變成強制之前就清理完存量，避免「一開 hard fail 所有 PR 都過不了」的窘境。

## False positive 處理

false positive 的處理有三條路，依復發頻率選：

| 路徑         | 適用情境               | 做法                             |
| ------------ | ---------------------- | -------------------------------- |
| 行內豁免     | 單一資源的合理例外     | 在該資源加 `checkov:skip` + 理由 |
| 全域跳過     | 整個規則不適用於此專案 | 加進 `.checkov.yaml` skip-check  |
| 自訂規則覆蓋 | 內建規則的判準不適合   | 寫自訂規則取代內建規則           |

最常見的 false positive 是 ALB 的 public-facing security group（設計就是要開 443）和開發環境的寬鬆設定（dev 允許、prod 不允許）。後者可以用 checkov 的 `--var-file` 搭配環境變數區分——dev 跑寬鬆規則集、prod 跑嚴格規則集。

處理 false positive 時要抵抗「加 skip 讓 CI 過」的捷徑衝動。每個 skip 都要問：這是設計意圖（ALB 要開放）還是技術債（dev 環境暫時放寬）？前者寫永久豁免加理由，後者寫臨時豁免加 TODO 和預計修復時間。

## 跨分類引用

- → [infra 走 PR 流程與自動化護欄](/infra/07-infra-as-pr/plan-review-apply-guardrails/)：掃描在 PR 流程裡的定位與 plan/apply 的關係
- → [Terraform CI Pipeline 設定](/infra/07-infra-as-pr/terraform-ci-pipeline-setup/)：掃描步驟怎麼嵌入完整的 CI workflow
- → [模組三：Security Group 稽核與清理](/infra/03-network-foundation/security-group-audit-cleanup/)：掃描命中 0.0.0.0/0 後的處理流程
