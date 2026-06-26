---
title: "從單一環境到環境分離：infra 需求的浮現過程"
date: 2026-06-26
description: "單一 EC2 + RDS 的結構在需要測試環境、多人協作時會撞到哪些操作極限，以及環境分離怎麼牽出身分、網路、變更流程等後續 infra 關注點"
weight: 1
tags: ["infra", "environment", "iac"]
---

多數服務的起點是一台運算實例加一台資料庫，部署方式是 SSH 進去拉 code 再重啟。這個結構在單人、單環境、低變更頻率的條件下運作正常，但它的隱性前提是：所有設定只有一份，且只有一個人在操作。機器的配置存在操作者的記憶裡，資料庫參數存在 Console 頁面上，security group 規則是建立時隨手設的。這些設定沒有被記錄在任何能回溯或重建的地方。

這個結構的操作極限會在兩個時間點浮現：第一次需要在正式環境以外的地方驗證變更時，以及第二個人開始操作同一組資源時。以下依序說明每個階段的操作現實與對應的 infra 需求。

## 資料庫變更需要驗證環境

應用新增功能時經常需要改資料庫的表結構 — 加欄位、改索引、拆表。這類操作（database migration）如果語法有誤或邏輯有缺，可能導致服務中斷或資料不一致。正常做法是先在非正式環境驗證通過，再推到 production 執行。

單一環境的情況下沒有驗證的場所。三種應對方式各有不同的風險邊界：

**直接在 production 執行**。成本最低，風險最高。migration 腳本跑下去的那一刻，正在使用服務的使用者直接承受後果 — 一個鎖住整張大表的 `ALTER TABLE` 會讓所有查詢卡住，一個 `DROP COLUMN` 刪錯欄位會造成不可逆的資料遺失。服務規模小、使用者少時代價尚可承受；一旦服務開始承載營收或外部依賴，這個做法的風險代價就超過了它省下的時間。

**手動複製一套環境**。到 Console 上照 production 的設定重新建一台 EC2、開一台 RDS、配一組 security group，得到一套「看起來一樣」的 staging。migration 先在 staging 驗證再推 production。這解決了驗證場所的問題，但引入了漂移問題 — 下一節說明。

**用程式碼描述環境，讓工具複製**。把 production 的設定寫成描述檔，用 Terraform 或 OpenTofu 根據同一份描述建出 staging。初始成本比手動複製高（要學工具、寫描述檔），但它保證了手動複製保證不了的一件事：staging 和 production 的結構來自同一份描述，差異只存在於刻意不同的參數（機器規格、備份天數）。這就是 Infrastructure as Code（IaC）的起點。

## 手動複製的環境會漂移

手動複製的 staging 在建立當天跟 production 一致。一個月後通常不再一致。

漂移的來源是日常操作中的局部調整：staging 的 security group 多了一條規則（某次除錯時加的，事後忘了刪）、production 的 RDS 參數被調過（線上出現慢查詢，DBA 改了 `work_mem` 但沒同步 staging）、staging 的 IAM role 多了一條 policy（測試新功能時加的，測完沒拿掉）。每一筆差異都很小，小到不值得專門同步，但它們會累積。

漂移引爆的時機跟產生的時機通常隔很遠。一個 migration 在 staging 通過、推到 production 失敗，排查半天後發現是一個月前的參數調整造成的 — staging 的 `work_mem` 跟 production 不同，剛好影響了這次 migration 的執行計畫。這種因果關係跨越時間的錯誤，排查成本遠高於錯誤本身。

漂移的根源是「兩套環境各自獨立維護」。只要兩份設定各自存在，同步就完全依賴操作者的記憶與紀律，而記憶會衰退、紀律會在壓力下鬆懈。結構性的解法是讓兩套環境共用同一份設定，差異只存在於刻意控制的參數。

## 同一份描述、不同的參數

IaC 工具消除漂移的方式，是把環境的結構寫成一份 module，用不同的參數值建出不同環境。程式碼只有一份，結構保證相同；差異全部收斂在參數裡，每一處「故意不同」都是明確且可審查的。

一個描述資料庫的 module：

