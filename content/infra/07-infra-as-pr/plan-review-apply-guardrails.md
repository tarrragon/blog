---
title: "infra 走 PR 流程與自動化護欄"
date: 2026-06-26
description: "infra 變更走 PR → plan → review diff → 合併 → apply，配 fmt / validate / tflint / checkov / tfsec 與 Atlantis 自動化，讓基礎設施可審查、可回溯、可交接"
weight: 1
tags: ["infra", "ci-cd", "review", "tflint", "checkov"]
---

infra 變更要走跟 application code 一樣的流程：開分支、提 PR、跑檢查、review diff、合併、發布。這條原則把基礎設施變更從「某個人在自己終端機 apply」轉成「團隊可審查的紀錄」，是 IaC 真正兌現價值的地方，也是解開「只有我懂 infra」這個單點依賴的關鍵。基礎設施跟程式碼一樣會出錯、會需要回溯、會交接給別人，所以它需要同一套保護機制。

## infra 變更走 code 流程

infra 變更的標準路徑是 PR → plan → review diff → 合併 → apply。這個順序的核心責任是把「執行前先看清楚要改什麼」變成強制步驟，而不是 apply 之後才從事故裡發現改錯了。每個環節各自承擔一段審查責任，少掉任一段，infra 就退回到不可審查的狀態。

### plan 是整條鏈最關鍵的一環

`terraform plan` 把當前 state、雲端實際資源、與目標設定三方比對，產出一份「會新增 / 修改 / 刪除哪些資源」的 diff。這份 diff 是 review 的對象：reviewer 直接看 plan 算出來的實際變更，而非讀 HCL 自行想像結果。

plan 輸出裡最關鍵的判讀訊號是操作類型。`+` 是新增，`~` 是就地更新，`-` 是銷毀，`-/+` 是先銷毀再重建。前兩者多數情境是安全的，後兩者需要逐行細看。改一個看似無害的欄位可能觸發整個資源重建（`-/+`），例如某些雲資源的 `name` 或 `identifier` 是 immutable 屬性，改它的唯一方式就是銷毀再建。對有狀態的服務（RDS、帶資料的 EBS volume），`-/+` 代表資料遺失或停機。Review 階段抓到這個 `-/+`，比 apply 到一半才發現便宜太多。

```text
# plan 輸出中要特別警惕的標記
# forces replacement  — 某個 immutable 屬性被修改，將觸發銷毀重建
# must be replaced    — 跟上面同義，Terraform 新版的表達方式
# will be destroyed   — 資源將被刪除

  # aws_db_instance.primary must be replaced
  -/+ resource "aws_db_instance" "primary" {
      ~ identifier = "app-prod" -> "app-production"  # forces replacement
        ...
    }
```

### 把 plan 結果貼回 PR

把 plan 結果貼回 PR 是讓 review 真正生效的做法。流程上，PR 觸發 CI 跑 plan，plan 輸出回貼成 PR comment，reviewer 連同程式碼 diff 一起看；approve 後才允許合併，合併才觸發 apply。

這裡有個取捨：plan 與 apply 之間若隔了很久，雲端實際狀態可能已經漂移（有人手動改了、或別的 PR 先 apply 了），導致 apply 時的 plan 跟 review 時看到的不一致。應對方式分保守與務實兩種。保守做法是 apply 前重跑一次 plan 並比對結果 — 一致才繼續，不一致就中斷。務實做法是在合併觸發 apply 時自動跑 plan 並只在無 destroy / replace 時自動執行，有 destroy / replace 就停下來要人確認。多數團隊從務實做法開始，到遇過一次 plan-apply 不一致的事故後才升級到保守做法。

### apply 失敗的回退邊界

infra apply 不像程式碼部署可以直接 rollback 到上一版 image — 中途失敗時部分資源已經建立、state 可能處於半完成狀態。例如 apply 建了一個新 subnet 但在建 route table 時 timeout，此時 subnet 存在於雲端和 state 裡，route table 只在雲端不在 state 裡（或反過來），下一次 plan 的計算基礎就不精準。

應對的紀律是：apply 失敗後，先跑一次 `terraform plan` 確認 state 與現實的差距，再決定是修正 code 重新 apply 還是手動清理殘留資源後 `terraform state rm`。在清理之前不要再改 code、不要連發第二次 apply — 第二次 apply 在不確定的 state 上跑，可能把問題擴大。

PR 流程的價值在這裡不只是事前審查，也是事後可追溯：每次變更都對應一個 commit 與一個 PR，要回溯時知道是哪次改的、為什麼改、誰 review 的。

