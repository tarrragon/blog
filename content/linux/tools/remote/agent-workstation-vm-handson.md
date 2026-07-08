---
title: "遠端 agent 工作機實作記錄：從 Docker image 到手機端跑通"
date: 2026-07-08
description: "要把 mosh + zellij + Claude Code + ntfy + 手機連線的遠端 agent 工作流在 VM 上實際架起來、需要每一步的驗證判準與除錯分流時回來讀"
weight: 3
tags: ["linux", "remote", "docker", "zellij", "mosh", "ntfy", "agent", "handson"]
---

本文是 [遠端 agent 工作機選型](../agent-workstation-home-vs-vps/) 的實作篇：把該文推導出的三層架構（連線 / session / 隔離）在一台 UTM Arch Linux ARM VM 上完整架起來、直到手機端能丟任務、斷線、收通知、回來看結果。十個步驟與三個端到端情境都經實機跑通、指令與輸出是實跑結果、每步的除錯判讀記的是實測踩到的狀況。

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

本次實測環境盤點結果：

| 項目     | 實測值                                                                  |
| -------- | ----------------------------------------------------------------------- |
| 宿主機   | macOS（Apple Silicon）、UTM QEMU 跑 VM                                  |
| 發行版   | Arch Linux ARM（aarch64）                                               |
| kernel   | `7.1.2-2-aarch64-ARCH`（session 起始，實作中因升級變 `7.1.3-1`）        |
| vCPU     | 4                                                                       |
| RAM      | 3.8 GiB（起始可用約 2.0 GiB）                                           |
| 磁碟     | `/dev/vda4` 37 GB、已用 7.8 GB、可用 27 GB（23%）                       |
| 網路模式 | NAT（UTM Shared Network）、`enp0s1` 192.168.64.6/24、閘道 .64.1（DHCP） |
| 已裝工具 | zellij 0.44.3、git、curl                                                |
| 待裝工具 | tailscale、mosh、docker                                                 |
| 手機端   | 由 client 選型段決定（本輪走現成 client）                               |

kernel 版本在盤點時記下、成了後面 docker 除錯的關鍵對照值：實作過程中一次 `pacman -Syu` 把 kernel 從 `7.1.2-2` 升到 `7.1.3-1`，而「執行中版本 vs 磁碟版本」的落差正是 Step 6 docker 起不來的根因（見該步除錯判讀）。這印證了盤點不是一次性動作——關鍵狀態值要能隨時回讀比對。

### 驗證

盤點表填完、每一項都有實際值而非「應該是」。

### 除錯判讀

這一步的失敗形態是「以為知道」：VM 網路模式記錯會讓 Step 3 的連線除錯走錯方向。判讀方法是每項都用指令回讀、以權威狀態為準，方法論見 [診斷讀權威狀態](../../../debug/diagnosis-read-authoritative-state/)。

## Step 2：VM 基線可連入

### 概念與工具

後續所有步驟都透過 SSH 進 VM 操作，這步先把「進得去」建立成基線。金鑰登入的 bootstrap 流程見 [SSH 免密碼登入 bootstrap](../../../install/ssh-keyless-bootstrap/)。

### 實作

- 宿主機（或同網段機器）以金鑰 SSH 進 VM

本次 VM 的金鑰登入在先前 session 已 bootstrap 完成（Mac 端 `~/.ssh/id_ed25519`、公鑰已進 VM 的 `authorized_keys`），這步只驗證基線仍成立：

```text
$ ssh tar@192.168.64.6 'echo CONNECTED; whoami'
CONNECTED
tar
```

一行指令即登入、無密碼提示。後續每一步的 VM 操作都透過這條 SSH 通道下達（`ssh tar@192.168.64.6 '<cmd>'`），把「進得去」從變數表移除。

### 驗證

從宿主機一行指令登入成功、免輸入密碼；重開 VM 後仍成立。實測登入即回 `CONNECTED`、免密碼。

### 除錯判讀

連不上先分層：機器沒起、網路不通、sshd 沒跑、認證失敗是四個不同層的問題，分流見 [機器連不到或起不來](../../../debug/machine-unreachable/) 與 [SSH 與終端機問題排查](../../../debug/ssh-and-terminal-troubleshooting/)。

## Step 3：Tailscale 打通私網

### 概念與工具

這步把「可達性」從 VM 的網路模式與家用 IP 解耦：VM 與手機加入同一個 tailnet 之後，手機用私網位址找到 VM、跟宿主機網段與公網 IP 都無關。原理與取捨見 [遠端連線與同步工具選型](../connection-and-sync-tools/) 的網路層段、決策層判讀見 [選型文的浮動 IP 段](../agent-workstation-home-vs-vps/)。（Tailscale 目前只有段落級介紹、專文缺口已記在 content-backlog。）

### 實作

- VM 安裝 tailscaled、登入 tailnet
- 手機裝 Tailscale app、登入同一 tailnet

VM 端安裝 tailscale（1.98.8）、啟用 daemon、`tailscale up` 取得 auth URL：

```text
$ sudo systemctl enable --now tailscaled
$ sudo tailscale up --hostname=agent-vm
To authenticate, visit:
	https://login.tailscale.com/a/…       # ← 在另一台裝置的瀏覽器開這個 URL 完成登入
```

headless 機器沒有瀏覽器、`tailscale up` 會印一個 auth URL、在任何已登入該 tailnet 帳號的裝置上開它、核准這個節點即上線。認證後 VM 取得 tailnet 位址 `100.68.144.88`、主機名 `agent-vm`。

### 驗證

- 手機在行動網路（非家用 Wi-Fi）下 ping 得到 VM 的 tailnet 位址
- VM 端 `tailscale status` 看得到手機裝置
- 家用網路換 IP（或模擬：重啟光貓）後，上述兩項仍成立

VM 端 `tailscale status` 認證後即列出 tailnet 全部裝置（VM `agent-vm`、Mac、iPad 等），登入這關通過。

跨裝置連通實測先從同帳號的 Mac 驗（Mac 也在 tailnet 上）：

