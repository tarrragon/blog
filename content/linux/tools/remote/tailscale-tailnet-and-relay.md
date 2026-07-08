---
title: "Tailscale 深入：tailnet、MagicDNS、直連與 DERP 中繼"
date: 2026-07-08
description: "要用 Tailscale 讓散在不同網路的機器互連、遇到連得到但延遲高、或想讀懂 tailscale status 的 relay / direct 標示時回來讀"
weight: 5
tags: ["linux", "remote", "tailscale", "vpn", "network"]
---

Tailscale 承擔的是可達性：給每台加入的裝置一個私網內固定的位址，讓它們互相找得到、跟各自當下的公網 IP 與所在網路無關。[遠端連線與同步工具選型](../connection-and-sync-tools/) 的網路層段已交代它在選型上的定位（要省事的 mesh VPN、對照自建 WireGuard）；這篇往下講它怎麼運作與配置——tailnet 的位址模型、用主機名連線、headless 機器怎麼加入、以及最容易困惑的「連得到但走中繼、延遲偏高」是怎麼回事。

## tailnet：每台裝置一個私網固定位址

加入同一個帳號的裝置組成一個 tailnet（你的私有網路）。Tailscale 給每台裝置分配一個 `100.x.y.z` 的私網位址（CGNAT 保留段），這個位址在裝置的整個生命週期內固定、跟它當下接的是家用 Wi-Fi、行動網路還是咖啡廳網路無關。裝置實際的網路位置變了，由它自己向 Tailscale 的協調伺服器回報、連線在底層自動重建，上層看到的 tailnet 位址不變。

這把「定位」跟「公網 IP」解耦：家裡 IP 重撥、手機切網路、機器躲在電信業者級 NAT（CGNAT，多戶共用一個公網 IP、對外開 port 這條路直接消失）後面，裝置之間用 tailnet 位址一樣連得到。tailnet 位址穩定這個性質，也是為什麼走 tailnet 的 TCP 連線有機會撐過一次實體換網（見 [TCP 連線與漫遊](/linux/dotfile/knowledge-cards/tcp-connection-roaming/) 的邊界段）。

## MagicDNS：用主機名而非 IP

記 `100.x.y.z` 不如記名字。MagicDNS 讓你用裝置的主機名連線——`ssh user@my-vm` 而不是 `ssh user@100.68.144.88`。主機名比位址更該當作連線座標寫進設定：位址雖然在 tailnet 內固定，但重裝、換帳號都可能拿到新位址，主機名則跟著機器的身分走。要把連線座標記進版控或腳本時，用主機名、留位址當備援。

## headless 機器怎麼加入 tailnet

沒有瀏覽器的機器（VM、伺服器）用 `tailscale up` 加入，它會印一個授權 URL、在任何已登入該帳號的裝置上開這個 URL 核准即上線：

```bash
sudo systemctl enable --now tailscaled     # 啟動 daemon
sudo tailscale up --hostname=my-vm         # 印出授權 URL
# → To authenticate, visit: https://login.tailscale.com/a/...
```

在手機或桌機的瀏覽器開那個 URL、用你的 Tailscale 帳號授權這個節點，機器就加入 tailnet、拿到位址。`--hostname` 指定它在 tailnet 裡的主機名。手機端則裝 Tailscale app、登入同一帳號、打開開關即加入——之後手機用 tailnet 位址就找得到那台 VM，跟手機接哪個網路無關。

## 直連 vs DERP 中繼：連得到但延遲高是怎麼回事

兩台 tailnet 裝置之間，Tailscale 會盡量建**直連**（peer-to-peer、封包直接走）；建不起來時退回 **DERP 中繼**（封包繞經 Tailscale 的中繼伺服器）。中繼一定通（只要兩端都連得上某個 DERP 伺服器），但封包多繞一段、延遲被放大。判讀在 `tailscale status`：

```text
100.68.144.88  my-vm  ...  active; direct 203.0.113.5:41641   # 直連
100.68.144.88  my-vm  ...  active; relay "hkg"                # 走香港 DERP 中繼
```

直連建不起來的典型原因是 NAT 穿透失敗：兩端的 NAT 類型不配合（對稱型 NAT——每次對外連線都換一個 port、讓對端無法預測該往哪打，或某些虛擬機的 NAT 網路模式）時，打洞（hole punching，兩端同時往對方猜測的位址送封包、在 NAT 上鑿出臨時通道）建不起 peer-to-peer 路徑、只能退中繼。一個實測到的例子：一台跑在筆電上的虛擬機（NAT 網路模式），從同一台筆電連它、tailscale 卻走跨國 DERP 中繼、延遲幾十毫秒——因為虛擬機的 NAT 讓直連打洞失敗。功能完全可用（能連、能傳），只是延遲被中繼繞路放大。

**看得到、`ping` 通但延遲偏高且標 `relay`**，就是 NAT 穿透失敗退中繼——功能可用只是慢、不必急著修，除非延遲影響到逐鍵互動的體感。要降延遲得從 NAT 類型下手：換 VM 的網路模式（bridged 讓 VM 直接掛在實體網段、比 NAT 模式容易建直連）、在路由器開 UPnP（讓裝置自動請求對外 port 映射、打洞更容易成功）、或用 Tailscale 的 exit node（指定一台裝置當所有對外流量的統一出口）與 subnet router（讓一台裝置把它所在的整個子網橋進 tailnet）換一條路徑。

## tailscale status 判讀

`tailscale status` 是這一層的權威狀態，除錯先看它：

- **對方不在清單** → 登入 / 帳號問題（是不是同一個 tailnet、有沒有上線）。
- **標 `offline`** → 那台裝置的 tailscaled 沒跑或斷網。
- **看得到、標 `relay`** → 上線且可達、只是走中繼（延遲議題、非連不通）。
- **看得到、標 `direct`** → 直連、最佳狀態。

從手機連 tailnet 位址回「connection timed out」時，逾時指向可達性層而非服務層——問題多半在手機的 Tailscale 沒連上、那個私網位址對手機根本不存在，而不在伺服器的 sshd。判別方法是分清「逾時 vs 被拒」，見 [連線逾時 vs 連線被拒](/linux/dotfile/knowledge-cards/connection-refused-vs-timeout/)。

## 跟連線層疊加、關掉公網入口

Tailscale 是網路層、跟連線層（SSH / mosh）是疊加關係：先有可達性、上面才談連線手感。這個疊加還帶來一個安全性質——服務可以只綁 tailnet 介面、公網防火牆全關：SSH / ttyd 這類只在私網位址上聽，對外沒有任何開放 port，公網入口縮到零。比「開公網 port 再堆 fail2ban」的維護成本低得多。連得到私網位址本身就代表通過了 tailnet 認證，定位與授權在這一層合一。

## 下一步路由

- 選型層（Tailscale vs 自建 WireGuard、跟連線 / 同步工具的關係）：[遠端連線與同步工具選型](../connection-and-sync-tools/)
- 在遠端 agent 工作機上實際用它打通手機到 VM（含 DERP 中繼實例）：[遠端 agent 工作機實作記錄](../agent-workstation-vm-handson/) 的 Step 3
- 機器連不到的完整分流（網路層 / 服務層 / 機器沒起）：[機器連不到或起不來](../../../debug/machine-unreachable/)
- 相關術語卡：[TCP 連線與漫遊](/linux/dotfile/knowledge-cards/tcp-connection-roaming/)、[連線逾時 vs 連線被拒](/linux/dotfile/knowledge-cards/connection-refused-vs-timeout/)
