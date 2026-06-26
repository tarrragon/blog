---
title: "斷網環境的 IaC"
date: 2026-06-26
description: "Terraform provider mirror、離線 plugin cache、本地 state backend、沒有雲端時的 plan/apply 流程與內網 CI"
weight: 2
tags: ["infra", "air-gapped", "iac", "terraform"]
---

Terraform 在連網環境執行 `init` 時會自動從 HashiCorp 的 registry 下載 provider plugin 和 module。斷網環境沒有這個路徑——provider、module、[state](/infra/knowledge-cards/state/) backend 全部要用離線替代。[IaC](/infra/knowledge-cards/iac/) 的核心價值（宣告式描述 + state 追蹤 + [plan 預覽](/infra/knowledge-cards/terraform-plan-apply/)）不因斷網而改變，改變的只是依賴的取得方式和 state 的存放位置。

## Provider 離線管理

### Provider Mirror

Terraform 的 `providers mirror` 指令在有網路的環境把指定 provider 的二進位檔下載到本地目錄，產出符合 filesystem mirror 結構的檔案：

```bash
# 在有網路的工作站執行
mkdir -p /path/to/mirror
terraform providers mirror -platform=linux_amd64 /path/to/mirror

# mirror 目錄結構
# /path/to/mirror/
# └── registry.terraform.io/
#     └── hashicorp/
#         └── aws/
#             └── 5.50.0/
#                 └── terraform-provider-aws_5.50.0_linux_amd64.zip
```

把整個 mirror 目錄搬進隔離網路後，在 Terraform 設定裡指定 filesystem mirror：

```hcl
# ~/.terraformrc 或 terraform.rc（Windows）
provider_installation {
  filesystem_mirror {
    path    = "/opt/terraform/providers"
    include = ["registry.terraform.io/*/*"]
  }
  direct {
    exclude = ["registry.terraform.io/*/*"]
  }
}
```

`direct` 區塊的 `exclude` 確保 Terraform 不會嘗試連網下載——如果 mirror 裡沒有某個 provider，init 會直接報錯而非 hang 在網路連線。

### Plugin Cache

替代 mirror 的另一個做法是 plugin cache directory。在有網路的環境跑過 `init` 後，`.terraform/providers/` 裡會有已下載的 plugin。把這整個目錄搬進隔離網路，用 `TF_PLUGIN_CACHE_DIR` 環境變數指向它：

```bash
export TF_PLUGIN_CACHE_DIR="/opt/terraform/plugin-cache"
terraform init
```

mirror 跟 plugin cache 的差別：mirror 是正式的離線分發機制（有版本結構、支援多平台）、plugin cache 是快取機制（省重複下載、但目錄結構跟 mirror 不同）。長期運作用 mirror，臨時驗證用 cache。

### Provider 版本鎖定

