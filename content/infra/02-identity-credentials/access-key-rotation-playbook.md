---
title: "Access Key 輪替手冊"
date: 2026-06-26
description: "從 credential report 盤點散落的長期 access key，到逐把輪替、自動化輪替與 key age 監控的完整操作步驟"
weight: 4
tags: ["infra", "iam", "access-key", "rotation"]
---

長期 access key 的風險隨時間單調上升——每多存在一天，被複製到新地方的機率就多一分，而輪替的難度也跟著副本數量增長。輪替不是「發現外洩才做」的緊急動作，而是定期執行的維運操作。本篇是操作手冊，從盤點開始、逐步完成輪替、最後建立自動化。

## 盤點：帳號裡有哪些 key

第一步是拿到帳號內所有 IAM user 的 access key 清單。AWS 的 credential report 是這個問題的標準資料來源，它列出每個 user 的 key 狀態、建立時間與最後使用時間。

```bash
aws iam generate-credential-report
aws iam get-credential-report \
  --query 'Content' --output text | base64 -d > credential-report.csv
```

產出的 CSV 包含每個 IAM user 的兩把 key（access_key_1、access_key_2）各自的狀態。關注的欄位：

| 欄位                          | 用途                                         |
| ----------------------------- | -------------------------------------------- |
| `user`                        | key 的擁有者                                 |
| `access_key_1_active`         | key 是否啟用                                 |
| `access_key_1_last_used_date` | 最後使用時間——長期未使用代表可能是遺棄的 key |
| `access_key_1_last_rotated`   | 建立或上次輪替的時間                         |

用 csvkit 或試算表打開這份報告，按 `access_key_1_last_rotated` 排序，最舊的 key 排最前面。超過 90 天未輪替的 key 列為第一批處理對象。

以下腳本使用 gawk 的 `systime()` 函式。如果系統的 awk 是 mawk（Ubuntu 預設），改用 `gawk` 或用 `date` 指令替代時間計算。

```bash
# 快速列出所有啟用中、超過 90 天的 key
aws iam list-users --query 'Users[].UserName' --output text | tr '\t' '\n' | while read user; do
  aws iam list-access-keys --user-name "$user" \
    --query "AccessKeyMetadata[?Status=='Active'].[UserName,AccessKeyId,CreateDate]" \
    --output text
done | awk -F'\t' '{
  cmd = "date -d \"" $3 "\" +%s 2>/dev/null || date -jf \"%Y-%m-%dT%H:%M:%S+00:00\" \"" $3 "\" +%s"
  cmd | getline created; close(cmd)
  age = (systime() - created) / 86400
  if (age > 90) printf "%s\t%s\t%.0f days\n", $1, $2, age
}'
```

## 識別每把 key 的用途

知道 key 存在之後，下一個問題是「這把 key 用在哪裡」。credential report 只告訴你 key 最後被用來呼叫什麼 service（`access_key_1_last_used_service`），但不告訴你它被存放在哪裡。

用途識別需要交叉比對多個來源：

| 可能的存放位置                | 檢查方式                                                        |
| ----------------------------- | --------------------------------------------------------------- |
| CI 環境變數（GitHub Actions） | repo Settings → Secrets and variables → Actions                 |
| CI 環境變數（GitLab CI）      | repo Settings → CI/CD → Variables                               |
| EC2 instance 的 user data     | `aws ec2 describe-instance-attribute --attribute userData`      |
| Lambda 環境變數               | `aws lambda get-function-configuration --function-name NAME`    |
| SSM Parameter Store           | `aws ssm get-parameters-by-path --path / --recursive`           |
| 開發者筆電                    | `~/.aws/credentials` — 需要口頭確認                             |
| 程式碼 repo                   | `git log --all -p \| grep AKIA` — AKIA 是 access key 的固定前綴 |
| Slack / email 歷史            | 無法自動掃描，靠團隊回報                                        |

對每把要輪替的 key，在以上位置逐一確認。找不到用途的 key 可以先停用觀察（而非直接刪除），停用後如果有服務壞了就知道它用在哪裡。

## 輪替步驟：五步流程

輪替一把 key 的標準流程分五步，順序不能跳：

### 第一步：建立新 key

```bash
aws iam create-access-key --user-name deploy-bot
```

輸出會包含新的 AccessKeyId 和 SecretAccessKey。SecretAccessKey 只在這一刻顯示一次，存進密碼管理器或 Secrets Manager，不要貼在 Slack 或 email 裡。

一個 IAM user 最多同時有兩把 key。如果已經有兩把，需要先刪除一把不用的才能建新的。

### 第二步：更新所有消費者

把新 key 部署到上一節識別出的所有存放位置。CI 變數、Lambda 環境變數、SSM Parameter Store、開發者的 `~/.aws/credentials` 都要同步更新。

每更新一個消費者就做一次功能驗證——CI 跑一次 pipeline、Lambda 觸發一次、開發者跑一次 `aws sts get-caller-identity` 確認新 key 能用。

