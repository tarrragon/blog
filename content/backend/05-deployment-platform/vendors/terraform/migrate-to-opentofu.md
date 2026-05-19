---
title: "Terraform → OpenTofu：HCL 跟 state file 級 drop-in、CI runner 切 binary 完成"
date: 2026-05-19
description: "OpenTofu 是 Terraform 在 BSL license 後的 fork、Terraform 1.5.x baseline 完全相容（HCL / state / provider）；本文是 Type B drop-in migration 的標準形態 — 用 code-led HCL / state diff sample 開頭、5 個 production 踩雷（provider version drift / state lock 微差 / Terraform Cloud feature 不支援 / CI binary name 假設 / registry routing）"
weight: 11
tags: ["backend", "deployment-platform", "terraform", "opentofu", "migration", "drop-in", "type-b"]
---

> 本文是跨 vendor migration playbook、cross-link [Terraform](/backend/05-deployment-platform/vendors/terraform/)（source）跟 OpenTofu（target）。Type B drop-in migration 標準形態、跑 [migration-playbook-methodology 6 維 audit](/posts/migration-playbook-methodology/) 後對映 *6 維皆 Low → Type B drop-in*；本文驗證 skill 的 Type B anatomy 在 IaC 領域成立。

## HCL / state file / provider 三層 diff sample

跟前批 [Redis → DragonflyDB](/backend/02-cache-redis/vendors/redis/migrate-to-dragonflydb/) 同為 Type B drop-in、本文用 code-led entry — 直接給 3 種 diff sample 證明「真 drop-in」：

```hcl
# 1. HCL syntax: 完全相同 (Terraform 1.5.x baseline)
resource "aws_s3_bucket" "logs" {
  bucket = "myapp-logs"
  tags = {
    Env = "production"
  }
}
# 兩家 binary 都接受、執行結果一致
```

```bash
# 2. State file: 完全相同 schema
$ cat terraform.tfstate | jq '.version, .terraform_version'
4
"1.5.7"

# 切 OpenTofu 後 re-init、state 保留
$ tofu init
$ cat terraform.tfstate | jq '.version, .terraform_version'
4
"1.6.0"  # tool version 標記變、其他不變
```

```hcl
# 3. Provider: registry 路徑唯一明顯差異
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"     # 兩家共用 source 字串
      version = "~> 5.0"
    }
  }
}
# Terraform 從 registry.terraform.io 拉
# OpenTofu 預設從 registry.opentofu.org 拉 (fallback 到 terraform registry)
```

3 層 diff sample 顯示：HCL / state schema / 主流 provider 配置完全相容；唯一明顯差異在 *registry routing*。

跑 [6 維 diff dimension audit](/posts/migration-playbook-methodology/)：

| 維度               | 評估                                              | 等級 |
| ------------------ | ------------------------------------------------- | ---- |
| Schema / API       | HCL 完全相容、CLI command 對映 (terraform → tofu) | Low  |
| Operational model  | 同 workflow (init / plan / apply)                 | Low  |
| Paradigm           | 同 IaC declarative                                | Low  |
| Components         | 同 single binary                                  | Low  |
| Application change | 無（不是 application、是 infrastructure tool）    | Low  |
| Data topology      | 同 single state file backend                      | Low  |

6 維皆 Low → Type B drop-in。

## 為什麼遷：license / governance / community 三條 driver

跟前批 [Redis → DragonflyDB](/backend/02-cache-redis/vendors/redis/migrate-to-dragonflydb/) 不同（cost / performance driver）、Terraform → OpenTofu 主要 driver 在 governance：

| Driver                  | 觸發場景                                                                                         |
| ----------------------- | ------------------------------------------------------------------------------------------------ |
| **License**             | Terraform 在 2023-08 改 BSL（Business Source License）、商業使用限制；OpenTofu 維持 MPL 2.0 開源 |
| **Vendor neutrality**   | 多雲 / 多客戶情境想避免 HashiCorp lock-in、用 Linux Foundation 治理的 OpenTofu                   |
| **Community / feature** | OpenTofu 1.6+ 加 state encryption、跟 Terraform 商業版差異化、社群驅動 feature                   |

反向 driver（OpenTofu → Terraform）：

- Terraform Cloud / Enterprise 特定 feature 依賴（policy as code 用 Sentinel、跟 OpenTofu 自家 OPA 不對等）
- 既有 module 在 Terraform registry 維護、未同步 OpenTofu registry

## 相容性 audit

Pre-cutover 必跑：

