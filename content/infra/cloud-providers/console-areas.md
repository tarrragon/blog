---
title: "雲端主控台的管理領域：身分、資源分組、運算、網路、儲存、費用、監控、稽核、安全服務與配額"
date: 2026-10-24
description: "雲端業者的主控台依管理需求分成幾個領域：每個領域管什麼、日常在那裡做哪些事、新帳號開好之後先去哪幾個領域看設定，以及 Oracle Cloud、Google Cloud、AWS 各自把它放在選單的哪個名稱底下"
weight: 3
tags: ["infra", "cloud-providers", "console", "iam", "cost"]
---

這篇整理 Oracle Cloud、Google Cloud 與 AWS 的主控台導覽選單背後共通的管理領域。各家的選單名稱與分類方式不同，而它們要滿足的管理需求是同一組：誰能做什麼、資源怎麼分組、主機與網路與磁碟、花了多少錢、系統現在的狀態、誰做過什麼、安全相關的服務、帳號能開多少資源。範圍是「在主控台上去哪裡做這件事」，每個領域的概念與設計連到站內對應的模組。

## 主控台的共通結構：選單、區域選擇器與資源分組篩選器

主控台上有三種元件第一次登入時要先找到，各家有沒有、放在哪裡不同：

- **導覽選單**：列出所有服務，依領域分類。Oracle Cloud 是左上角的 ☰，AWS 與 Google Cloud 也有同樣位置的選單，另外都有一個搜尋框，打服務名稱就能直接跳過去。不知道某個功能在哪一類底下時，搜尋框比翻選單快。
- **區域選擇器**：大部分資源屬於某一個區域，主控台一次只顯示目前選定區域裡的資源。主機建在東京、選擇器停在新加坡時，主機清單是空的。Oracle Cloud 與 AWS 的選擇器在右上角；Google Cloud 的主控台不以區域切換，而是在清單上列出每個資源的區域。
- **資源分組篩選器**：資源還歸屬於某一個分組（Oracle Cloud 的 compartment、Google Cloud 的 project、AWS 的帳號），清單頁只列出目前選定分組裡的資源。Oracle Cloud 的清單頁上有一個 compartment 篩選器，預設常停在 root，資源建在別的 compartment 時，要切過去才看得到；Google Cloud 在頂端列切換專案；AWS 的分組由目前登入的帳號決定，清單頁上沒有篩選器。

清單看起來是空的、或剛建的資源找不到時，先查區域與分組這兩個篩選條件，多數時候資源還在，只是篩掉了。

## 身分與權限：誰能登入、能做什麼

帳號的管理員在這個領域管理使用者、群組、角色與權限政策，以及登入方式（密碼政策、多因素驗證、外部身分提供者）。日常的工作是加人、移除人、調整誰能動哪些資源，以及替程式建立服務帳號或 API 金鑰。

新帳號開好之後，這個領域裡要先做兩件事：替申請時建立的管理員帳號開啟多因素驗證，並另外建一個日常使用、權限較小的帳號（權限只給到工作需要的範圍，見 [Least Privilege](/backend/knowledge-cards/least-privilege/) 卡），管理員帳號只在必要時用。理由是管理員帳號能動整個帳號裡的一切，它的密碼外洩時沒有任何一層權限擋得住；日常操作用權限較小的帳號，外洩時影響範圍就限在那些權限裡。帳號不是自己申請的（公司指派、接手別人的帳號）時，先確認誰持有那個管理員帳號、它有沒有開多因素驗證。公司的帳號常屬於一個組織，組織的政策（AWS Organizations 的 SCP、Google Cloud 的組織政策）可能讓某些選項建不起來，建立時收到權限不足的錯誤而自己的權限看起來沒問題時，去問管理組織的人。權限的分級與日常帳號的設計見 [團隊權限分級與存取管理](/infra/02-identity-credentials/team-access-management/)，概念見 [IAM](/infra/knowledge-cards/iam/) 卡。

## 資源分組與標籤：資源屬於哪個專案、誰付錢

管理員與使用者在這個領域把資源分組，讓權限、預算與清理以組為單位進行；標籤則在組之外再加一層分類，用來分攤費用、篩選資源。Oracle Cloud 的分組是 compartment（可以巢狀），Google Cloud 是 project（上面還有 folder 與 organization），AWS 是帳號本身（多個帳號由 Organizations 統一管理）。