```hcl
variable "instance_class" {
  type = string
}

variable "backup_retention_days" {
  type    = number
  default = 7
}

resource "aws_db_instance" "main" {
  engine                  = "postgres"
  instance_class          = var.instance_class
  backup_retention_period = var.backup_retention_days
}
```

Production 傳入大機器和長備份，staging 傳入小機器和短備份：

```hcl
# production
module "database" {
  source                = "./modules/database"
  instance_class        = "db.r6g.large"
  backup_retention_days = 14
}

# staging
module "database" {
  source                = "./modules/database"
  instance_class        = "db.t3.small"
  backup_retention_days = 3
}
```

兩個環境跑的是同一段 module 程式碼。引擎版本、連線方式、安全設定完全相同（寫在 module 裡、不是參數），差異只有機器規格和備份天數（刻意透過參數控制）。改動 module 一次、兩個環境同時生效，漂移的空間被結構性消除。

IaC 工具會維護一份 state 記錄，追蹤每個環境裡實際建了哪些資源和它們的屬性。改了程式碼後跑 `terraform plan`，工具會比對新的程式碼和 state 的差異，列出「會新增 / 修改 / 刪除什麼」。確認差異符合預期後才執行 `apply`。state 的角色與安全存放方式在[模組一：最小可行 IaC](/infra/01-minimal-iac/) 展開，環境的目錄結構與 module 設計在[模組四：環境分離與模組化](/infra/04-environment-separation/) 展開。

## 環境分離牽出的後續關注點

環境分離解決了「在哪裡驗證」和「為什麼 staging 跟 production 不同」的問題。但多環境運行後，一組後續的操作需求會依序浮現，每一個對應 infra 的一個能力層：

**身分與權限隔離**。三個環境代表三組資源。如果所有人對所有環境都有完整操作權限，一次誤操作就可能改壞 production。production 的修改權限應該比 staging 嚴格、操作身分應該分開。這是[模組二：身分與憑證地基](/infra/02-identity-credentials/)的範圍。

**變更審查流程**。多人同時操作 infra 時，沒有經過 review 的變更會互相覆蓋。把 infra 變更接上跟應用程式碼相同的 PR 流程 — 開分支、自動跑 plan、review 通過才 apply — 讓每一次改動都有提案、審查和歷史。這是[模組七：infra 走 PR 流程](/infra/07-infra-as-pr/)的範圍。

**機密值管理**。資料庫密碼、API key 這些機密值在有版本控制之前可能直接寫在 `.env` 或 CI 變數裡。一旦有了 IaC 和 git，這些值如果跟著程式碼進了版本歷史，就會隨著每一次 clone 擴散。機密值要存在專用的密鑰管理服務裡，程式碼只持有指向它的參照。這是[模組八：治理好習慣](/infra/08-governance-habits/)的範圍。

**可觀測性**。三個環境各自需要 log、metric 和告警，這些監控要跟環境本身一起建立，而非等服務中斷後才發現沒有可查的資料。這是[模組六：可觀測性與 log](/infra/06-observability-logging/) 的範圍。

**網路邊界**。三個環境如果共用同一個網段和防火牆規則，staging 的某個被入侵的服務可能橫向觸及 production 的資料庫。每個環境需要有自己的網路邊界。這是[模組三：網路地基](/infra/03-network-foundation/)的範圍。

這些關注點的共同根源是同一件事：當服務從單人單環境長成多人多環境，原本藏在記憶和手動操作裡的決策，必須變成可描述、可審查、可重建的規則。整套教材的地圖在[模組零：infra 是什麼](/infra/00-infra-mindset/)，每個模組各自處理一個能力層。

## 跨分類引用

- → [模組零：infra 是什麼](/infra/00-infra-mindset/)：責任邊界與成熟度階梯（從全手動到全程式碼治理的五階分級）的完整定義
- → [模組負一：還沒有 infra 的環境](/infra/before-infra/)：導入 IaC 之前的低成本護欄
- → [模組一：最小可行 IaC](/infra/01-minimal-iac/)：state 與 IaC 工具的選型與起步
- → [模組四：環境分離與模組化](/infra/04-environment-separation/)：目錄結構、module、參數化的完整設計
