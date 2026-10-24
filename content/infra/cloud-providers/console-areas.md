---
title: "雲端主控台的管理領域：身分、資源分組、運算、網路、儲存、費用、監控、稽核、安全服務與配額"
date: 2026-10-24
description: "雲端業者的主控台依管理需求分成幾個領域：每個領域管什麼、日常在那裡做哪些事、新帳號開好之後先去哪幾個領域看設定，以及 Oracle Cloud、Google Cloud、AWS 各自把它放在選單的哪個名稱底下"
weight: 3
tags: ["infra", "cloud-providers", "console", "iam", "cost"]
---

這篇整理 Oracle Cloud、Google Cloud 與 AWS 的主控台導覽選單背後共通的管理領域。各家的選單名稱與分類方式不同，而它們要滿足的管理需求是同一組：誰能做什麼、資源怎麼分組、主機與網路與磁碟、花了多少錢、系統現在的狀態、誰做過什麼、安全相關的服務、帳號能開多少資源。範圍是「在主控台上去哪裡做這件事」，每個領域的概念與設計連到站內對應的模組。

## 主控台的共通結構：選單、區域選擇器與資源分組篩選器

三家主控台的版面有三個共同的元件，第一次登入時先找到它們：

- **導覽選單**：列出所有服務，依領域分類。Oracle Cloud 是左上角的 ☰，AWS 與 Google Cloud 也有同樣位置的選單，另外都有一個搜尋框，打服務名稱就能直接跳過去。不知道某個功能在哪一類底下時，搜尋框比翻選單快。
- **區域選擇器**：大部分資源屬於某一個區域，主控台一次只顯示目前選定區域裡的資源。主機建在東京、選擇器停在新加坡時，主機清單是空的。Oracle Cloud 與 AWS 的選擇器在右上角；Google Cloud 的主控台不以區域切換，而是在清單上列出每個資源的區域。
- **資源分組篩選器**：資源還歸屬於某一個分組（Oracle Cloud 的 compartment、Google Cloud 的 project、AWS 的帳號），清單頁只列出目前選定分組裡的資源。Oracle Cloud 的清單頁上有一個 compartment 篩選器，預設常停在 root；資源建在別的 compartment 時，要切過去才看得到。

清單看起來是空的、或剛建的資源找不到時，先查區域與分組這兩個篩選條件，多數時候資源還在，只是篩掉了。

## 身分與權限：誰能登入、能做什麼

管理使用者、群組、角色與權限政策，以及登入方式（密碼政策、多因素驗證、外部身分提供者）。日常的工作是加人、移除人、調整誰能動哪些資源，以及替程式建立服務帳號或 API 金鑰。

新帳號開好之後最先要做的事，有兩件在這個領域：替申請時建立的管理員帳號開啟多因素驗證，並另外建一個日常使用、權限較小的帳號，管理員帳號只在必要時用。理由是管理員帳號能動整個帳號裡的一切，它的密碼外洩時沒有任何一層權限擋得住；日常操作用權限較小的帳號，外洩時影響範圍就限在那些權限裡。帳號不是自己申請的（公司指派、接手別人的帳號）時，先確認誰持有那個管理員帳號、它有沒有開多因素驗證。權限的分級與日常帳號的設計見 [團隊權限分級與存取管理](/infra/02-identity-credentials/team-access-management/)，概念見 [IAM](/infra/knowledge-cards/iam/) 卡。

## 資源分組與標籤：資源屬於哪個專案、誰付錢

把資源分組，讓權限、預算與清理以組為單位進行；標籤則在組之外再加一層分類，用來分攤費用、篩選資源。Oracle Cloud 的分組是 compartment（可以巢狀），Google Cloud 是 project（上面還有 folder 與 organization），AWS 是帳號本身（多個帳號由 Organizations 統一管理）。

實驗用的資源放進一個專用的分組，清理時刪那一組的資源，不會碰到正式環境；權限政策也能限定只作用在那一組。用帳號或專案隔開環境的設計見 [跨帳號策略 — Organizations、SCP 與帳號工廠](/infra/02-identity-credentials/multi-account-strategy/)。

## 運算：主機與映像檔