| 議題                                                              | 處理方式                                                                                               |
| ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Terraform version pin（`required_version = ">= 1.5.0, < 1.6.0"`） | 改 `>= 1.6.0` 涵蓋 OpenTofu / 移除 upper bound                                                         |
| Provider 來源 (registry path)                                     | 主流 provider（aws / azurerm / gcp / k8s）都同源、自家 / 第三方 provider 確認 OpenTofu registry mirror |
| Terraform Cloud / Enterprise feature                              | Sentinel policy → OpenTofu OPA / Conftest；workspace API 對等性逐項 check                              |
| CLI binary name 在 CI pipeline                                    | `terraform plan` → `tofu plan`、或 alias `terraform=tofu` 保留兼容                                     |
| State backend (S3 / GCS / Azure / Consul / Terraform Cloud)       | S3/GCS/Azure 完全相容；Consul backend 兩家都支援；Terraform Cloud 走自家 remote backend、不直通        |
| Module source                                                     | git-based module 完全相容；registry module 確認 OpenTofu registry 有 mirror                            |

Audit output：列「100% drop-in」block + 「需處理」block；後者通常 < 5% 範圍。

## Step-by-step cutover

```bash
# 1. Install OpenTofu (跨 OS)
brew install opentofu                # macOS
snap install --classic opentofu      # Ubuntu
# https://opentofu.org/docs/intro/install/

# 2. 在 workspace 跑 tofu init
$ cd terraform-workspace/
$ tofu init -upgrade
# 升級 provider / module、re-init backend、保留 state

# 3. Plan diff（應該 = 0 changes）
$ tofu plan
# Plan: 0 to add, 0 to change, 0 to destroy.
# 如果有 diff、表示 provider version 不對齊、檢查 lock file

# 4. Apply（保險起見、staging 先跑）
$ tofu apply

# 5. CI / CD pipeline 切 binary
# Before
terraform init
terraform plan -out=tfplan
terraform apply tfplan

# After
tofu init
tofu plan -out=tfplan
tofu apply tfplan
# 或保留 terraform 字面、用 alias / symlink
```

整個 cutover 通常 < 1 天（單 workspace）；多 workspace organization 視規模 1-4 週逐個切。

## Production 故障演練

### Case 1：Provider version drift、staging plan 出現意外 diff

**徵兆**：`tofu plan` 顯示 100+ resource 有 in-place update、實際業務沒改任何 config。

**根因**：`.terraform.lock.hcl` 鎖的 provider version 在 Terraform / OpenTofu registry 不一致（同 version 但 binary checksum 微差）；OpenTofu 在 init 時拉新 checksum、視為「provider 變了」。

**修法**：

1. **預先對齊**：`tofu init -upgrade` 重建 lock file、把 OpenTofu 端 checksum 寫進去
2. **CI lockfile commit**：lock file 進版控、不同 binary 端跑前先 lockfile 對齊
3. **若 plan 仍有差異**：通常是 provider 內部 schema 對 nil 值處理不同、用 `lifecycle.ignore_changes` 暫忽略、後續逐項 fix

### Case 2：State file lock 機制微差

**徵兆**：兩個 CI pipeline 同時跑 `tofu apply`、其中一個應該 lock 拒絕、實際兩個都跑、production 端 race condition。

**根因**：Terraform DynamoDB lock 跟 OpenTofu lock 用相同 schema 但 lock_id 規則略不同；舊 lock entry 殘留時 OpenTofu 端解析失敗、視為「無 lock」繼續跑。

**修法**：

1. **DynamoDB lock table 手動清舊 entry**：cutover 期間先 `aws dynamodb delete-item` 清舊 lock
2. **單向流量切換**：cutover 期間 freeze 所有 CI、只一個 pipeline 跑、避免 race
3. **架構**：用 *fully replicated lock backend*（如 Consul）avoid backend-specific lock 怪異

### Case 3：Terraform Cloud workspace 不能直接搬

**徵兆**：team 已用 Terraform Cloud workspace 跑 100+ pipeline、想切 OpenTofu、發現 `terraform login` / workspace API / VCS integration 全 HashiCorp-specific。

**根因**：OpenTofu 沒對等 Terraform Cloud 服務；自家 backend 用 S3 + Atlantis / Spacelift / env0 等第三方 platform 對接、不是 1:1 替代。

**修法**：

