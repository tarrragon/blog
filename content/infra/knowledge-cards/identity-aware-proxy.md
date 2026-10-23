---
title: "Identity-Aware Proxy（身分感知代理）"
date: 2026-10-23
description: "要讓管理員或使用者不經公開入口連到內部主機與服務、評估把存取控制從來源 IP 改成帳號身分時，查身分感知代理的連線路徑、前提與代價"
weight: 54
tags: ["infra", "knowledge-cards", "network", "access", "zero-trust"]
---

身分感知代理（identity-aware proxy）是一個放在網際網路與內部主機之間的 [Reverse Proxy](/infra/knowledge-cards/reverse-proxy/)：它接收外部連線，先向組織的 [Identity Provider](/backend/knowledge-cards/identity-provider/) 確認發起連線的帳號、再依授權規則決定是否替這條連線開到後端。通過的連線送到後端的方式有兩種：由代理從它自己的固定位址段連到主機的內部 IP（GCP 的 IAP），這時主機的防火牆只放行那段代理位址；或經由主機上的代理程式（connector，例如 `cloudflared`）主動往外建立的反向連線送進去（Cloudflare Tunnel、Teleport agent），這時主機不開任何入站 port。兩種方式下主機都不必持有公開 IP。它是 [Zero Trust（零信任）](/backend/knowledge-cards/zero-trust/) 原則在存取入口上的一種實作：放行的依據是每一次連線的身分，網路位置不構成信任的理由。

## 概念位置

管理通道拆成網路可達性、通道授權、主機登入驗證三層來看時（模型見[伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)），身分感知代理同時承擔網路可達性與通道授權：sshd 只對代理可見，而能不能開通道由代理用 IdP 帳號判斷——這個判斷就是通道授權，指的是決定「這個人能不能打開通往主機的連線」，與登入主機時驗證 SSH 金鑰是兩回事。主機登入驗證在多數實作裡仍由主機上的 sshd 負責；Teleport 的節點這類實作用自己內建的 SSH 伺服器與代理簽發的憑證，主機登入驗證跟著換掉。由 sshd 負責時，金鑰的發放方式另見 [OS Login](/infra/knowledge-cards/os-login/) 與 [SSH Certificate（SSH 憑證）](/infra/knowledge-cards/ssh-certificate/)。

它與 [Bastion Host（跳板機）](/infra/knowledge-cards/bastion-host/) 都讓內部主機不必各自對外，差別在對外接收連線的元件由誰維運、用什麼判斷身分：跳板機是自己維運的主機、用 SSH 金鑰判斷；身分感知代理是廠商提供或自己架設的代理服務、用 IdP 帳號判斷。它與一般反向代理的差別在轉送前多了一次身分驗證與授權。

常見的實作有 GCP 的 IAP（Identity-Aware Proxy，對 HTTPS 應用與 TCP 連線各有一種模式，TCP forwarding 的來源位址段是 `35.235.240.0/20`，到得了同一家雲端裡的主機與經專線或 VPN 接進來的地端主機）、Cloudflare Access、Teleport 的 proxy。Cloudflare Access 與 Teleport 用反向連線把流量送進主機，主機上的 connector 怎麼往外連、斷線時會怎樣見 [Outbound Tunnel（出站隧道）](/backend/knowledge-cards/outbound-tunnel/)。這個模式的公開源頭是 Google 2014 年起發表的 BeyondCorp 系列論文。

## 可觀察訊號

由代理連到內部 IP 的模式（GCP IAP）：

- 主機的入站規則只放行某一段固定的代理位址，沒有任何來源是 `0.0.0.0/0` 的管理 port 規則
- 主機上的認證紀錄裡，SSH 連線的來源 IP 全部落在代理的位址段，看不出是哪個人——要查人得看代理或 IdP 的 audit log

經由代理程式反向連線的模式（Cloudflare Tunnel、Teleport agent）：

- 主機上有一個常駐的代理程式（例如 `cloudflared`、`teleport`），主機的入站規則完全沒有管理 port
- 認證紀錄裡的 SSH 來源是 `127.0.0.1` 或代理程式所在的本機位址

兩種模式共同的樣子是主機沒有公開 IP，管理員仍然用 `ssh` 或廠商 CLI 連得進去。

## 設計責任

導入身分感知代理之後，主機自己不再判斷連線者是誰，下面這些判斷移到代理與 IdP 上：

- **IdP 帳號的安全強度**：存取權限轉移到帳號上之後，帳號被釣魚等於通道被打開，所以 IdP 端要強制多因素驗證，管理員帳號優先用防釣魚的硬體金鑰或 [Passkey](/backend/knowledge-cards/passkey/)
- **授權範圍**：授權綁給負責維運的群組，並限定可以連的 port 與主機，避免整個組織的帳號都拿得到通道
- **代理的 session 長度**：IdP 停用一個帳號之後，代理已經簽給他的 session 或憑證要到期或被撤銷才失效（Cloudflare Access 的 session 最長可以設到一個月，`gcloud` 在本機保存 refresh token），所以收回延遲的上限是代理端設定的 session 長度；處理離職或帳號外洩時另外在代理端撤銷 session。登入後留在本機的 token 檔可以被複製重放，不會再過一次多因素驗證，session 越短、或綁定裝置，被複製之後能用的時間越短
- **代理的可用性與延遲**：所有位元組都經過代理轉送，代理服務中斷時管理通道一起中斷，大量傳檔也比直連慢；救援時的備用路徑見 [Serial Console（序列主控台）](/infra/knowledge-cards/serial-console/)
- **稽核紀錄的位置與開啟時機**：主機端只看得到代理的位址，「誰在什麼時候連進哪台主機」要從代理或 IdP 的 audit log 取得。這份紀錄只記錄開啟之後的連線，事後要調查一次入侵時，開啟之前的連線查不回來，所以在切換到代理的同一天開啟

## 鄰卡

- [Bastion Host（跳板機）](/infra/knowledge-cards/bastion-host/) — 同樣收斂對外入口，由自己維運的主機轉接
- [Security Group](/infra/knowledge-cards/security-group/) — 放行代理位址段的那一條入站規則所在的位置；AWS 叫 security group，GCP 對應的是 VPC 防火牆規則
- [Identity Provider](/backend/knowledge-cards/identity-provider/) — 代理用來確認帳號的系統
- [GCP VM 的 SSH 與 RDP 管理通道](/infra/03-network-foundation/gcp-iap-ssh-access/) — GCP IAP 的防火牆規則、IAM 權限與切換順序的實際指令
- [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/#網路可達性主機分布與代理把連線送進主機的方式) — 從代理位址段連入與代理程式反向連線兩種送達方式，依主機分布的選擇條件