建立、停止、刪除主機，管理映像檔、主機範本與自動擴展的主機群組。建立主機時的每個選項見 [建立雲端虛擬機的選項](/infra/cloud-providers/vm-options/)。日常會來這裡做的事是看主機狀態、停機省錢、調整規格，以及刪除不用的主機。

## 網路：虛擬網路、負載平衡、DNS 與公開 IP

管理虛擬網路與 subnet、路由與閘道、防火牆規則、負載平衡器、DNS 區域、保留的公開 IP。主機連不進去、或連不到其他服務時，原因多半在這個領域的路由與防火牆規則。subnet 怎麼切、路由與防火牆規則怎麼設計見 [模組三：網路地基](/infra/03-network-foundation/)；建立主機時的網路欄位見 [網路：subnet、私有 IP、公開 IP 與防火牆規則](/infra/cloud-providers/vm-options/networking/)。

## 儲存：區塊磁碟、物件儲存與檔案系統

三種儲存在選單上通常分開：區塊磁碟（主機的開機磁碟與資料磁碟、它們的備份）、物件儲存（以 bucket 存放檔案，經由 HTTP 存取）、共享檔案系統（多台主機同時掛載）。刪除主機之後留下的開機磁碟、沒有人記得的備份與 bucket 仍然是存在的資源，會繼續佔用免費額度、超出額度的部分照一般價格計費，清理時要回來看。開機磁碟的選項見 [磁碟：開機磁碟與區塊磁碟的大小、效能、加密與去留](/infra/cloud-providers/vm-options/storage/)。

## 帳單與成本：花了多少、會花多少

查看帳單與付款方式、依服務與分組分析費用、設定預算與警示。新帳號開好之後要來這裡設一個預算警示，讓費用超過預期時有人收到通知。帳號已經升級成付費帳戶時，超出免費額度或用到非免費機型的費用會直接扣款，所以這類帳號一定要設。

Oracle Cloud 沒有升級的帳號在試用結束後不會開始計費，預算警示在這種帳號上的用處是在試用期間提早看到哪些資源不在免費額度內。成本管理的概念見 [運行期維運的成本管理](/operations/08-cost-management/)；從預算通知觸發自動停損的建置，目前只有 Google Cloud 的實作篇 [GCP 上的雲端費用失控防護](/infra/cloud-providers/gcp/spend-protection-gcp-budget-killswitch/)。免費額度的規則見 [雲端免費額度與小型主機的收費比較](/infra/cloud-providers/pricing-comparison/)。

## 監控、日誌與告警：系統現在的狀態

主機與服務的指標（CPU、記憶體、網路流量）、日誌的收集與搜尋、告警規則與通知管道。主機變慢、服務停掉時，先來這裡看指標與日誌。log group、metric 與 alarm 怎麼跟資源一起管理見 [模組六：可觀測性與 log](/infra/06-observability-logging/)。

## 稽核紀錄：誰在什麼時候做了什麼

業者自動記錄對雲端資源的管理操作（建立、修改、刪除）：誰、什麼時間、從哪個 IP、做了什麼操作、對哪個資源。主控台上建立、修改、刪除資源的點擊最後也是 API 呼叫，同樣會留下紀錄。要查出某個資源是誰、在什麼時候改掉或刪掉的，看這裡的紀錄。讀取資料這一類操作不一定預設記錄：Google Cloud 的 Data Access 稽核紀錄除了 BigQuery 之外預設關閉，AWS CloudTrail 的 Event history 只列管理操作，兩者都要另外打開。稽核紀錄的保存期限各家不同，要長期保存時要另外匯出。AWS 的同一個功能見 [CloudTrail](/infra/knowledge-cards/cloudtrail/) 卡。

## 安全服務：管理通道、金鑰、秘密與弱點掃描

業者提供的安全服務多半集中在一個領域：不經公開 IP 登入主機的服務（Oracle Cloud Bastion、Google Cloud IAP、AWS Systems Manager）、金鑰與秘密的保管（Oracle Cloud 的 Vault、Google Cloud 的 Secret Manager、AWS 的 Secrets Manager）、主機的弱點掃描、組態風險的偵測。管理通道的設計見 [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)。Oracle Cloud 的 Vault 是業者的金鑰管理服務，跟 HashiCorp 公司的同名自架產品是兩個不同的產品；不用業者服務、自己架秘密管理時的選項見 [HashiCorp Vault](/infra/knowledge-cards/vault/) 卡。

