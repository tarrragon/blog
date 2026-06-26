---
title: "有 SSH 但沒有 IaC 的雲端環境接管"
date: 2026-06-26
description: "接手一個全手動建立的雲端環境時，怎麼盤點資源、推導依賴關係、收斂 credential、驗證備份、建立變更紀律，以及什麼時候該開始導入 IaC"
weight: 2
tags: ["infra", "takeover", "cloud", "aws"]
---

雲端資源存在且正在服務 production 流量，但沒有人能回答「我們有什麼、為什麼這樣設定、改了會影響什麼」。Console 裡有幾十個資源，有些名稱是 `test-final-v2`，有些沒有名稱，security group 規則不知道哪條還在用，IAM user 清單裡有幾個已離職的人。這是接手全手動雲端環境的典型起點。

接管的操作順序是：先拍下現況（盤點）、再理解結構（依賴）、再收斂風險（credential、備份）、再建立紀律（變更紀錄）、最後才考慮 IaC 導入。每一步都在不改動 production 的前提下進行。

## 資源盤點：拍下雲端現況

盤點的目標是把「雲端上有什麼」轉成一份可版本控制的清單。這份清單是後續所有操作的事實基礎 — 沒有清單就無法判斷哪些資源重要、哪些可以回收、哪些的設定有風險。

### 用 CLI 拉清單

從有 tag 的資源開始，再補沒有 tag 的。AWS 的 Resource Groups Tagging API 能跨服務撈出所有被標記的資源：

```bash
aws resourcegroupstaggingapi get-resources \
  --output json > inventory/tagged-resources.json
```

沒有 tag 的資源不會出現在這裡，需要按服務類型逐一拉。以下是接手時最該優先盤點的四類：

```bash
# EC2：哪些機器在跑、什麼規格、在哪個 subnet
aws ec2 describe-instances \
  --query 'Reservations[].Instances[].[InstanceId,InstanceType,State.Name,SubnetId,SecurityGroups[].GroupId,Tags]' \
  --output json > inventory/ec2.json

# RDS：資料庫的備份設定、刪除保護、Multi-AZ
aws rds describe-db-instances \
  --query 'DBInstances[].[DBInstanceIdentifier,Engine,DBInstanceClass,MultiAZ,BackupRetentionPeriod,DeletionProtection]' \
  --output json > inventory/rds.json

# Security Group：哪些規則對外開放
aws ec2 describe-security-groups \
  --query 'SecurityGroups[].[GroupId,GroupName,IpPermissions]' \
  --output json > inventory/security-groups.json

# S3：哪些 bucket、versioning 是否開啟
for bucket in $(aws s3api list-buckets --query 'Buckets[].Name' --output text); do
  echo "$bucket: $(aws s3api get-bucket-versioning --bucket $bucket --query 'Status' --output text)"
done > inventory/s3-versioning.txt
```

把所有輸出存進一個 Git repo 的 `inventory/` 目錄。這份快照的價值在於：一週後再跑一次比對差異，就能看出環境在背景長出了什麼新資源。

### 優先查三件事

盤點不需要一次做完所有服務，但三件事要第一天就查：

**對外暴露面**：security group 裡有沒有 `0.0.0.0/0` 入站規則指向非 HTTP/HTTPS 的 port（22、3306、5432、6379）。這些規則讓資料庫埠或管理埠直接暴露在公網掃描流量下。

```bash
# 找出所有對全網開放的非標準埠
aws ec2 describe-security-groups \
  --query 'SecurityGroups[].IpPermissions[?contains(IpRanges[].CidrIp, `0.0.0.0/0`)]' \
  --output json | jq '[.[][] | select(.FromPort != 80 and .FromPort != 443)]'
```

**備份狀態**：RDS 的 `BackupRetentionPeriod` 是不是 0（代表沒有自動備份）。S3 的 versioning 是不是關的。如果是，這是接手後第一個要改的設定 — 改備份設定不影響服務運作，但沒有備份時任何資料操作失誤都不可逆。

**誰最近在動環境**：CloudTrail 記錄了所有 API 呼叫。查最近 30 天的變更事件，能看出哪些資源被頻繁修改、被誰修改。這比逐一問前團隊成員可靠——CloudTrail 不會漏記。

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ReadOnly,AttributeValue=false \
  --start-time $(date -v-30d +%Y-%m-%dT%H:%M:%S) \
  --max-items 50 \
  --query 'Events[].[EventTime,Username,EventName,Resources[0].ResourceName]' \
  --output table