```text
$ ping -c3 100.68.144.88
64 bytes from 100.68.144.88: … time=77.6 ms   # 0% loss、通
$ tailscale status | grep agent-vm
100.68.144.88  agent-vm  …  active; relay "hkg"   # ← 走 DERP 中繼、非直連
```

這裡有個值得記的實測現象：VM 其實就跑在這台 Mac 上（UTM），物理上同一條區網，tailscale 卻走香港 DERP 中繼、不是直連（77 ms 而非區網的 sub-ms）。原因是 UTM 的 NAT（Shared Network）讓 tailscale 的 NAT 穿透建不起直連、退回中繼。功能完全可用（能連、能傳），只是延遲被中繼繞路放大——這正好是下面除錯判讀說的「中繼通但直連失敗」情境的實例。

手機側在 Step 4 / Step 9 的手機連線過程一併驗證：手機（Android、Galaxy A70）在**行動網路**下透過 tailnet 連上 VM、`tailscale status` 兩邊互見。而且觀察到路徑會依實體網路自動選擇——手機走家用 Wi-Fi 時是 DERP 中繼、切到行動網路後 tailscale 建起**直連**（`direct <行動網路公網 IP>`）。這印證了 tailnet 位址與可達性跟實體網路解耦：換網路只換底層路徑、tailnet 位址不變。

### 除錯判讀

實測命中「看得到但走 DERP 中繼」這個分流：`tailscale status` 的裝置那行標 `relay "hkg"`、而非直連的 peer 位址，代表直連沒建起來、走了中繼。判讀鏈：tailnet 裝置清單看不到對方 → 登入 / 帳號問題；看得到、`ping` 通但延遲偏高且標 `relay` → NAT 穿透失敗退回中繼（本次 UTM NAT 就是這情況、功能可用只是慢）；看得到但 `ping` 完全不通 → 才往防火牆 / ACL 方向查。中繼可用時不必急著修直連——除非延遲影響到逐鍵互動的體感，否則中繼是可接受的退路。

還有一個從手機端連線時實測踩到、且最容易誤判方向的症狀：**手機端 client 連 VM 的 tailnet 位址回「connection timed out」。** 直覺會往「sshd 掛了 / 防火牆擋了 / client 設錯」查，但這些的症狀是「連線被拒」（送達但拒絕）、不是「逾時」（送不到）。逾時指向可達性層——`100.68.144.88` 是 tailnet 私網位址、只有在同一個 tailnet 上的裝置才路由得到，手機的 Tailscale 若沒連上（app 沒開、開關沒打開、登入到別的帳號），這個位址對手機根本不存在、封包送不出去。判讀方法是從 VM 側 `tailscale status` 看那台手機在不在清單、是不是 `offline`：手機沒出現或標 offline，問題就在手機端進 tailnet 這關、不在 VM。這條把「連線被拒 vs 連線逾時」當分岔點：前者往服務 / 認證層查、後者往網路可達性層查，兩者的除錯方向相反（通用判別見 [連線逾時 vs 連線被拒](/linux/dotfile/knowledge-cards/connection-refused-vs-timeout/)）。VM 側要先自證清白——`sudo ss -tlnp | grep :22` 確認 sshd 在聽、`tailscale status` 確認自己上線，把 VM 這層從變數表移除，再回頭要求手機端進 tailnet。

## Step 4：mosh 補連線手感

### 概念與工具

mosh 在連線層補兩個 SSH 的弱點：手機切網路不斷線（UDP 漫遊）、高 RTT 下打字順（本地回顯預測）。SSH 為何一換 IP 就斷、mosh 為何用 UDP 繞過見 [TCP 連線與漫遊](/linux/dotfile/knowledge-cards/tcp-connection-roaming/)；本地回顯預測的機制與 CJK 代價見 [mosh 本地回顯預測](/linux/dotfile/knowledge-cards/mosh-local-echo-prediction/)；機制與代價（UDP port、無 port forwarding）的選型面見 [遠端連線與同步工具選型](../connection-and-sync-tools/) 的 mosh 段。

### 實作

- VM 安裝 mosh、確認 UDP port 範圍放行（走 tailnet 的話防火牆範圍縮到 tailscale 介面）

VM 端安裝：

```text
$ sudo pacman -S --needed mosh
$ mosh-server --version
mosh-server (mosh 1.4.0) [build mosh-1.4.0-dirty]
```

VM 目前沒有啟用防火牆（NAT 後面、只對 tailnet 暴露的規劃在 Step 3），mosh 預設 UDP port 範圍 60000-61000 無需額外放行；日後在 VM 上啟防火牆時，要把這段 UDP 範圍限定到 tailscale 介面而非對全世界開。client 端連線指令與漫遊實測併入 Step 9 手機端一起做（mosh 的價值要在真實網路切換下才顯現，在同網段 SSH 通道裡看不出差異）。

### 驗證

- 手機用 mosh 連入後、Wi-Fi 切行動網路，session 存活、免重連
- 高延遲下打字即時回顯（體感判準：按鍵顯示追得上輸入）

實測用 Termius（Android、本輪未見任何 Pro / 付費提示）開 mosh 連入，在 zellij session 裡跑一個每秒印時間戳的迴圈、然後把手機從 Wi-Fi 切到行動網路：時間戳**無斷檔**（沒有跳掉任何一秒、輸出連續），但切換當下畫面**凍結約 3 秒**才恢復更新、不需手動重連。這是 mosh 漫遊的真實體感、要據實描述——它的價值是「不丟狀態、自動接回」，不是「零延遲、感覺不到切換」：那 3 秒是 tailscale 重建路徑加 mosh 重新同步的時間，恢復後前面的輸出一格不少。跟純 SSH 的對照才是關鍵：mosh 是凍 3 秒後無損接回、純 SSH 是直接斷線讓前景任務死。

