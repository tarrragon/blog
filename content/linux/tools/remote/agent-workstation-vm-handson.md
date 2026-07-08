---
title: "遠端 agent 工作機實作記錄：從 Docker image 到手機端跑通"
date: 2026-07-08
description: "要把 mosh + zellij + Claude Code + ntfy + 手機連線的遠端 agent 工作流在 VM 上實際架起來、需要每一步的驗證判準與除錯分流時回來讀"
weight: 3
draft: true
tags: ["linux", "remote", "docker", "zellij", "mosh", "ntfy", "agent", "handson"]
---

本文是 [遠端 agent 工作機選型](../agent-workstation-home-vs-vps/) 的實作篇：把該文推導出的三層架構（連線 / session / 隔離）在現有 VM 上完整架起來、直到手機端能丟任務、斷線、收通知、回來看結果。目前是實作骨架：步驟順序與每步的驗證判準已定，具體指令與實測輸出標「待實測補」、跟著實機進度回填；全部驗證完成前維持 draft。

每一步固定四段：**概念與工具**（這步在架構裡承擔什麼、細節連到對應文章）、**實作**（具體動作）、**驗證**（這步成功的可觀測判準）、**除錯判讀**（失敗症狀怎麼分流）。寫法對齊 [讓機器跑無人值守的長任務](../../../install/unattended-remote-work/) 的障礙拆解、與 [vm-hyprland 實作記錄](../../../dotfile/vm-hyprland-handson-record/) 的邊做邊記形式。

## 全局圖與步驟總表

目標狀態：手機 → Tailscale 私網 → mosh 進 VM → zellij session → container 內的 Claude Code；跑完由 hooks 推 ntfy 通知回手機。

| 步驟                      | 架構層     | 產出物                        |
| ------------------------- | ---------- | ----------------------------- |
| 1. 前置盤點               | ——         | 三台裝置與帳號的現況清單      |
| 2. VM 基線可連入          | 連線層之下 | SSH 金鑰登入成功              |
| 3. Tailscale 打通私網     | 連線層     | 手機與 VM 互 ping 得到        |
| 4. mosh 補連線手感        | 連線層     | 漫遊不斷線的互動 shell        |
| 5. zellij 常駐 session    | session 層 | detach / attach 後任務仍在    |
| 6. Dockerfile 建工作環境  | 隔離層     | 可重建的 agent 工作環境 image |
| 7. Claude Code 落地與憑證 | 隔離層     | container 重建後免重新登入    |
| 8. hooks 接 ntfy 通知     | 通知       | 任務結束手機收到推播          |
| 9. 手機端連線與輸入       | 行動端     | 手機可操作、按鍵齊全          |
| 10. 端到端驗收            | 全部       | 三個情境全數通過              |

## Step 1：前置盤點

### 概念與工具

實作前先固定三台裝置的現況、把「環境不明」從除錯變數裡排除：宿主機（跑 VM 的機器）、VM 本體、手機。未知機器的盤點方法見 [盤點一台不明機器](../../../install/inventory-unknown-machine/)。

### 實作

- 記錄宿主機平台、VM 的發行版與資源配額（vCPU / RAM / 磁碟）、VM 網路模式（NAT / bridged）
- 記錄手機平台與要用的 client 候選
- 確認 Tailscale 帳號與 ntfy 的 topic 規劃（私密值遵守只放佔位、真值不進 git 的原則）
- （待實測補：實際盤點結果表）

### 驗證

盤點表填完、每一項都有實際值而非「應該是」。

### 除錯判讀

這一步的失敗形態是「以為知道」：VM 網路模式記錯會讓 Step 3 的連線除錯走錯方向。判讀方法是每項都用指令回讀、以權威狀態為準，方法論見 [診斷讀權威狀態](../../../debug/diagnosis-read-authoritative-state/)。

## Step 2：VM 基線可連入

### 概念與工具