## fmt 與 validate：最便宜的第一道檢查

`fmt` 與 `validate` 是進到任何安全掃描之前的基礎檢查，責任是擋掉格式不一致與語法 / 型別錯誤這類不需要動腦判斷的問題。它們跑得快（通常不到五秒）、沒有誤判空間，適合放在 CI 最前面當作快速 fail 的關卡。

`terraform fmt -check` 驗證程式碼是否符合標準排版。它本身不影響基礎設施行為，價值在於消除 diff 噪音：當每個人的編輯器縮排習慣不同，PR diff 會混入大量純排版變動，把真正的邏輯變更淹沒，reviewer 更容易看漏。統一格式後，diff 裡剩下的就是語意變更。在本地開發階段配合 editor plugin 或 pre-commit hook 在存檔時自動 fmt，讓 CI 的 fmt check 幾乎不會再 fail — 它存在的意義是攔住那些沒裝 plugin 的人。

`validate` 則檢查設定在語法與內部一致性上是否成立 — reference 到不存在的變數、型別不匹配、必填參數缺漏、module 呼叫的 source 解析不了，這些在 validate 階段就會報錯，不必等到 plan 連線雲端才發現。validate 需要先跑 `terraform init`，但可以用 `-backend=false` 跳過連線 state backend，這樣在 CI 裡不需要雲端憑證就能跑完。

```yaml
# .github/workflows/terraform.yml — plan 前的基礎檢查
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
      - run: terraform fmt -check -recursive
      - run: terraform init -backend=false
      - run: terraform validate
```

判讀上，fmt 與 validate 失敗代表的是「這份 code 還沒準備好被認真 review」，屬於作者自己該先修掉的問題，不該佔用 reviewer 注意力。把它們設成 CI 必過的 gate，作者在本地就會先跑、先修，PR 送出時已經是乾淨的。

## tflint / checkov / tfsec：抓壞寫法與安全漏洞

fmt 與 validate 確認 code「語法正確」，但語法正確的設定仍然可能是危險的設定。tflint、checkov、tfsec 這類靜態掃描工具承擔的是「語意正確」這層：在不實際建立資源的前提下，從 HCL 裡比對已知的壞寫法與安全反模式，把問題擋在 plan 之前。它們補的是 reviewer 肉眼容易漏掉的盲區 — 人會看漏一個 `0.0.0.0/0`，規則不會。

### 三者的側重

| 工具    | 側重領域                         | 典型命中                                          |
| ------- | -------------------------------- | ------------------------------------------------- |
| tflint  | provider 層正確性與慣例          | 棄用參數、region 不存在的 instance type、命名違規 |
| checkov | 安全與合規（CIS benchmark 導向） | S3 公開、未加密、缺少 log、IAM 過寬               |
| tfsec   | 安全反模式（HCL 結構導向）       | 敏感埠全開、未加密、hardcode secret               |

checkov 與 tfsec 的覆蓋範圍有重疊（都會掃 S3 公開與 SG 全開），差別在規則來源與報告格式。checkov 的規則對標 CIS benchmark 和多雲合規框架（AWS、Azure、GCP、Kubernetes），tfsec 更專注在 Terraform HCL 結構。兩者跑在一起時，重複的命中可以用其中一個的 skip 標記豁免。

### 兩個最常攔下的反模式

**S3 bucket 對外公開**。一個漏設 `block_public_access` 或 ACL 寫成 `public-read` 的 bucket，會讓裡面的物件對整個網際網路可讀。這類設定在 HCL 裡只是一兩行，肉眼 review 時很容易因為「看起來像樣板」而放過，但後果是資料外洩。checkov 規則 `CKV_AWS_19`（S3 bucket 未啟用 server-side encryption）和 `CKV_AWS_53`（block public access 未全開）會標記這類漏洞：

```hcl
# checkov 會攔下的寫法 — 缺少 block_public_access
resource "aws_s3_bucket" "data" {
  bucket = "acme-customer-data"
}

# 正確寫法 — 顯式關閉公開存取
resource "aws_s3_bucket_public_access_block" "data" {
  bucket                  = aws_s3_bucket.data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
```

**Security group 對全世界開放**。一條 ingress 寫成 `cidr_blocks = ["0.0.0.0/0"]` 加上 port 22 或 3306，等於把 SSH 或資料庫埠暴露給全網掃描器。tfsec 與 checkov 都會標記這種「敏感埠 + 全開 CIDR」的組合。這條規則跟[模組三：網路地基](/infra/03-network-foundation/)講的 security group 收斂原則是同一件事的兩端 — 模組三教怎麼把規則寫對，本章用靜態掃描確保寫錯時擋得下來。