```

## 依賴關係推導

盤點回答「有什麼」，依賴推導回答「改一個會連帶影響什麼」。手動環境沒有 Terraform 的依賴圖可以看，需要從資源的引用關係反推。

### 從 security group 開始

Security group 是依賴推導的最佳起點，因為它的引用關係最密集 — 幾乎每個資源都掛著至少一個 SG，而 SG 之間可以互相引用（app SG 的入站來源是 LB SG、DB SG 的入站來源是 app SG）。

```bash
# 列出每個 SG 被哪些 ENI（網卡）使用
aws ec2 describe-network-interfaces \
  --query 'NetworkInterfaces[].[NetworkInterfaceId,Description,Groups[].GroupId]' \
  --output json > inventory/sg-usage.json
```

從 SG 的引用鏈可以畫出一張粗略的依賴圖：

| 層次 | 資源      | 入站來自      | 出站到          |
| ---- | --------- | ------------- | --------------- |
| 入口 | ALB       | 0.0.0.0/0:443 | app SG          |
| 應用 | EC2 / ECS | ALB SG        | DB SG、外部 API |
| 資料 | RDS       | app SG:5432   | —               |

這張圖不需要精確到每個 port — 它的用途是在改動任何資源前，快速判斷影響範圍。例如要改 app SG 的規則時，先查它被哪些 EC2 和 ECS 引用、它的入站來源 ALB SG 是否受影響。

### 其他依賴面向

除了 SG，以下幾個引用關係也要記錄：

- **EC2 → IAM role**：instance profile 決定這台機器能存取什麼（S3 bucket、Secrets Manager、其他 AWS 服務）
- **RDS → subnet group**：決定資料庫在哪些 subnet 裡，改 VPC 或 subnet 時會受影響
- **ALB → target group → EC2/ECS**：流量路徑，改 target group 的 health check 或移除成員會影響服務可用性
- **Lambda → VPC 設定**：如果 Lambda 被放進 VPC，它的出站走 NAT，改 NAT 或 route table 會影響它
- **Route 53 → ALB/EC2**：DNS 指向哪個資源，改資源 IP 或 ALB 時要同步更新

## credential 盤點與收斂

接手環境時，credential 是風險最高的一類 — 前團隊建立的 IAM user 和 access key 可能還在活躍狀態，而那些人已經不在團隊裡了。

### 產出 credential 報告

```bash
aws iam generate-credential-report
aws iam get-credential-report \
  --query 'Content' --output text | base64 -d > inventory/credential-report.csv
```

這份 CSV 列出所有 IAM user、每把 access key 的建立時間、上次使用時間、MFA 是否啟用。從中篩出三類需要處理的：

| 類別                   | 判斷方式                                 | 處理                                         |
| ---------------------- | ---------------------------------------- | -------------------------------------------- |
| 已離職人員的 key       | user 名稱對照離職清單                    | 停用 key → 觀察 7 天無異常 → 刪除 user       |
| 超過 90 天未使用的 key | `access_key_last_used` 超過 90 天        | 停用 → 觀察是否有服務中斷 → 確認無影響後刪除 |
| 有 admin 權限的 key    | policy 含 `AdministratorAccess` 或 `*:*` | 降權到實際需要的最小權限                     |

停用（deactivate）而非直接刪除是關鍵 — 停用後如果某個自動化腳本依賴這把 key 會立刻報錯，這時候可以快速重新啟用；直接刪除就回不去了。觀察期設 7 天，涵蓋一個完整的業務週期（含週末的 cron job）。

### 檢查 key 散落的位置

Access key 可能被寫在不只一個地方：

```bash
# EC2 user data 裡是否有 hardcode 的 key
aws ec2 describe-instance-attribute \
  --instance-id i-xxx --attribute userData \
  --query 'UserData.Value' --output text | base64 -d | grep -i "aws_access_key\|aws_secret"

# Lambda 環境變數
aws lambda list-functions --query 'Functions[].FunctionName' --output text | \
  xargs -I{} aws lambda get-function-configuration --function-name {} \
  --query 'Environment.Variables' --output json | grep -i "key\|secret\|password"

# SSM Parameter Store
aws ssm describe-parameters --query 'Parameters[].Name' --output text
```

找到 hardcode 的 key 後，替換路徑是改用 IAM role（EC2 用 instance profile、Lambda 用 execution role）。替換前先確認 role 的 policy 涵蓋這把 key 原本在做的操作。

## 備份驗證

盤點出的每個 stateful 資源（RDS、S3、EBS）都要確認備份狀態。接手環境時不能假設「前團隊應該有設定備份」— 要親自驗證。

### RDS 備份

```bash
# 檢查每個 RDS instance 的備份設定
aws rds describe-db-instances \
  --query 'DBInstances[].[DBInstanceIdentifier,BackupRetentionPeriod,LatestRestorableTime,DeletionProtection]' \
  --output table