後續所有步驟都透過 SSH 進 VM 操作，這步先把「進得去」建立成基線。金鑰登入的 bootstrap 流程見 [SSH 免密碼登入 bootstrap](../../../install/ssh-keyless-bootstrap/)。

### 實作

- 宿主機（或同網段機器）以金鑰 SSH 進 VM
- （待實測補：本次 VM 的實際連線參數與金鑰配置）

### 驗證

從宿主機一行指令登入成功、免輸入密碼；重開 VM 後仍成立。

### 除錯判讀

連不上先分層：機器沒起、網路不通、sshd 沒跑、認證失敗是四個不同層的問題，分流見 [機器連不到或起不來](../../../debug/machine-unreachable/) 與 [SSH 與終端機問題排查](../../../debug/ssh-and-terminal-troubleshooting/)。

## Step 3：Tailscale 打通私網

### 概念與工具

這步把「可達性」從 VM 的網路模式與家用 IP 解耦：VM 與手機加入同一個 tailnet 之後，手機用私網位址找到 VM、跟宿主機網段與公網 IP 都無關。原理與取捨見 [遠端連線與同步工具選型](../connection-and-sync-tools/) 的網路層段、決策層判讀見 [選型文的浮動 IP 段](../agent-workstation-home-vs-vps/)。（Tailscale 目前只有段落級介紹、專文缺口已記在 content-backlog。）

### 實作

- VM 安裝 tailscaled、登入 tailnet
- 手機裝 Tailscale app、登入同一 tailnet
- （待實測補：實際指令、MagicDNS 主機名、裝置清單截圖或輸出）

### 驗證

- 手機在行動網路（非家用 Wi-Fi）下 ping 得到 VM 的 tailnet 位址
- VM 端 `tailscale status` 看得到手機裝置
- 家用網路換 IP（或模擬：重啟光貓）後，上述兩項仍成立

### 除錯判讀

（待實測補：實際遇到的狀況）預期的分流：tailnet 裝置清單看不到對方是登入 / 帳號問題；看得到但 ping 不通要看是否走 DERP 中繼（`tailscale status` 有標示）、中繼通但直連失敗是 NAT 穿透問題、影響延遲但功能可用。

## Step 4：mosh 補連線手感

### 概念與工具

mosh 在連線層補兩個 SSH 的弱點：手機切網路不斷線（UDP 漫遊）、高 RTT 下打字順（本地回顯預測）。機制與代價（UDP port、無 port forwarding）見 [遠端連線與同步工具選型](../connection-and-sync-tools/) 的 mosh 段。

### 實作

- VM 安裝 mosh、確認 UDP port 範圍放行（走 tailnet 的話防火牆範圍縮到 tailscale 介面）
- （待實測補：實際安裝與 client 端連線指令）

### 驗證

- 手機用 mosh 連入後、Wi-Fi 切行動網路，session 存活、免重連
- 高延遲下打字即時回顯（體感判準：按鍵顯示追得上輸入）

### 除錯判讀

（待實測補）預期的分流：mosh 連線起不來多半是 UDP 被擋（防火牆 / client 支援度）；能連但漫遊會斷要查 client 是否真用 mosh 協定而非退回 SSH。

## Step 5：zellij 常駐 session

### 概念與工具

session 層讓工作獨立於連線存活：zellij session 常駐在 VM、連線只是 attach 上去看，斷線任務照跑。session 持久化概念見 [tmux 基礎](../../cli/tmux-persistence-and-basics/)、zellij 操作見 [zellij 分頁與 pane](../../cli/zellij-pane/)。

### 實作

- VM 安裝 zellij、建立固定名稱的工作 session
- 登入流程收斂成「連入即 attach」（shell 起始指令或 alias）
- （待實測補：實際配置）

### 驗證