```bash
# 三道掃描串在一起，任一 fail 就中斷
tflint --recursive
checkov -d . --quiet --compact
tfsec . --soft-fail=false
```

### 命中是候選不是判決

判讀這些工具的命中時，要區分「真漏洞」與「情境合理的例外」。並非每個 `0.0.0.0/0` 都是錯 — 一個對外的 HTTPS load balancer 在 port 443 開全網是設計本意。所以掃描的命中是候選不是判決。

多數工具支援用行內註解標記豁免。checkov 用 `#checkov:skip=CKV_AWS_260:ALB 443 對外是設計本意`，tfsec 用 `#tfsec:ignore:aws-elb-alb-not-public`。豁免的紀律是：每個 skip 都要寫理由、要在 PR 裡可見。沒有理由的 skip 跟關掉整條規則沒有差別 — review 時看到無理由的 skip 應該當成跟看到裸 `0.0.0.0/0` 一樣的警報。

把例外顯式化、留下為什麼豁免的紀錄，比關掉整條規則安全。隨時間累積的 skip 也要定期盤點：某個當初合理的例外，在架構演進後可能已經不再合理。

## Atlantis 與 GitHub Actions：自動化 plan 與 apply

把上述流程自動化，需要一個能監聽 PR 事件、在對的時機跑 plan 與 apply 的執行層。兩種常見做法是直接用 CI 平台（如 GitHub Actions）寫 workflow，或用 Atlantis 這類專為 Terraform PR 流程設計的工具。

### Atlantis

Atlantis 是一個常駐服務，掛在 git 平台的 webhook 上。PR 開啟時它自動跑 `plan` 並把結果貼回 PR comment，reviewer approve 後在 PR 留言 `atlantis apply`，它才執行 apply 並回報結果。它的價值在於把「誰能 apply、apply 前要不要 approve、plan 結果在哪看」這些規則收斂成一致的、可設定的流程。

Atlantis 內建的 state lock 語意在多 PR 並行時特別有用：當兩個 PR 都改到同一個 Terraform project，第二個 PR 的 plan 會被 lock 擋住，直到第一個 apply 完成或 PR 關閉。這避免了兩個 PR 各自拿到的 plan 基於不同的 state 快照、apply 時互相覆蓋的問題。用 GitHub Actions 要自己實作這個 lock 邏輯（通常靠 Terraform 自己的 state lock + workflow concurrency group），複雜度高得多。

Atlantis 的代價是它本身是一個要部署、要升級、要保護的常駐服務 — 它持有對雲端的寫入權限，所以它的部署環境必須嚴格控制存取。

### GitHub Actions

GitHub Actions workflow 的優點是不必額外維運服務、跟既有 CI 共用同一套 runner。缺點是 apply 的 gating 邏輯要自己用 workflow 條件拼出來。一個完整的 workflow 通常分成兩個 job：PR 觸發 plan job（跑 fmt / validate / scan / plan、把結果貼回 PR），合併到 main 才觸發 apply job。

無論哪種執行層，自動化的 apply 都需要對雲端的寫入權限，而這個權限怎麼來是整條管線的安全根基。這裡正是[模組二：身分與憑證地基](/infra/02-identity-credentials/)鋪設的 OIDC 兌現的地方 — 管線不該存放長期的 access key，而是在 runner 執行時用 OIDC 向雲端換取短期 token。

```yaml
# 合併到主幹後，用 OIDC 換短期憑證再 apply（呼應模組二）
jobs:
  apply:
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions:
      id-token: write   # 允許 runner 取得 OIDC token
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/infra-apply
          aws-region: ap-northeast-1
      - uses: hashicorp/setup-terraform@v3
      - run: terraform init
      - run: terraform apply -auto-approve
```

### 選型判準

| 考量         | GitHub Actions                  | Atlantis                             |
| ------------ | ------------------------------- | ------------------------------------ |
| 維運成本     | 無額外服務                      | 需部署 + 升級常駐服務                |
| state lock   | 靠 Terraform 自身 + concurrency | 內建 project lock、跨 PR 互斥        |
| apply gating | 自己用 environment rule 拼      | 內建 approve + `atlantis apply` 語意 |
| 跨 repo 一致 | 每 repo 各自寫 workflow         | 一套 server config 管所有 repo       |
| 適合規模     | 少量 repo、簡單流程             | 多 repo、需統一 apply 治理           |

