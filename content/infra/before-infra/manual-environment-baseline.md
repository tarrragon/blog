---
title: "手動環境的可控底線與納管準備"
date: 2026-06-26
description: "還沒有 IaC 的環境怎麼守住底線、讓變更可追溯、降低未來納管成本，以及辨識何時該開始導入 IaC"
weight: 1
tags: ["infra", "iac", "bootstrap", "migration"]
---

手動起家是絕大多數服務的常態起點。從一個人在 Console 點出第一台 EC2 驗證想法，到小團隊接手開始長出更多資源，環境會經歷一段「全部靠手動、沒有任何程式碼描述」的階段。這個階段在[成熟度階梯](/infra/00-infra-mindset/#成熟度階梯)（從全手動到全程式碼治理的五階分級）上屬於第零階，它的責任是把自己管理成「可控的手動」，而不是假裝已經納管。可控意味著三件事：高風險操作有護欄、關鍵變更有痕跡、現實長什麼樣有紀錄。做好這三件事，當下出事的成本降低，未來把資源 import 進 IaC 的成本也跟著降低。

## 判讀自己是否可控

可控的手動環境能在五分鐘內回答以下問題：

1. production 有哪些對外開放的 port？
2. 上週誰動過資料庫參數，動了什麼？
3. 刪掉某台機器會不會連帶弄壞別的東西？
4. 現在用了幾把長期 access key，每把用在哪裡？
5. 有沒有一份清單能對照 Console 上的資源，確認沒有漏掉的？

五題都能答的團隊不多，目標也不是一次全通。辨識出哪些區域不可見，按傷害代價從高到低逐一收斂，就是這一章的路線。

## 護欄先上在回退代價最高的操作

手動環境沒有 IaC 的 `plan` / `diff` 當預檢，人為操作直接生效。護欄的優先級看的是失誤的回退代價，不是操作頻率。回退代價最高的三類操作各自有最低成本的防線。

### 長期憑證外洩

長期 access key 一旦外流，攻擊者拿到的是不會過期的權限。回退代價高的原因不只是撤銷這把 key 本身，而是要找出所有使用它的地方同步更換 — 而「所有使用它的地方」在手動環境裡幾乎沒有完整清單。一把用了半年的 key 可能已經被複製到 CI 環境變數、某個同事的測試腳本、一個早已被遺忘但還在跑的 cron job 裡。

最低成本的護欄分三步。第一步是盤點：列出帳號裡所有長期 access key，記下建立時間、上次使用時間與對應用途。

```bash
aws iam generate-credential-report
aws iam get-credential-report --output text --query Content | base64 -d
```

第二步是替換路徑。對人類操作者，改用會過期的登入工作階段（如 AWS IAM Identity Center 的臨時憑證，幾小時後自動失效）。對跑在雲上的自動化（EC2 上的腳本、ECS task），改用平台原生的角色綁定 — instance profile 或 task role 會自動輪替短期憑證，程式碼不需要存任何 key。對跑在雲外的 CI/CD（如 GitHub Actions），改用 OIDC 聯合（見[模組二：身分與憑證地基](/infra/02-identity-credentials/)）。

第三步是輪替紀律。把還在用的長期 key 設定定期輪替提醒（60 天或 90 天，對齊 AWS IAM credential report 的建議週期），每次輪替時問自己：這把 key 能不能這次就換成臨時憑證，讓它成為最後一次輪替？

### 刪除 production 資源

在 Console 選中一個 security group 按刪除，平台可能只問「確定嗎？」就直接執行，不會告訴你有三個 EC2 instance 正在引用這個 group。EBS volume 被刪除後，上面的資料就不存在了 — 除非之前有做 snapshot，而手動環境裡有沒有做 snapshot 通常取決於某個人的記憶。

對承載狀態的資源，最低成本的護欄是開啟平台的刪除保護：

```bash
aws rds modify-db-instance \
  --db-instance-identifier payments-prod \
  --deletion-protection \
  --apply-immediately

aws ec2 modify-instance-attribute \
  --instance-id i-0abc123 \
  --disable-api-termination
```

RDS 有 `deletion_protection`，EC2 有 `termination_protection`，S3 bucket 可以開 MFA delete。這些機制把「一鍵刪除」變成「先關保護再刪除」兩步操作，擋不住蓄意刪除，但能擋住手滑跟批次操作的誤傷。

刪除保護之外，備份是另一道防線。手動環境裡至少確認 RDS 的自動備份是開著的（預設保留 7 天），以及 S3 bucket 的 versioning 是開著的。S3 bucket 的 versioning 預設是關的，一個沒開 versioning 的 bucket，覆寫或刪除物件後就回不去了。

### 網路規則的大改

手動調整 VPC 路由、subnet 關聯的 route table、或 security group 的入站規則，影響範圍跨越多個服務，而且在手動環境裡沒有版本控制可以 diff 改了什麼。一條路由改錯，某些 private subnet 的服務可能瞬間失去出站能力。

最低成本的護欄是「改之前先把現況存下來」：

```bash
aws ec2 describe-security-groups \
  --group-ids sg-0abc123 \
  --output json > sg-backup-$(date +%Y%m%d).json
```

用 CLI 把當前的 security group 規則、route table 設定匯出一份 JSON。改完後如果出問題，這份 JSON 就是回退的依據。這不是自動回退 — 手動環境沒有那個能力 — 但至少讓「改回去」有個明確的目標狀態。網路地基的系統性設計在[模組三：網路地基](/infra/03-network-foundation/)展開。

### 該先做什麼

這三類護欄的共同判準是：護欄成本低（幾條 CLI 指令或 Console 設定）、失誤代價高（憑證外洩、資料遺失、服務中斷）。判讀某個資源該不該現在就加護欄，問自己一個問題：「這個資源出事的回退時間是分鐘級、小時級、還是不可回退？」不可回退的（資料刪除、key 外洩）優先加；分鐘級可回退的（重啟一個 stateless service）可以排後面。

## 讓變更留下痕跡

變更留痕的責任是讓「誰、在什麼時候、改了什麼、為什麼」事後可追溯。IaC 的 git history 天然提供這件事，手動環境得靠人為紀律補上。

### 人工變更日誌

最低限度是一份變更日誌，可以只是 repo 裡的一個 markdown 檔或團隊共用文件。一條記錄至少包含四個欄位：

```markdown
## 2026-06-20

- **操作者**：alice
- **資源**：sg-0abc123 (payments-api-prod)
- **變更**：新增 ingress rule, port 8080 from 10.0.0.0/16
- **原因**：內部監控服務需要存取 health check endpoint
- **回退方式**：刪除該 ingress rule
```

格式不需要精美，需要的是「每次都寫」。常見陷阱是只在「大改動」時才記錄，結果真正出事的往往是某次以為無關緊要的小調整 — 改了一個 parameter group 的值、調了一條路由的目標、把某個 instance 的 security group 換了一個。判準簡化成一句：只要這個操作別人事後可能需要知道，就記。

### 平台稽核日誌

和人工日誌互補的是平台的稽核日誌（如 AWS CloudTrail、GCP Audit Log）。稽核日誌自動記錄 API 層級「發生了什麼」— 某個 IAM user 在某個時間對某個資源呼叫了哪個 API — 不依賴人為紀律、也不會漏。但它只記錄事實，不記錄意圖。它告訴你 security group 在幾點被改，卻不告訴你改的原因。人寫的變更日誌補上的正是「為什麼」這一段。

```bash
aws cloudtrail describe-trails \
  --query 'trailList[].{Name:Name,S3Bucket:S3BucketName}'

aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=AuthorizeSecurityGroupIngress \
  --max-items 10
```

CloudTrail 在 AWS 帳號裡預設開啟 management event 的 90 天查閱。手動環境裡至少確認 management event 的 trail 存在且在寫入 — 這是事後回推「到底誰動了什麼」的最後防線。兩者一起，事故排查時才能從「哪裡變了」一路追到「為什麼改、能不能安全回退」。

## 命名與 tagging 從手動階段就開始

命名規範與資源標籤讓每個資源自帶「我是誰、屬於哪個服務、誰負責、哪個環境」的身分資訊。手動點出來的資源若名稱是 `test-2`、`new-db-final`、`temp-sg`，日後納管時得靠人逐一辨認哪個還在用、屬於哪條業務線，考古成本遠高於當初多打幾個字。

### 命名規範

從手動階段就固定一套命名規則，讓名稱本身攜帶足夠的上下文。一個實用的格式是 `{service}-{component}-{env}`：

| 資源類型       | 命名範例                   | 攜帶的資訊                |
| -------------- | -------------------------- | ------------------------- |
| EC2 instance   | `payments-api-prod`        | 服務 + 角色 + 環境        |
| Security group | `payments-api-prod-sg`     | 同上 + 資源類型           |
| RDS instance   | `payments-db-prod`         | 服務 + 資源類型 + 環境    |
| S3 bucket      | `acme-payments-assets-dev` | 組織 + 服務 + 用途 + 環境 |

命名不需要完美或涵蓋所有維度，需要的是一致。同類資源都用同一套格式，人眼掃一頁 Console 就能分辨「這個屬於 payments 的 prod」跟「這個屬於 auth 的 dev」。不一致的命名（有些用底線、有些用連字號、有些帶 env 有些不帶）會在日後盤點時讓每個資源都變成需要考古的謎題。

### 最小 tag 集合

標籤至少包含三個維度：

| Tag       | 問的問題 | 典型值                       |
| --------- | -------- | ---------------------------- |
| `service` | 這屬於誰 | `payments-api` / `auth`      |
| `env`     | 哪個環境 | `prod` / `staging` / `dev`   |
| `owner`   | 出事找誰 | `team-payments` / `platform` |

手動階段的 tag 靠人工填。在 Console 建資源時順手加 tag 幾乎零成本 — 多打三行字而已。但如果沒有約定「哪些 tag 是必填」，多數人會跳過。最低限度的紀律是：在團隊文件裡寫下「建任何資源前先填這三個 tag」，並在每次盤點時檢查有沒有漏標的資源。

這套規則在導入 IaC 後直接升級成 Terraform 的 `default_tags` — 自動套用、不靠人記（見[模組八：治理好習慣](/infra/08-governance-habits/)）。先在手動階段建立習慣，導入 IaC 時只是換一個強制機制，而不是從零學起一套分類法。

## 盤點現有資源作為納管輸入

資源盤點把「現實長什麼樣」寫成一份清單，它是日後納管的直接輸入。手動環境裡最難管理的是未標記的閒置資源 — 測試用的 EC2、實驗用的 RDS — 持續計費但沒有標籤，無法用查詢系統性找出，也無法確認是否仍有服務依賴。

### 盤點方法

按資源類型分批拉，每批存一份 JSON 或 CSV 進 repo：

```bash
aws ec2 describe-instances \
  --query 'Reservations[].Instances[].[InstanceId,InstanceType,State.Name,Tags[?Key==`Name`].Value|[0],Tags[?Key==`env`].Value|[0]]' \
  --output table

aws rds describe-db-instances \
  --query 'DBInstances[].[DBInstanceIdentifier,Engine,DBInstanceClass,MultiAZ,DeletionProtection]' \
  --output table

aws ec2 describe-security-groups \
  --query 'SecurityGroups[].[GroupId,GroupName,IpPermissions]' \
  --output json > security-groups-$(date +%Y%m%d).json

aws s3api list-buckets --query 'Buckets[].Name'
```

### 盤點後的三件事

這份清單同時服務三個目的。

**當下的安全盤查**：security group 清單裡有沒有不該開的對外 port？有沒有 EC2 直接掛著公網 IP 卻不是 load balancer？用 `0.0.0.0/0` 搜一遍 security group 的輸出，命中的每一條都要能說出「這個全開是故意的、理由是什麼」。

**未來 IaC import 的範圍界定**：哪些資源該先 import。判準是「改動頻率」與「改錯代價」的乘積 — 頻繁改動且改錯代價高的（security group、IAM role）先排進來，很少動的（一個已經穩定的 S3 bucket）可以排後面。

**成熟度評估的事實基礎**：成熟度階梯的定位（見[模組零：infra 是什麼](/infra/00-infra-mindset/)）需要知道「全手動到底有多少資源、分布在幾個帳號、跨幾個 region」，這份清單就是評估的輸入。

### 盤點的節奏

第一次盤點最花時間，因為很多資源的用途需要考古。之後每月或每季重跑一次比對差異 — 重點是看「上次到這次之間長出了什麼新資源」。如果每次比對都發現大量未標記的新資源，這本身就是一個訊號：手動操作的可見性不足，該考慮導入 IaC 了。

## 資源與信任不足下的高槓桿取捨

當時間、人力或上層信任都不足，無法一次把上面每件事做齊時，取捨原則是先做「失誤代價高且護欄成本低」的少數幾件：

| 護欄          | 實施成本 | 失誤代價 | 優先級         |
| ------------- | -------- | -------- | -------------- |
| 長期 key 盤點 | 低       | 極高     | 立刻做         |
| 刪除保護      | 低       | 極高     | 立刻做         |
| 變更日誌      | 低       | 中       | 第二順位       |
| 命名規範      | 近零     | 累積     | 新資源立刻套用 |
| 資源盤點      | 中       | 累積     | 有空就做       |
| 存量重命名    | 高       | 累積     | 等有餘力       |

長期憑證盤點與刪除保護兩者加起來的實施時間可能不到一小時。命名與 tagging 的策略是「新的一律照規範、舊的等有餘力再補」，而不是停下來先整理全部存量。資源不足時怎麼跟上層談這些工作的優先級，在[模組九：怎麼把 infra 推動起來](/infra/09-driving-adoption/)展開。

## 該開始導入 IaC 的訊號

手動環境到了某些訊號出現時，繼續手動的邊際成本會超過導入 IaC 的一次性成本。訊號是規模與協作的函數，不是時間的函數 — 一個人運維一個簡單服務，手動可能撐很久；三個人同時動一個稍微複雜的環境，幾週內就會踩到手動的極限。

**環境數量變多**：當需要 dev、staging、production 三套幾乎一樣的環境，手動複製會在環境之間留下難以察覺的差異。某個人在 staging 加了一條 security group 規則，忘了在 prod 也加，結果 staging 測通了、prod 部署後服務連不上。IaC 用同一份程式碼複製環境，環境差異只存在於參數值。

**多人同時動資源**：一個人手動操作還能靠記憶維護，兩三個人並行時，沒有 plan / review 的手動變更會互相覆蓋。A 改了一個設定解了自己的問題，B 幾天後改了另一個設定把 A 的修正覆蓋掉，事故原因得靠翻 CloudTrail 才查得到。

**環境爆炸頻率上升**：如果「改一個設定結果弄壞別的東西」這類事故開始每月發生，代表手動環境的隱性依賴已經超過人腦能追蹤的上限。一個典型的隱性依賴：security group A 被 instance X 和 instance Y 同時引用，改 A 時只想著 X 的需求、忘了 Y 也依賴它，改完 Y 就斷了。

**合規或稽核要求**：外部稽核（SOC 2、ISO 27001）開始要求「列出所有對外暴露的服務」「提供存取權限的變更紀錄」「證明 production 環境的變更有經過審查」。手動環境回答這些問題時，每次都是一場考古工程。IaC 加上 PR 流程後，答案就在 repo 裡。

任一訊號穩定出現，就是把第一個資源納入 IaC 的起點 — 前面做的命名、tagging、資源盤點此時直接成為 import 的輸入。第一步怎麼跨進去在[模組一：最小可行 IaC](/infra/01-minimal-iac/)。

在訊號出現前過早導入 IaC 也有代價：單人、單環境、低變更頻率時，IaC 的學習與維護成本可能高於它省下的手動工 — 寫一份 HCL、配一個 state backend、設一條 pipeline 的固定成本，在只有三個資源的環境裡不一定划得來。這裡的判準是等訊號、不是趕進度。

## 跨分類引用

- → [模組零：infra 是什麼](/infra/00-infra-mindset/)：成熟度階梯上「全手動」這一階的定位
- → [模組一：最小可行 IaC](/infra/01-minimal-iac/)：訊號出現後，第一步怎麼跨進 IaC
- → [模組二：身分與憑證地基](/infra/02-identity-credentials/)：長期憑證護欄的系統性設計
- → [模組三：網路地基](/infra/03-network-foundation/)：手動階段網路大改的回退考量、之後的系統性設計
- → [模組八：治理好習慣](/infra/08-governance-habits/)：tagging 在成本歸因與批次操作的後續價值
- → [模組九：怎麼把 infra 推動起來](/infra/09-driving-adoption/)：資源不足時怎麼跟上層談優先級
