---
title: "Console 唯讀鐵律與最小可行資源集合"
date: 2026-06-26
description: "Console 只用來看不用來改的操作紀律、drift 的延遲浮現與偵測，以及能跑出第一個完整 apply 迴路的最小資源集合"
weight: 2
tags: ["infra", "iac", "terraform", "drift"]
---

state 管好之後，下一件要釘死的事是保證 state 與現實不會分歧。[IaC 工具選型與 state 地基](/infra/01-minimal-iac/iac-tool-state-backend/)建立了 state 作為工具記憶的角色，這篇處理的是怎麼讓這份記憶不被背後偷改 — Console 唯讀鐵律，以及怎麼用最小資源集合驗證整條 IaC 鏈路端到端可運作。

## Console 唯讀鐵律：把 Console 當儀表板，不當方向盤

Console 唯讀鐵律是一條操作紀律：雲端 Console 只用來觀察與排查，所有會改變資源的動作都回到程式碼走 apply。這條紀律維護的是 state 與現實的一致 — IaC 工具能正確運作的前提，是它的 state 反映得了真實世界，而每一次在 Console 點按鈕改設定，都是在 state 不知情的情況下動了現實。

### drift 的延遲浮現

state 與現實的分歧叫 drift。drift 的後果在後續某次 apply 時才浮現——工具用過時的 state 比對雲端現況、把手動設定判定為「不該存在」並覆蓋掉，手動改的當下一切正常。手動改的當下一切正常，後果要等到下一次不相關的 apply 才出現。

常見的 drift 路徑：在 Console 手動加了一條 security group 規則（例如讓外部監控系統連進來），state 不知道這條規則存在。後續某次 apply 時，工具比對 state 和雲端現況、把這條規則判定為「不在記憶裡」而刪除。同樣的機制也發生在手動調整的 RDS parameter group（例如增加 `max_connections`）— 後續 apply 會把參數重設回程式碼裡的值。

Console 改得越多、與程式碼分歧越久，某次例行 apply 就越可能掃掉一批沒人記得的手動設定。drift 的累積是單調遞增的 — 每一次手動改動都加一筆，沒有任何自然機制會讓它減少。

### drift 偵測

主動偵測 drift 的方式是定期跑 `terraform plan` 而不做 apply — plan 的輸出會列出「code 描述的狀態」與「雲端現況」之間的差異。如果 plan 在沒有 code 變更的情況下顯示非零差異，代表有人在背後動了資源。

```bash
# 定期 drift 偵測：plan 結果非零就告警
terraform plan -detailed-exitcode
# exit code 0 = 無差異, 1 = 錯誤, 2 = 有差異
```

把這個 plan 接進 CI，讓 drift 在累積之前就被發現。判讀 plan 輸出時，重點看那些「會被 Terraform 改回去」的差異 — 它們就是手動變更的痕跡。

### import 的痛苦

鐵律越早立越好，因為回頭納管的代價隨時間累積。手動建的資源要納入 IaC，得先用 `terraform import` 把現實資源綁進 state，再補一段與現實完全吻合的 HCL：

```bash
terraform import aws_security_group.web sg-0abc123def456
```

import 只把資源 ID 寫進 state，不會幫忙生程式碼。那個資源在 Console 上被點出來的每一個屬性 — 每條 ingress 規則、每個 tag、每項關聯設定 — 都得一字不差地補成 HCL。任何一項對不上，下次 apply 就會試圖把現實改回程式碼寫的版本 — 對 security group 來說可能是把一條正在用的規則刪掉，對 RDS 來說可能是觸發一次重啟。

Terraform 1.5 之後提供了 `import` 區塊，可以在 HCL 裡宣告式地寫 import，配合 `terraform plan -generate-config-out=generated.tf` 自動生成對應的資源描述。這比手寫減少了大量逆向工程，但生成的 code 仍然需要人工確認每一個屬性是否正確 — 自動生成是起點，不是終點。

```hcl
import {
  to = aws_security_group.web
  id = "sg-0abc123def456"
}
```

import 成本隨資源數量非線性增長。一個資源的逆向工程可控，幾十個各自手動微調過的資源累積起來，團隊會停止嘗試納管，環境分裂成 IaC 管理的部分和手動管理的部分。第一天就立鐵律，要納管的存量永遠是零。

### 鐵律靠權限落地，不靠自律

光靠約定「別在 Console 改」撐不久，救火當下手最快的永遠是 Console。真正讓鐵律站得住的，是把人的日常身分收斂成唯讀、把寫入權限留給跑 apply 的自動化身分，讓「在 Console 改不動」變成預設狀態。

