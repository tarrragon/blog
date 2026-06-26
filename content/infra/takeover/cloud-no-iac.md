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

盤點的工具依環境類型不同：

- **VM 為主（EC2 / GCE）** → 先跑 [VM 快照與系統清單](#vm-層級的快照)，再跑 [CLI 資源盤點](#用-cli-拉清單)
- **Managed service 為主（RDS / Lambda / S3）** → 直接跑 [CLI 資源盤點](#用-cli-拉清單)
- **混合（VM + managed）** → 兩個都跑：先 VM 快照（拍下機器狀態），再 CLI 盤點（拍下所有雲端資源）

### 用 CLI 拉清單

盤點有三層工具可用，從粗到細：

**全貌掃描**：先用跨服務工具拿到「到底有多少資源」的量級感。AWS Resource Explorer 在 Console 開啟後可以用搜尋語法跨 region、跨 service 查資源（例如搜 `resourcetype:ec2:instance` 列出所有 EC2）。Steampipe 是開源的 SQL 介面雲端查詢工具，用 `select * from aws_ec2_instance` 這類語法查詢，對習慣 SQL 的人比 CLI flag 直覺。兩者都能在幾分鐘內拿到環境的全貌。

**Tag 層掃描**：AWS Resource Groups Tagging API 能跨服務撈出所有被標記的資源，但會漏掉沒有 tag 的 — 而接手環境裡沒 tag 的資源往往是風險最高的（沒人認領、不敢動）。

```bash
aws resourcegroupstaggingapi get-resources \
  --output json > inventory/tagged-resources.json
```

**Per-service 細節**：全貌掃描只告訴你資源存在，細節（備份設定、SG 規則、IAM policy）要用 per-service describe 拉。以下是接手時最該優先盤點的四類：

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

**對外暴露面**：security group 裡有沒有 `0.0.0.0/0` 入站規則指向非 HTTP/HTTPS 的 port（22、3306、5432、6379）。手動逐條查很慢 — 用安全掃描工具一次跑完更可靠。Prowler 是開源的 AWS 安全掃描工具，一次執行就能產出「哪些 SG 對外開放、哪些 S3 public、哪些 IAM 過寬」的分類報告：

```bash
# 安裝後執行，針對最相關的服務掃描
prowler aws --services ec2 iam s3 rds -M json-ocsf -o inventory/

# 如果只想快速查 SG 暴露面，用 CLI：
aws ec2 describe-security-groups \
  --query 'SecurityGroups[].IpPermissions[?contains(IpRanges[].CidrIp, `0.0.0.0/0`)]' \
  --output json | jq '[.[][] | select(.FromPort != 80 and .FromPort != 443)]'
```

ScoutSuite 是類似工具、支援多雲（AWS / GCP / Azure）。AWS Trusted Advisor 的免費 tier 也有基本安全檢查（S3 public access、SG 開放埠），但覆蓋面比 Prowler 窄。接手時三者選一跑一次，比手動翻 Console 快且不會漏。

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

### VM 層級的快照

如果接手的環境包含 EC2 或 GCE 等 VM，在做任何改動之前先對每台 VM 建一個 AMI（AWS）或 machine image（GCP）。這是最粗粒度但最完整的「拍照」——整台機器的 OS、安裝的軟體、設定檔、磁碟內容全部打包成一個可重建的映像。

```bash
# AWS: 對 EC2 建 AMI（--no-reboot 避免服務中斷）
aws ec2 create-image \
  --instance-id i-0abc123 \
  --name "takeover-baseline-$(date +%Y%m%d)" \
  --no-reboot

# 確認 AMI 建立完成
aws ec2 describe-images \
  --owners self \
  --filters "Name=name,Values=takeover-baseline-*" \
  --query 'Images[].[ImageId,Name,State]' \
  --output table
```

`--no-reboot` 讓快照過程中服務不中斷，代價是檔案系統快照的一致性不如有 reboot 的版本（記憶體中的寫入可能還沒 flush 到磁碟），但對接手基線已經足夠。AMI 的費用是底層 EBS 快照的儲存費用（按 GB 計費、差異儲存），作為接手保險措施這筆成本值得。

除了 VM 快照，有 SSH 存取時也要拍 VM 內部的軟體環境——AMI 可以還原整台機器，但看不到「裡面裝了什麼、跑了什麼」的摘要：

```bash
# 作業系統與版本
cat /etc/os-release

# 已安裝的套件清單
dpkg -l > ~/takeover/packages-$(date +%Y%m%d).txt   # Debian/Ubuntu
rpm -qa > ~/takeover/packages-$(date +%Y%m%d).txt    # RHEL/CentOS/Amazon Linux

# 執行中的服務
systemctl list-units --type=service --state=running > ~/takeover/services.txt

# 所有使用者的 cron jobs
for user in $(cut -f1 -d: /etc/passwd); do
  echo "=== $user ===" >> ~/takeover/crontabs.txt
  crontab -u "$user" -l 2>/dev/null >> ~/takeover/crontabs.txt
done

# 網路監聽的 port（哪個 process 在聽哪個 port）
ss -tlnp > ~/takeover/listening-ports.txt
```

把這些輸出存進盤點 repo，跟 CLI 資源盤點（describe 指令的輸出）放在一起。`listening-ports.txt` 跟 security group 規則對照，可以看出「哪些 port 有服務在聽但 SG 沒開」（可能是內部服務）和「哪些 port SG 開了但沒有服務在聽」（可能是殘留規則）。

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

AWS Console 的 VPC 頁面有 Resource Map 功能，可以視覺化 subnet → instance → SG 的對應關係，接手時第一次瀏覽依賴用它比 CLI 直覺。要產出可存檔的依賴圖，draw.io（有 AWS icon set）或 Lucidchart 都能畫，重點是圖要存進 repo、不是畫完就丟。

如果後續打算導入 Terraform，Former2 可以掃描現有 AWS 資源、自動產出 Terraform / CloudFormation / CDK 程式碼。產出的程式碼不會完美（屬性常漏、命名要改），但作為反推依賴關係的起點比從零寫快。Inframap 則是從 Terraform state 產出依賴關係圖（在 import 階段才用得到）。

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

接手後第一件事是用 aws-vault 管理自己的 credential。aws-vault 把 AWS access key 存在 OS keychain（macOS Keychain / Windows Credential Manager），而非明文放在 `~/.aws/credentials`。執行 AWS 指令時由 aws-vault 注入臨時 session，本地磁碟上不留長期 key 的明文。不要沿用前人留下的 AWS CLI profile — 那些 profile 的權限範圍和用途都不確定。

```bash
# 安裝後設定新的 profile
aws-vault add takeover-admin
# 用臨時 session 執行指令
aws-vault exec takeover-admin -- aws sts get-caller-identity
```

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

### 成本現況

接手環境通常伴隨「這個月帳單多少」的問題。AWS Cost Explorer（免費）能看過去幾個月的花費分布，按服務類型、帳號、tag 維度拆。接手時先拉一次 Cost Explorer 的月度趨勢，看有沒有異常成長或不預期的高額服務。後續導入 IaC 後，Infracost 可以在 `terraform plan` 階段預估變更的成本影響（例如「升 RDS 規格會多花多少」），讓成本決策在 apply 之前就被看見。

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

- → [有半套 IaC 但文件缺失的環境接管](/infra/takeover/partial-iac-no-docs/)：如果盤點過程中發現環境裡已有部分 Terraform code
- → [模組負一：還沒有 infra 的環境](/infra/before-infra/)：盤點完成後的操作紀律對齊
- → [模組零：infra 是什麼](/infra/00-infra-mindset/)：成熟度階梯作為接手後現況評估的座標
- → [模組一：最小可行 IaC](/infra/01-minimal-iac/)：盤點完成後的第一步 IaC 導入
- → [模組二：身分與憑證](/infra/02-identity-credentials/)：credential 收斂的完整設計
- → [團隊權限分級與存取管理](/infra/02-identity-credentials/team-access-management/)：接手後重新建立權限分級