要確認「真的走 mosh、不是退回 SSH」不能只信 client 說已連線、要看 server 側的權威狀態：mosh 運作時 VM 上會有 `mosh-server` 程序、而 SSH 連線在 spawn 完 mosh-server 後就關閉——所以 mosh 活著時 `ss -tnp` 反而看**不到**該 client 的 TCP:22。實測 VM 上 `ps aux | grep mosh-server` 看到 `mosh-server new -s -l LANG=…`、同時 `ss` 看不到手機的 SSH 連線，這個組合才是 mosh 生效的簽章。

這裡有個判讀教訓值得記：第一條連線的快照曾看到手機的 `ESTAB … :22`、沒有 mosh-server（那條是 SSH），若就此下「Termius 退回 SSH」的結論會下太快——重連後 mosh 才正確接管、`mosh-server` 才出現。client 用不用 mosh 是會變的狀態，要以 server 側程序為準、且不能只查一次。

漫遊當下還觀察到網路層的協作：手機從 Wi-Fi（`tailscale status` 標走 `relay "hkg"`）切到行動網路後、tailscale 變成**直連**（`direct <行動網路公網 IP>`）。tailscale 在網路層保持 tailnet IP 不變並重建底層路徑、mosh 在連線層用 UDP 扛住端點變化，兩層疊起來才有「切網無感」。

### 除錯判讀

安裝階段實測踩到一個跟 mosh 本身無關、但會擋住安裝的狀況：`pacman -S mosh` 中途對某個相依套件（`python-absl`）回 HTTP 404、`failed to retrieve some files`。根因不是網路、是本地套件資料庫過時——記錄的版本在 mirror 上已被新版取代（Arch 的 partial upgrade 陷阱）。判讀方法是看錯誤是「404 檔案不存在」而非「連線逾時」：前者是 DB 與 mirror 不同步、`sudo pacman -Syu` 對齊即解；後者才是網路層問題。這個修法有連鎖後果——`-Syu` 會順帶升級 kernel，是 Step 6 docker 起不來的伏筆。

連線階段的分流：mosh 連線起不來多半是 UDP 被擋（防火牆 / client 支援度）；「能連但漫遊會斷」要查 client 是否真用 mosh 協定而非退回 SSH——查法就是上面驗證段的 server 側 `mosh-server` 程序判斷，別只看 client 端顯示的連線狀態。本輪還意外驗到一個相關對照：第一次漫遊測試把迴圈跑在**純 SSH shell**（不在 zellij）裡、SSH 一斷迴圈就被 SIGHUP 殺掉；第二次把迴圈放進 **zellij session** 才在斷線期間存活。這印證了工作要放進 session 層（Step 5）——連線層無論 mosh 多穩、直接掛在 SSH shell 的前景程序都不該當成安全的長任務容器。

mosh 的本地回顯預測還有一個要記的代價：它跟 CJK 雙寬字元有顯示衝突、開了中文輸入後 mosh 連線下輸入行會錯位、純 SSH 才正常（詳見 Step 10 情境一的 CJK 段）。所以 mosh 與 SSH 各有適用場景——要打中文對話時、純 SSH 的無預測才是對的選擇、mosh 的漫遊優勢在此反成負擔。

## Step 5：zellij 常駐 session

### 概念與工具

session 層讓工作獨立於連線存活：zellij session 常駐在 VM、連線只是 attach 上去看，斷線任務照跑。session 持久化概念見 [tmux 基礎](../../cli/tmux-persistence-and-basics/)、本步用到的 zellij session CLI 操作（`attach -b` 背景常駐、`--session run` 注入、`ls`、`delete-session`）見 [Zellij session 生命週期](../../cli/zellij-session-lifecycle/)、pane 內部操作見 [zellij 分頁與 pane](../../cli/zellij-pane/)。

### 實作

- VM 安裝 zellij、建立固定名稱的工作 session
- 登入流程收斂成「連入即 attach」（shell 起始指令或 alias）

VM 已內建 zellij 0.44.3。0.44 提供 `attach -b`（`--create-background`）直接建一個背景 detached session，適合把「連入即 attach」跟「session 常駐」拆開：session 先在背景存在，連線只是之後 attach 上去。實測用它建一個名為 `work` 的 session、在裡面用 `zellij --session work run` 起一個每秒寫時間戳的 heartbeat 任務：

```text
$ zellij attach -b work                        # 建背景 session
$ zellij --session work run -- bash -c '...heartbeat...'   # 在 session 內起長任務
$ zellij ls
work [Created 3s ago]
```

「連入即 attach」的收斂留給登入 shell 處理（`.zshrc` / `.bashrc` 尾端 `zellij attach -c work`），本輪先驗 session 與連線解耦這個核心性質。

### 驗證

- session 內啟動一個長任務、detach、關掉連線，幾分鐘後重連 attach，任務仍在跑且輸出連續

實測：起 heartbeat 後關掉 SSH 連線（斷線發生在 tick 3 之後），用**全新 SSH 連線**重連：

```text
$ zellij ls
work [Created 18s ago]          # session 存活
$ wc -l ~/heartbeat.log
18                              # 18 筆、且 tick 編號 1→18 連續無斷檔
```

tick 編號連續（行數等於最後 tick 號）證明斷線那十幾秒內任務沒中斷——session 活在 VM 端的 zellij server、跟 SSH 連線的生死無關。

- VM 重開機後 session 消失是預期行為（session 活在記憶體）——這條列出來是把「重開機後要重建 session」記成已知邊界而非除錯項。本次 session 中段為修 docker 重開過一次機，重開後 `zellij ls` 確實空空如也，印證這條邊界

### 除錯判讀

attach 不到 session 先看 session 是否存在（`zellij list-sessions`）、再看是否 attach 到同名的新空 session——名稱拼錯會靜默開新 session、看起來像「任務不見了」、任務仍活在原名稱的 session 裡。

## Step 6：Dockerfile 建 agent 工作環境

### 概念與工具

