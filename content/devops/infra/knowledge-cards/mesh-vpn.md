---
title: "Mesh VPN（網狀 VPN）"
date: 2026-11-21
description: "要讓自己的幾台裝置與主機在不同網路之間互連、在 Tailscale 與自建 WireGuard 之間取捨，或判斷管理服務該放在 VPN 還是 Cloudflare Tunnel 後面時，查 mesh VPN 的連線方式、它跟集中式 VPN 與 outbound tunnel 的分界，以及信任邊界的預設"
weight: 78
tags: ["infra", "knowledge-cards", "network", "vpn", "access"]
---

Mesh VPN（網狀 VPN）是每一台裝置都裝用戶端、裝置之間各自建立加密連線的 VPN：每台裝置拿到一個 VPN 網路裡的私有位址，兩台裝置之間的流量盡量直接送到對方，不經過一台集中的 VPN 伺服器。Tailscale（底層用 WireGuard）、ZeroTier、Nebula 都屬於這一類；自建 WireGuard 時讓每一台的設定都列出其他各台，也組得出同樣的拓撲。裝置在 [CGNAT（電信業者級 NAT）](/devops/infra/knowledge-cards/cgnat/) 或其他 NAT 後面、沒有連得進來的公開位址時，Tailscale、ZeroTier 這類產品先經由協調的一方交換兩端在 NAT 外面的位址與連接埠，再讓兩端同時往外送封包來打通直接連線（NAT traversal），Tailscale 在打不通時改經它的中繼伺服器轉送（Nebula 的中繼要另外設定）。原生的 WireGuard 沒有這兩項功能：手動組的網狀拓撲裡，每一對要互連的裝置至少有一端要連得進來，或另外架一台中繼。

## 跟其他概念的關係

集中式 VPN（hub-and-spoke）指所有用戶端都連到一台 VPN 閘道、彼此之間的流量也經過那台閘道轉送的做法，閘道要有連得進來的公開位址，它停掉時全部用戶端一起斷線；mesh VPN 指裝置之間各自連線的做法，沒有一台轉送全部流量的閘道。mesh VPN 也需要一個知道全部裝置的角色：Tailscale 由它營運的協調伺服器（coordination server）把每台裝置的公鑰與位址發給其他裝置，自建 WireGuard 時這件事由管理者手動在每一台的設定裡做，中間的選項是自架相容的協調伺服器（例如開源的 Headscale）。這個角色停擺時，已經建好的連線照常運作，新裝置加入與設定變更受影響。

[Outbound Tunnel](/backend/knowledge-cards/outbound-tunnel/)（例如 `cloudflared`）指主機往外連到服務商的邊緣、把一個服務發佈成公開網址的做法，訪客用一般瀏覽器連那個網址，不必另外安裝軟體；mesh VPN 指每一個連線方都要裝用戶端、加入同一個 VPN 網路的做法，網路外的人連不到裡面的服務。兩者的連線都由裝置主動往外建立，差別在服務端：mesh VPN 裡的服務仍然在 VPN 的網路介面上接受入站連線，所以誰連得到它，由 VPN 這一層的存取規則與主機的防火牆決定。

管理員連進私有網路裡的主機，還有 [Bastion Host（跳板機）](/devops/infra/knowledge-cards/bastion-host/) 與 [Identity-Aware Proxy（身分感知代理）](/devops/infra/knowledge-cards/identity-aware-proxy/) 兩種做法：跳板機與身分感知代理都在入口的一個點上檢查連線，後面的主機只接受來自那個點的連線；mesh VPN 把檢查放在加入網路的那一刻，裝置通過認證、加入網路之後，預設就連得到網路裡的其他裝置。

## 可觀察訊號與例子

- **裝置多了一個網路介面與一個固定位址**：Tailscale 在 Linux 上建立 `tailscale0` 介面，位址落在 `100.64.0.0/10`；這個位址不隨裝置換網路而改變，手機從 Wi-Fi 切到行動網路後仍然用同一個位址連到家裡的主機。
- **連線經過中繼**：`tailscale status` 對某一台顯示 `active; relay "<地區代碼>"`（經由 DERP 中繼）而不是 `active; direct <位址:連接埠>` 時（沒有流量的裝置兩者都不顯示），代表兩端之間的 NAT 沒有打通，延遲比直接連線高；判讀方式見 [Tailscale 深入：tailnet、MagicDNS、直連與 DERP 中繼](/linux/tools/remote/tailscale-tailnet-and-relay/)。
- **家人或另一台伺服器加入同一個網路之後，連得到原本只給管理者用的服務**：Tailscale 預設的存取規則讓網路裡的裝置全部互通，新加入的裝置連得到任何只聽 VPN 介面的服務。

## 判斷條件與後果

- **連線方是自己或少數認識的人，每台裝置都裝得了用戶端**：服務只聽 VPN 介面的位址（或主機防火牆只放行 VPN 介面，或服務只聽本機、由 VPN 的用戶端轉送，Tailscale 的做法見 [5.10 Outbound Tunnel 入口與生命週期](/backend/05-deployment-platform/outbound-tunnel-entry/) 的〈用 tailscale serve 讓只聽本機的 HTTP 服務給 tailnet 連：實測、限制與 HTTPS 模式的代價〉），而且主機沒有其他公開入口時，服務在公開網路上沒有任何位址，網際網路上的掃描連登入頁都碰不到，SSH、SMB 這些 HTTP 以外的協定直接可用，流量也不經第三方解密。代價是每一台裝置都要裝用戶端、加入網路，所以連線方是不特定的訪客時這個做法用不了，公開服務改用 Outbound Tunnel 或公開的入口。同一台主機上公開網站與管理服務怎麼分給這兩種入口，見 [5.10 Outbound Tunnel 入口與生命週期](/backend/05-deployment-platform/outbound-tunnel-entry/) 的〈同一台家用主機的公開網站與管理服務：分給 Tunnel 與 mesh VPN 的取捨，與分開之後仍然存在的風險〉。
- **網路裡有不只一種角色的裝置**（伺服器與個人裝置、管理者與家人）：預設互通時，任何一台被入侵或交給別人用的裝置都在信任範圍內，連得到其他每一台的每一個連接埠，原因是加入網路就是預設唯一的一道檢查。要限制哪一台連得到哪一台的哪個連接埠，靠 VPN 自己的存取規則（Tailscale 的 ACL）或每台主機的防火牆；服務與它的管理介面是同一個程式、同一個連接埠時，存取規則用連接埠分不開兩者。
- **用的是服務商營運協調伺服器的產品**：服務商的管理帳號改得到誰能加入網路與存取規則，這個帳號被別人拿到時，對方可以改存取規則，沒有開 Tailnet Lock 時還可以把自己的裝置加進來，直接連到只聽 VPN 介面的服務；自建 WireGuard 時沒有這個帳號，金鑰的分發與撤銷回到管理者手上。兩種情形的信任錨與防護見 [7.43 兩個網路之間的連線安全](/backend/07-security-data-protection/cross-network-connection-security/) 的〈WireGuard 與 Tailscale 的金鑰與控制平面〉。
- **VPN 本身壞掉**：主機的網路設定或 VPN 的程式出問題時，經由 VPN 也連不進主機，所以 mesh VPN 是一條管理通道，不是救援入口；救援入口要不經過主機作業系統的網路設定，見 [伺服器管理通道的設計：網路可達性、通道授權、主機登入驗證三層的做法與選擇，以及救援入口](/devops/infra/03-network-foundation/management-access-channel/)。
