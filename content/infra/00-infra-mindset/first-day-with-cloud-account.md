---
title: "拿到雲端帳號的第一天"
date: 2026-06-30
description: "被指派 infra 工作、拿到 AWS 或 GCP 帳號、不確定該先做什麼時讀 — 第一小時安全底線、帳號現況判讀、後續學習路線分流"
weight: 4
tags: ["infra", "aws", "onboarding", "iam"]
---

這篇寫給一種特定的讀者：你的專業可能是後端、前端、資料工程或其他領域，但因為組織需要，你被指派處理雲端基礎設施。公司（或主管）給了你一個 AWS / GCP / Azure 帳號，你登入之後看到一個很大的 Console，不確定該做什麼、也不確定動了什麼會出事。

這是 infra 工作最常見的真實入口。比起從零自學建一套環境，「接到指派、拿到帳號、搞清楚狀況」才是多數工程師第一次碰 infra 的方式。

這篇用 AWS 為主要範例。GCP 和 Azure 的判讀邏輯相同（安全底線 → 現況盤點 → 路線分流），但具體服務名稱、IAM 模型和 Console 操作位置不同。

## 第一小時：安全底線

登入帳號後，在做任何其他事之前先完成這些。這些步驟的共同目的是確保帳號的存取控制處於安全狀態——雲端帳號被入侵的代價遠高於本機電腦被入侵，因為雲端資源可以在幾分鐘內被大量建立（產生帳單）或被刪除（資料遺失）。

### 確認 root 帳號的 MFA

Root 帳號是雲端環境的最高權限，能做任何事，包括關閉整個帳號。如果 root 帳號沒有 MFA（Multi-Factor Authentication，多因子驗證），任何拿到 root 密碼的人都能完全控制整個環境。

確認路徑（AWS）：Console 右上角帳號名稱 → Security credentials → Multi-factor authentication (MFA)。如果顯示「No MFA device」，立刻設定一個——手機 app（Google Authenticator / Authy）或硬體 key（YubiKey）都可以。

如果你拿到的帳號是公司用 AWS Organizations 開出來的子帳號，子帳號 root 的密碼和 MFA 是獨立的——管理帳號無法代設。子帳號 root 通常需要先用帳號 email 做密碼重置才能首次登入。確認 root MFA 後，日常操作用 IAM Identity Center 登入。

### 確認你的登入身分

你登入用的是哪種身分？這決定了你的權限範圍和操作方式。

**IAM user**：Console 右上角會顯示 `username @ account-id`。這是最傳統的登入方式——帳號管理員幫你建了一個使用者，給了你一組帳密。

**IAM Identity Center（SSO）**：你透過一個特別的登入頁面（通常是 `https://d-xxxxxxxxxx.awsapps.com/start`）登入，然後選擇帳號和角色。這是較新的做法，多帳號組織常用。

**Root 帳號**：Console 右上角顯示帳號 email 而非 username。如果你拿到的是 root 帳號的帳密，日常操作應該換成 IAM user 或 SSO 登入——root 帳號只在需要 root-only 操作（如設定 MFA、關閉帳號）時使用。建立 IAM user 的方式見模組一的[動手前的前提](/infra/01-minimal-iac/iac-tool-state-backend/)段。

### 檢查既存的 access key

帳號如果被前人用過，可能有暴露風險的 access key——之前的管理員建了 IAM user、生了 key，但那組 key 可能已經寫在某個 Git repo 或環境變數裡而沒有停用。

確認路徑：Console → IAM → Users → 逐一點每個 user → Security credentials 分頁 → Access keys。檢查每組 key 的狀態（Active / Inactive）和建立時間。超過 90 天未 rotate 的 Active key 是風險——帳號接手後優先 rotate 或停用這些 key。如果帳號裡沒有任何 IAM user，這步跳過。

### 確認 CloudTrail 是否開啟

CloudTrail 記錄帳號內所有 API 操作（誰在什麼時間做了什麼）。AWS 預設會開啟 90 天的事件歷史，但長期保存需要建一個 Trail 把 log 寫到 S3。

確認路徑：Console 搜尋 CloudTrail → Dashboard。如果有 Trail 已建立，表示操作紀錄有長期保存。如果只有預設的 Event history，90 天前的紀錄會消失——這是一個需要但不緊急的改善點，[模組六：可觀測性](/infra/06-observability-logging/)會展開。

現階段只需要確認 CloudTrail 存在，不需要馬上改它。

### 設定帳單警報

雲端帳單是開放式的——資源跑著就持續產生費用，被入侵後被開出大量資源更可能在幾小時內累積數千美元帳單。設一個帳單警報，超過閾值時收到通知。

設定路徑（AWS）：Console 搜尋 Billing → Budgets → Create budget → Cost budget。設一個月預算（如 $50 或 $100，依你的環境規模），超過 80% 和 100% 時發 email 通知。

## 帳號現況判讀：空帳號還是有東西？

安全底線做完後，下一步是搞清楚帳號的現況。這決定了你接下來走哪條路線。

### 怎麼判斷