隔離層把 agent 的工作環境做成可重建、可搬遷的 image：base image 拉取、Dockerfile 疊上工具鏈、掛載與資源上限在 run 時宣告。設計判讀見 [選型文的隔離段](../agent-workstation-home-vs-vps/)；container 內日常操作的人體工學見 [container 使用的人體工學](../../../dotfile/10-prod-parity/container-ergonomics/)、跟生產環境對齊的 runtime 選擇見 [prod parity 的 runtime](../../../dotfile/10-prod-parity/prod-parity-runtime/)、tag 固定的理由見 [image tag pinning](../../../dotfile/knowledge-cards/image-tag-pinning/)。

### 實作

- VM 安裝 docker、確認非 root 使用者可操作
- 寫 Dockerfile：base image（固定 tag）、開發工具鏈、非 root 使用者
- 設計 `docker run` 的掛載與上限：專案目錄、`~/.claude` volume、memory / CPU 上限

安裝後把使用者加進 docker group（`sudo usermod -aG docker tar`），重登入後即可免 sudo 操作 docker。實測的 Dockerfile：

```dockerfile
# base image 固定 tag：Claude Code 是 npm 套件、用官方 node image 省一層 runtime 版本漂移
FROM node:22-bookworm-slim

# 開發工具鏈：git 給版本控制、ripgrep 給搜尋、ca-certificates 給 HTTPS
# curl 是 ntfy hook（Step 8）依賴、node:slim 不內建、少了 hook 會靜默失效
RUN apt-get update && apt-get install -y --no-install-recommends \
      git ca-certificates curl ripgrep less \
    && rm -rf /var/lib/apt/lists/*

# agent 程式裝進 image（Step 7）
RUN npm install -g @anthropic-ai/claude-code

# 預建 ~/.claude 並 chown 給 node：named volume 首次掛載會沿用 image 內該目錄的 owner
# 少了這行、空 volume 會以 root 掛上、container 內的 node 寫不進憑證（實測踩過、見除錯判讀）
RUN mkdir -p /home/node/.claude && chown -R node:node /home/node/.claude

# 非 root 使用者：直接用 node base 內建的 node(UID 1000)、對齊 host 的 tar(1000)
USER node
ENV HOME=/home/node
WORKDIR /work
CMD ["bash"]
```

base image 用 tag `node:22-bookworm-slim`。tag 會隨上游 patch 移動，嚴格的固定是釘到 digest——本次 build 拉到的實際 digest 是 `node@sha256:53ada149…`，把這串記進版本文件、就能在任何機器重現同一個 base（tag pinning 的理由見 [image tag pinning](../../../dotfile/knowledge-cards/image-tag-pinning/)）。

run 指令把三件事在 run time 宣告——專案目錄掛 `/work`、`~/.claude` 掛 named volume（Step 7）、記憶體上限：

```bash
docker run --rm -it \
  -v ~/agent-workstation/testproj:/work \
  -v claude-home:/home/node/.claude \
  --memory=2g \
  agent-workstation:v1
```

### 驗證

- `docker build` 從零跑到完成、無 cache 情況下可重現

實測 `docker build --no-cache` 約 2 分鐘完成、image 990 MB，內含 node v22.23.1、Claude Code 2.1.204、git 2.39.5、ripgrep 13.0.0，使用者 `node`(UID 1000)。

- container 內以非 root 使用者起 shell、看得到掛進來的專案目錄、看不到未掛載的 host 路徑

實測掛 `~/agent-workstation/testproj:/work`：container 內 `ls /work` 讀得到 host 放的 `MARKER.txt`、`ls /home/tar`（未掛載）回 `No such file or directory`；container 內以 `node` 寫的檔、回到 host 看 owner 是 `tar`(1000)——UID 對映讓兩側 owner 一致，沒有「container 寫的檔在 host 上變成別人的」。

- 在 container 內故意吃滿記憶體（壓力測試）、被 OOM 掉的是 container 內程序、host 的 tailscaled 與 zellij 無感

實測 `--memory=256m` 下用 node 逐塊配置記憶體，配到約 200 MB 觸上限、程序被砍、container 退出碼 137（OOM kill 的 128+SIGKILL）。同時 host 的 `free` 從 258 MiB 用量升到 294 MiB（幾乎沒動）、事先起的 host 對照程序存活、SSH 連線不受影響。資源上限把工作負載的爆炸限縮在 container cgroup 內、連線基礎設施在 host 側安然無事。

### 除錯判讀

本步實測踩到兩個 gotcha，分屬不同層：

**daemon 起不來、症狀在 iptables、根因在 kernel。** `sudo systemctl start docker` 失敗，journal 顯示 `iptables (nf_tables): Could not fetch rule set generation id: Invalid argument`、建 NAT chain `DOCKER` 失敗。照症狀往「docker 網路 / 防火牆規則」除錯會走錯方向——根因是前一步為修 pacman 404 跑的 `-Syu` 順帶升級了 kernel（`7.1.2-2` → `7.1.3-1`）、但機器沒重開，執行中 kernel 的 module 目錄已不存在（磁碟只剩新版），`nf_tables` 模組載不進來。判讀方法是讀權威狀態：`uname -r`（執行中）對比 `ls /usr/lib/modules/`（磁碟上），兩者不一致就是 kernel 升級後未重開機，重開即解（方法論見 [診斷讀權威狀態](../../../debug/diagnosis-read-authoritative-state/)）。這條 gotcha 鏈提醒：一個看似無關的修法（`-Syu`）可能埋下三步後才引爆的伏筆。

**named volume 掛載點是 root、非 root 使用者寫不進。** 把 `~/.claude` 掛成 named volume 後、container 內的 `node` 對它 `touch` 回 `Permission denied`——掛載點 owner 是 `root`。根因是 Docker 對「image 內不存在的路徑」建 named volume 時預設 root-owned。修法是在 Dockerfile 裡（`USER node` 之前、還是 root 時）先 `mkdir -p /home/node/.claude && chown node:node`：Docker 掛空 volume 時會沿用 image 內該目錄的 owner。這是「掛載點要先在 image 裡以對的 owner 存在」的通用原則、對任何要讓非 root 使用者寫的 volume 都適用（見 [Docker named volume 掛載點 owner](/linux/dotfile/knowledge-cards/docker-named-volume-ownership/)）。