斷網環境的 provider 版本管理比連網更嚴格——升級一個 provider 代表要重新搬運整個 provider binary。在 `versions.tf` 裡鎖定精確版本（`= 5.50.0` 而非 `~> 5.50`），避免 `init` 期待一個 mirror 裡沒有的版本：

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 5.50.0"
    }
  }
}
```

## Module 離線來源

連網環境的 module source 常指向 Terraform Registry 或 GitHub：`source = "terraform-aws-modules/vpc/aws"`。斷網環境要改成本地路徑或內部 git server。

### 本地路徑

最簡單——module 放在同一個 repo 或共用檔案系統的目錄裡：

```hcl
module "network" {
  source = "../../modules/network"
}
```

### 內部 Git Server

如果有架 Gitea 或 GitLab CE（見[斷網通用原則](/infra/air-gapped/air-gapped-principles/)），module 可以指向內部的 git repo：

```hcl
module "network" {
  source = "git::http://gitea.internal/infra/modules.git//network?ref=v1.2.0"
}
```

`ref=v1.2.0` 鎖定版本。內部 git server 的 module repo 用 git bundle 從外部搬運更新。

## State Backend：沒有 S3 時的替代

連網環境的 state 通常放 S3 + DynamoDB lock。斷網環境如果沒有 AWS（地端機房或隔離網路），state backend 的替代選項：

| Backend              | 適用情境              | Lock 機制                  |
| -------------------- | --------------------- | -------------------------- |
| 本地檔案 + 共用磁碟  | 小團隊、單人操作      | 無（靠紀律避免並行 apply） |
| Consul               | 內網有 Consul cluster | 內建 lock                  |
| PostgreSQL           | 內網有 PostgreSQL     | 內建 lock                  |
| GitLab managed state | 內網有 GitLab CE      | 內建 lock                  |
| HTTP backend         | 自建簡易 API          | 自建 lock                  |

最常見的組合是 **PostgreSQL backend**——多數環境已經有 PostgreSQL，不需要額外裝服務：

```hcl
terraform {
  backend "pg" {
    conn_str = "postgres://terraform:password@db.internal/terraform_state?sslmode=disable"
  }
}
```

PostgreSQL backend 的 lock 機制用 PostgreSQL 的 advisory lock，多人同時 apply 時第二個人會被擋住。

state 的備份紀律不變——定期 `terraform state pull > backup.json`，backup 存在版本控制或另一台機器上。

## Plan / Apply 流程

斷網不影響 plan 和 apply 的執行——它們操作的是本地 provider 和目標基礎設施（地端伺服器、內部雲、VMware vSphere 等）。影響的是 provider 初始化和 module 取得，這些在前面幾節已處理。

### 沒有雲端 API 的情境

如果基礎設施不是雲端（地端 VMware、OpenStack、裸機），Terraform 有對應的 provider：

- VMware vSphere：`hashicorp/vsphere`
- OpenStack：`terraform-provider-openstack/openstack`
- Proxmox：`telmate/proxmox`（社群維護）
- 裸機管理：用 `null_resource` + `local-exec` 呼叫 Ansible 或 shell script

provider 的離線管理方式相同——mirror 或 plugin cache。

### Plan 輸出的離線 Review

沒有 GitHub PR 的環境，plan 輸出用檔案分享 review：

```bash
# 產出 plan 並存成可讀格式
terraform plan -out=plan.tfplan
terraform show plan.tfplan > plan-review-$(date +%Y%m%d).txt

# 把 review 檔放到內部共用位置供 reviewer 閱讀
cp plan-review-*.txt /shared/reviews/
```

reviewer 讀完後以 email、內部 chat、或直接在 review 檔旁邊放一個 `approved-by-alice-20260626.txt` 標記核准。不優雅但可追溯。

## 內網 CI/CD

斷網環境的 CI/CD 用自架的 CI server：

| 工具                       | 特性                                 | 適用規模                 |
| -------------------------- | ------------------------------------ | ------------------------ |
| GitLab CE + Runner         | 完整的 git + CI + review，功能最豐富 | 中大團隊                 |
| Gitea + Drone / Woodpecker | 輕量 git + 輕量 CI                   | 小團隊                   |
| Jenkins                    | 老牌 CI、plugin 生態豐富             | 任何規模（但維護成本高） |

CI server 本身也需要離線安裝——GitLab CE 有 offline 安裝指南（`.deb` / `.rpm` 包）、Gitea 是單一二進位。CI runner 執行 Terraform 時使用內部的 provider mirror 和 module source。

CI workflow 的離線版本跟連網版本結構相同（init → fmt → validate → plan → review → apply），差別在 init 用 `-plugin-dir` 而非連網下載。

時程參考：內網 CI server 的初次建置（含 git server + CI runner + Terraform 離線環境）約需 3-5 天。之後的維護主要是 provider 版本更新的搬運（每次 1-2 小時）。

## 跨分類引用

- → [斷網環境的通用原則](/infra/air-gapped/air-gapped-principles/)：provider 和 module 的搬運走 content ferry 模式
- → [模組一：最小可行 IaC](/infra/01-minimal-iac/)：連網環境的 IaC 選型和 state 管理
- → [模組七：infra 走 PR 流程](/infra/07-infra-as-pr/)：連網環境的 CI pipeline 設定