EC2 Dashboard 只顯示當前 region 的資源。Console 右上角有 region 選擇器——先切幾個主要 region（us-east-1、ap-northeast-1、ap-southeast-1）看一下，確認資源是否分散在不同 region。

打開 EC2 Dashboard（Console 搜尋 EC2）。如果 Running instances 是 0、沒有 volumes、沒有 security groups（除了 default）——大概率是空帳號。也檢查 Lambda（Console 搜尋 Lambda → Functions）——如果有 function 在跑但 EC2 是空的，可能是 serverless 架構，帳號不是空的。

再看 S3（Console 搜尋 S3）。S3 是全域服務，不分 region。如果沒有 bucket，或只有 CloudTrail 的 log bucket——大概率是空帳號。

如果有正在跑的 EC2 instance、有 Lambda function、有 RDS 資料庫、有 S3 bucket 存著資料——這是一個有東西的帳號，可能是前人建的、可能是其他團隊在用的。

### 空帳號 → 從零建置

帳號是空的，你要從零開始建基礎設施。這是最乾淨的起點。

路線：先讀[模組零](/infra/00-infra-mindset/)建立心智模型（什麼是 infra、成熟度階梯），然後照模組一到五的順序走。模組一的[動手前的前提](/infra/01-minimal-iac/iac-tool-state-backend/)段會帶你設好本機工具和認證。

### 有東西的帳號 → 接手維運

帳號裡已經有資源在跑。你需要先搞清楚「有什麼」「誰建的」「哪些還在用」，再決定怎麼處理。

路線：讀[接手維運](/infra/takeover/)模組。它按環境類型（全手動的遺留環境、部分有 IaC、多帳號結構）分篇，教你怎麼盤點、怎麼在不搞壞的前提下逐步接管。

### 不確定 → 先盤點再說

如果帳號裡有東西但你不確定是不是還在用、能不能動，先盤點。以下指令需要 AWS CLI 並完成認證——安裝和 `aws configure` 設定見模組一的[前提段](/infra/01-minimal-iac/iac-tool-state-backend/)（macOS 快速安裝：`brew install awscli && aws configure`）：

```bash
# 列出所有 region 的 EC2 instance
for region in $(aws ec2 describe-regions --query 'Regions[].RegionName' --output text); do
  echo "=== $region ==="
  aws ec2 describe-instances --region "$region" \
    --query 'Reservations[].Instances[].[InstanceId,State.Name,Tags[?Key==`Name`].Value|[0]]' \
    --output table
done

# 列出所有 S3 bucket
aws s3 ls

# 列出所有 RDS instance
aws rds describe-db-instances \
  --query 'DBInstances[].[DBInstanceIdentifier,Engine,DBInstanceStatus]' \
  --output table
```

這些指令只做讀取，不會改變任何東西。如果輸出很多資源，去讀[接手維運](/infra/takeover/)再決定下一步。如果幾乎是空的，走「從零建置」路線。

## 雲端 Console 的基本導覽

AWS Console 列出幾百個服務，日常 infra 工作常用的集中在以下幾個：

| 服務       | 做什麼           | 什麼時候用                          |
| ---------- | ---------------- | ----------------------------------- |
| EC2        | 虛擬機器（運算） | 看有什麼機器在跑、管 security group |
| S3         | 物件儲存         | 放檔案、放 Terraform state、放 log  |
| IAM        | 身分與權限       | 管使用者、角色、權限                |
| VPC        | 虛擬網路         | 管網路拓撲、子網路、路由            |
| RDS        | 託管資料庫       | 看有沒有資料庫在跑                  |
| CloudWatch | 監控與 log       | 看 metric、設 alarm、查 log         |
| CloudTrail | 操作審計         | 查誰做了什麼                        |
| Billing    | 帳單             | 看花了多少錢                        |

Console 左上角的搜尋列可以直接搜服務名稱，不用從選單找。

每個服務在 Console 上的操作都有一個對應的 AWS CLI 指令和 API 呼叫。這個對應關係是 IaC 的基礎——[模組一](/infra/01-minimal-iac/)會教怎麼把 Console 上的操作轉成程式碼。

## 你接下來該讀什麼

根據你的情境選一條路線：

| 你的情境                     | 路線         | 從哪裡開始                                                                                 |
| ---------------------------- | ------------ | ------------------------------------------------------------------------------------------ |
| 完全沒碰過雲端、想先理解概念 | 入門認識     | [個人專案到團隊服務](/infra/00-infra-mindset/personal-project-to-infra/)                   |
| 空帳號、要從零建 infra       | 從零建置     | [模組一：最小可行 IaC](/infra/01-minimal-iac/)                                             |
| 帳號有東西、要接手維運       | 接手前人專案 | [接手維運](/infra/takeover/)                                                               |
| 手動環境、暫時無法導入 IaC   | 還沒有 IaC   | [模組負一：還沒有 infra 的環境](/infra/before-infra/)                                      |
| 要跟主管解釋為什麼要做 infra | 說服決策者   | [給非工程人員的 infra 說明](/infra/09-driving-adoption/infra-explained-for-non-engineers/) |

如果你不確定自己屬於哪種情境，先做完本篇的「帳號現況判讀」再決定。