build 失敗的分流（本次未遇）：看是哪一層指令、跟 base image 版本漂移有關先查 tag / digest 是否固定；run 起來但檔案權限錯亂多半是 host / container 的 UID 對映問題（本次用 node(1000) 對齊 tar(1000) 避開）。

## Step 7：Claude Code 落地與憑證持久化

### 概念與工具

agent 程式裝進 image、真正要解的是「認證怎麼活過 container 重建」。實測發現對 headless 工作機、Claude Code 的 `setup-token` 給出的是比持久化 OAuth session 更貼合的模型：它產生一個**長效 token**（實測有效一年）、用環境變數 `CLAUDE_CODE_OAUTH_TOKEN` 注入。這讓認證變成一顆 host 側的 secret——存在 image 外、git 外，`docker run` 時才注入（機密為何不進 image layer 也不進 repo、runtime 注入才對，見 [機密 runtime 注入](/linux/dotfile/knowledge-cards/runtime-secret-injection/)）。設定（`settings.json`、含 hooks）走 volume 持久化、認證走 env var 注入，兩者分離：憑證輪替只要換 env 檔、不用碰 volume。信任邊界的判讀見 [選型文的隔離段](../agent-workstation-home-vs-vps/)。（Claude Code 在本 blog 沒有安裝與 hooks 專文、缺口已記在 content-backlog。）

### 實作

Claude Code 已在 Step 6 的 image 裡（實測版本 2.1.204）。認證分三步：產 token、存成 secret、注入。

第一步用 `setup-token` 走一次互動登入。它需要真 TTY（`docker run -it`），而 SSH 要帶 `-t` 才配置 TTY——**從自己的終端機**跑（透過工具管線或非互動 shell 都拿不到 TTY、會報 `cannot attach stdin to a TTY-enabled container`）：

```bash
ssh -t tar@<vm> 'docker run -it -v claude-home:/home/node/.claude agent-workstation:v1 claude setup-token'
```

流程會印一個授權 URL、在瀏覽器用 Anthropic 帳號授權、把授權碼貼回終端。完成後它印出長效 token。

這裡有個實測會混淆的點、要講清楚——過程出現**兩個不同的憑證**：

- **授權碼**：授權那步你貼進**瀏覽器流程**的一次性碼，用完即棄，不是要保存的東西。
- **長效 token**：`setup-token` 跑完印在終端、`sk-ant-oat01-` 開頭那串，這才是要保存、之後每次啟動 container 用的憑證。

第二步把長效 token 存成 host 側的 gitignored secret。`setup-token` **不會**把它寫進 `~/.claude`（它只印出來、明示要你設成 `CLAUDE_CODE_OAUTH_TOKEN`），所以持久化的責任在你、模型是「存 secret」而非「持久化登入態」。存的時候用 `read -s` 靜默讀入、避免 token 進 shell history。remote shell 是 zsh 時 `read` 語法跟 bash 不同（bash 的 `read -rsp "提示" VAR` 在 zsh 會報 `no coprocess`、zsh 要寫成 `read -rs "VAR?提示"`）：

```bash
# 在 VM 上（remote 為 zsh）：靜默讀入、寫成 600 權限的 env 檔
umask 077
read -rs "T?貼上 token 後按 Enter: "
printf 'CLAUDE_CODE_OAUTH_TOKEN=%s\n' "$T" > ~/agent-workstation/.env
chmod 600 ~/agent-workstation/.env
```

第三步 `docker run` 時 `--env-file` 注入。加 `--dangerously-skip-permissions` 在這個架構下是正確選擇而非偷懶：container 邊界本身就是權限邊界（隔離層的核心論點），agent 只碰得到掛進去的 `/work`、爆了困在 cgroup 裡，容器內不必再疊一層檔案權限確認——這實機印證選型文「信任邊界等於 mount 清單」。

```bash
docker run --rm --env-file ~/agent-workstation/.env \
  -v claude-home:/home/node/.claude \
  -v ~/agent-workstation/testproj:/work \
  agent-workstation:v1 \
  claude -p "在目前目錄建立 hello.txt、寫一行問候語" --dangerously-skip-permissions
```

上面是 `-p` 一次性任務（fire-and-forget）。互動對話（坐著跟 agent 來回聊）用同一套注入、只是把 `-p` 換成 `-it`：把這串包成 helper、手機端一個指令就進已認證的互動 session。

```bash
#!/usr/bin/env bash
# claude-shell.sh：注入 token、掛專案目錄、起互動 Claude Code
docker run --rm -it \
  --env-file "$HOME/agent-workstation/.env" \
  -v claude-home:/home/node/.claude \
  -v "$HOME/agent-workstation/testproj:/work" \
  agent-workstation:v1 \
  claude --dangerously-skip-permissions "$@"
```

這裡要點破一個實測會誤解的心智模型：**認證綁在「每次 run 有沒有注入 token」、不綁在 session 或登入態上**。env-var 模型下沒有「一次登入、之後都在」這回事——直接打 `claude`（沒注入 token）即使在同一個還活著的 zellij session 裡、也會要你重新認證；而在 `--rm` 的臨時 container 裡真的走一次互動登入、憑證寫進容器的 `~/.claude`、容器一結束就蒸發（除非登入時掛了 volume 讓它落在 `claude-home`）。所以「臨時容器裡互動登入」多半是白做、下次又被要求認證。可靠的做法是不依賴任何登入態、每次用 helper 注入 token。這點用隔離測試釘死過：**不掛任何 volume（排除一切存檔登入）、只注入 token 即認證成功；不注入 token 則回 `Not logged in`**——證明認證來源純粹是注入的 token、與 session、與 volume 裡有沒有登入檔都無關。

### 驗證

- 在掛載的專案目錄內給 agent 一個小任務、能完成並寫入檔案、host 側看得到變更

實測跑上面那條：agent 認證成功、在 `/work` 建了 `hello.txt`、回報「已建立」。回到 host 看：

