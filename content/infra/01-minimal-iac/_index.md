---
title: "模組一：最小可行 IaC — state 地基與 Console 唯讀鐵律"
date: 2026-06-26
description: "Terraform / OpenTofu 選型、remote state 與 lock，以及「Console 只能看不能改」鐵律"
weight: 1
tags: ["infra", "iac", "terraform", "state"]
---

踏上成熟度階梯第二階（宣告式 IaC，也就是 state 檔誕生那一階，見模組零：infra 是什麼）的最小路徑，只做兩件具體的事：把 state 管好，並立下所有資源都走程式碼的鐵律。這兩件事決定了往後每一階的地基穩不穩 — state 是 IaC 工具對現實的唯一記憶，Console 唯讀鐵律則保證這份記憶不會在背後被偷偷改掉。其餘的網路、身分、服務都還沒上場，先把這兩件事釘死，後面的擴張才有可重現的起點。

## IaC 工具選型：宣告式狀態管理 vs 程式語言抽象

IaC 工具的核心職責是把「我要的基礎設施長什麼樣」描述成可版本控制的程式碼，再由工具負責算出現況與目標的差異並收斂。市場上的工具分成兩條路線，差別落在「用什麼語言描述」與「狀態由誰持有」這兩個軸上，而非功能多寡。

第一條路線是宣告式 DSL，代表是 Terraform 與其開源分支 OpenTofu。寫的是 HCL，描述的是資源的最終樣貌，工具自己維護一份 state 來追蹤每個資源的真實 ID 與屬性。這條路線適合團隊成員背景混雜、需要讓非專職後端的人也能讀懂 infra 定義的情境 — HCL 的閱讀門檻低，diff 直觀，review 時看得出「這個 PR 會新增一個 RDS、改掉一條 security group」。

第二條路線是用通用程式語言寫 infra，代表是 AWS CDK 與 Pulumi。寫的是 TypeScript、Python、Go 這類語言，靠迴圈、函式、類別來生成資源。這條路線適合 infra 邏輯本身複雜、需要大量條件分支與抽象複用的團隊，例如要根據環境清單動態生成數十組對稱資源。代價是 review 難度上升：一段 `for` 迴圈展開後到底建了哪些東西，得在腦中執行程式才看得出來，diff 不再等於變更本身。

CDK 與 Pulumi 同屬程式語言路線，但「狀態由誰持有」這個軸把它們再分開。CDK 把程式碼 synth 成 CloudFormation 模板，再交給 CloudFormation 服務端執行與追蹤，state 由 AWS 代管 — 沒有一份 tfstate 檔要自己存放、加密、回捲，也不需要額外的鎖表來防並行，這份「狀態維運外包給雲端」正是 CDK 在 AWS 生態內的賣點之一，代價是綁定 CloudFormation 與單一雲。Pulumi 走的是另一邊：它維護一份自己的 state，預設交給 Pulumi Cloud 託管，也能改用 S3 之類的後端自管 — 形態上更接近 Terraform 的 state 模型，state 的存放、保護與並行控制重回團隊手上。同一條程式語言路線，選 CDK 等於把 state 責任讓給雲端，選 Pulumi 則保留對 state 落點的掌控。

選型看的是團隊組成與變更的審查需求。若多數變更要跨職能 review、希望 diff 一眼可讀，宣告式 DSL 較划算；若 infra 由專職平台團隊維護、抽象複用的收益大於審查透明度的損失，程式語言路線較划算。Terraform 與 OpenTofu 之間，OpenTofu 是授權變更後社群分叉出的相容實作，HCL 與 provider 生態幾乎共用；選擇主要看對授權條款與治理模式的偏好，技術判準在這一階沒有實質差異。本模組後續一律以 HCL 示意，換成任一宣告式工具判準仍成立。

## state 是工具對現實的唯一記憶

state 是 IaC 工具用來記錄「上一次 apply 之後，每個資源在雲端真實長什麼樣」的快照，它的作用是讓工具能算出「現況」與「目標」之間的最小差異。沒有 state，工具每次都得把所有資源重新查一遍才知道該不該動，而且無法分辨「這個資源是我建的、該由我管」還是「別人手動建的、不歸我管」。