## 配額與限制：帳號最多能開多少

每個帳號對每種資源都有數量上限（主機台數、核心數、公開 IP 數），超過時建立會失敗。這個領域列出每項上限與目前用量，要開更多時從這裡申請調高。上限是帳號允許的數量，不保證那一區有那麼多硬體——Oracle Cloud 的配額表會列出某一區根本沒有提供的機型，實例見 [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/)。

## 新帳號開好之後先看的領域

帳號的第一小時要處理的安全底線——管理員帳號的多因素驗證、確認自己的登入身分、檢查既存的存取金鑰、確認稽核紀錄有在記、設帳單警報——整理在 [拿到雲端帳號的第一天](/infra/00-infra-mindset/first-day-with-cloud-account/) 的〈第一小時：安全底線〉，那一篇的操作路徑以 AWS 為例，其他業者對應的選單見下方〈各家的選單名稱：各管理領域在三家主控台上的位置〉；接手已經有資源的帳號時，先看同一篇的〈帳號現況判讀：空帳號還是既有資源〉。在那幾項之外，要開始建資源之前再看兩個領域：

- **資源分組**：建一個實驗用的分組，之後的資源都建在裡面，清理時整組處理。Oracle Cloud 建一個 compartment，Google Cloud 建一個 project；AWS 的分組單位是帳號本身，另開帳號要由組織的管理帳號在 AWS Organizations 裡做，被指派管理單一帳號的人在那個帳號裡改用標籤與 Resource Groups 分組。
- **配額與限制**：確認要用的機型在這個帳號、這個區域的上限不是 0；上限不是 0 也不代表那一區有那種硬體。

## 各家的選單名稱：各管理領域在三家主控台上的位置

| 管理領域   | Oracle Cloud                                                                | Google Cloud                               | AWS                                            |
| ---------- | --------------------------------------------------------------------------- | ------------------------------------------ | ---------------------------------------------- |
| 身分與權限 | Identity & Security → Identity                                              | IAM & Admin                                | IAM、IAM Identity Center                       |
| 資源分組   | Identity & Security → Identity → Compartments                               | 專案選擇器、IAM & Admin → Manage resources | AWS Organizations                              |
| 標籤       | Governance & Administration → Tenancy Management → Tag Namespaces           | IAM & Admin → Tags、Labels                 | Resource Groups & Tag Editor                   |
| 運算       | Compute                                                                     | Compute Engine                             | EC2                                            |
| 網路       | Networking                                                                  | VPC network、Network services              | VPC                                            |
| 儲存       | Storage                                                                     | Cloud Storage、Compute Engine → Storage    | S3、EC2 → Elastic Block Store                  |
| 帳單與成本 | Billing & Cost Management                                                   | Billing                                    | Billing and Cost Management                    |
| 監控、日誌 | Observability & Management                                                  | Monitoring、Logging                        | CloudWatch                                     |
| 稽核紀錄   | Observability & Management → Logging → Audit                                | Logging（Cloud Audit Logs）                | CloudTrail                                     |
| 安全服務   | Identity & Security                                                         | Security                                   | Security Hub、Secrets Manager、Systems Manager |
| 配額與限制 | Governance & Administration → Tenancy Management → Limits, quotas and usage | IAM & Admin → Quotas & System Limits       | Service Quotas                                 |

AWS 的身分與權限有兩處：公司帳號用 SSO 登入時，人員與他們能進的帳號在 IAM Identity Center 管理；IAM 管的是帳號裡的角色與程式用的身分。Oracle Cloud 的選單取自 2026-10-24 的主控台英文介面；選單名稱各家會隨改版調整，對不上時用搜尋框找服務名稱。Oracle Cloud 主控台各分類的完整內容見 [Oracle Cloud 主控台導覽](/infra/cloud-providers/oracle-cloud/console-navigation/)。

## 延伸閱讀：各領域的概念模組

- [模組二：身分與存取憑證地基](/infra/02-identity-credentials/)：身分與權限領域裡的角色、政策與憑證設計
- [運行期維運的成本管理](/operations/08-cost-management/)：帳單與成本領域裡的預算、警示與停損
- [建立雲端虛擬機的選項](/infra/cloud-providers/vm-options/)：運算領域裡建立主機時的每一個選項