1. **保留 Terraform Cloud 跑 production**（OpenTofu 不替代）、用 OpenTofu 跑 dev / sandbox
2. **遷出 Terraform Cloud**：state 遷 S3 + 用 Atlantis 跑 PR-based plan/apply（mature open source）
3. **評估 Spacelift / env0** 商業替代、支援 OpenTofu + 對等 workspace feature

### Case 4：CI pipeline 寫死 `terraform` binary name

**徵兆**：cutover 後 CI 跑 `terraform plan` 報「command not found」；team 100+ pipeline / GitHub Action / GitLab CI / shell script 都寫死 `terraform`。

**根因**：rollout 計畫沒 grep 全 organization 找 binary name 引用。

**修法**：

1. **Alias 策略**：CI image 內 `ln -s /usr/local/bin/tofu /usr/local/bin/terraform`、保留兼容 1-3 個月
2. **逐步改 `tofu`**：跟著 IaC team 修 pipeline file、target 100% 改完才 remove alias
3. **架構**：避免在 pipeline / script 寫死 binary、用 env variable `IAC_BINARY=${IAC_BINARY:-tofu}`

### Case 5：Registry routing、自家 module 拉不到

**徵兆**：cutover 後 `tofu init` 對自家 private module 報「not found」；同 module 在 Terraform 端跑得好好的。

**根因**：private module 註冊在 *Terraform Cloud private registry*、OpenTofu 預設不知道這個 endpoint；需要顯式設 registry source URL。

**修法**：

1. **顯式 source URL**：`source = "app.terraform.io/myorg/myapp/aws"` 改 git source 或自架 module registry
2. **架構**：用 git-based module source（`source = "git::ssh://git@github.com/myorg/myapp.git"`）、避開 registry lock-in
3. **長期**：自家 module 同時 publish 到 OpenTofu registry / Terraform Cloud / git、跨 tool 兼容

## Capacity / cost

| 維度                 | Terraform                         | OpenTofu                                     |
| -------------------- | --------------------------------- | -------------------------------------------- |
| Binary cost          | 免費 (community edition)          | 免費（永遠）                                 |
| Terraform Cloud cost | $20 / user / month、enterprise 高 | 無對等服務（用 Atlantis / Spacelift / env0） |
| State storage        | S3 / 自家 backend、低             | S3 / 自家 backend、低                        |
| Migration cost       | -                                 | 1-5 person-day（含 audit + cutover + CI 改） |
| License risk         | BSL 限制商業使用                  | MPL 2.0 開源、無 license risk                |
| Long-term governance | HashiCorp 單一供應商              | Linux Foundation + 多廠商貢獻                |

**判讀**：純 IaC 用戶切 OpenTofu 風險低 + 省 license 風險；重度依賴 Terraform Cloud feature 的 organization 保留或評估 commercial alternatives（Spacelift / env0）。

## 整合 / 下一步

### 跟 [Atlantis / Spacelift / env0](https://www.runatlantis.io/) 整合

OpenTofu 沒對等 Terraform Cloud、需要 third-party orchestrator：

- **Atlantis**：自架、開源、輕量、適合中小型 team
- **Spacelift**：SaaS、policy as code、支援 OpenTofu first-class
- **env0**：SaaS、cost estimation、workflow 完整

### 跟 [Terragrunt](https://terragrunt.gruntwork.io/) 整合

Terragrunt（OpenTofu / Terraform 共用 wrapper）已支援 OpenTofu 1.6+；多環境配置抽象保留、底層 binary 切換無感。

### 反向 migration（OpenTofu → Terraform）

罕見、通常是 organization 走商業合約綁 HashiCorp Enterprise 才會做；流程鏡像對稱、注意 OpenTofu 1.6+ 自家 feature（state encryption / provider for_each）在 Terraform 端可能缺。

### 下一步議題

- **State encryption（OpenTofu 1.7+）**：sensitive state 加密、Terraform 商業版才有對等 feature
- **跨 IaC tool（Pulumi / CDK）**：Pulumi / AWS CDK 是不同 paradigm（imperative）、不在本 migration scope
- **Provider ecosystem 長期分裂**：兩家 registry 自我演化、需要 quarterly review provider compat

## 相關連結

- Source vendor：[Terraform](/backend/05-deployment-platform/vendors/terraform/)
- 平行 migration playbook（Type B）：[Redis → DragonflyDB](/backend/02-cache-redis/vendors/redis/migrate-to-dragonflydb/)
- Methodology：[Migration playbook methodology](/posts/migration-playbook-methodology/) / [#127 Process content 結構由最大差異維度決定](/report/content-structure-by-max-diff-dimension/)