### 第三步：驗證新 key 生效

所有消費者更新完後，等待一個完整的業務週期（至少 24 小時），確認沒有任何服務還在用舊 key。檢查方式是看舊 key 的 `LastUsedDate` 有沒有在更新之後還被使用：

```bash
aws iam get-access-key-last-used --access-key-id AKIAOLD12345
```

如果 `LastUsedDate` 在你更新消費者之後仍有新的使用紀錄，代表有漏網的消費者還在用舊 key。

### 第四步：停用舊 key

確認無殘留使用後，停用（不是刪除）舊 key：

```bash
aws iam update-access-key \
  --user-name deploy-bot \
  --access-key-id AKIAOLD12345 \
  --status Inactive
```

停用是安全的中間狀態——用到這把 key 的服務會開始報 `InvalidClientTokenId` 錯誤，但 key 還在、可以隨時重新啟用。如果停用後有意料之外的服務壞了，重新啟用就能立刻恢復。

### 第五步：寬限期後刪除

停用後保持 7-14 天的寬限期。這段時間是「如果有漏掉的消費者」的安全網。寬限期內無異常，刪除：

```bash
aws iam delete-access-key \
  --user-name deploy-bot \
  --access-key-id AKIAOLD12345
```

刪除後不可回復。如果有服務還在用這把 key，只能建一把新 key 然後去更新那個服務。

## 自動化輪替：Secrets Manager

手動輪替的瓶頸在「找到所有消費者」這一步。如果 key 的消費者都從 Secrets Manager 讀取（而非各自存一份副本），輪替就簡化成「在 Secrets Manager 裡更新值」——所有消費者下次讀取時自動拿到新 key。

Secrets Manager 支援自動輪替：設定一個 Lambda function 作為 rotation function，它負責建新 key → 更新 secret value → 停用舊 key 的全流程。

```hcl
resource "aws_secretsmanager_secret" "deploy_key" {
  name = "prod/deploy-bot/access-key"
}

resource "aws_secretsmanager_secret_rotation" "deploy_key" {
  secret_id           = aws_secretsmanager_secret.deploy_key.id
  rotation_lambda_arn = aws_lambda_function.key_rotator.arn

  rotation_rules {
    automatically_after_days = 90
  }
}
```

自動輪替的前提是所有消費者都改成從 Secrets Manager 讀 key，而非從環境變數或設定檔。這個前提本身就是一次 migration——跟手動輪替的固定成本（盤點 + 更新 + 驗證）相比，migration 的一次性成本更高，但之後的每次輪替接近零成本。

判斷該不該投入自動化的依據是 key 的數量和輪替頻率。3 把 key、每季輪替一次，手動流程 2-3 小時可以完成，自動化的 ROI 不高。10 把以上、或合規要求 30 天輪替，手動已經吃掉固定的工程師時間，自動化的投入才有回報。

## Key age 監控

輪替做完不代表可以不管——如果沒有監控，三個月後又會回到「不知道有幾把超齡的 key」的狀態。

最低成本的監控是一條定期跑的 check，掃描所有 key 的年齡並在超過閾值時告警：

```bash
# 列出所有超過 90 天的 active key（用 AWS Config 規則更可靠）
aws configservice put-config-rule --config-rule '{
  "ConfigRuleName": "access-keys-rotated",
  "Source": {
    "Owner": "AWS",
    "SourceIdentifier": "ACCESS_KEYS_ROTATED"
  },
  "InputParameters": "{\"maxAccessKeyAge\":\"90\"}"
}'
```

AWS Config 的 `ACCESS_KEYS_ROTATED` managed rule 會持續掃描所有 IAM user 的 key age，超過設定天數的標記為 non-compliant。把 Config 的 non-compliant 事件接到 SNS → Slack 或 email，就有了持續的 key 超齡告警。

Prowler 也提供 key age 檢查（`prowler aws --checks access_key_1_rotated`），適合當一次性掃描工具。Config rule 適合持續監控。

管理層報告可以用 Config 的 compliance dashboard：compliant key 數 / 總 key 數 = key rotation 覆蓋率，這個百分比適合放進月報。

IAM Access Analyzer 的 unused access 功能（需啟用 analyzer）可以持續掃描帳號內未使用的 key 和 permission，跟 Config rule 互補——Config 看 key age，Access Analyzer 看 key 是否被使用。兩者搭配可以同時回答「這把 key 多久沒輪替」和「這把 key 有沒有在用」。

## 跨分類引用

- → [身分與憑證地基](/infra/02-identity-credentials/iam-oidc-privilege-boundary/)：access key 風險的系統性分析、OIDC 作為長期 key 的替代方案
- → [團隊權限分級與存取管理](/infra/02-identity-credentials/team-access-management/)：離職時的 key 撤銷流程
- → [治理好習慣](/infra/08-governance-habits/tagging-secrets/)：secret 的儲存與引用紀律