state 裡通常含有資源的真實 ID、相依關係，以及部分敏感屬性 — 例如資料庫的初始密碼、private key 的輸出值。這帶來兩條邊界。

第一條：state 絕不能進 git。state 含明文敏感值，一旦推進版控就等於把密碼寫進每個 clone 的歷史裡，事後 rotate 也清不掉 git 歷史。

第二條：state 不能只放本地。本地 state 的失敗模式是它把整份基礎設施的記憶綁在一台筆電上 — 換人接手、換台機器、或多人同時 apply 時，記憶就分裂了。兩個人各自拿著不同版本的本地 state 去 apply，工具會用各自過時的記憶去算差異，互相把對方建的資源判定成「不該存在、刪掉」，基礎設施被反覆來回破壞。

這兩條邊界共同指向同一個結論：state 需要一個團隊共享、有版本、有存取控制、且能防止同時寫入的存放處。這就是 remote state backend 要解的問題。

## remote state backend：自管 vs 託管

remote state backend 是把 state 從本地移到團隊共享儲存的機制，它要同時滿足三件事：持久保存、防止並行寫入衝突、以及保護敏感內容。達成方式分成自管儲存與託管服務兩種，差別在維運責任落在誰身上。

自管路線以雲端物件儲存加鎖機制為典型組合。以 AWS 為例，state 檔放 S3、用一張鎖表防止兩個人同時 apply：

```hcl
terraform {
  backend "s3" {
    bucket         = "acme-tf-state"
    key            = "prod/network/terraform.tfstate"
    region         = "ap-northeast-1"
    encrypt        = true
    dynamodb_table = "acme-tf-lock"
  }
}
```

這段設定的每一項都對應前一節的一條邊界，值得逐項拆開。`encrypt = true` 讓 state 在 S3 落地時加密，回應「state 含敏感值」的風險。承載 state 的 bucket 必須開 versioning：apply 寫壞或誤刪 state 時，versioning 是把記憶回捲到上一個正確版本的唯一退路，沒開的話一次壞寫就讓工具失去對現實的記憶。`dynamodb_table` 指向一張鎖表，apply 開始時寫入一筆鎖、結束才釋放，第二個人同時跑就會被擋下並提示鎖被誰持有 — 這正是本地 state 無法提供、卻是多人協作底線的並行保護。`key` 則是 state 在 bucket 內的路徑，這裡先用 `prod/network` 之類的分層命名，實際怎麼依環境切分 state 留待模組四：環境分離與模組化展開。

託管路線把這些維運細節包起來，由 Terraform Cloud、Spacelift 這類平台代管 state、鎖與加密，附帶 web UI 與 audit log。判讀訊號是團隊規模與維運餘裕：自管 backend 的成本是要自己把 bucket versioning、加密、鎖表、IAM 權限配對，配錯任何一項都可能讓 state 失去保護；託管服務用月費換掉這份配置與維運負擔，代價是 state 託付給第三方、且進階治理功能常綁在付費級距。小團隊起步、不想第一週就花在配 backend 上，託管較划算；對 state 存放位置有合規或主權要求、或希望基礎設施盡量自持的團隊，自管較划算。

## Console 唯讀鐵律：把 Console 當儀表板，不當方向盤

Console 唯讀鐵律是一條操作紀律：雲端 Console 只用來觀察與排查，所有會改變資源的動作都回到程式碼走 apply。這條紀律維護的是 state 與現實的一致 — IaC 工具能正確運作的前提，是它的 state 反映得了真實世界，而每一次在 Console 點按鈕改設定，都是在 state 不知情的情況下動了現實。

這種 state 與現實的分歧叫 drift。drift 的代價會延遲引爆，而非當下浮現。某人在 Console 臨時把一條 security group 規則打開救火，state 並不知道；下一次別人為了不相干的變更跑 apply，工具拿過時的 state 去比對，會把那條手動規則判定成「不在我的記憶裡、刪掉」，於是悄悄關掉，救火的洞重新出現，而且沒人在 PR 裡看得到這件事發生過。Console 改得越多、與程式碼分歧越久，某次例行 apply 就越可能掃掉一批沒人記得的手動設定。