```text
$ ls -la ~/agent-workstation/testproj/hello.txt
-rw-r--r-- 1 tar tar 37 … hello.txt          # owner = tar(1000)、UID 對映正確
$ cat ~/agent-workstation/testproj/hello.txt
你好，祝你有美好的一天！
```

- container 砍掉重建後、Claude Code 免重新登入直接可用

這個模型下「免重登」不靠 volume 裡的登入態、靠的是 env 檔：`--rm` 砍掉 container、下次 `docker run` 一樣 `--env-file` 注入同一顆 token 即認證，image 重建（Step 6 改 Dockerfile 那幾次）也不影響——認證跟 image、container 生命週期完全解耦。

### 除錯判讀

實測任務跑通、但輸出帶一則非致命警告：`Claude configuration file not found at: /home/node/.claude.json`。這揭露一個持久化邊界：Claude Code 的頂層設定檔 `.claude.json`（存專案信任、onboarding 狀態）在 `$HOME/.claude.json`、**不在** `~/.claude/` 這個 volume 裡，所以它不跨 container 重建持久化。用 token 注入 + `--dangerously-skip-permissions` 的無人值守流程不需要它（信任由 skip-permissions 跳過），任務照跑；但若要保留專案級狀態（MCP 設定、逐專案信任），得額外把 `/home/node/.claude.json` 也掛成持久檔。判讀原則：先分清缺的是「認證」（env var、缺了 agent 直接無法認證）還是「設定」（`.claude.json`、缺了只是回到預設狀態、非致命）。

另一個要記的排除點：volume 掛載點若 root-owned、非 root 使用者寫不進（Step 6 已解，Dockerfile 預建 chown）。認證這條路的第一個檢查點永遠是 env var 有沒有真的注入進去（`docker run … env | grep CLAUDE_CODE_OAUTH_TOKEN` 回讀），以權威狀態為準、再往上懷疑 token 本身失效。

## Step 8：hooks 接 ntfy 通知

### 概念與工具

通知把工作流從「掛在終端上等」翻成「離開、跑完被叫回來」：agent 的任務結束事件觸發 hook、hook 對 ntfy topic 發一則推播、手機 app 訂閱該 topic。ntfy 的架構與自架取捨見 [ntfy 推播通知服務](../../../debug/ntfy-push-notification-service/)、無人值守情境下「結果推得出去」的定位見 [讓機器跑無人值守的長任務](../../../install/unattended-remote-work/)。

### 實作

- 手機安裝 ntfy app、訂閱規劃好的 topic
- Claude Code 配置 Stop / Notification hooks、對 topic 發訊（topic 真值不進 git）

觸發事件選 `Stop`——Claude Code 每次回應結束時觸發，對應「一輪任務跑完」這個要通知的時機（另一個候選 `Notification` 是 agent 主動要求關注時觸發、語意是「需要你介入」而非「跑完了」，兩者可並存但語意不同）。hook 設定寫進掛在 volume 的 `settings.json`、跨 container 重建持久化（認證則走 env var 注入、見 Step 7——設定持久化與認證注入是分開的兩條路）：

```json
{
  "hooks": {
    "Stop": [
      { "hooks": [
        { "type": "command",
          "command": "curl -s -H 'Title: Claude Code 任務完成' -d 'agent 在 VM 上跑完了' https://ntfy.sh/<你的-topic>" }
      ] }
    ]
  }
}
```

topic 是私密值——猜到 topic 名的人就能發推播到你手機、也能收你的通知，所以真值不進 git（本輪用一個拋棄式測試 topic 驗鏈路）。

### 驗證

- 從 shell 手動 curl 一則測試訊息、手機收到（先驗 ntfy 鏈路本身）

實測從 VM 對 `https://ntfy.sh/<test-topic>` 手動 curl 一則：

```text
$ curl -s -w '\nHTTP %{http_code}\n' -d 'Step 8 鏈路測試：VM 發得出去' https://ntfy.sh/<test-topic>
{"id":"XqDoIWLaB3a7", … ,"event":"message","topic":"…","message":"Step 8 鏈路測試：VM 發得出去"}
HTTP 200
```

ntfy.sh 回 HTTP 200、訊息被接收（帶 message id）——VM→ntfy 這段鏈路本身通。手機端訂閱同一 topic 收訊的驗證屬行動端、隨手機配合一起做。

- 給 agent 一個會跑幾分鐘的任務、手機關螢幕等待、任務結束收到推播（再驗 hook 觸發）

實測：Step 7 那個真實 agent 任務（建 `hello.txt`）跑完後、poll ntfy 看最近訊息：

```text
$ curl -s 'https://ntfy.sh/<test-topic>/json?poll=1&since=5m'
{… "title":"Claude Code 任務完成","message":"agent 在 VM 上跑完了"}
```

`Stop` hook 在任務結束時確實觸發、發出設定裡那則推播，手機端也收到——真實 agent 任務 → hook → ntfy → 手機這條端到端閉環成立。（本輪一併確認：手機訂閱該 topic 後，稍早 VM 側與 container 側的兩則手動測試推播都收到、鏈路無誤。）

### 除錯判讀

兩段驗證把問題切開：手動 curl 通、hook 沒動靜，問題在 hook 配置層（`settings.json` 路徑 / JSON 格式 / container 內有沒有 curl）；curl 就不通，問題在 ntfy 鏈路（topic 名稱、網路、app 訂閱狀態）。

「container 內有沒有 curl」這點本輪實測真的踩到：`node:22-bookworm-slim` 不內建 curl，第一版 image 裡 hook 的 curl 指令會找不到執行檔而靜默失效——ntfy 鏈路手動測是通的、hook 卻不會發訊，剛好落在「手動 curl 通、hook 沒動靜」這個分流。修法是把 curl 加進 Dockerfile 的 `apt-get install`（Step 6 的 Dockerfile 已含）。這提醒 hook 的除錯要把「hook 指令依賴的工具在 container 裡存不存在」當第一個檢查點。修好後從 container 內 curl 到 ntfy 回 HTTP 200、鏈路層排除，剩下的變數收斂在手機訂閱與 hook 觸發兩點。

