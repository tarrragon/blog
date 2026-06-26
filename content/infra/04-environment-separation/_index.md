---
title: "模組四：環境分離與模組化"
date: 2026-06-26
description: "dev / staging / prod 切分、目錄結構 vs workspace、用可重用 module 避免環境漂移"
weight: 4
tags: ["infra", "iac", "environment", "module"]
---

從目錄結構就定好環境邊界的專案，dev 跟 prod 是兩棵獨立的 state 樹、改錯一邊不會波及另一邊；等資源都長出來、流量都上線了才回頭切的專案，每一次 retrofit 都在帶電作業，動到的是正在服務客戶的網路與身分。同樣一套 module、同樣的工程師，差別只在「環境邊界是設計出來的、還是事後補的」，而這個差別在第一天幾乎零成本、在第一百天可能是一個季度的遷移專案。這一章談的是怎麼讓 dev 跟 prod 共用同一套 code、卻不互相污染，以及已經單環境建好地基的人怎麼安全地補上這條邊界。

## 環境分離從第一天的目錄結構就定好

環境分離的本質是把「同一套基礎設施定義」複製成多份隔離的執行實例，每份有自己的 state、自己的雲端資源、自己的故障半徑。它承擔的責任是讓 dev 的實驗、staging 的驗證、prod 的真實流量彼此不可見也不可達 — 在 dev 跑壞一個資料庫、套錯一條 security group 規則，prod 完全無感。

這個邊界要在第一天就用目錄結構表達出來，原因是 state 一旦混在一起就難以無痛拆開。Terraform 這類工具用 state 檔記錄「哪個資源由哪段 code 管理」，如果 dev 跟 prod 的資源都登記在同一份 state，後續想把 prod 移出去，等於要對正在服務的資源做 `state mv` 或 import/remove 操作 — 任何一步算錯，工具可能判定資源該銷毀重建，而那是 prod 的資料庫。第一天就分目錄，dev 與 prod 從來不曾共用 state，這個風險根本不存在。

判讀訊號很簡單：如果現在只有一份 `main.tf`、裡面同時宣告了 `dev-db` 跟 `prod-db`，這個專案已經欠下環境分離的債，債齡每天都在增加。下一步路由是先確立目錄骨架，再決定差異怎麼參數化。

## 目錄分離 vs Terraform workspace 的取捨

切分環境有兩條主流路徑：每個環境一個獨立目錄（各自持有 backend 與 state），或共用一份 code 用 Terraform workspace 切換不同 state。兩者都能讓 state 隔離，差別在「環境差異藏在哪裡」以及「誤操作的故障半徑多大」。

在挑這兩條路之前，先把它們放回完整的分離強度光譜：環境分離橫跨一條從帳號到 workspace、隔離由粗到細的階梯，目錄與 workspace 只是相鄰的兩格，依隔離需求與維運成本取捨決定落在哪一格。最粗也最強的是帳號級隔離 — dev 與 prod 落在不同雲端帳號，憑證、計費與權限邊界天然分開，帳號邊界讓誤操作止於單一帳號（見[模組二：身分與憑證地基](/infra/02-identity-credentials/)）。次強的是每環境一個獨立 repo，把 code、IAM 權限與 CI pipeline 都按環境切開，適合各環境由不同團隊維護或受不同合規等級約束。再往細是本章主要討論的目錄分離 — 同一 repo 內各環境有獨立目錄與 state，邊界仍顯式、但共用一套 code 與一組權限。最細的是 workspace，code 完全共用、只在執行期切換 state。光譜越靠粗的一端，隔離越強、跨環境共用越少、初始與維運成本越高；越靠細的一端，重複越少、邊界越隱性。多數早期團隊在目錄分離這一格落腳，因為它在顯式邊界與維運成本之間平衡得宜；當隔離需求升高（例如 prod 要法規等級的帳務與權限隔離），再沿光譜往帳號級或獨立 repo 移。

目錄分離把每個環境寫成可獨立進入的工作目錄，差異透過各自的 `terraform.tfvars` 表達，prod 的 backend 設定、變數值、甚至 provider 版本都各自鎖定。它的代價是目錄之間有重複的 boilerplate，好處是邊界顯式 — 你 `cd` 進哪個目錄、apply 就只會動那個環境，prod 的 state 位址寫死在 prod 目錄的 backend 設定裡，不會因為忘記切換而打錯環境。

