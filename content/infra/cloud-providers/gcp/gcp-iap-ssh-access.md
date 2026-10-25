---
title: "GCP VM 的 SSH 與 RDP 管理通道：從預設的全開規則改走 IAP TCP forwarding"
date: 2026-10-23
description: "GCP 預設網路自帶的防火牆規則與它們留下的暴露面、IAP TCP forwarding 的連線路徑與日常連線指令、切換到 IAP 的順序為什麼這樣排、IAP 通道連不上時的依層判讀，以及 IAM 授權範圍、OS Login 的啟用條件與工作階段的結束、拿掉外部 IP 之後的出站路徑、Organization Policy、階層式防火牆、稽核紀錄與 Security Command Center 的 OPEN_SSH_PORT finding 在 GCP 上的處理"
weight: 1
aliases: ["/infra/03-network-foundation/gcp-iap-ssh-access/"]
tags: ["infra", "network", "gcp", "ssh", "rdp", "iap", "firewall"]
---

這篇整理 GCP Compute Engine 上管理員登入 VM 的通道（Linux 的 SSH、Windows 的 RDP），從防火牆對 `0.0.0.0/0` 開放 22 與 3389 port 改成走 Identity-Aware Proxy（IAP）TCP forwarding 的機制與判斷依據：預設網路的規則與它們留下的暴露面、IAP 的連線路徑、切換的順序為什麼這樣排、連不上時的依層判讀、IAM 授權的範圍、OS Login、拿掉外部 IP 之後的出站路徑、組織層級的護欄與稽核。範圍從專案裡已經有 VM、而且用的是預設網路（`default` network）開始；自建網路上手寫的全開規則，處理方式相同。從盤點、救援入口、建規則與授權、停用舊規則驗證、啟用 OS Login 到移除外部 IP 的逐步操作與實跑結果，在 [GCP VM 的 SSH 與 RDP 改走 IAP 的實測紀錄](/infra/cloud-providers/gcp/hands-on/iap-ssh-migration-walkthrough/)。IAP 這一類代理服務的共通機制見 [Identity-Aware Proxy（身分感知代理）](/infra/knowledge-cards/identity-aware-proxy/)。

管理通道為什麼要收斂、它拆成哪幾層、各層有哪些與廠商無關的做法，在[伺服器管理通道的設計：網路可達性、通道授權、主機登入驗證三層的做法與選擇，以及救援入口](/infra/03-network-foundation/management-access-channel/)。本篇是那套模型在 GCP 上的一種組合：

| 管理通道的層 | 本篇在 GCP 上的做法                                       |
| ------------ | --------------------------------------------------------- |
| 網路可達性   | 防火牆只放行 IAP 的來源位址段，VM 移除外部 IP             |
| 通道授權     | Google 帳號加 IAM role `roles/iap.tunnelResourceAccessor` |
| 主機登入驗證 | Linux 用 OS Login；Windows 用 VM 上的 Windows 帳號        |

救援入口用 Serial Console，它不經過上面三層的設定，有自己的 IAM 權限與開關。

這個組合假設組織的身分提供者（[identity provider](/backend/knowledge-cards/identity-provider/)，IdP）是 Google 帳號：IAP 與 OS Login 都依 Google 的 IAM 判斷。組織用的是 Microsoft Entra ID、Okta 這類其他 IdP 時，有兩條路。一條是讓 Cloud Identity 以 SAML 單一登入接那個 IdP、並由 IdP 把帳號同步進來，使用者在原本的 IdP 登入、拿到的是 Google 身分，本篇全部適用。另一條是通道授權改用能接那個 IdP 的代理服務，網路可達性跟著那個代理走（防火牆改放行它的位址段，或改用不開入站 port 的反向連線）；這時本篇依賴 Google 帳號的幾節——〈IAP 的 IAM 授權範圍：誰拿得到通道〉、〈SSH 金鑰在 GCP 上的管理位置：metadata 金鑰與 OS Login 的啟用條件〉的 OS Login 與組織政策的 `compute.requireOsLogin`、稽核紀錄裡 IAP 的 Data Access 紀錄——都不適用，Cloud NAT、移除外部 IP、Serial Console 與防火牆規則的收斂仍然適用。

另外四種環境要先調整做法再往下讀：

- **由 managed instance group（MIG）或 GKE 管理的 VM**：tag、metadata、救援帳號與移除外部 IP 都要改在 instance template、node pool 設定或映像檔裡。逐台用 `gcloud` 修改，VM 在自動修復、升級或縮放時重建，修改就消失，tag 消失之後 IAP 規則也套不到新的 VM。這兩種環境的設定位置、救援改用重建的做法與 GKE 控制層的存取，見[GCP 上由 MIG 與 GKE 管理的 VM 的管理存取](/infra/cloud-providers/gcp/gke-mig-management-access/)。
- **Shared VPC 的 service project**：防火牆規則住在 host project，防火牆相關的指令要在 host project 執行；停用 `default-allow-ssh` 這類規則會同時影響其他 service project 的 VM。
- **用 Terraform 這類 IaC 管理的專案**：每一個 `gcloud` 修改都要改寫成程式碼。只在 CLI 加的 tag、IAM 授權與 metadata，若所屬資源在程式碼裡被完整定義（例如 `google_compute_instance` 寫了 `tags`、用 `google_project_iam_policy` 管 IAM），下一次 apply 會把它拿掉；只在 CLI 刪掉的規則與外部 IP，下一次 apply 會建回來。用 CLI 停用舊規則做驗證的期間要暫停所有 apply。兩個方向的落差與過渡期的做法見[兩套真相並存的過渡期操作](/infra/takeover/partial-iac-dual-truth-operation/)。
- **新專案從零開始**：沒有舊規則要移走，切換前的盤點與停用驗證可以跳過，直接建 IAP 規則、OS Login 與 Cloud NAT；建 VM 時加 `--no-address` 就不配外部 IP。2024 年 5 月 3 日之後建立的 Organization 會預設強制一組 Organization Policy，其中可能已經包含本篇〈組織層級的護欄：Organization Policy 與階層式防火牆〉提到的幾項；用 `gcloud resource-manager org-policies list --organization=<org-id>` 查組織層級設定了哪些（`<org-id>` 用 `gcloud organizations list` 查）。