- session 內啟動一個長任務、detach、關掉連線，幾分鐘後重連 attach，任務仍在跑且輸出連續
- VM 重開機後 session 消失是預期行為（session 活在記憶體）——這條列出來是把「重開機後要重建 session」記成已知邊界而非除錯項

### 除錯判讀

attach 不到 session 先看 session 是否存在（`zellij list-sessions`）、再看是否 attach 到同名的新空 session——名稱拼錯會靜默開新 session、看起來像「任務不見了」、任務仍活在原名稱的 session 裡。

## Step 6：Dockerfile 建 agent 工作環境

### 概念與工具

隔離層把 agent 的工作環境做成可重建、可搬遷的 image：base image 拉取、Dockerfile 疊上工具鏈、掛載與資源上限在 run 時宣告。設計判讀見 [選型文的隔離段](../agent-workstation-home-vs-vps/)；container 內日常操作的人體工學見 [container 使用的人體工學](../../../dotfile/10-prod-parity/container-ergonomics/)、跟生產環境對齊的 runtime 選擇見 [prod parity 的 runtime](../../../dotfile/10-prod-parity/prod-parity-runtime/)、tag 固定的理由見 [image tag pinning](../../../dotfile/knowledge-cards/image-tag-pinning/)。

### 實作

- VM 安裝 docker、確認非 root 使用者可操作
- 寫 Dockerfile：base image（固定 tag）、開發工具鏈、非 root 使用者
- 設計 `docker run` 的掛載與上限：專案目錄、`~/.claude` volume、memory / CPU 上限
- （待實測補：實際 Dockerfile 全文與 run 指令、image 大小）

### 驗證

- `docker build` 從零跑到完成、無 cache 情況下可重現
- container 內以非 root 使用者起 shell、看得到掛進來的專案目錄、看不到未掛載的 host 路徑
- 在 container 內故意吃滿記憶體（壓力測試）、被 OOM 掉的是 container 內程序、host 的 tailscaled 與 zellij 無感

### 除錯判讀

（待實測補）預期的分流：build 失敗看是哪一層指令、跟 base image 版本漂移有關先查 tag 是否固定；run 起來但檔案權限錯亂是 host / container 的 UID 對映問題。

## Step 7：Claude Code 落地與憑證持久化

### 概念與工具

agent 程式裝進 image、但登入狀態與設定（`~/.claude/`）要活得比 container 久——掛成 volume 才免去每次 rebuild 重新走 OAuth。信任邊界的判讀（推送憑證怎麼給）見 [選型文的隔離段](../agent-workstation-home-vs-vps/)。（Claude Code 在本 blog 沒有安裝與 hooks 專文、缺口已記在 content-backlog。）

### 實作

- image 內安裝 Claude Code、首次啟動走 headless 登入流程
- `~/.claude/` 掛 volume、git 憑證依信任邊界決策給入（deploy key 或留在 host 側）
- （待實測補：headless OAuth 的實際流程與卡點）

### 驗證

- container 砍掉重建後、Claude Code 免重新登入直接可用
- 在掛載的專案目錄內給 agent 一個小任務、能完成並寫入檔案、host 側看得到變更

### 除錯判讀

（待實測補）預期的卡點：headless 環境的 OAuth 要來回貼 code、瀏覽器在另一台裝置上完成；登入狀態沒保住先在 container 內用 `mount` 回讀確認 volume 已掛上、以權威狀態為準。

## Step 8：hooks 接 ntfy 通知

### 概念與工具

通知把工作流從「掛在終端上等」翻成「離開、跑完被叫回來」：agent 的任務結束事件觸發 hook、hook 對 ntfy topic 發一則推播、手機 app 訂閱該 topic。ntfy 的架構與自架取捨見 [ntfy 推播通知服務](../../../debug/ntfy-push-notification-service/)、無人值守情境下「結果推得出去」的定位見 [讓機器跑無人值守的長任務](../../../install/unattended-remote-work/)。

### 實作