實驗用的資源放進一個專用的分組，清理時刪那一組的資源，不會碰到正式環境；權限政策也能限定只作用在那一組。用帳號或專案隔開環境的設計見 [跨帳號策略 — Organizations、SCP 與帳號工廠](/infra/02-identity-credentials/multi-account-strategy/)。

## 運算：主機與映像檔

使用者在這個領域建立、停止、刪除主機，管理映像檔、主機範本與自動擴展的主機群組，建立主機時的每個選項見 [建立雲端虛擬機的選項](/infra/cloud-providers/vm-options/)。日常會來這裡做的事是看主機狀態、停機省錢、調整規格，以及刪除不用的主機。

## 網路：虛擬網路、負載平衡、DNS 與公開 IP

管理虛擬網路與 subnet、路由與閘道、防火牆規則、負載平衡器、DNS 區域、保留的公開 IP。主機連不進去、或連不到其他服務時，原因多半在這個領域的路由與防火牆規則。subnet 怎麼切、路由與防火牆規則怎麼設計見 [模組三：網路地基](/infra/03-network-foundation/)；建立主機時的網路欄位見 [網路：subnet、私有 IP、公開 IP 與防火牆規則](/infra/cloud-providers/vm-options/networking/)。

## 儲存：區塊磁碟、物件儲存與檔案系統

三種儲存在選單上通常分開：區塊磁碟（主機的開機磁碟與資料磁碟、它們的備份）、物件儲存（以 bucket 存放檔案，經由 HTTP 存取）、共享檔案系統（多台主機同時掛載）。刪除主機之後留下的開機磁碟、沒有人記得的備份與 bucket 仍然是存在的資源，會繼續佔用免費額度，超出額度之後的結果依業者與帳號狀態而定（例如試用中由試用金支付、付費帳戶照一般價格計費），清理時要回來看。Oracle Cloud 三種帳號狀態各自的結果見 [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/) 的〈超出 Always Free 額度時：試用中、未升級與付費帳戶各自的結果〉，Google Cloud 與 AWS 的見 [雲端免費額度與小型主機的收費比較](/infra/cloud-providers/pricing-comparison/) 的〈試用結束後帳號與資源的處置〉。開機磁碟的選項見 [磁碟：開機磁碟與區塊磁碟的大小、效能、加密與去留](/infra/cloud-providers/vm-options/storage/)。

## 帳單與成本：花了多少、會花多少

負責付款的人在這個領域查看帳單與付款方式、依服務與分組分析費用、設定預算與警示。新帳號開好之後要來這裡設一個預算警示，讓費用超過預期時有人收到通知。帳號已經升級成付費帳戶時，超出免費額度或用到非免費機型的費用會直接扣款，所以這類帳號一定要設。

Oracle Cloud 沒有升級的帳號在試用結束後不會開始計費，預算警示在這種帳號上的用處是在試用期間提早看到哪些資源不在免費額度內。成本監控與異常告警見 [運行期維運的成本管理](/operations/08-cost-management/)；預算警示的門檻與從預算通知觸發自動停損的建置，目前只有 Google Cloud 的實作篇 [GCP 上的雲端費用失控防護](/infra/cloud-providers/gcp/spend-protection-gcp-budget-killswitch/)。帳單上已經出現費用、要找出是哪個資源在計費時，在成本分析頁依服務與資源拆開；免費額度的帳號最常見的來源是刪除主機後留下的開機磁碟（[磁碟：開機磁碟與區塊磁碟的大小、效能、加密與去留](/infra/cloud-providers/vm-options/storage/) 的〈刪除（終止）主機時開機磁碟的預設去留〉）、選到不在免費額度內的機型，以及 AWS 對公開 IPv4 位址的計費。免費額度的規則見 [雲端免費額度與小型主機的收費比較](/infra/cloud-providers/pricing-comparison/)。

## 監控、日誌與告警：系統現在的狀態

主機與服務的指標（CPU、記憶體、網路流量）、日誌的收集與搜尋、告警規則與通知管道。主機變慢、服務停掉時，先來這裡看指標與日誌。log group、metric 與 alarm 怎麼跟資源一起管理見 [模組六：可觀測性與 log](/infra/06-observability-logging/)。

## 稽核紀錄：誰在什麼時候做了什麼

