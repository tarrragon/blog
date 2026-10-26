---
title: "Bastion Host（跳板機）"
date: 2026-10-23
description: "內部主機不想各自對外開管理 port、要設定 ProxyJump 經由跳板機連線、判斷 agent forwarding 的風險，或要評估自建跳板機與改用身分感知代理的取捨時，查跳板機的連線方式、暴露面與維運責任"
weight: 55
tags: ["infra", "knowledge-cards", "network", "ssh", "access", "bastion"]
---

管理員要登入 private [Subnet](/infra/knowledge-cards/subnet/) 裡的主機時，跳板機（bastion host，也稱 jump host；其他中文資料常寫作「堡壘主機」）是常見的中繼點：一台放在公開網段、只負責轉接管理連線的主機。其他主機的防火牆只接受來自跳板機的 SSH，管理員先連上跳板機，再從那裡連到目的主機。OpenSSH 用 `ssh -J <bastion-host> <target-host>`（設定檔裡的 `ProxyJump`）一次完成兩段連線，私鑰留在管理員自己的電腦上，不必複製到跳板機。

跳板機處理的是主機以 [SSH](/infra/knowledge-cards/ssh/) 登入管理的情境：每台主機上跑著接受 SSH 連線的服務程式 sshd、預設監聽 22 port。只部署在 PaaS 或 serverless 平台、沒有任何可以 SSH 登入的主機時，平台自己的主控台與 CLI 就是管理入口，用不到跳板機。

## 概念位置

把管理通道拆成網路可達性、通道授權、主機登入驗證三層時（見[伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)），跳板機是網路可達性的做法之一：它把「每台主機都對外開 22 port」收斂成「只有一台對外開」。它同時兼任通道授權——決定誰能打開通往主機的連線——判斷依據是跳板機上的 SSH 金鑰，或跳板機信任的 SSH CA 所簽的憑證；跳板機與目的主機接受同一把金鑰時，一把私鑰外洩就同時通過通道授權與主機登入驗證。

跳板機放在 public subnet，目的主機留在 private subnet，兩者之間的放行用 [Security Group](/infra/knowledge-cards/security-group/) 的來源引用表達：目的主機的入站規則把來源寫成「跳板機所屬的那個 security group」而不是一個 IP，跳板機換了 IP 或多加一台，規則都不必改。

暴露面收斂成一台，但沒有消失：跳板機仍然對網際網路開著管理 port，它的 sshd 漏洞與金鑰管理就是整個環境的入口。不讓任何自管主機對外的做法是 [Identity-Aware Proxy（身分感知代理）](/infra/knowledge-cards/identity-aware-proxy/)，對外接收連線的那一層改由代理服務承擔。雲端廠商也提供受管的跳板服務（例如 Azure Bastion、Oracle Cloud 的 Bastion），主機的修補由廠商負責，連線方式與身分驗證依各家服務而定，位置介於自建跳板機與身分感知代理之間。Oracle Cloud 的 Bastion 建立時要指定一個目標 subnet（主機所在的 subnet，或主機所在 subnet 接受其流量的另一個 subnet），經由它登入的主機不需要公開 IP，誰能開工作階段由 IAM 政策決定，設定方式見 [登入：SSH 金鑰、預設使用者、建立後加金鑰與不放金鑰時的登入服務](/infra/cloud-providers/vm-options/login/) 的〈不放金鑰時的登入服務〉。

## 可觀察訊號

- private subnet 主機的 security group 只允許來自某一個 security group（或某一台主機）的 22 port
- 管理員的 `~/.ssh/config` 裡有 `ProxyJump` 設定，或團隊文件寫著「先連 bastion」

## 設計責任

自建跳板機時，整個環境對外的 SSH 暴露都集中在這一台上，所以下面這幾件事的標準比一般主機高：

- **跳板機的來源範圍**：管理員有固定的對外 IP 時，跳板機的 22 port 只放行那幾個 IP；遠端工作、IP 會變動時，白名單縮不下來，跳板機的 22 port 實質上對全網開放，認證紀錄裡會持續出現來自陌生 IP 的失敗登入，它的 sshd 修補速度就是整個環境的暴露期。只放行管理員 IP 時，ISP 重新分配了那個 IP，管理員就連不進跳板機，舊 IP 的新使用者反而在放行範圍裡；這一類會在主機外面改變的設定怎麼定期比對，見 [長期上線主機的維護項目：會累積的資料、定期讀的 log、對外入口的盤點、安全更新、會到期的設定與檢查間隔的推算](/operations/09-host-lifecycle/long-running-host-maintenance/)〈會到期與會改變的外部設定〉
- **私鑰不落地**：agent forwarding 是讓遠端主機借用管理員本機 ssh-agent 裡的私鑰去做下一段認證的功能（`ssh -A` 或設定檔的 `ForwardAgent yes`），開著它時，任何在跳板機上取得 root 的人都能借那把私鑰連到其他主機；把私鑰直接放上跳板機的後果相同。`ProxyJump` 讓第二段認證也在管理員電腦上完成，不需要 agent forwarding。這種從一台主機往其他主機擴散的攻擊見 [Lateral Movement（橫向移動）](/backend/knowledge-cards/lateral-movement/)
- **金鑰不共用、不可複製**：跳板機與目的主機各用不同的金鑰或憑證，讓一把私鑰外洩只通過一層；目的主機的金鑰發放可以改用 [SSH Certificate（SSH 憑證）](/infra/knowledge-cards/ssh-certificate/) 或 [OS Login](/infra/knowledge-cards/os-login/)；跳板機與目的主機信任同一把 SSH CA 時，用不同的 principal 把兩層分開，做法見 [OpenSSH 內建 CA 的 SSH 憑證導入](/infra/03-network-foundation/openssh-ca-setup/)。管理員的私鑰放在硬體安全金鑰裡（OpenSSH 8.2 起的 `ed25519-sk`）時，私鑰檔無法被複製走
- **修補與監控**：跳板機要比其他主機更快套用 sshd 的安全更新，並保留連線紀錄
- **操作紀錄**：外包人員登入正式環境、或稽核要求逐條指令留紀錄時，需要集中錄製管理員在目的主機上執行了什麼；所有管理連線都經過跳板機，所以它是放錄製工具的位置。這個屬性與廠商無關，一套設定涵蓋多雲與地端混用的環境。組織有 IdP 時，讓跳板機只接受 IdP 簽發的短期 SSH 憑證，錄製與隨帳號收回兩者都保留

## 鄰卡

- [SSH](/infra/knowledge-cards/ssh/) — 跳板機轉接的協定與金鑰認證
- [Identity-Aware Proxy（身分感知代理）](/infra/knowledge-cards/identity-aware-proxy/) — 改用代理服務承擔對外接收連線
- [Serial Console（序列主控台）](/infra/knowledge-cards/serial-console/) — 跳板機本身連不上時的備用登入路徑
- [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/#通道授權的身分來源存取者與主機擁有者的關係身分所在的帳號系統) — 存取者是組織成員、外部合作方、個人或機器時，跳板機與其他做法的選擇條件