## Step 9：手機端連線與輸入

### 概念與工具

行動端輸入是整套工作流最容易用不下去的環節：終端 UI 依賴 Esc / Ctrl / 方向鍵、手機軟體鍵盤預設沒有，client 的擴充鍵列補這個缺。判讀見 [選型文的使用形態段](../agent-workstation-home-vs-vps/)、client 之間（Blink / Termius / 自製 ttyd）的比較見 [手機終端 client 選型](../mobile-terminal-client-selection/)。

### 實作

- 候選 A：現成 client（Termius / Blink Shell 這類），配 mosh + 擴充鍵列
- 候選 B：自製通道（ttyd 轉 WebSocket、走 tailnet、原生 app 收），適合要客製認證與稽核的情境
- 順序已定：本輪用候選 A 跑通全部步驟（控制變數——工作流本身未驗證時、client 端用成熟工具歸零變數）；候選 B 的功能對齊（擴充鍵列、斷線重連、多 endpoint、TUI 相容）記在該工具自己專案的提案系統、驗收規格採用本文跑通後凍結的判準

本輪的手機是 Android（Galaxy A70），這件事先卡掉一半候選：Blink Shell 是 iOS 專屬、Android 裝不了，所以現成 client 落在 Termius。連線分兩步建立：先純 SSH 把「連得上 + 金鑰認證」驗通、再開 mosh 測漫遊（Step 4），控制變數。金鑰用 Termius 產一把 ED25519、把公鑰加進 VM 的 `authorized_keys`——手機端一律走金鑰、不用密碼（沿用 Step 2 的基線；私鑰在客戶端 / 公鑰授權在伺服器、per-device 各配一把的模型見 [SSH 金鑰儲放與 authorized_keys](/linux/dotfile/knowledge-cards/ssh-key-storage/)）。實測 Termius 預設會退回問密碼、`tar` 沒設密碼所以失敗，加完公鑰重連即免密碼登入，VM 側 `journalctl -u sshd` 看到 `Accepted publickey from 100.71.173.84`。

### 驗證

- 手機端完成一次完整互動：attach session、給 agent 下指令、Esc 中斷一次、方向鍵翻歷史

實測 Termius（Android）連上後跑 `zellij attach -c work`、走四個關鍵按鍵：

| 動作         | 手機鍵列實測                                                                                            |
| ------------ | ------------------------------------------------------------------------------------------------------- |
| Tab 補全     | 鍵列有 Tab、可用                                                                                        |
| Ctrl-C 中斷  | 鍵列有 Ctrl、`Ctrl+C` 中斷得了                                                                          |
| 方向鍵翻歷史 | 鍵列有方向鍵、上鍵叫回歷史指令                                                                          |
| Esc          | 鍵列**有 Esc**、但被水平捲動的鍵列推到畫面外遮住、需橫向拖動鍵列才露出；`Ctrl+[` 是不依賴找鍵的等價替代 |

Esc 這格的實測過程本身就是一個判讀教訓：第一眼掃過 Termius 的擴充鍵列沒看到 Esc、以為缺這個鍵，實際是**鍵列可以水平捲動、Esc 被推到可見範圍外遮住了**，橫向拖動鍵列就露出來。行動端的擴充鍵列常是可橫向捲動的、可見的那幾顆不等於全部——「按鍵缺失」的結論要先把鍵列拖過一遍再下，這正是第一印象與實際互動不符時、以互動為準的例子。就算真的找不到某個鍵，終端層還有等價組合鍵可用：`Ctrl+[` 送出與 Esc 相同的 `0x1b` 控制碼、任何終端通用（實測在 zellij 進 PANE 模式後 `Ctrl+[` 能退回 NORMAL、等同 Esc），這條不依賴 client 把鍵擺在哪。這格印證選型文說的「擴充鍵列決定手機端是可操作還是只能看」——但可操作性的判讀要把「鍵列可捲動」算進去、別被預設可見範圍誤導。

- 輸入體感可長用（判準：一段 prompt 打完的錯誤率與速度自評）

實測純 SSH 與 mosh 下四個關鍵動作都能完成一次完整互動；mosh 漫遊下切網路有約 3 秒凍結（Step 4）、但輸出不丟、恢復後可續打，長用可接受。手機端派 agent 任務的免引號 helper 與踩到的引號 gotcha 記在 Step 10 情境一。

### 除錯判讀

手機 client 連不上要先分「逾時 vs 被拒」：**連線逾時（timed out）多半是手機不在 tailnet 上**——client 設定沒問題也連不到 tailnet 私網位址，先回 Step 3 從 VM 側 `tailscale status` 確認手機有沒有上線，這是本輪實測第一個踩到的關卡（Termius 連 `100.68.144.88` 逾時、根因是手機 Tailscale 沒連上、詳見 Step 3 除錯判讀）；連線被拒（refused）才往 sshd / 認證 / 防火牆查。

連上之後的分流：以為某個鍵缺失時（本輪一度以為沒 Esc）先別急著換 client——第一步是把擴充鍵列橫向拖過一遍（行動端鍵列常可捲動、鍵藏在可見範圍外，本輪的 Esc 就是這樣），找不到再用等價組合鍵（`Ctrl+[` 等於 Esc、`Ctrl+H` 等於 Backspace 這類終端通用等價），還要不到才看 client 能不能自訂鍵列、最後才換 client；亂碼與斷行錯位是終端 TERM / 字型問題，分流見 [SSH 與終端機問題排查](../../../debug/ssh-and-terminal-troubleshooting/)。

## Step 10：端到端驗收

### 概念與工具

前九步各自驗過自己那層、這步驗跨層組合：三個情境對應三個最可能在真實使用中出現的失敗面。

### 實作與驗證

三個情境全部從手機端執行：

1. **fire-and-forget**：手機丟一個任務給 agent、鎖螢幕走人、收到 ntfy 推播後重連看結果。驗證斷線期間任務持續、通知準確。