業者自動記錄對雲端資源的管理操作（建立、修改、刪除）：誰、什麼時間、從哪個 IP、做了什麼操作、對哪個資源。主控台上建立、修改、刪除資源的點擊最後也是 API 呼叫，同樣會留下紀錄。要查出某個資源是誰、在什麼時候改掉或刪掉的，看這裡的紀錄。讀取資料這一類操作不一定預設記錄：Google Cloud 的 Data Access 稽核紀錄除了 BigQuery 之外預設關閉，AWS CloudTrail 的 Event history 只列管理操作，兩者都要另外打開。稽核紀錄的保存期限各家不同，要長期保存時要另外匯出。AWS 的同一個功能見 [CloudTrail](/infra/knowledge-cards/cloudtrail/) 卡。

## 安全服務：管理通道、金鑰、秘密與弱點掃描

業者提供的安全服務多半集中在一個領域：不經公開 IP 登入主機的服務（Oracle Cloud Bastion、Google Cloud IAP、AWS Systems Manager）、金鑰與秘密的保管（Oracle Cloud 的 Vault、Google Cloud 的 Secret Manager、AWS 的 Secrets Manager）、主機的弱點掃描、組態風險的偵測。管理通道的設計見 [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)。Oracle Cloud 的 Vault 是業者的金鑰管理服務，跟 HashiCorp 公司的同名自架產品是兩個不同的產品；不用業者服務、自己架秘密管理時的選項見 [HashiCorp Vault](/infra/knowledge-cards/vault/) 卡。

## 配額與限制：帳號最多能開多少

每個帳號對每種資源都有數量上限（主機台數、核心數、公開 IP 數），超過時建立會失敗。這個領域列出每項上限與目前用量，要開更多時從這裡申請調高。上限是帳號允許的數量，不保證那一區有那麼多硬體——Oracle Cloud 的配額表會列出某一區根本沒有提供的機型，實例見 [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/) 的〈E2.1.Micro 在各區域的供應：服務配額表與 404 錯誤〉。

## 新帳號開好之後先看的領域

帳號的第一小時要處理的安全底線——管理員帳號的多因素驗證、確認自己的登入身分、檢查既存的存取金鑰、確認稽核紀錄有在記、設帳單警報——整理在 [拿到雲端帳號的第一天](/infra/00-infra-mindset/first-day-with-cloud-account/) 的〈第一小時：安全底線〉，那一篇的操作路徑以 AWS 為例，其他業者對應的選單見下方〈各家的選單名稱：各管理領域在三家主控台上的位置〉；接手已經有資源的帳號時，先看同一篇的〈帳號現況判讀：空帳號還是既有資源〉。在那幾項之外，要開始建資源之前再處理下面這幾件事：

- **身分與權限**：另外建一個日常使用、權限較小的帳號，理由見〈身分與權限：誰能登入、能做什麼〉。

- **資源分組**：建一個實驗用的分組，之後的資源都建在裡面，清理時只看這一組。Oracle Cloud 建一個 compartment，compartment 要先清空裡面的所有資源才能刪除，刪除的順序見 [Oracle Cloud 建立主機的實測紀錄](/infra/cloud-providers/oracle-cloud/launch-instance-walkthrough/) 的〈刪除這組資源的順序〉；Google Cloud 建一個 project，刪除 project 會連同裡面的資源一起刪；AWS 的分組單位是帳號本身，另開帳號要由組織的管理帳號在 AWS Organizations 裡做，被指派管理單一帳號的人在那個帳號裡改用標籤與 Resource Groups 分組。
- **配額與限制**：上限依帳號類型而不同（Oracle Cloud 的〈Service Limits〉在運算的上限表上分成 Universal Credits 一欄，與 Pay As You Go 和試用帳號共用的一欄（欄名「Pay As You Go or Trial」），兩欄的值不同），所以要用的機型在自己這個帳號、這個區域的上限是多少，要到這個領域的頁面查；上限是 0 時那種機型建不起來，要先申請調高。上限不是 0 也不代表那一區有那種硬體。

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

## 延伸閱讀：服務層的對照

這篇對照的是三家主控台上的管理領域與建立主機的欄位；資料庫、訊息佇列、函式這類託管服務在 AWS、Google Cloud 與 Azure 之間怎麼對應、對應的服務在哪些地方不等價，見 [雲端服務對照地圖（AWS / GCP / Azure）](/backend/00-service-selection/cloud-vendor-capability-mapping/)。