## 預設網路自帶的防火牆規則

專案第一次啟用 Compute Engine API 時，GCP 會自動建一個叫 `default` 的 auto-mode VPC，並在上面預先建好四條入站規則。這四條規則的設計目標是讓第一次用 GCP 的人開完 VM 就連得上，所以來源範圍放得很寬。

| 規則名稱                 | 放行內容                            | 來源範圍       |
| ------------------------ | ----------------------------------- | -------------- |
| `default-allow-ssh`      | tcp:22                              | `0.0.0.0/0`    |
| `default-allow-rdp`      | tcp:3389                            | `0.0.0.0/0`    |
| `default-allow-icmp`     | ICMP                                | `0.0.0.0/0`    |
| `default-allow-internal` | 同網路內 TCP、UDP 所有 port 與 ICMP | `10.128.0.0/9` |

GCP 的防火牆規則依 priority 數字由小到大評估。這四條的 priority 是 65534，只排在 VPC 隱含的「拒絕所有入站」規則（65535）前面，所以自己建立的規則（不指定時是 1000）都會比它們先被評估。它們也沒有指定 target tag（防火牆規則用來挑選作用對象的標記），作用對象是這個網路裡的每一台 VM。Oracle Cloud 與 AWS 預設網路的同類規則見 [網路：subnet、私有 IP、公開 IP 與防火牆規則](/infra/cloud-providers/vm-options/networking/) 的〈各家預設網路規則對 SSH 的開放〉。

只收掉 `default-allow-ssh` 會留下兩個暴露面。`default-allow-rdp` 讓每一台 Windows VM 的遠端桌面對整個網際網路開放，而 RDP 預設接受密碼登入。`default-allow-internal` 讓同一個網路裡的 VM 之間不受 port 限制，一台 VM 被入侵之後，攻擊者從那台機器能直接連到其他 VM 的資料庫 port 與管理 port，這種擴散方式叫[橫向移動（lateral movement）](/backend/knowledge-cards/lateral-movement/)。另外，這四條自動建立的規則預設沒有開啟 firewall rules logging，防火牆這一層不會留下被掃描或被連入的紀錄。管理 port 對外開放的風險與廠商無關，見[伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)的〈對外開放管理 port 的實際風險〉。

CIS Google Cloud Platform Foundation Benchmark 的 3.1 條因此建議專案裡不保留 `default` 網路，改用自己規劃 subnet 的 custom-mode VPC。已經有服務跑在 `default` 網路上的專案，可以先收斂這四條規則，搬遷網路排進另一次變更；收斂 `default-allow-internal` 與 `default-allow-icmp` 的指令與實測結果在 [GCP VM 的 SSH 與 RDP 改走 IAP 的實測紀錄](/infra/cloud-providers/gcp/hands-on/iap-ssh-migration-walkthrough/) 的〈收斂 default-allow-internal 與 default-allow-icmp〉。

列出專案目前在 `default` 網路上的規則，`--format` 讓 `gcloud` 把來源範圍與 target tag 兩欄加進輸出（預設表格沒有這兩欄）：

```bash
# 列出 default 網路上的防火牆規則，含來源範圍、放行內容與 target tag
gcloud compute firewall-rules list --filter="network:default" \
  --format="table(name,priority,sourceRanges.list():label=SRC_RANGES,allowed[].map().firewall_rule().list():label=ALLOW,targetTags.list():label=TARGET_TAGS,disabled)"
```

輸出裡要看 `SRC_RANGES` 欄是 `0.0.0.0/0` 的列，以及 `TARGET_TAGS` 欄是空白的列——空白代表規則套用到整個網路的每一台 VM。這兩條規則要換掉、不能直接刪：刪除的當下，管理員自己的 SSH 與 RDP 連線會一起中斷，理由見〈切換到 IAP 的順序〉。從 Security Command Center 的 `OPEN_SSH_PORT` 或 `OPEN_RDP_PORT` finding 進來的，finding 裡寫著被標記的那條規則的資源名稱，以那個名稱替換指令裡的 `default-allow-ssh`；網路不是 `default` 時，把 `--filter` 裡的網路名稱一起換掉。

## IAP TCP forwarding 的連線路徑與來源範圍

IAP TCP forwarding 是 GCP 的身分感知代理：管理員的 `gcloud` 先用 HTTPS 連到 Google 的 IAP 端點，IAP 檢查這個 Google 帳號有沒有開通道的 IAM 權限，通過之後由 IAP 從 `35.235.240.0/20` 這段位址連到 VM 的內部 IP 與指定 port，再把兩端的位元組來回轉送。

一條連線因此由兩個元件各檢查一次，分別對應通道授權與主機登入驗證：