實測從手機在 zellij session 裡呼叫一個把 `docker run --env-file … claude -p` 包起來的 helper、派一個「在 /work 建 report.txt、寫三行架構重點」的任務、鎖螢幕離開。約一分鐘後手機收到 ntfy 推播 `Claude Code 任務完成`、重連 `zellij attach work` 看到任務輸出、host 的 `~/agent-workstation/testproj/report.txt`（281 bytes、owner `tar`）已生成、內含 agent 寫的三行。端到端閉環成立：派任務 → 離線 → agent 跑 → hook 推 → 手機收 → 接回。

這情境實測踩到兩個純行動端的輸入 gotcha 值得記。

其一是引號：第一次呼叫 helper 沒帶到任務參數、腳本印出用法提示就退出（VM 側查證：沒有新 container、沒生檔、沒推播——不是失敗、是腳本正確拒絕空任務）。根因是手機軟體鍵盤容易把直引號 `"` 自動換成智慧引號 `“”`、shell 不認、參數解析壞掉。解法是把 helper 設計成免引號、而不是要求使用者小心打引號：沒帶參數時互動式從 stdin 讀整行任務、且用 `"$*"` 收全部參數而非只取 `$1`。行動端派工具要假設引號會被鍵盤偷換、從介面設計上避開，而不是靠使用者不犯錯。

其二是 CJK 輸入、且牽出一個 mosh 與中文顯示的硬權衡：本輪派任務時手機在終端裡打不出中文、只能用英文描述任務（這是為什麼 agent 回報是英文系統事實、而非中文架構重點——先前一度誤判成 agent 自行填補模糊、實際是輸入端受限）。逐層定位下來釐清了三件事：

- 預設狀態下 Termius 終端不接受 CJK 即時輸入（輸入法切不到中文），但中文**貼**進終端能正常送出、編碼無誤——所以不是編碼問題。
- Termius 有個 `Experimental Keyboard Support（Voice input and CJK layout support）`開關、開了之後終端就能切中文即時打字。
- 但開 CJK 後、**mosh 連線下中文輸入行的畫面會錯位**（輸出正常、只有正在編輯的輸入行亂）；同樣設定改用**純 SSH 就完全正常**。

根因是 mosh 的本地回顯預測撞上 CJK 雙寬字元：mosh 先猜按鍵顯示、但雙寬字的寬度在預測層算錯、游標位置與重繪就錯位；純 SSH 沒有預測、只呈現 server 端（bash / zellij 正確處理雙寬字）的真實渲染、所以乾淨（雙寬字顯示與 raw 模式擋 IME 組字的完整機制見 [終端 CJK 雙寬字與即時輸入](/linux/dotfile/knowledge-cards/terminal-cjk-input/)）。這帶出一個實用的權衡——**要坐著打中文跟 agent 對話、用純 SSH（顯示對、無漫遊但 zellij 補上斷線接回）；要移動中漫遊、用 mosh（但別打 CJK、會亂）**。兩個使用形態不太重疊：移動中多半丟英文任務看結果、坐著深談才打大量中文而此時網路固定不需漫遊，所以存 SSH 與 mosh 兩個 host profile 分別服務，比勉強用一個好。理論上 `mosh --predict=never` 關掉預測能兩全、但 client 未必讓你傳 mosh 參數。這條把「行動端能不能派複雜任務」精確到：CJK 即時輸入要靠終端的 CJK 支援開關、且與 mosh 預測有顯示衝突——選型與使用形態要納入這一格。

2. **斷線復原**：任務進行中把手機從 Wi-Fi 切到行動網路。驗證 mosh 漫遊 + zellij session 兩層的組合行為。

這情境的核心在 Step 4 已實測：zellij 裡跑著的迴圈、手機切網路後畫面凍約 3 秒、恢復後輸出無斷檔、不需手動重連。兩層在此協作——mosh 在連線層用 UDP 扛端點變化、zellij 在 session 層讓工作獨立於連線存活。對照組也驗到了：同樣的迴圈若跑在純 SSH shell（不在 zellij）、SSH 一斷就被 SIGHUP 殺掉。所以「斷線復原」要兩層都在位：只有 mosh 沒有 zellij、連線接回了但前景任務已死；只有 zellij 沒有 mosh、任務活著但要手動重連 attach。

3. **資源保護**：讓 container 內任務吃滿記憶體上限。驗證 OOM 只影響工作負載、連線與 session 基礎設施存活。

這情境的機制在 Step 6 已實測：`--memory=256m` 下 container 內程序吃爆被砍、退出碼 137（OOM kill）、host 的 `free` 幾乎沒動、host 側對照程序與 SSH 連線存活。而「連線與 session 基礎設施活得比工作負載久」這個前提，在情境 2 已被獨立驗證（mosh + zellij 跟 container 是分開的層）——所以 container OOM 時、手機的 mosh session 與 zellij 不受波及、事後 attach 回去看得到發生什麼事，是這兩個獨立事實的組合結論。

### 除錯判讀

情境失敗時回對應步驟的除錯段：通知沒來回 Step 8、斷線任務死掉回 Step 5、OOM 拖垮連線回 Step 6 的資源上限配置。跨層問題先確認單層驗證是否仍通過、再懷疑組合行為。

## 完成與後續

十個步驟與三個端到端情境都經實機跑通、本文的指令與輸出是實跑結果。過程中最值得回頭修正選型判斷的一點是 Step 7 的憑證模型：`setup-token` 給的是**長效 token 的 env-var 注入模型**、不是「持久化 OAuth session 到 volume」——[選型文](../agent-workstation-home-vs-vps/) 隔離段講「狀態要顯式持久化」時把憑證與設定混在一起，實測顯示這兩者該分開（設定走 volume 持久化、認證走 runtime 注入的 secret），是該文可以再細化的一格。

session 層的 zellij 操作（背景常駐、注入指令、attach/detach 持久化、清理）在本文只帶過用到的部分、完整的 CLI 操作見 [Zellij session 生命週期](../../cli/zellij-session-lifecycle/)。