目錄分離的 boilerplate 重複可以用 Terragrunt 這類工具收斂。Terragrunt 的存在理由正是把跨環境目錄共通的 backend、provider、module 呼叫抽成一份範本，各環境目錄只留差異值，等於在保留目錄顯式邊界的前提下補上一層 DRY。它划算的情境是環境數量多、共通 boilerplate 開始拖慢維護時，這層強化值得引入；環境只有兩三個時，直接維護幾份目錄的成本通常還低於多引入一個工具與它的學習曲線。

```text
infra/
├── modules/                  # 可重用模組、不含任何環境專屬值
│   ├── network/
│   ├── database/
│   └── service/
└── environments/
    ├── dev/
    │   ├── main.tf           # 呼叫 modules、傳 dev 參數
    │   ├── backend.tf        # state 指向 dev 專屬位址
    │   └── terraform.tfvars  # dev 的差異值
    ├── staging/
    │   └── ...
    └── prod/
        ├── main.tf
        ├── backend.tf        # state 指向 prod 專屬位址
        └── terraform.tfvars  # prod 的差異值
```

Workspace 共用同一份 code、用 `terraform workspace select prod` 在執行期切換 state。它的好處是零重複，所有環境的 code 保證同步；代價是環境差異只能靠 `terraform.workspace` 在 code 裡寫條件判斷，而當前選中哪個 workspace 是 shell 的隱性狀態 — 在 dev workspace 以為自己在改 dev、其實上一個指令切到了 prod，apply 下去才發現故障半徑是 prod。這個隱性狀態正是早期最該避免的失誤來源。

早期推薦目錄分離，理由是故障半徑與認知負荷的取捨在小團隊明顯偏向「顯式邊界」這一側：團隊還沒有成熟的 CI gate 攔截誤 apply，顯式目錄是最便宜的防呆。Workspace 較划算的情境是環境數量多且高度同構（例如每個客戶一個隔離環境、差異只有名稱與配額），重複目錄的維護成本開始超過 workspace 隱性狀態的風險時，再切過去。每個環境的 state 要怎麼各自隔離、backend 怎麼設定，見[模組一：最小可行 IaC](/infra/01-minimal-iac/)。

## module 化：同一套 code、不同參數

Module 是把一組會被多環境重複使用的資源封裝成有輸入參數的單元，承擔的責任是讓 dev 與 prod 共享同一份邏輯定義、只在參數上分歧。沒有 module 時，dev 與 prod 各自維護一份 copy-paste 的資源宣告，兩份會隨時間漂移 — 有人只在 prod 補了一條 security group 規則、忘了同步 dev，於是「dev 能跑、prod 卻爆掉」或更糟的「dev 測過了、prod 行為不同」。

避免漂移的關鍵是讓環境之間唯一合法的差異來源是傳進 module 的參數，而不是 module 內部的 code 分支。Module 內部不寫 `if env == "prod"` 這類判斷，所有環境相關的值都從 `variable` 進來：

```hcl
# modules/database/variables.tf — module 只宣告它需要什麼參數
variable "instance_class" {
  type = string
}

variable "multi_az" {
  type    = bool
  default = false
}

variable "backup_retention_days" {
  type    = number
  default = 7
}
```

```hcl
# environments/prod/main.tf — prod 傳自己的值
module "database" {
  source                = "../../modules/database"
  instance_class        = "db.r6g.xlarge"
  multi_az              = true
  backup_retention_days = 30
}
```

這樣 dev 與 prod 跑的是位元層級相同的 module code，差異全部收斂在 `main.tf` 的呼叫參數裡、一眼可審。判讀訊號是 review 時只要 diff 各環境的參數區塊就能看完所有環境差異；如果發現有人為了某環境的特例去改 module 內部，那是漂移正在發生的徵兆，該把特例改寫成新的參數。核心服務怎麼用 module 跨環境重用，見[模組五：核心服務上 IaC](/infra/05-core-services/)。

## 環境差異參數化：prod 放大、dev 縮小

環境之間真正該不同的是規模與冗餘等級，而這些差異全部表達成參數值、不表達成不同的 code。Prod 承擔真實流量與可用性承諾，所以跨多個可用區（multi-AZ）部署、機器規格放大、備份保留更久、開啟刪除保護；dev 承擔的是迭代速度與成本控制，所以單 AZ、最小機型、短備份甚至無備份，壞了重建即可。