這道權限地基屬於[模組二：身分與憑證地基](/infra/02-identity-credentials/)的範圍，本階先確立紀律方向：人類日常用的 IAM 身分只有 `ReadOnlyAccess`，寫入權限只存在於 CI pipeline 使用的 role，這個 role 靠 OIDC 取得短期憑證（不存長期 key）。具體的 IAM 設計和 OIDC 信任關係在模組二展開。

## 最小可行：能 apply 出一個完整環境的最小資源集合

最小可行 IaC 的目標是用最少的資源，跑出一條「改程式碼 → review → apply → 環境真的變了」的完整迴路。它承擔的責任是驗證地基本身能動，把所有服務都搬上來是後面的事。判準是這套程式碼能獨立 apply 出一個雖小但自洽、別人能重現的環境。

### 最小集合的組成

| 資源                         | 職責                           | 驗證標準                     |
| ---------------------------- | ------------------------------ | ---------------------------- |
| S3 bucket + DynamoDB（鎖表） | remote state backend           | state 能寫入、鎖能取得和釋放 |
| IAM role（唯讀 + apply）     | 人類唯讀、自動化寫入的身分基線 | 人登入後 Console 改不動東西  |
| VPC + 最少的 subnet          | 網路骨架                       | 資源能被放進正確的 subnet    |
| 一個微小的真實資源           | 端到端驗證                     | apply 出現、destroy 消失     |

把一個微小資源（例如一個 S3 bucket 或一台最小的測試 EC2）刻意留在最小集合裡，是因為它是最便宜的端到端驗證。apply 跑完後它確實出現、`terraform destroy` 後它確實消失，就證明從程式碼到雲端的整條鏈路是通的。

```hcl
resource "aws_s3_bucket" "smoke_test" {
  bucket = "acme-smoke-test-${var.env}"

  tags = {
    purpose = "validate-iac-pipeline"
    env     = var.env
    owner   = "platform"
  }
}
```

### 刻意不放進來的東西

正式的應用服務、資料庫、跨環境的複製、複雜的模組抽象，全部留到地基驗證通過之後。在 state 與 Console 唯讀都還沒站穩前就堆服務，等於把房子蓋在還沒灌漿的地基上。

常見的過早引入包括：在最小集合裡就加 RDS（state 操作出問題時資料庫可能被影響）、在還沒有環境分離前就建多層 module 嵌套（驗證地基的複雜度不應該來自抽象層）、在一個人開發時就配好 Atlantis 或 Terraform Cloud 的完整 PR 流程（固定成本太高、且需要[模組七](/infra/07-infra-as-pr/)的完整護欄才能發揮價值）。

網路骨架怎麼長、身分怎麼切，分別由[模組三：網路地基](/infra/03-network-foundation/)與[模組二：身分與憑證地基](/infra/02-identity-credentials/)接手深入；這一階只需要它們各自最薄的一層，湊出一個能 apply、能 destroy、能交接的閉環。

### 驗證閉環

最小集合就位後的驗證步驟：

1. `terraform init` — 確認 backend 設定正確、provider 能下載
2. `terraform plan` — 確認 plan 輸出符合預期、沒有意外的 destroy 或 replace
3. `terraform apply` — 確認資源在雲端確實出現
4. `terraform plan`（再跑一次）— 確認輸出是零差異，代表 state 與現實一致
5. `terraform destroy` — 確認資源能被乾淨拆除（smoke test 資源）

第四步「再跑一次 plan」是容易被跳過卻最關鍵的一步。如果第一次 apply 之後立刻 plan 就出現差異，代表 provider 的行為和 HCL 描述之間有落差（例如某些屬性是雲端自動設的、HCL 沒寫），這類落差要在最小集合階段就修掉，等到正式服務上線後再修，成本會高很多。

最小可行 IaC 跑通後，下一步是收斂身分與憑證——把 Console 唯讀鐵律從紀律升級成權限限制，見[模組二：身分與憑證地基](/infra/02-identity-credentials/)。

## 跨分類引用

- → [IaC 工具選型與 state 地基](/infra/01-minimal-iac/iac-tool-state-backend/)：state 怎麼管、backend 怎麼選
- → [模組二：身分與憑證地基](/infra/02-identity-credentials/)：Console 唯讀鐵律靠權限落地，人類唯讀、自動化身分持有寫入權
- → [模組三：網路地基](/infra/03-network-foundation/)：最小集合裡的 VPC 與 subnet 怎麼設計
- → [模組七：infra 走 PR 流程](/infra/07-infra-as-pr/)：state 變更與 apply 怎麼納入 review