鐵律越早立越好，因為回頭納管的代價隨時間累積。手動建的資源要納入 IaC，得先用 `terraform import` 把現實資源綁進 state，再補一段與現實完全吻合的 HCL：

```bash
terraform import aws_security_group.web sg-0abc123def456
```

import 只把資源 ID 寫進 state，不會幫忙生程式碼。那個資源在 Console 上被點出來的每一個屬性 — 每條 ingress 規則、每個 tag、每項關聯設定 — 都得一字不差地補成 HCL，任何一項對不上，下次 apply 就會試圖把現實改回程式碼寫的版本。一個資源還能忍，等到累積了幾十個各自手動微調過的資源才想納管，逆向工程的工作量會大到讓人乾脆放棄，基礎設施就此分裂成「程式碼管的」與「沒人敢動的」兩塊。第一天就立鐵律，要納管的存量永遠是零。

讓鐵律落地靠的是權限、不是自律。光靠約定「別在 Console 改」撐不久，救火當下手最快的永遠是 Console。真正讓鐵律站得住的，是把人的日常身分收斂成唯讀、把寫入權限留給跑 apply 的自動化身分，讓「在 Console 改不動」變成預設狀態 — 這道權限地基屬於模組二：身分與憑證地基的範圍，本階先確立紀律方向。

## 最小可行：能 apply 出一個完整環境的最小資源集合

最小可行 IaC 的目標是用最少的資源，跑出一條「改程式碼 → review → apply → 環境真的變了」的完整迴路。它承擔的責任是驗證地基本身能動，把所有服務都搬上來是後面的事。判準是這套程式碼能獨立 apply 出一個雖小但自洽、別人能重現的環境。

這一階的最小集合通常包含：一個設定好 versioning、加密與鎖表的 remote state backend；一個收斂後人類唯讀的身分權限基線；一個能放東西的網路骨架（一個 VPC 加最少的 subnet）；以及一個微不足道但真實存在的資源（例如一個 S3 bucket 或一台最小的測試機），用來證明 apply 確實作用到了雲端。把這個微小資源刻意留在最小集合裡，是因為它是最便宜的端到端驗證 — apply 跑完後它真的出現、`terraform destroy` 後它真的消失，就證明從程式碼到雲端的整條鏈路是通的。

刻意不放進來的東西同樣重要：正式的應用服務、資料庫、跨環境的複製、複雜的模組抽象，全部留到地基驗證通過之後。在 state 與 Console 唯讀都還沒站穩前就堆服務，等於把房子蓋在還沒灌漿的地基上。網路骨架怎麼長、身分怎麼切，分別由模組三：網路地基與模組二：身分與憑證地基接手深入；這一階只需要它們各自最薄的一層，湊出一個能 apply、能 destroy、能交接的閉環。

## 章節文章

| 文章                                                                                         | 主題                                                                                                    |
| -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| [IaC 工具選型與 state 地基](/infra/01-minimal-iac/iac-tool-state-backend/)                   | Terraform / OpenTofu / CDK / Pulumi 選型判準，state 作為唯一記憶，remote state backend 的自管與託管路線 |
| [Console 唯讀鐵律與最小可行資源集合](/infra/01-minimal-iac/console-readonly-minimal-viable/) | Console 唯讀的操作紀律、drift 的延遲引爆與偵測，以及第一個完整 apply 迴路的最小資源集合                 |

## 跨分類引用

- → [模組二：身分與憑證地基](/infra/02-identity-credentials/)：Console 唯讀鐵律靠權限落地，人類唯讀、自動化身分持有寫入權
- → [模組三：網路地基](/infra/03-network-foundation/)：最小集合裡的 VPC 與 subnet 怎麼設計
- → [模組四：環境分離與模組化](/infra/04-environment-separation/)：state 的 key 怎麼依環境切分、state 跟環境怎麼對應
- → [模組七：infra 走 PR 流程](/infra/07-infra-as-pr/)：state 變更與 apply 怎麼納入 review
