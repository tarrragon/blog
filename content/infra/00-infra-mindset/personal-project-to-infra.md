---
title: "雲端部署裡已經存在的 infra 元件"
date: 2026-06-26
description: "VPC、security group、IAM、儲存 — 這些元件在任何雲端部署裡都已經在運作，差別在於有沒有被有意識地管理"
weight: 0
tags: ["infra", "mindset"]
---

任何一次雲端部署都會用到基礎設施元件 — 網路隔離、存取控制、儲存、身分認證。即使從來沒有手動設定過這些東西，雲端平台也會用預設值替你建立它們。這篇文章把那些藏在預設值裡的 infra 元件逐一攤開，說明各自解決什麼問題，以及不管理它們時會在什麼時間點造成什麼後果。

## 每次部署都會觸及的四個元件

在 AWS Console 上建立一台 EC2 instance 時，精靈流程的每一步各對應一個 infra 元件。Console 把它們包進填表流程裡，讓建立動作看起來只是「選規格 → 按確認 → 機器出現」，但每一步的選擇都在決定這台機器的網路位置、存取邊界與儲存策略。

### VPC 與 subnet

Network settings 那一步，Console 預設選一個 default VPC。VPC（Virtual Private Cloud）是雲端帳號裡的一塊邏輯隔離網段 — 裡面的機器彼此可達，外部流量要經過明確的入口才進得來。subnet 是 VPC 裡再切出來的子區域，決定機器落在哪個可用區（availability zone）以及對外暴露的程度。

default VPC 在每個 region 自動存在，它的特性是所有 subnet 都是 public（有對外路由）、security group 預設接受部分入站流量。這組預設值讓部署能快速完成，但它的隱含假設是「所有資源都可以對外」— 把資料庫放進 default VPC 時，資料庫的網路位置跟對外的 web server 在同一層，沒有隔離。

### Security group

同一個精靈流程會出現 security group 選項。security group 是掛在機器網路介面上的防火牆規則，決定哪些來源 IP、哪些 port 的流量可以進出。

預設建立的 security group 通常開放 SSH（port 22）給 `0.0.0.0/0` — 任何 IP 都能嘗試連線。對一台短期測試機來說，這讓操作者能連進去；對一台開始承載服務的機器來說，全球的自動掃描工具會在上線幾分鐘內開始對 SSH port 嘗試登入。這條規則是功能正確的（SSH 能連），但安全邊界是開放的（誰都能試）。

### IAM

登入 Console 本身就用到了 IAM（Identity and Access Management）。IAM 管理「誰能對哪些資源做什麼操作」。首次註冊時使用的 root account 擁有帳號內所有權限，用 root 做日常操作等於每次都拿著能開所有門的萬能鑰匙。

開發者與 IAM 的第一個交集通常是 access key — 一組靜態憑證，讓 CLI 工具或部署腳本能用程式化方式操作雲端資源。這把 key 被存進 `~/.aws/credentials` 或專案的 [`.env`](/infra/knowledge-cards/dotenv/) 檔後，它就是一個有權限的身分憑證，決定了持有者能動多少東西。key 沒有到期時間，權限範圍取決於它綁定的 IAM user 或 role 被授予了什麼 policy。

### 儲存

EC2 附帶的 [EBS](/infra/knowledge-cards/ebs/) volume 是儲存層 infra。預設大小通常是 8 GB，預設沒有加密，預設沒有快照排程。磁碟裡只有 OS 跟應用程式時，壞了重建即可。一旦上面開始跑資料庫、存使用者檔案，磁碟裡就有了不可重建的狀態，「壞了重建」這個退路就消失了。

### 預設值的共同特性

VPC、subnet、security group、IAM、EBS — 這些在每次部署時全部自動存在或被預設建立。預設值的設計目標是「讓部署能完成」，而非「讓環境安全且可管理」。兩者之間的落差會在特定時間點浮現。

## 不管理這些元件的後果

infra 元件不被管理時，後果不會立刻出現 — 它們在特定條件觸發時一次浮現。以下是依觸發頻率排列的常見情境。

### 環境無法重建

帳號需要遷移、機器需要在另一個 region 重建、或者某個資源損壞需要從頭來過。這時才發現：security group 開了哪些規則、RDS 的 parameter group 改了哪些值、S3 bucket 的 CORS policy 怎麼設的 — 這些設定散落在 Console 各頁面，唯一的重建方式是逐頁翻 Console 比對。