判讀自動 apply 的邊界：對會觸發資源重建或刪除的高風險 plan，多數團隊會保留人工 apply 的關卡（Atlantis 的手動 `atlantis apply`、或 workflow 加 environment protection rule 要人按確認），不讓這類變更在合併瞬間無人看管地執行。自動化的目的是消除重複勞動與人為遺漏，不是把判斷也一起省掉。

## 知識留在 code，而不是留在個人腦中

走完整套 PR 流程後，infra 的真正收穫是知識從個人的記憶移到了 repo 裡。每一次「為什麼這個 security group 開這個埠」「為什麼這台機器選這個 instance type」的決策，都以 code + PR 描述 + review 討論的形式留下，新人讀 repo 就能還原當初的判斷，不必去問那個「只有他懂 infra」的人。基礎設施可被閱讀，等於它可被交接。PR 流程上線後，管理層可以從 repo 的 PR merge 歷史與 plan comment 確認所有 infra 變更都經過提案與審查——這本身就是稽核要求的變更紀錄證據，不需要額外產出。

### git revert 的能力與邊界

可 revert 是 PR 流程最直接的兌現。當某次變更引發問題，回退手段是 `git revert` 那個 commit 再走一次 PR 流程，讓基礎設施回到變更前的設定 — 跟回退一段壞掉的程式碼是同一個動作。對照手動操作的舊狀態：回退靠的是當事人記得自己改了什麼、手動在 Console 改回去，記錯或人不在就無從回退。把變更歷史留在 git，回退就從「依賴某人的記憶」變成「依賴版本紀錄」。

這份 revert 能力的邊界要講清楚。revert code 救得回的是「設定」，救不回已經被銷毀的狀態與資料：

- revert 掉一個刪除 RDS 的 commit，只是讓設定回到「該資源應該存在」。apply 時 Terraform 會試圖建一個新的空資料庫 — 但被刪掉的資料庫裡的資料不會跟著回來。
- rename 或 replace 類的變更 revert 後，可能再觸發一次資源重建 — 因為 `identifier` 又改回去了，而 identifier 是 immutable 屬性。
- apply 到一半失敗的 state 不能直接 revert code 修復，得先處理 state 與雲端現實的不一致。

stateful 變更的真正回退仍然靠備份與快照，這正是[模組五：核心服務上 IaC](/infra/05-core-services/) stateful 處理與[模組八：治理好習慣](/infra/08-governance-habits/) secret / state 保護要顧的事。把 git revert 當「設定層回退」就誠實，把它當「資料層回退」就會在事故裡踩空。

### 知識共享的判讀訊號

判讀一個團隊是否確實把知識留在 code 的訊號：當主要負責 infra 的人請假，其他人能不能只靠讀 repo 就理解現狀並安全地改一個小設定。如果答案是「得等他回來」，那不論工具鏈多完整，知識還在個人腦中，PR 流程只是形式。這個訊號比任何工具設定都更能反映 infra 的成熟度。

讓知識真正從個人腦中搬進 repo 的方式，除了 PR 流程本身，還需要組織層的配合 — 刻意的 review 輪替、on-call 輪值、配對操作。這條路線在[模組九：怎麼把 infra 推動起來](/infra/09-driving-adoption/)展開到組織層。本章解決的是技術機制 — code 留得住知識；模組九解決的是怎麼讓團隊實際願意走這套流程、把知識交出來。

## 跨分類引用

- → [CI/CD 教學](/ci/)：infra 管線用的就是這套驗證 / 發布 gate，plan / apply 對應 build / deploy 階段
- → [模組二：身分與憑證地基](/infra/02-identity-credentials/)：管線用 OIDC 取得 apply 權限，本章是該章 OIDC 設計的回報兌現處
- → [模組三：網路地基](/infra/03-network-foundation/)：security group 收斂原則，本章用 tfsec / checkov 在 CI 攔下寫錯的全開規則
- → [模組五：核心服務上 IaC](/infra/05-core-services/)：stateful 資源的保護策略，git revert 救不回資料層
- → [模組八：治理好習慣](/infra/08-governance-habits/)：secret / state 保護
- → [模組九：怎麼把 infra 推動起來](/infra/09-driving-adoption/)：本章把知識留在 code 的技術機制，在該章展開成組織層的採用與知識共享
- → [backend 模組七：資安與資料保護](/backend/07-security-data-protection/)：S3 公開、敏感埠全開這類掃描攔截的反模式，對應的資料保護原則
- → [團隊權限分級](/infra/02-identity-credentials/team-access-management/)：權限變更走 PR 流程，讓 policy 調整有審查紀錄
- → [職務交接設計](/infra/08-governance-habits/handover-design/)：PR 歷史是交接時的知識載體
