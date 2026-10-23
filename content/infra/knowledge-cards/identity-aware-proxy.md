---
title: "Identity-Aware Proxy（身分感知代理）"
date: 2026-10-23
description: "要讓管理員或使用者不經公開入口連到內部主機與服務、評估把存取控制從來源 IP 改成帳號身分時，查身分感知代理的連線路徑、前提與代價"
weight: 54
tags: ["infra", "knowledge-cards", "network", "access", "zero-trust"]
---

身分感知代理（identity-aware proxy）是一個放在網際網路與內部主機之間的 [Reverse Proxy](/infra/knowledge-cards/reverse-proxy/)：它接收外部連線，先向組織的 [Identity Provider](/backend/knowledge-cards/identity-provider/) 確認發起連線的帳號、再依授權規則決定是否替這條連線開到後端，通過的連線由代理從固定的內部位址段送進去。後端主機的防火牆只需要放行代理的位址段，主機本身不必持有公開 IP。它是 [Zero Trust（零信任）](/backend/knowledge-cards/zero-trust/) 原則在存取入口上的一種實作：放行的依據是每一次連線的身分，網路位置不構成信任的理由。

## 概念位置

在伺服器管理通道的模型裡，身分感知代理同時承擔兩層：網路可達性（sshd 只對代理可見）與通道授權（用 IdP 帳號判斷誰可以開通道）。主機登入驗證仍由主機上的 sshd 負責，金鑰的發放方式另見 [OS Login](/infra/knowledge-cards/os-login/) 與 [SSH Certificate（SSH 憑證）](/infra/knowledge-cards/ssh-certificate/)。

它與 [Bastion Host（跳板機）](/infra/knowledge-cards/bastion-host/) 解決同一件事——讓內部主機不必各自對外——差別在對外接收連線的那一台由誰維運、用什麼判斷身分：跳板機是自己維運的主機、用 SSH 金鑰判斷；身分感知代理是廠商或自管的代理服務、用 IdP 帳號判斷。它與一般反向代理的差別在轉送前多了一次身分驗證與授權。

常見的實作有 GCP 的 IAP（Identity-Aware Proxy，對 HTTPS 應用與 TCP 連線各有一種模式，TCP forwarding 的來源位址段是 `35.235.240.0/20`）、Cloudflare Access、Teleport 的 proxy。這個模式的公開源頭是 Google 2014 年起發表的 BeyondCorp 系列論文。

## 可觀察訊號

- 主機的防火牆規則只放行某一段固定的代理位址，沒有任何來源是 `0.0.0.0/0` 的管理 port 規則
- 主機沒有公開 IP，管理員仍然用 `ssh` 或廠商 CLI 連得進去
- 主機上的認證紀錄裡，SSH 連線的來源 IP 全部落在代理的位址段，看不出是哪個人——要查人得看代理或 IdP 的 audit log

## 設計責任

導入身分感知代理時要決定：

- **IdP 帳號的安全強度**：存取權限轉移到帳號上之後，帳號被釣魚等於通道被打開，所以 IdP 端要強制多因素驗證，管理員帳號優先用防釣魚的硬體金鑰
- **授權範圍**：授權綁給負責維運的群組，並限定可以連的 port 與主機，避免整個組織的帳號都拿得到通道
- **代理的可用性與延遲**：所有位元組都經過代理轉送，代理服務中斷時管理通道一起中斷，大量傳檔也比直連慢；救援時的備用路徑見 [Serial Console（序列主控台）](/infra/knowledge-cards/serial-console/)
- **稽核紀錄的位置**：主機端只看得到代理的位址，「誰在什麼時候連進哪台主機」要從代理或 IdP 的 audit log 取得，這份紀錄要先開啟

## 鄰卡

- [Bastion Host（跳板機）](/infra/knowledge-cards/bastion-host/) — 同樣收斂對外入口，由自己維運的主機轉接
- [Security Group](/infra/knowledge-cards/security-group/) — 放行代理位址段的那一條入站規則所在的位置
- [Identity Provider](/backend/knowledge-cards/identity-provider/) — 代理用來確認帳號的系統