```

`BackupRetentionPeriod` 為 0 代表沒有自動備份 — 立刻改成至少 7 天。`DeletionProtection` 為 false 代表一個誤操作就能刪掉資料庫 — 立刻開啟。這兩項設定的修改不需要重啟、不影響服務。

備份存在不等於備份可用。接手後的第一週內，從最近的 snapshot 還原一台測試 RDS、連進去確認資料完整。這個步驟的成本是一台 RDS 跑幾小時的費用，換到的是「備份確定能用」的確認 — 等到要用備份的時候才發現不能還原，代價是另一個量級。

### S3 versioning

沒有開 versioning 的 bucket，物件被覆寫或刪除後不可回復。對承載業務資料的 bucket（上傳的檔案、匯出的報表、設定檔），開啟 versioning：

```bash
aws s3api put-bucket-versioning \
  --bucket my-business-data \
  --versioning-configuration Status=Enabled
```

開啟 versioning 不影響既有物件，但會讓後續的每次覆寫都保留舊版本。儲存成本會因為保留歷史版本而增加 — 配一條 lifecycle rule 設定 noncurrent version 的過期天數來控制。

## 建立變更紀律

盤點、依賴推導、credential 收斂做完後，環境的現況已經有一份可查的記錄。下一步是確保從現在開始的每一次變更都留下痕跡。

### 變更日誌

在 inventory repo 裡建一份 `CHANGELOG.md`，每次改動 production 就追加一筆：

```markdown
## 2026-06-26

- **操作者**：alice
- **資源**：rds/payments-prod
- **變更**：BackupRetentionPeriod 0 → 14, DeletionProtection false → true
- **原因**：接手盤點發現備份未開啟
- **回退方式**：BackupRetentionPeriod 改回 0（不建議）
```

### CloudTrail 確認

確認 CloudTrail 正在記錄 management events。如果沒有 trail 存在，建一個指向 S3 bucket 的 trail — 這是事後追溯「誰動了什麼」的最後防線。

```bash
aws cloudtrail describe-trails --query 'trailList[].{Name:Name,S3:S3BucketName,IsLogging:IsLogging}'
```

### 開始標 tag

盤點過程中辨識出的每個資源，標上 `env`、`owner`、`service` 三個 tag。接手階段的 `owner` 通常標「待確認」或新接手的團隊名稱。tag 的價值在於讓後續的盤點和清理可以用查詢系統性地進行 — 沒有 tag 的資源無法被 filter 找到。

## 往 IaC 的銜接

盤點和紀律建立完成後，環境已經從「不知道有什麼」推進到「知道有什麼、知道誰在動、改了有紀錄」。這個狀態對應[成熟度階梯](/infra/00-infra-mindset/)的第零階到第一階之間。

往 IaC 的銜接不需要一次做完。按穩定度和改動風險排序：

| 優先級 | 資源類型                 | 理由                                            |
| ------ | ------------------------ | ----------------------------------------------- |
| 先做   | VPC、subnet、route table | 形狀穩定、幾乎不會改、import 風險低             |
| 次做   | security group           | 規則明確、import 後 plan 容易驗證               |
| 後做   | RDS、EC2、ALB            | stateful 或與部署耦合、import 風險較高          |
| 最後   | Lambda、API Gateway      | 通常跟應用程式碼耦合、import 後維護邊界需要釐清 |

每批 import 的操作流程是：`terraform import` → `terraform plan` 確認零變更 → 寫 HCL 補齊差異 → 再跑 `plan` 直到零變更。具體的 import 步驟和工具選型在[模組一：最小可行 IaC](/infra/01-minimal-iac/)。

時程參考：10-20 個資源的環境，完成盤點 + credential 收斂 + 備份驗證約需 3-5 天；往 IaC 的 import 約需 1-2 週。兩者可以平行進行但建議先完成盤點 — 沒有完整的資源清單就開始 import，容易漏掉關鍵的依賴關係。

## 跨分類引用

- → [模組負一：還沒有 infra 的環境](/infra/before-infra/)：盤點完成後的操作紀律對齊
- → [模組零：infra 是什麼](/infra/00-infra-mindset/)：成熟度階梯作為接手後現況評估的座標
- → [模組一：最小可行 IaC](/infra/01-minimal-iac/)：盤點完成後的第一步 IaC 導入
- → [模組二：身分與憑證](/infra/02-identity-credentials/)：credential 收斂的完整設計
- → [團隊權限分級與存取管理](/infra/02-identity-credentials/team-access-management/)：接手後重新建立權限分級