可重建性的判準：能不能在空白帳號裡，不靠記憶、不靠翻舊帳號 Console，把環境完整重建出來。

### 憑證外洩

access key 被推進 git 歷史 — `.env` 檔忘記加進 `.gitignore`，一次 push 就把 key 送上了公開 repo。GitHub 上有自動掃描工具在監控 commit，從 push 到 key 被利用可能只需要幾分鐘。常見的攻擊操作是在帳號裡開大量高規格 instance 跑礦機，帳單可以在幾小時內衝到數千美元。

即使立刻撤銷 key，git 歷史裡的 key 還在 — 每個 clone 過 repo 的人都有一份副本。回退代價取決於 key 的權限範圍：如果綁的是 AdministratorAccess，攻擊者能做的事等於帳號擁有者能做的所有事。

### 誤刪資源

在 Console 清理資源時刪錯一個 security group，另一台還在跑的機器引用了它 — 網路規則瞬間歸零，服務斷線。Console 沒有「刪了會影響什麼」的預覽，確認按下去就生效。

資料庫的誤刪代價更大。RDS instance 被刪除時如果沒有開啟刪除保護、沒有 snapshot，資料永久消失。手動環境裡沒有自動防護，保護要靠人記得去開。

### 變更不可追溯

某次改了 security group 規則讓某個 API 能通，隔週另一個服務斷線。排查時發現是那條規則影響了未知的依賴，但沒有變更紀錄，「上次改了什麼」只存在改動者的記憶裡。Console 不標記規則的新增時間，要查得去 CloudTrail 翻 API 呼叫日誌。

## 多人協作時的放大效應

一個人操作時，所有隱性知識都在自己腦裡。第二個人加入時，這套隱性知識立刻變成障礙。

身分管理的第一個問題是：共用 access key 還是建新的 IAM user。共用 key 代表兩人的操作在 CloudTrail 裡無法區分是誰做的；建新 user 需要決定權限範圍 — 給太寬怕誤操作，給太窄什麼都做不了。

變更衝突是第二個問題。Console 沒有鎖機制 — 兩人可以同時打開同一個 security group 的編輯頁面，各自修改不同規則，後存的覆蓋先存的，沒有提示。一人改了設定沒通知另一人，排查時不確定「這條規則是原本就有的還是新加的」。

這些問題的共同根源是環境狀態只存在於 Console 和個別人的記憶裡，沒有所有人都能讀到的、可比對差異的事實來源。Infrastructure as Code（IaC）把環境描述寫進程式碼，讓事實來源從記憶變成 repo 裡可以 diff、可以 review 的檔案 — 這是[模組一：最小可行 IaC](/infra/01-minimal-iac/) 的主題。

## 依規模遞增的 infra 需求

infra 的複雜度隨服務的使用者數量、團隊大小與合規要求遞增，但核心責任在每個規模都相同：讓環境可被理解、可被重建、可被安全地變更。

單人運維時，infra 的最小需求是盤點（知道環境裡有什麼）、描述（能重建）、憑證管理（access key 不外洩）。這三件事不需要 Terraform — 一份手動清單、固定命名規則、把 key 換成短期憑證，就覆蓋了最高代價的風險。做法見[模組負一：還沒有 infra 的環境](/infra/before-infra/)。

多人協作時，需要變更可追溯和最小權限。IaC 在這個階段開始產生收益，因為「從程式碼看環境」比「翻 Console」快，而且程式碼可以 review。做法見[模組一](/infra/01-minimal-iac/)。

服務有營收、團隊超過十人時，需要環境分離（dev 與 prod 不互相干擾）、自動化護欄（變更走 PR 流程）、可觀測性（出事時查得到）。這些能力疊加在前面兩層之上。完整的能力階梯見[模組零：infra 是什麼](/infra/00-infra-mindset/)。

## 跨分類引用

- → [模組零：infra 是什麼](/infra/00-infra-mindset/)：五個責任面向與成熟度階梯（從全手動到全程式碼治理的五階分級）的完整定義
- → [模組負一：還沒有 infra 的環境](/infra/before-infra/)：手動環境怎麼守底線、降低未來納管成本
- → [模組一：最小可行 IaC](/infra/01-minimal-iac/)：第一行 IaC 從哪裡開始
- → [模組二：身分與憑證地基](/infra/02-identity-credentials/)：access key 的風險與替代方案