把這些差異參數化的好處是「環境拓樸的形狀一致、只有刻度不同」。Dev 與 prod 都經過同一段 module 邏輯，prod 不會出現一段 dev 從未執行過的 code path — 真正上線的設定，在 dev 已經以縮小版驗證過邏輯正確性。常見陷阱是把成本差異做成「dev 直接砍掉某個元件」：例如 dev 為了省錢不建負載平衡器、prod 才建，結果 prod 的 LB 相關設定從來沒在 dev 測過。較划算的做法是 dev 也建同型元件、只把規格與數量縮到最小，讓拓樸保持同構、只縮放刻度。

邊界在於少數差異無法只靠刻度表達 — 例如 prod 需要合規要求的稽核 log、dev 不需要。這類用 `count` 或 `for_each` 配一個布林參數開關，仍然走參數化、不分叉 code。跨可用區與冗餘的網路面怎麼鋪，見[模組三：網路地基](/infra/03-network-foundation/)。

## retrofit 路徑：把單環境拆成 per-env module

很多專案是先在單一環境把 IAM、VPC、核心資源都建起來、跑通了，才意識到需要環境分離 — 這是常見且合理的演進順序，尤其是先救火上線、之後才回頭納管的情況。Retrofit 的目標是在不破壞正在服務的資源前提下，把這份「隱含為 prod」的單環境，重構成「modules + per-env 呼叫」的結構，並讓現有資源平移成 prod 環境。承接[模組二：身分與憑證地基](/infra/02-identity-credentials/)與[模組三：網路地基](/infra/03-network-foundation/)先建好的單環境地基，這一段就是把它們納入 per-env 管理的路線。

安全的步驟順序是先重構 code、再動資源歸屬，且每一步都用 `terraform plan` 確認「零變更」：

1. **把現有資源宣告抽成 module**：把 `main.tf` 裡的資源搬進 `modules/`、原地用 module 呼叫取代，所有值先寫死成現況。此時 `plan` 必須顯示無任何新增或銷毀 — 只是重新組織 code，資源在 state 裡的位址若有變，用 `moved {}` 區塊宣告搬遷、避免工具誤判為「銷毀舊的、建新的」。
2. **把寫死的值換成 prod 的參數**：把現況值搬進 `environments/prod/terraform.tfvars`，module 改吃參數。`plan` 仍須零變更，因為參數值就等於現況值。
3. **建立其他環境目錄**：複製 prod 的呼叫結構成 `environments/dev/`，給它自己的 backend（獨立 state）與縮小的參數值。這一步是純新增、不碰 prod。
4. **逐一驗證**：先在 dev `apply` 出一套完整的縮小版環境、確認 module 在新環境也能 plan/apply 乾淨，再回頭確信 prod 的重構沒有副作用。

最大的風險集中在前兩步：現有資源是活的，任何讓工具判定「需要替換」的改動，對 IAM 角色可能是短暫權限真空、對 VPC 可能是子網重建導致服務中斷。防護是把每一次 `plan` 的輸出當成必須為零的驗收條件，非零就停下來查 `moved` 區塊或參數值哪裡跟現況不符。狀態危險的訊號是 `plan` 出現任何 `destroy` 或 `forces replacement`，在 prod 路徑上這幾乎都該先暫停。第二個風險是 state 操作本身 — retrofit 期間務必先備份 state 檔，`state mv` 與 `moved` 區塊優先用後者（宣告式、可 review、可回滾），手動 `state mv` 留給 `moved` 表達不了的跨 module 搬遷。整個 retrofit 走 PR 流程、讓 plan 輸出在 review 時可見，見[模組七：infra 走 PR 流程](/infra/07-infra-as-pr/)。

## 章節文章

| 文章                                                                                                                              | 主題                                                                                                        |
| --------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| [環境分離與模組化 — 目錄結構、module 參數化與 retrofit 路徑](/infra/04-environment-separation/directory-module-parameterization/) | 用目錄結構隔開 dev 與 prod 的 state，用 module 讓環境共用同一套邏輯只差參數，以及單環境跑起來後怎麼安全拆分 |

## 跨分類引用

- → [模組一：最小可行 IaC](/infra/01-minimal-iac/)：每個環境的 state 怎麼隔開
- → [模組五：核心服務上 IaC](/infra/05-core-services/)：核心服務怎麼用 module 跨環境重用
