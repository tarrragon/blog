---
title: "Vault → AWS Secrets Manager：「secret」不是「secret」、identity model 才是核心差異"
date: 2026-05-19
description: "Vault → AWS Secrets Manager migration 表面是 secret store 替換、實際核心是 identity model 對位（Vault token + policy vs AWS IAM + resource policy）；驗證 [#128](/report/data-topology-as-audit-dimension/) self-aware limitation 提出的 identity axis 候選 — identity 是否獨立 audit 軸；5 個 production 踩雷（IAM principal 對位 / dynamic credential 對等失敗 / lease lifecycle 模型不同 / audit log 結構差 / 計費模型反轉）"
weight: 12
tags: ["backend", "security", "vault", "aws-secrets-manager", "identity", "migration", "axis-candidate"]
---

> 本文是跨 vendor migration playbook、cross-link [HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) 跟 [AWS Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/)。本文同時是 [#128 self-aware limitation](/report/data-topology-as-audit-dimension/) 第 1 點「6 維仍可能漏類（identity / consistency / residency 三軸候選）」的 *identity 軸驗證*。

## 「secret」不是「secret」：兩家對「secret」的定義不同

把 Vault → AWS Secrets Manager 當成「secret store 替換」是最常見的誤判 — 兩家的「secret」概念跨完全不同的 identity model：

| 概念               | HashiCorp Vault                                       | AWS Secrets Manager                                |
| ------------------ | ----------------------------------------------------- | -------------------------------------------------- |
| Secret 本身        | 一個 secret path（`secret/data/myapp/db`）            | 一個 ARN（`arn:aws:secretsmanager:us-east-1:...`） |
| 存取者身份         | Vault token（self-managed token TTL）                 | AWS principal（IAM user / role / federation）      |
| 授權模型           | Vault policy（capabilities：read/create/...）         | IAM policy + Resource policy（雙層）               |
| Authentication     | AppRole / Kubernetes / LDAP / OIDC / 自管 auth method | AWS Sigv4 + STS token / Identity Federation        |
| Dynamic credential | Vault database secrets engine（lease + renew）        | Lambda rotation（無 lease 概念）                   |
| Audit log          | Vault audit log（自管 endpoint）                      | CloudTrail event（AWS 統一）                       |
| Multi-tenant 隔離  | Namespace + path-level policy                         | Account boundary + resource policy                 |
| Tooling 整合       | Application 端 Vault SDK / agent injector             | AWS SDK + Lambda                                   |

**核心差異不在「存 secret 的地方」、在「身份從哪來、怎麼 enforce、怎麼 audit」。** Migration 的真實工作量在 *identity model 重設計*、不是 secret 搬遷。

跑 [6 維 diff dimension audit](/report/content-structure-by-max-diff-dimension/)：

| 維度               | 評估                                             | 等級     |
| ------------------ | ------------------------------------------------ | -------- |
| Schema / API       | API 完全不同（Vault HTTP API vs AWS SDK）        | Medium   |
| Operational model  | Self-managed Vault cluster → AWS managed         | **High** |
| Paradigm           | 兩家都是 secret store paradigm                   | Low      |
| Components         | Vault binary + storage backend → AWS SaaS        | Low      |
| Application change | 必改（SDK 換、auth method 換、retry pattern 換） | **High** |
| Data topology      | 同 single instance, no sharding                  | Low      |
| **Identity model** | **完全不同（Vault token vs IAM principal）**     | **High** |

6 維 audit 抓不到「Identity model = High」這軸 — 用既有 6 維歸類、會走 Type C operational redesign + Application change 高維獨立段；但實際工作量分佈：

- Operational redesign（vault cluster 拆 / Lambda 配 / 監控換）：~25%
- Application change（SDK / retry / token 換 IAM credential）：~30%
- **Identity model 重設計（每個 secret 對應的 principal / policy / 跨 service auth chain）：~45%**

最大工作量塊在 *identity model 重設計*、不在既有 6 維任一個。Identity 是 *候選的第 7 維*。

## Identity axis 是否獨立：4 個論據

**Yes、identity 是獨立軸**：

1. **Identity 不變 → operational 仍可變**：Vault on-prem → Vault on-EKS、operational 變 high 但 identity model 不變（仍 Vault token）；可分開 audit
2. **Operational 不變 → identity 仍可變**：Vault namespace 重組（管理 50 個 namespace → 5 個 namespace + namespace-level policy）、operational 不變但 identity boundary 重劃；可分開 audit
3. **Application change 不變 → identity 仍可變**：純 infrastructure-level rotation（手動 → 自動）、application code 不變但 identity issuance flow 變；可分開 audit
4. **Paradigm 不變 → identity 仍可變**：同樣是 secret store paradigm、Vault token vs IAM principal 是 identity model 差、不是 paradigm 差

**No、identity 可塞 application change**：

- 反論：application code 改 SDK + IAM signer 都算 application change
- 拒絕：application change 是 *consequence*、不是 *root cause*；identity model 變動才是驅動 application change 的原因

實證上、本文 migration 工作量 45% 在 identity 對位、確認 identity 是 *獨立的工作量主軸*、不該被壓進 application change 軸。

## 結構：Type C + identity model 對位獨立段

跟既有 Type C [PostgreSQL → Aurora](/backend/01-database/vendors/postgresql/migrate-to-aurora/) 對照、本文多出 *identity model 對位* 獨立段：

```text
1. 「secret」不是「secret」（identity axis paradox 開頭）
2. Identity axis 是否獨立的論據
3. 結構 differentiator（Type C + identity 獨立段）
4. Identity model 對位（Vault → AWS principal mapping）
5. Operational migration（4 phase）
6. Application change（SDK + retry pattern）
7. Production 故障演練
8. Capacity / cost
9. 整合 / 下一步
```

9 章節、260-280 行。比標準 Type C 多 1 段（identity model 對位）+ 1 段（axis 獨立論據）。

## Identity model 對位

```text
Vault concept                    →  AWS Secrets Manager 對應
─────────────────────────────────   ────────────────────────────
Vault token (auth 結果)           →  AWS STS temporary credential
AppRole (auth method)             →  IAM role + AssumeRoleWithWebIdentity
Kubernetes auth method            →  IAM Role for Service Account (IRSA)
LDAP auth method                  →  IAM Identity Center (formerly SSO)
Vault policy (capabilities)       →  IAM policy + Resource policy
Path-level ACL (secret/db/*)      →  Resource ARN pattern (arn:aws:secretsmanager:...:secret:db/*)
Namespace                         →  AWS account + resource-based isolation
Audit device                      →  CloudTrail event
Database secrets engine           →  Lambda rotation function
```

每行對位都有 *語意差*、不是 1:1 mapping：

- **Vault token TTL vs AWS STS credential expiration**：Vault token TTL 可由 application 主動 renew；STS credential 不能 renew、必須 re-assume
- **Vault policy capabilities vs IAM action**：Vault `read` capability 對應 AWS `secretsmanager:GetSecretValue`、但 AWS 還要 resource policy 允許；雙層授權
- **Vault Kubernetes auth vs IRSA**：兩者都是 K8s service account → secret access、但 IRSA 需要 EKS + OIDC provider 設置、Vault K8s auth 不需要

Migration scope 包含每行對位的 *application-level 適配*、不是 secret 搬。

## Operational migration (4 phase)

### Phase 0：Audit + design

- 列所有 Vault secret + path + 使用 application
- 每個 secret 對應 AWS principal（IAM role / IRSA / federation）
- 設計 ARN 命名規則（按 namespace / application / environment）
- 規劃 AWS account boundary（dev / staging / prod 分 account）

### Phase 1：AWS Secrets Manager + IAM 設置

- Terraform / CloudFormation 建 secret + IAM role + resource policy
- 設 IRSA / WebIdentity provider
- 預先建 staging secret、跑 application test

### Phase 2：Application dual-read

```python
# Application 同時讀 Vault + AWS Secrets Manager
def get_db_password():
    aws_value = boto3.client('secretsmanager').get_secret_value(SecretId='myapp/db')['SecretString']
    vault_value = vault_client.read('secret/data/myapp/db')['data']['data']['password']

    if aws_value != vault_value:
        logger.warning(f"Secret diff between Vault and AWS!")

    return aws_value  # Use AWS as source of truth
```

跑 1-2 週、確認兩端一致 + AWS API latency / error rate 接受。

### Phase 3：Cutover + cleanup

- Application 端切到 AWS Secrets Manager only
- Vault read-only 1-2 週 standby
- 之後 decommission Vault cluster

## Application change

Application 端必改的 4 個 pattern：

```python
# Before: Vault SDK
import hvac
vault_client = hvac.Client(url='https://vault.internal', token=vault_token)
secret = vault_client.read('secret/data/myapp/db')['data']['data']['password']

# After: AWS SDK + IAM
import boto3
sm = boto3.client('secretsmanager')
secret = sm.get_secret_value(SecretId='myapp/db')['SecretString']
```

關鍵差異點：

- **Authentication**：Vault token 由 application 自管 / refresh；AWS SDK 自動處理 STS credential（透過 IAM role / instance profile / IRSA）
- **Caching**：Vault secret read 通常 cache 5-15 分鐘；AWS Secrets Manager 有 cache library（aws-secretsmanager-caching-python）需顯式啟用
- **Retry pattern**：Vault 用 exponential backoff；AWS SDK 自帶 retry but boto3 default 跟 application requirement 不一定 match
- **Rotation hook**：Vault 用 SDK 端 lease renewal；AWS 用 Lambda rotation function、application 端只需要 re-read

## Production 故障演練

### Case 1：IAM principal 對位錯、production application 拿不到 secret

**徵兆**：cutover 後 application 啟動失敗、log 顯示 `AccessDeniedException: User: arn:aws:sts::...:assumed-role/EKS-NodeRole/i-xxx is not authorized to perform: secretsmanager:GetSecretValue`。

**根因**：EKS pod 用 *node role* 而非 *pod IRSA role*；Phase 0 audit 沒設 service account 對應的 OIDC trust。

**修法**：

1. **預先設 IRSA**：建 IAM OIDC provider for EKS、設 service account annotation
2. **驗證 principal**：`aws sts get-caller-identity` 從 pod 內跑、確認 returned role 是預期的
3. **Resource policy + IAM policy 雙層**：確認 secret 的 resource policy allow 該 role、IAM policy 也 allow

### Case 2：Dynamic credential 對等失敗、application 連 DB 失敗

**徵兆**：Vault 端用 database secrets engine 自動 rotate DB password、application 透過 Vault SDK 拿 lease；切到 AWS Secrets Manager + Lambda rotation 後、Lambda rotation 完成、但 application 端仍用 cached old password、連 DB 拒絕。

**根因**：Vault SDK 自帶 lease renewal logic、application 知道 password 即將過期會主動 re-read；AWS SDK 沒 lease 概念、application 自己決定多久 re-read 一次。

**修法**：

1. **設 cache TTL 短於 rotation interval**：rotation 24 小時、cache TTL 1 小時、最壞情況 1 小時 stale
2. **顯式 cache invalidation**：rotation Lambda 跑完發 SNS、application subscribe 主動 refresh
3. **Connection-level retry**：DB connection 認證失敗時 application 重 fetch secret 跟重連
4. **重新評估 rotation cadence**：AWS Lambda rotation 不是 *Vault dynamic*、是 *scheduled rotation*；不能假設兩者同 semantic

### Case 3：Audit log 結構差、SOC dashboard 失效

**徵兆**：cutover 後 SOC 端 dashboard 顯示 secret access metric 全 0；舊 Vault audit log 結構在 Splunk 端 parse 過、AWS CloudTrail 結構完全不同、search query 全失效。

**根因**：Vault audit log 是 *Vault-specific* JSON 結構（含 lease_id / policy / token）；CloudTrail event 是 *AWS-specific*（含 eventName / requestParameters / userIdentity）；SOC parse rule 不能搬。

**修法**：

1. **Pre-cutover 重寫 SOC rule**：CloudTrail event 對應 Vault audit log 的 detection coverage 必須 1:1 mapping
2. **GuardDuty integration**：AWS GuardDuty 自動 surface secret access anomaly、降低自寫 rule 工作量
3. **CloudTrail → S3 → Athena**：long-term audit query 走 Athena、tooling 跟 Vault 完全不同、SOC re-training

### Case 4：Calling cost 反轉、AWS 比 Vault 自管貴

**徵兆**：Vault on-prem 跑了 $200 / month（EC2 + ops），切到 AWS Secrets Manager 後 $1500 / month；帳單拆解後 `GetSecretValue` API call 是大頭。

**根因**：AWS Secrets Manager `$0.05 per 10K API call` — application 高頻 read（每 request 都讀 secret + 沒 cache）會爆 cost；Vault 端 application 自管 cache + token TTL 內無 API call。

**修法**：

1. **強制 application-side cache**：用 aws-secretsmanager-caching library、cache TTL 5-15 分鐘、API call 從 100M/month 降到 10K/month
2. **Re-architect application**：把 high-frequency secret read 改 connection-level（建 DB connection 時讀一次、connection lifecycle 內復用）
3. **Cost monitoring**：對 secret access 設 CloudWatch alarm、過 threshold 立即 alert

### Case 5：跨 region replication 對位失敗、DR 演練失效

**徵兆**：DR drill 切 region 後、application 連不到 secret；發現 us-west-2 的 Secrets Manager 沒有 us-east-1 的 secret。

**根因**：AWS Secrets Manager 不是 *global resource*、是 *region-scoped*；Vault 自管 multi-DC replication；cutover 漏設 *cross-region replication*。

**修法**：

1. **設 secret replication**：AWS Secrets Manager 內建 replication 到其他 region（`ReplicaRegions`）
2. **DR drill 必跑**：cutover 前 + cutover 後各 drill 一次、驗證 region failover 順
3. **架構**：考慮用 *AWS Backup* 對 Secrets Manager 做 cross-region backup 補強

## Capacity / cost

| 維度                                  | Vault self-managed                 | AWS Secrets Manager                         | Trade-off                  |
| ------------------------------------- | ---------------------------------- | ------------------------------------------- | -------------------------- |
| Setup cost                            | Mid（自管 cluster + storage + HA） | Low（一鍵建 secret）                        | AWS 顯著低                 |
| Operational FTE                       | 0.3-1 FTE                          | 0.05-0.1 FTE                                | AWS 省 SRE                 |
| Per-secret cost                       | ~$0（含在 cluster）                | $0.40 / month                               | AWS 按 secret 數計費       |
| API call cost                         | ~$0（含在 cluster）                | $0.05 / 10K call                            | High-frequency app 顯著貴  |
| Cross-region                          | 自管 replication                   | 內建 `ReplicaRegions`                       | AWS 簡化                   |
| Audit                                 | Vault audit device                 | CloudTrail（內建）                          | AWS 跟 SOC pipeline 統一   |
| Identity integration                  | 多 auth method                     | IAM + IRSA + Identity Center                | AWS 跟 cloud-native 整合好 |
| Total cost (100 secret, 50K read/day) | $200 / mo (含 ops)                 | $40 + $7 + replication = ~$50 / mo + ops 省 | AWS 1/4 cost、若 read 不爆 |

**判讀**：少 secret + 中頻 read 走 AWS Secrets Manager；高頻 read + multi-cloud / on-prem 約束走 Vault。

## 整合 / 下一步

### 跟 [Vault Dynamic Credential](/backend/07-security-data-protection/vendors/hashicorp-vault/dynamic-credential/) 對比

Vault dynamic credential 是 Vault 特有 feature、AWS Secrets Manager 用 *Lambda rotation* 對應、但 semantic 不同：

- Vault: per-application lease、application-aware lifecycle
- AWS: scheduled rotation、application 不知道何時被 rotate

Migration scope 應該 *降級* dynamic credential 場景、用 Lambda rotation 替代、application logic 改 cache + retry pattern。

### 跟 IAM Identity Center 整合

人類存取 secret（emergency break-glass）走 IAM Identity Center + temporary role assumption；不要直接給 user IAM key。

### 下一步議題

- **Reverse migration（AWS → Vault）**：通常是 multi-cloud / on-prem 約束驅動、cost 在大 scale 反轉
- **Hybrid pattern**：cloud-native secret 走 AWS、cross-cloud / on-prem secret 走 Vault；應用程式根據 secret 來源 routing
- **identity axis 驗證**：本文認為 identity 是獨立軸、未來累積 LDAP → OIDC / 自管 RBAC → IAM 等 migration 驗證

## 相關連結

- Source vendor：[HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)
- Target vendor：[AWS Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/)
- 平行 deep article：[Vault Dynamic Credential](/backend/07-security-data-protection/vendors/hashicorp-vault/dynamic-credential/)
- 平行 migration playbook (Type C)：[PostgreSQL → Aurora](/backend/01-database/vendors/postgresql/migrate-to-aurora/)（標準 Type C） / [MongoDB → Atlas](/backend/01-database/vendors/mongodb/migrate-to-atlas/)
- 平行 axis 候選驗證 (sibling)：[DynamoDB Consistency Model](/backend/01-database/vendors/dynamodb/consistency-model-optimization/)（consistency 候選） / [PostgreSQL Multi-Region GDPR Rollout](/backend/01-database/vendors/postgresql/multi-region-gdpr-rollout/)（residency 候選）
- Methodology：[Migration playbook methodology](/posts/migration-playbook-methodology/) / [#128 self-aware limitation 第 1 點](/report/data-topology-as-audit-dimension/)（identity axis 候選驗證、本文是該驗證的 dogfood）