- 手機安裝 ntfy app、訂閱規劃好的 topic
- Claude Code 配置 Stop / Notification hooks、對 topic 發訊（topic 真值不進 git）
- （待實測補：hook 設定檔實際內容、觸發事件的選擇）

### 驗證

- 從 shell 手動 curl 一則測試訊息、手機收到（先驗 ntfy 鏈路本身）
- 給 agent 一個會跑幾分鐘的任務、手機關螢幕等待、任務結束收到推播（再驗 hook 觸發）

### 除錯判讀

兩段驗證把問題切開：手動 curl 通、hook 沒動靜，問題在 hook 配置層；curl 就不通，問題在 ntfy 鏈路（topic 名稱、網路、app 訂閱狀態）。（待實測補：實際遇到的狀況）

## Step 9：手機端連線與輸入

### 概念與工具

行動端輸入是整套工作流最容易用不下去的環節：終端 UI 依賴 Esc / Ctrl / 方向鍵、手機軟體鍵盤預設沒有，client 的擴充鍵列補這個缺。判讀見 [選型文的使用形態段](../agent-workstation-home-vs-vps/)。（手機終端 client 的選型比較是缺口、跑通後依實測心得評估是否成文。）

### 實作

- 候選 A：現成 client（Termius / Blink Shell 這類），配 mosh + 擴充鍵列
- 候選 B：自製通道（ttyd 轉 WebSocket、走 tailnet、原生 app 收），適合要客製認證與稽核的情境
- 順序已定：本輪用候選 A 跑通全部步驟（控制變數——工作流本身未驗證時、client 端用成熟工具歸零變數）；候選 B 的功能對齊（擴充鍵列、斷線重連、多 endpoint、TUI 相容）記在該工具自己專案的提案系統、驗收規格採用本文跑通後凍結的判準
- （待實測補：實際採用的 client、鍵位配置；候選 B 對照測結果在其提案完成後回填）

### 驗證

- 手機端完成一次完整互動：attach session、給 agent 下指令、Esc 中斷一次、方向鍵翻歷史
- 輸入體感可長用（判準：一段 prompt 打完的錯誤率與速度自評）

### 除錯判讀

（待實測補）預期的分流：連得上但按鍵缺失是 client 能力問題、換 client 而非調 VM；亂碼與斷行錯位是終端 TERM / 字型問題，分流見 [SSH 與終端機問題排查](../../../debug/ssh-and-terminal-troubleshooting/)。

## Step 10：端到端驗收

### 概念與工具

前九步各自驗過自己那層、這步驗跨層組合：三個情境對應三個最可能在真實使用中出現的失敗面。

### 實作與驗證

三個情境全部從手機端執行：

1. **fire-and-forget**：手機丟一個編譯級任務給 agent、關 app 走人、收到 ntfy 推播後重連看結果。驗證斷線期間任務持續、通知準確。
2. **斷線復原**：任務進行中把手機從 Wi-Fi 切到行動網路、再切回來。驗證 mosh 漫遊 + zellij session 兩層的組合行為。
3. **資源保護**：讓 container 內任務吃滿記憶體上限。驗證 OOM 只影響工作負載、連線與 session 基礎設施存活、且事後手機仍能 attach 回去看發生什麼事。

（待實測補：三情境的實測記錄與時間）

### 除錯判讀

情境失敗時回對應步驟的除錯段：通知沒來回 Step 8、斷線任務死掉回 Step 5、OOM 拖垮連線回 Step 6 的資源上限配置。跨層問題先確認單層驗證是否仍通過、再懷疑組合行為。

## 完成條件

- 十個步驟的「待實測補」全數回填、指令與輸出是實跑結果
- 三個端到端情境通過
- 移除 `draft: true`、把本文加進 [遠端工具索引](../)、在 [選型文](../agent-workstation-home-vs-vps/) 加上往本文的路由
- 實作中發現的判讀若推翻選型文內容、同步修正該文並記 retrospective