| 驗證位置 | 由誰檢查                                | 檢查什麼                                                                   |
| -------- | --------------------------------------- | -------------------------------------------------------------------------- |
| IAP 端點 | Google IAM                              | 這個 Google 帳號在這個 VM 上有沒有 `iap.tunnelInstances.accessViaIAP` 權限 |
| VM 內部  | Linux 上的 sshd／Windows 的遠端桌面服務 | SSH 金鑰在不在授權清單裡（metadata 金鑰或 OS Login）／Windows 帳號密碼     |

IAP 只決定是否允許開通道，開了通道之後登入 VM 仍然要過 VM 自己的認證，所以兩者要分開設定、分開稽核：IAM 給得太寬，sshd 就暴露給不該碰這台 VM 的成員；VM 的金鑰管理鬆散，拿到通道的人就能用別人留下的金鑰登入。

`35.235.240.0/20` 是 Google 文件公開的 IAP TCP forwarding 來源範圍，裡面包含 IAP 轉送時使用的全部位址。IPv6 的 VM 要另外放行 `2600:2d00:1:7::/64`；auto-mode 的 `default` 網路只有 IPv4 subnet，IPv6 的規則只在自建、開了 dual-stack subnet 的 custom-mode VPC 上用得到。這兩段位址是 Google 定義的規格值，每個專案都相同，可以直接寫進防火牆規則；Google 調整範圍時以 [IAP TCP forwarding 文件](https://cloud.google.com/iap/docs/using-tcp-forwarding)為準。防火牆規則的關鍵是 `--source-ranges=35.235.240.0/20` 加上 `--target-tags` 限定作用的 VM、`--rules` 只開需要的 port，完整的建立指令與各引數在 [GCP VM 的 SSH 與 RDP 改走 IAP 的實測紀錄](/infra/cloud-providers/gcp/hands-on/iap-ssh-migration-walkthrough/) 的〈啟用 IAP API、開啟稽核紀錄並建立只放行 IAP 來源的防火牆規則〉。

設定完成之後，日常的連線指令是這幾條，`<instance-name>` 與 `<zone>` 用 `gcloud compute instances list` 查，第一欄是 VM 名稱、第二欄是 zone：

```bash
# Linux：透過 IAP 通道 SSH 進 VM
gcloud compute ssh <instance-name> --zone=<zone> --tunnel-through-iap

# Linux：透過 IAP 通道傳檔
gcloud compute scp <local-file> <instance-name>:<remote-path> --zone=<zone> --tunnel-through-iap

# Windows：把 VM 的 3389 port 經 IAP 轉到本機的 13389，再用 RDP 用戶端連 localhost:13389
gcloud compute start-iap-tunnel <windows-instance-name> 3389 --local-host-port=localhost:13389 --zone=<zone>
```

主控台上 VM 旁的 SSH 按鈕（SSH-in-browser）不是這幾條指令：官方〈Connect to Linux VMs using IAP〉寫明它只在 VM 沒有外部 IP 時才走 IAP，VM 還帶外部 IP 時它連的是外部 IP，舊規則停用之後就連不上。本機的 port 用 3389 以外的號碼（這裡是 `13389`），管理員自己的 Windows 電腦開著遠端桌面時，本機的 3389 已經被占用。Ansible 這類用一般 `ssh` 連線的工具，在 ssh 設定裡用 `ProxyCommand` 讓 `gcloud` 開通道：

```text
# ~/.ssh/config：<vm-name> 寫 VM 名稱，ssh 連線時代入 %h
Host <vm-name>
  ProxyCommand gcloud compute start-iap-tunnel %h 22 --listen-on-stdin --zone=<zone> --project=<project-id>
  User <os-login-username>
  IdentityFile <private-key-file>
```

`--listen-on-stdin` 讓 `gcloud` 把通道接到標準輸入輸出，ssh 就經由 IAP 連到 `%h`；這個旗標不出現在 `gcloud compute start-iap-tunnel --help` 的輸出裡，而功能存在。VM 啟用了 OS Login 時，一般 `ssh` 不會像 `gcloud compute ssh` 那樣自動把公鑰登錄到帳號的 OS Login profile，所以先以 Ansible 開通道所用的[服務帳號](/infra/knowledge-cards/service-account/)（`<ci-service-account-email>`）的身分登錄一次：`gcloud compute os-login ssh-keys add --key-file=<public-key-file> --impersonate-service-account=<ci-service-account-email>`，`<public-key-file>` 是 `<private-key-file>` 對應的公鑰檔；`<os-login-username>` 用同樣加上 `--impersonate-service-account` 的 `gcloud compute os-login describe-profile` 輸出裡的 `username`。

IAP 通道的代價在傳輸速度：所有位元組都經過 Google 的轉送，傳大檔案比直連慢，大量傳檔適合改用 Cloud Storage 當中轉。

## 切換到 IAP 的順序

切換的順序由兩個事實決定。`default-allow-ssh` 的來源 `0.0.0.0/0` 本身就涵蓋 IAP 的位址段，所以舊規則還在的時候，經由 IAP 的連線成功，可能是舊規則放行的，證明不了新規則寫對了；驗證新規則因此要先停用舊規則。而停用舊規則的那一刻，從公開網際網路來的 SSH 與 RDP 都會被拒絕，包括管理員自己的連線與依賴這條規則的 CI、監控、廠商連線。所以：依賴舊規則的連線要先盤點出來並改走 IAP；救援入口（Serial Console 與本機救援帳號）要在停用之前準備好並實際登入過；新規則、tag 與 IAM 權限要在停用之前建好；停用之後確認新路徑可用，才刪除舊規則。與廠商無關的推導見[伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)的〈切換管理通道時避免把自己鎖在外面〉。

這個順序裡有三件事的判斷落在 GCP 的機制上：

- **盤點靠 VM 上的登入紀錄，不只靠防火牆紀錄**：全開規則的紀錄大部分是網際網路掃描程式的來源，CI 託管執行環境的 IP 每次不同，混在裡面認不出來；VM 上 sshd 紀錄的帳號與金鑰指紋才認得出是哪個人或哪個工具。
- **驗證用停用而不是刪除**：停用的規則用 `--no-disabled` 一行恢復原樣，刪除之後要重建、重建時可能寫錯；防火牆規則透過 GCP 的 API 修改，SSH 連不上也改得回來。
- **Serial Console 的權限收不窄**：連 Serial Console 需要能修改這台 VM 的權限（例如 `roles/compute.instanceAdmin.v1`），而這個角色也是一般 VM 管理會用到的權限，所以光靠 IAM 收不窄救援入口；真正把它收窄的是組織政策 `compute.disableSerialPortAccess`（見〈組織層級的護欄：Organization Policy 與階層式防火牆〉）。組織強制了這條政策時，救援名單裡要有持有組織政策權限、能對專案解除它的人。

每一步的指令、實跑看到的輸出，以及每一步沒做或換一種做法時的結果，在 [GCP VM 的 SSH 與 RDP 改走 IAP 的實測紀錄](/infra/cloud-providers/gcp/hands-on/iap-ssh-migration-walkthrough/)：盤點在〈切換前的盤點：依賴舊規則的連線〉，救援入口在〈準備救援入口：Serial Console 與本機救援帳號〉，停用驗證在〈停用舊規則，用 IAP 驗證新規則〉，`default-allow-internal` 與 `default-allow-icmp` 的收斂在〈收斂 default-allow-internal 與 default-allow-icmp〉。

## IAP 通道連不上時的依層判讀

`--tunnel-through-iap` 的連線失敗時，錯誤訊息與它停在哪一層對得起來：

- **錯誤訊息說 API 未啟用**：連線停在 IAP 端點之前，專案上還沒有啟用 `iap.googleapis.com`。
- **`4033`（not authorized）**：停在通道授權。成因是這個帳號沒有 `roles/iap.tunnelResourceAccessor`、IAM Conditions 不允許這個 port 或 VM、條件的期限已過，或 VM 不存在、沒有在執行；帳號實際拿不拿得到權限，以 Policy Troubleshooter 的結果為準（見〈IAP 的 IAM 授權範圍：誰拿得到通道〉）。IAM 綁定送出之後約 60 到 120 秒才生效，這段時間內的 `4033` 不代表條件寫錯。
- **`4003`（failed to connect to backend）**：IAP 已經放行，連不到 VM 的那個 port。成因在網路可達性那一層：VM 沒帶 tag、新規則的網路或 port 寫錯、組織的階層式防火牆或 network firewall policy 先擋下（這類政策優先於專案規則，專案規則寫對了也連不上），或 VM 上的作業系統防火牆（ufw、firewalld、Windows 防火牆）與 sshd 沒有在監聽。防火牆這一段由 Connectivity Tests（`gcloud network-management connectivity-tests create`，來源給 IAP 位址段裡的一個 IP、目的地給這台 VM 與 port）模擬一次 IAP 到 VM 的連線，結果指出是哪一條規則或政策擋下；完整的指令在 [GCP VM 的 SSH 與 RDP 改走 IAP 的實測紀錄](/infra/cloud-providers/gcp/hands-on/iap-ssh-migration-walkthrough/) 的〈停用舊規則，用 IAP 驗證新規則〉。VM 內部的成因要從 Serial Console 進去看。
- **通道開了、登入時 `Permission denied (publickey)`**：停在主機登入驗證。啟用了 OS Login 時，成因是 OS Login 的登入角色或 `roles/iam.serviceAccountUser` 缺了；沒啟用時，成因是 metadata 裡沒有這把公鑰或缺修改 metadata 的權限（見〈SSH 金鑰在 GCP 上的管理位置：metadata 金鑰與 OS Login 的啟用條件〉）。

## IAP 的 IAM 授權範圍：誰拿得到通道

改走 IAP 之後，VM 的連線權限改由 IAM 決定，所以 IAM policy 的寬度就是 SSH 與 RDP 的暴露面。開通道的角色 `roles/iap.tunnelResourceAccessor` 可以用 IAM Conditions 限定 port（`destination.port == 22`）、單台 VM（`destination.ip == "<vm-internal-ip>"`）或期限（`request.time < timestamp("<expiry-time>")`），各種條件的完整指令在 [GCP VM 的 SSH 與 RDP 改走 IAP 的實測紀錄](/infra/cloud-providers/gcp/hands-on/iap-ssh-migration-walkthrough/) 的〈授予開通道的 IAM 權限〉。幾個地方會讓這個範圍在不知不覺中變大或對不到人：

- **專案層級的基本角色**：Owner 這一類基本角色涵蓋開通道的權限，而且不受 IAM Conditions 限制。日常登入用的帳號拿掉基本角色、改授本篇列出的具體角色，Owner 只留給緊急時才用的帳號；團隊全員都是 Owner 時，IAM Conditions 對任何人都不生效，OS Login 的單台先行驗證也找不到非 Owner 的人來做。綁定之前先用 `gcloud projects get-iam-policy <project-id>` 列出目前持有基本角色的成員，再用 IAM 的 Policy Troubleshooter 確認某個帳號實際拿不拿得到 `iap.tunnelInstances.accessViaIAP`；`get-iam-policy` 只列出直接綁定，群組與繼承來的權限以 Policy Troubleshooter 的結果為準。稽核要一份「所有拿得到通道的人」的清單時，用 Policy Analyzer（`gcloud asset analyze-iam-policy --organization=<org-id> --permissions=iap.tunnelInstances.accessViaIAP --expand-groups`），`--expand-groups` 讓結果把 Google Group 展開成成員（預設不展開，只列到群組），要逐台列出 VM 時另加 `--expand-resources`；Policy Troubleshooter 一次只回答一個帳號。
- **整批授權**：把 `roles/iap.tunnelResourceAccessor` 綁給 `domain:` 或大型群組，等於讓整個組織的帳號都能開通道。綁給負責維運的群組，並用 IAM Conditions 限定 port 與 VM。
- **服務帳號**：CI 或自動化工具用的服務帳號若持有通道權限，它的金鑰外洩就等同一把能連進所有 VM 的鑰匙。GCP 上這類帳號用 Workload Identity Federation（[Workload Identity](/backend/knowledge-cards/workload-identity/)）取得短期存取憑證，不發長期金鑰：CI 平台簽發的 OIDC token 換成服務帳號的身分，設定方式以 GCP 的 Workload Identity Federation 文件為準，與 AWS 上用 OIDC 換取 IAM role 的對照見[身分與存取憑證地基 — IAM 模型、OIDC 短期憑證與權限邊界設計](/infra/02-identity-credentials/iam-oidc-privilege-boundary/)的〈OIDC：給 CI/CD 的短期憑證〉。服務帳號要的角色與人相同：開通道的 `roles/iap.tunnelResourceAccessor`，啟用 OS Login 之後另加 OS Login 的登入角色，VM 掛著服務帳號時再加那個服務帳號的 `roles/iam.serviceAccountUser`。
- **組織外的帳號**：外包人員用他自己公司或個人的 Google 帳號時，OS Login 預設不讓組織外的帳號登入，要在組織層級另外授予 `roles/compute.osLoginExternalUser`（未實跑：測試帳號底下沒有 Organization）；組織若強制了 Organization Policy 的 `iam.allowedPolicyMemberDomains`（只允許組織網域的成員出現在 IAM 綁定裡），連綁定本身都會被拒絕；2024 年 5 月 3 日之後建立的 Organization 預設就強制這一條，用〈組織層級的護欄：Organization Policy 與階層式防火牆〉的 `org-policies list` 確認。這類帳號也不受組織的兩步驟驗證強制管轄，所以替外包人員在組織的 Cloud Identity 建帳號，比授權給外部帳號更容易控制，合約到期時停用帳號、或用帶 `request.time` 的條件讓綁定自動失效。

通道授權改用 Google 帳號之後，帳號被釣魚，攻擊者就能從 IAP 開通道。GCP 上的對應設定是在 Google Workspace 或 Cloud Identity 對能開通道的帳號強制兩步驟驗證，管理員帳號用硬體安全金鑰或 [passkey](/backend/knowledge-cards/passkey/) 這類防釣魚的方式——一次性驗證碼會在釣魚頁面上被一起騙走。`gcloud` 登入之後會在本機保存 refresh token，管理員帳號停用前這份 token 一直可用，而 token 檔可以被複製；Workspace 與 Cloud Identity 的管理控制台有 Google Cloud 工作階段控制，設定多久要重新驗證一次（1 到 24 小時）；這項設定預設關閉，啟用之後這個間隔才是本機 token 被複製之後能用多久的上限，被設成受信任而豁免的應用程式不受它限制。需要再收緊時，Context-Aware Access 可以在 IAM 綁定上加 access level 條件（Access Context Manager 定義的一組連線條件，例如只允許公司管理的裝置或特定網段）。

人員異動時，移出群組或移除 IAM 綁定只擋下下一次開通道；已經開著的工作階段要另外在 VM 上結束，做法見〈SSH 金鑰在 GCP 上的管理位置：metadata 金鑰與 OS Login 的啟用條件〉最後結束工作階段的那兩段。

## SSH 金鑰在 GCP 上的管理位置：metadata 金鑰與 OS Login 的啟用條件

GCP 上把 SSH 公鑰交給 Linux VM 有兩種方式，分別對應[伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)〈主機登入驗證的做法：SSH 金鑰怎麼發、怎麼收回〉裡的靜態公鑰與由中央服務決定的公鑰：metadata 金鑰寫在專案或 VM 的 metadata（設在專案或 VM 上的鍵值設定）裡，由 VM 上的 guest agent（GCP 映像檔內建、把 metadata 同步進 VM 的常駐程式）寫進 `authorized_keys`；[OS Login](/infra/knowledge-cards/os-login/) 依 Google 帳號與 IAM role 決定誰能登入、能不能用 sudo。寫在專案 metadata 的公鑰對專案內每一台沒有啟用 OS Login 的 VM 都生效，成員離職時漏刪一把，那把金鑰就持續能登入整個專案，而沒啟用 OS Login 時 `gcloud compute ssh` 預設就是把公鑰寫進專案 metadata。兩者的機制與差別見 OS Login 卡。Oracle Cloud 與 AWS 上不放金鑰時由哪些服務登入、各自包辦管理通道的哪幾層，見 [登入：SSH 金鑰、預設使用者、建立後加金鑰與不放金鑰時的登入服務](/infra/cloud-providers/vm-options/login/) 的〈不放金鑰時的登入服務〉。

啟用 OS Login（metadata 的 `enable-oslogin=TRUE`）之後，VM 不再接受 metadata 裡的金鑰，原本靠 metadata 金鑰登入的管理員與自動化工具會立刻連不進去。啟用的順序因此由三個條件決定：

- **角色先授**：每一位管理員與每一個要登入 VM 的服務帳號先拿到登入角色（`roles/compute.osLogin` 一般登入，`roles/compute.osAdminLogin` 含 sudo）；VM 掛著服務帳號時（`gcloud compute instances describe` 輸出的 `serviceAccounts` 欄不是空的，用 Google Cloud 控制台以預設值建立的 VM 會掛上 Compute Engine 預設服務帳號），每一個登入者另外需要那個服務帳號的 `roles/iam.serviceAccountUser`。
- **單台先行**：先在單一 VM 上啟用，讓角色漏授這類錯誤只鎖住那一台；驗證要由非 Owner 的管理員做，Owner 本身持有全部權限，只由 Owner 驗證會看不出漏授。
- **VM 層級蓋過專案層級**：專案層級啟用之後，VM 層級設了 `enable-oslogin=FALSE` 的 VM 仍然讀 metadata 金鑰；專案 metadata 的 `ssh-keys` 留著前任與現任成員的公鑰，OS Login 一旦還原成 `FALSE` 它們就又能用，所以全部 VM 都啟用之後要清掉。

啟用、還原、列出 `FALSE` 的 VM 與清除 `ssh-keys` 的指令，在 [GCP VM 的 SSH 與 RDP 改走 IAP 的實測紀錄](/infra/cloud-providers/gcp/hands-on/iap-ssh-migration-walkthrough/) 的〈啟用 OS Login：先授角色、單台先行、再做專案層級〉。OS Login 只作用在 Linux VM，Windows VM 的登入仍由 Windows 帳號決定。OS Login 也可以要求登入時的兩步驟驗證（metadata 設 `enable-oslogin-2fa=TRUE`），讓每一次 SSH 登入都多一次 Google 帳號的第二因素；沒有啟用兩步驟驗證的帳號會登不進去，所以同樣先對單一 VM 設定驗證。OS Login 文件寫明這項要求不套用在服務帳號上，CI 這類登入者不受它約束。

帳號停用或角色移除之後，下一次登入就會失敗；已經建立的工作階段不受影響，所以處理離職或帳號外洩時，管理員要另外登入 VM 結束那個使用者的工作階段。在 systemd 的發行版上：

```bash
# 結束 systemd-logind 登記過的工作階段
sudo loginctl terminate-user <username>

# 確認那個使用者的行程已經全部結束；有輸出就代表還有行程在跑
pgrep -u <username> -a

# 還有剩下的行程時，直接結束
sudo pkill -KILL -u <username>
```

`<username>` 是 OS Login 由 Google 帳號轉成的使用者名稱，例如 `alice_example_com`。確認的依據是 `pgrep` 的輸出，而不是 `terminate-user` 的回傳值：`loginctl` 只結束 systemd-logind 登記過的工作階段，登入時 `pam_systemd` 登記失敗的工作階段（VM 的日誌裡有 `pam_systemd(sshd:session): Failed to create session`）不在它的清單裡，這時 `loginctl terminate-user` 會回報使用者沒有登入，而行程仍在執行。Windows VM 上用 `query session` 找出那個使用者的 RDP 工作階段，再用 `logoff <session-id>` 結束。

## 拿掉外部 IP 之後的出站路徑：Cloud NAT 與 Private Google Access

Cloud NAT 承接沒有外部 IP 的 VM 往外的連線，`apt update`、`docker pull`、呼叫第三方 API 都靠它；它和 AWS 的 NAT Gateway 承擔同一件事，機制見 [NAT](/infra/knowledge-cards/nat/)。Cloud NAT 建在 Cloud Router（GCP 管理 VPC 路由的元件）上，以 region 為單位生效，VM 分布在幾個 region 就要各建一組；出站 IP 可以讓 GCP 自動配發（可能變動），或改用預留的靜態 IP（外部服務要求來源 IP 白名單時）。VM 要存取 Cloud Storage、Artifact Registry 這類 Google API 時，subnet 開啟 Private Google Access，就能用內部 IP 連到 Google API，不經過 Cloud NAT，也就不產生 NAT 的資料處理費。

拿掉外部 IP 的判斷有兩點：

- **哪些 VM 可以拿**：對外提供服務的 VM（網站、API）移除外部 IP 之前，要先把流量入口換到負載平衡器，否則移除的當下服務就中斷，入口層的設計見[流量入口層 — 請求怎麼從使用者到達應用](/infra/03-network-foundation/traffic-entry-layer/)。只做管理用途的 VM 可以直接移除。
- **驗證要在移除之後做**：網卡還帶著外部 IP 時，Cloud NAT 不處理這張網卡的出站流量，流量走的是 VM 自己的外部 IP，所以移除之前測出站一定是通的，證明不了 Cloud NAT 有效。移除之後在 VM 上看出站的來源 IP，判斷依據是那個 IP 在不在 Cloud NAT 的 IP 清單（`gcloud compute routers get-nat-ip-info`）裡，而不是移除前後的 IP 有沒有變：自動配發的 Cloud NAT 可能正好配到這台 VM 剛釋放的那個外部 IP。

建 Cloud NAT、開 Private Google Access、查 access config 名稱與移除外部 IP、驗證出站的指令與實跑結果，在 [GCP VM 的 SSH 與 RDP 改走 IAP 的實測紀錄](/infra/cloud-providers/gcp/hands-on/iap-ssh-migration-walkthrough/) 的〈建 Cloud NAT 並移除外部 IP〉。移除之後，這台 VM 只剩 IAP 一條管理路徑，連線一律加 `--tunnel-through-iap`。

## 組織層級的護欄：Organization Policy 與階層式防火牆

`default` 網路與 `default-allow-ssh`、`default-allow-rdp` 這些預設規則，每個新建的專案都會重新長出來，所以單一專案的收斂只保護那一個專案。要讓組織裡的新專案不再帶著這些規則，在 Organization Policy 設定下面幾個 constraint。這一節的指令需要專案屬於一個 Organization 資源，執行者要有組織層級的權限（`roles/orgpolicy.policyAdmin` 與 `roles/compute.orgFirewallPolicyAdmin`）；這一節的指令沒有實跑（測試帳號底下沒有 Organization）。2024 年 5 月 3 日之後建立的 Organization 會預設強制一組 constraint，先用 `gcloud resource-manager org-policies list --organization=<org-id>` 看哪些已經生效。

- `compute.skipDefaultNetworkCreation`：新專案不再自動建立 `default` 網路。
- `compute.vmExternalIpAccess`：只允許列在清單上的 VM 持有外部 IP，其餘 VM 建立時帶外部 IP 會被拒絕。
- `compute.requireOsLogin`：新建的專案與 VM 啟用 OS Login，任何層級都無法用 metadata 把它關掉；既有 VM 是否已啟用要另外盤點，而既有的管理員要先拿到 OS Login 的登入角色。
- `compute.disableSerialPortAccess`：關閉 Serial Console 的存取，讓救援入口平時保持關閉；救援時由持有組織政策權限的人對那個專案解除，救援結束後恢復。

```bash
# 在組織層級強制布林型的 constraint（skipDefaultNetworkCreation、requireOsLogin、disableSerialPortAccess 同一種寫法）
gcloud resource-manager org-policies enable-enforce compute.skipDefaultNetworkCreation \
  --organization=<org-id>

# 救援時，對單一專案解除 Serial Console 的限制
gcloud resource-manager org-policies disable-enforce compute.disableSerialPortAccess \
  --project=<project-id>

# 救援結束後，刪掉專案層級的例外，讓專案重新繼承組織層級的強制
gcloud resource-manager org-policies delete compute.disableSerialPortAccess \
  --project=<project-id>
```

`<org-id>` 用 `gcloud organizations list` 查。`compute.vmExternalIpAccess` 是清單型的 constraint，要用政策檔列出允許的 VM，寫法以 Organization Policy 文件為準。

階層式防火牆政策（hierarchical firewall policy）套用在組織或資料夾上，優先於專案的 VPC 防火牆規則評估。政策裡的規則依 priority 數字由小到大評估，命中 `allow` 或 `deny` 就停止，專案的規則不會再被看到；命中 `goto_next` 則把這條連線交給下一層（最終是專案的 VPC 規則）判斷。所以規則的相對 priority 決定結果：

- 交給專案判斷的 IAP 規則（來源 `35.235.240.0/20`，有 IPv6 VM 時加上 `2600:2d00:1:7::/64`；tcp:22 與 tcp:3389；動作 `goto_next`）priority 要比拒絕規則小，否則 IAP 的流量先被拒絕規則擋下。它用 `goto_next` 而不用 `allow`：`allow` 會讓 IAP 的位址段直接通到組織內每一台 VM，繞過專案用 target tag 做的收斂。
- VM 之間或從 VPN 進來的 SSH 需要保留時，它們的來源（內部網段、VPN 的位址段）同樣要有一條 priority 比拒絕規則小的 `goto_next` 規則，因為拒絕規則的 `0.0.0.0/0` 也涵蓋內部位址。
- 拒絕 `0.0.0.0/0` 連到 tcp:22 與 tcp:3389 的規則只涵蓋 IPv4，IPv6 要另寫一條拒絕 `::/0` 的規則，這兩條拒絕規則之間沒有先後依賴。

```bash
# 建立組織層級的防火牆政策，加入規則，再關聯到一個資料夾（之後再關聯到組織）
gcloud compute firewall-policies create --short-name=<policy-name> --organization=<org-id>

gcloud compute firewall-policies rules create 100 --firewall-policy=<policy-name> \
  --organization=<org-id> --direction=INGRESS --action=goto_next \
  --src-ip-ranges=35.235.240.0/20 --layer4-configs=tcp:22,tcp:3389

gcloud compute firewall-policies rules create 1000 --firewall-policy=<policy-name> \
  --organization=<org-id> --direction=INGRESS --action=deny \
  --src-ip-ranges=0.0.0.0/0 --layer4-configs=tcp:22,tcp:3389

gcloud compute firewall-policies associations create --firewall-policy=<policy-name> \
  --organization=<org-id> --folder=<folder-id>
```

`100`、`1000` 是規則的 priority，只要 `goto_next` 那幾條比拒絕規則小就行，中間留空號給之後要插入的規則。`<policy-name>` 是自己取的政策名稱。`--folder=<folder-id>` 把政策關聯到一個資料夾；組織與資料夾層級的政策影響其下每一個專案，先關聯到一個測試用的資料夾，確認既有服務沒有依賴被擋掉的路徑，再關聯到組織（拿掉 `--folder`）。

## 稽核與偵測：firewall log、Cloud Audit Logs 與 Security Command Center

[伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)〈組織層級的護欄與稽核紀錄〉列出事後要查的三項事件，在 GCP 上分別從這幾個來源查：

- **誰在什麼時候經由哪條通道登入了哪台 VM**：開通道的帳號與目標 VM 記在 Cloud Audit Logs 裡 IAP 的 Data Access 紀錄，要為 Cloud Identity-Aware Proxy 開啟「管理員讀取」（`ADMIN_READ`）類型才有：開通道時 IAP 檢查的權限 `iap.tunnelInstances.accessViaIAP` 歸在這個類型，只開「資料讀取」（`DATA_READ`）時，實測連了十次左右，開通道的紀錄一筆都沒有。開啟之後經由 IAP 連一次、查到方法名稱為 `AuthorizeUser` 的紀錄才算開對，查詢指令在 [GCP VM 的 SSH 與 RDP 改走 IAP 的實測紀錄](/infra/cloud-providers/gcp/hands-on/iap-ssh-migration-walkthrough/) 的〈啟用 IAP API、開啟稽核紀錄並建立只放行 IAP 來源的防火牆規則〉。登入 VM 的帳號記在 VM 上的 sshd 紀錄，啟用 OS Login 時是由 Google 帳號轉成的使用者名稱。啟用 OS Login 時，每一次登入另外在 Cloud Audit Logs 留下 OS Login 檢查登入權限的 Data Access 紀錄，記著 Google 帳號與目標 VM，而且存在 VM 之外，取得 VM root 的人清不掉：

  ```bash
  # 列出最近七天每一次 OS Login 的時間、Google 帳號與目標 VM；--freshness 依調查範圍調整
  gcloud logging read 'protoPayload.serviceName="oslogin.googleapis.com" AND protoPayload.methodName:"CheckPolicy"' \
    --freshness=7d --format="value(timestamp,protoPayload.authenticationInfo.principalEmail,protoPayload.resourceName)"
  ```

  實測的專案沒有為 Cloud OS Login API 另外開啟 Data Access 紀錄，`CheckPolicy` 的紀錄仍然寫進了 `data_access` 這個紀錄檔；查不到時，到「IAM 與管理 > 稽核記錄」確認 Cloud OS Login API 的 Data Access 設定，並用 `gcloud projects get-iam-policy <project-id> --format="json(auditConfigs)"` 看專案層有沒有排除它。firewall rules logging 記錄每一次放行的來源 IP、目的 VM、port 與命中的規則名稱，經由 IAP 的連線來源都是 IAP 的位址段，從這份紀錄看不出是哪個人。
- **誰在什麼時候開了救援入口**：開啟 Serial Console 的 metadata 修改與組織政策的解除屬於 Admin Activity 紀錄，預設就有。
- **環境裡是否出現新的對外開放管理 port**：Security Command Center 的 Security Health Analytics 持續掃描組織內的防火牆規則，`OPEN_SSH_PORT` 與 `OPEN_RDP_PORT` 這兩類 finding 對應的就是對外開放 22 與 3389 的規則。處理方式是照〈切換到 IAP 的順序〉把規則換掉（逐步指令在 [GCP VM 的 SSH 與 RDP 改走 IAP 的實測紀錄](/infra/cloud-providers/gcp/hands-on/iap-ssh-migration-walkthrough/)），直接刪除會中斷管理員自己的連線；規則刪除或縮小來源之後，下一次掃描會把對應的 finding 標為已解決。

事件發生時才發現 IAP 的 Data Access 紀錄沒開，開啟之前的通道紀錄查不回來，剩下的來源是 Admin Activity 紀錄裡 metadata 與 IAM 的變更，以及 VM 上的 sshd 紀錄；sshd 紀錄只存在 VM 本機，取得 root 的攻擊者可以清掉，所以要保全時先把 VM 的磁碟做快照，證據的保全與分流見 [8.18 Incident Intake & Evidence Triage](/backend/08-incident-response/incident-intake-evidence-triage/)。

AWS 上同類的盤點流程見 [Security Group 稽核與清理](/infra/03-network-foundation/security-group-audit-cleanup/)：兩邊都是先列出來源是 `0.0.0.0/0` 的規則，逐條確認有沒有服務依賴，再刪除或縮小來源。

## 延伸閱讀：逐步的實作、與廠商無關的設計模型與 VPC 的分層規則

- → [GCP VM 的 SSH 與 RDP 改走 IAP 的實測紀錄](/infra/cloud-providers/gcp/hands-on/iap-ssh-migration-walkthrough/)：盤點、救援入口、IAP 規則與 IAM、停用舊規則驗證、OS Login 啟用與移除外部 IP 的逐步指令、實跑看到的輸出，以及每一步沒做或換一種做法時的結果
- → [伺服器管理通道的設計：網路可達性、通道授權、主機登入驗證三層的做法與選擇，以及救援入口](/infra/03-network-foundation/management-access-channel/)：跳板機、VPN、代理程式反向連線、SSH 憑證這些 GCP 以外的做法，以及依存取者身分、代理把連線送進主機的方式、金鑰收回方式選擇組合的依據
- → [OpenSSH 內建 CA 的 SSH 憑證導入](/infra/03-network-foundation/openssh-ca-setup/)：主機不全在 GCP、OS Login 用不上時，改用 SSH 憑證讓登入權限自動到期
- → [GCP 上由 MIG 與 GKE 管理的 VM 的管理存取](/infra/cloud-providers/gcp/gke-mig-management-access/)：本篇的 tag、OS Login 與移除外部 IP 在 instance template 與 node pool 上的寫法，以及 GKE 控制平面的存取
- → [網路地基 — VPC、subnet 分層與 security group 設計](/infra/03-network-foundation/vpc-subnet-security-group/)：VPC 與 subnet 的分層與最小開放原則，本篇的防火牆規則是同一套原則在 GCP 上的寫法
