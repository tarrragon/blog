---
title: "外部連入、SSH key 與無 key 的 bootstrap 路徑"
date: 2026-07-01
description: "要從本機終端機操作新裝好的 Linux 機器、設 SSH key 免密碼、或還沒有 key 就想把 dotfile 弄進機器跑 install.sh 時回來讀"
weight: 5
tags: ["dotfile", "linux", "ssh", "bootstrap"]
---

操作一台新機器，從你本機的終端機透過 SSH 連進去是阻力最小的位置。直接在主控台操作有兩個實際的痛點：純文字的主控台（TTY 或虛擬機的序列 console）往往不能貼上，長指令只能手打、還容易掉字；畫面也通常擠、不能捲。把機器的 sshd 跑起來、從本機 SSH 進去之後，貼上、捲動、補全全部回到你熟悉的環境，而且這條路本身就貼近真實的遠端維運。

這篇處理三件事：把 sshd 跑起來並從本機連入、設 SSH key 達到免密碼、以及一個容易被卡住的情境——你還沒有 SSH key 時，怎麼把 dotfile 弄進機器、跑完基礎安裝。

## 啟用 sshd 並從本機連入

讓機器能被 SSH 連入只需要兩步：裝 SSH 伺服器、啟動它的服務。

```bash
pacman -S openssh             # 剛裝好的系統套件資料庫是新的，-S 不必先 -Sy
systemctl enable --now sshd   # enable 開機自啟、--now 立刻啟動
```

指令以 Arch 為例。換發行版時套件管理器不同（Fedora `dnf`、Debian/Ubuntu `apt`），服務名也可能不同——Debian 系的 OpenSSH 服務叫 `ssh` 不是 `sshd`，那邊要 `systemctl enable --now ssh`。

從本機連的時候用一般使用者、不要用 root：

```bash
ssh user@<機器 IP>            # IP 來自機器上的 ip -brief a
```

用一般使用者是因為多數發行版的 sshd 預設擋 root 密碼登入（`PermitRootLogin prohibit-password`）——root 只能用 key、不能用密碼。這個預設是好的安全姿態，順著它走、用你裝系統時建的一般使用者連即可。連進去之後，後續所有需要長指令、需要貼上的操作都在這個 session 裡做，不再回主控台手打。

這裡啟用 sshd 是為了 bootstrap 期間從本機連入操作，跟 [操作順序指引](/linux/dotfile/00-dotfile-mindset/setup-order-guide/) 後段把 sshd 當「桌面就緒後的常駐遠端救援通道」是兩個不同的時間點與目的——同一個 `systemctl enable sshd` 動作，這裡是為了「現在好操作」，那裡是為了「之後好救援」。

## SSH key 免密碼

每次連線都打密碼很快會變成阻力，尤其當你要反覆同步檔案或跑自動化時。SSH key 讓本機免密碼連入，做法是生一把金鑰、把公鑰放進機器、本機用私鑰認證。

生 key 時建議生一把專用的、不要佔用本機的預設金鑰槽，並在 SSH 設定裡給它一個好記的別名：

```bash
ssh-keygen -t ed25519 -f ~/.ssh/vm_arch -N "" -C "vm_arch host->target"
# 在 ~/.ssh/config 加一段別名：
#   Host vm
#       HostName <機器 IP>
#       User <你的使用者>
#       IdentityFile ~/.ssh/vm_arch
#       IdentitiesOnly yes
```

專用 key 的好處是它的權限範圍清楚——這把只給這台機器用，跟你其他身分的金鑰互不牽連。設好別名後，`ssh vm` 就免密碼連入，後面的 `rsync`、`scp` 也跟著免密碼。

把公鑰放進機器有兩條路。標準工具是 `ssh-copy-id`，它會在本機跑、要你輸入一次目標機的密碼。另一條省一次切換的路是：當你已經用密碼連進機器、且這個 session 在真終端機裡（貼上可用），直接把公鑰內容貼進機器的 `authorized_keys`：

```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh
echo "ssh-ed25519 AAAA... 你的公鑰內容" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

兩條路等價，選哪條看你當下在哪——還沒連上就用 `ssh-copy-id`，已經連上就直接貼，少一次切換。

## 還沒有 SSH key 時，怎麼把 dotfile 弄進去

設 SSH key 是讓「之後」連線變方便，但 bootstrap 的第一步——把 dotfile repo 弄進機器——並不一定需要 key。常見的卡點是把「clone repo」跟「有 SSH key」綁在一起，但 clone 有不需要 key 的路徑。怎麼把 dotfile 弄進去，取決於這份 dotfile 放在哪。

**repo 是公開的（在 GitHub 之類）**：用 HTTPS clone，公開 repo 的唯讀 clone 不需要任何認證。

```bash
git clone https://github.com/<帳號>/dotfiles ~/dotfiles
cd ~/dotfiles && ./scripts/install.sh
```

這是最直接的路——機器只要能上網就能拉到 dotfile，完全繞過 key 的問題。clone URL 裡的帳號要對；用錯帳號（例如把 email handle 當成 GitHub 帳號）會 clone 失敗或抓到別的 repo，這類筆誤在只看 README 範例時很容易漏掉。SSH key 在這個情境只有「之後要從機器 push 回去」才需要，純粹跑部署用不到。

**repo 是私有的、但機器能上網**：機器可以直接 clone，用 GitHub Personal Access Token（PAT）走 HTTPS——這是私有 repo 免 SSH key 的標準解。clone 時把 PAT 當密碼填進認證，機器就拉得到，一樣不必在它上面設 SSH key。

**repo 還沒推到任何遠端、或機器離線**：從本機把檔案傳進去。如果本機到機器的 SSH 已經能用（即使只是密碼登入），用 `tar` over SSH 一次傳進去（跟 `scp -r` 等價，差別只在 tar 能一次打包、又好控制要不要帶 `.git`）：

```bash
tar czf - --exclude '.git' . | ssh user@host 'mkdir -p ~/dotfiles && tar xzf - -C ~/dotfiles'
```

這條只需要兩邊都有的 `ssh` 跟 `tar`，不依賴目標機有 rsync。從 macOS 傳的時候要關掉 AppleDouble 中繼檔，否則會夾帶一堆 `._` 開頭的中繼檔到 Linux 上：在指令前加 `COPYFILE_DISABLE=1`。完全離線、連 SSH 都還沒通時，最後手段是把 repo 放進 USB、掛載到機器上複製出來。

把 dotfile 弄進去之後，跑它的 `install.sh` 完成基礎安裝。如果安裝腳本一開始就要用 sudo，記得 sudo 必須在工具驗證階段就備好——它是 [最小安裝後的工具驗證與補足](../minimal-install-verify/) 的前置，bootstrap 自身補不了。

## 換一台新機器（或重裝）時，SSH 為什麼突然連不上

SSH 的別名、金鑰、`known_hosts` 都是綁在「某一台特定機器」上的，所以當你重裝、或換一台新 VM，先前設好的 `ssh <別名>` 往往會以看似無關的錯誤失敗——那套設定是為舊機器建的，而重裝後是另一台機器：不同的 IP、不同的 SSH host key、還沒裝 sshd、`authorized_keys` 也是空的。判讀的起點是把重裝後的機器當成全新的一台，重做第一次連線的設定，而不是沿用舊別名。私鑰放哪、`authorized_keys` 授權模型、per-device 金鑰與 deploy key vs full key 的信任邊界，見 [SSH 金鑰儲放與 authorized_keys](/linux/dotfile/knowledge-cards/ssh-key-storage/)。

失敗會以三種形式出現，各對應不同層、各有各的修法：

`Permission denied (publickey)` 是認證被拒，代表 sshd 有在跑、連線有到（這是進度），卡在金鑰這關。常見於你用的別名設了 `IdentitiesOnly yes` 只送某一把 key，而新機器的 `authorized_keys` 還沒有它。修法是改用帳號加 IP 直連、走密碼，繞過那個鎖死金鑰的別名：`ssh user@<新 IP>`，密碼是「這次安裝」為該使用者設的（每次重裝各自獨立，不是舊機器那個）。連進去後再把公鑰貼回新機器的 `authorized_keys`、把別名的 `HostName` 更新成新 IP，免密碼才會恢復。

`Host key verification failed`（或 `REMOTE HOST IDENTIFICATION HAS CHANGED`）發生在新機器剛好拿到跟舊機器一樣的 IP 時：你本機 `known_hosts` 存的是舊機器的 host key，SSH 偵測到同一個 IP 換了 key、當成可能的中間人攻擊而拒連。修法是刪掉那筆舊紀錄，再重連時接受新 key：

```bash
ssh-keygen -R <IP>       # 刪掉該 IP 的舊 host key
ssh-keygen -R <別名>     # 有用別名的話一併刪
```

`Connection refused` 代表沒有 sshd 在監聽，也就是新機器還沒把 SSH server 起來。修法回到最開始——在新機器的 console 裝 openssh、啟動服務（見本篇開頭「啟用 sshd」），這一步在每台全新機器上都要重做。

三個症狀的共同根因是同一件事：SSH 的便利設定（別名、金鑰、host key 快取）綁的是機器身分、不會跟著「重裝」自動轉移。把它們當成「為某一台機器設好的」，換機器就重做第一次連線，能省下對著看似無關的錯誤瞎猜的時間。

## 連入後可能遇到的兩個終端機問題

SSH 連線本身通了之後，互動 shell 還可能因為終端機環境不對而出現「打字變亂碼、prompt 重繪錯位」。這類問題在你用現代終端機（如 Ghostty、Kitty）連進一台剛裝好的最小 Linux、又跑了 unicode 較重的 prompt（如 Powerlevel10k）時最容易出現，根源是兩個跟字元處理有關的終端機設定，跟你的 shell 配置無關。

第一個是 locale。macOS 的終端機 SSH 連線時常把 `LC_CTYPE=UTF-8` 送到遠端，但 `UTF-8` 不是合法的 Linux locale 名稱，Linux 收到後 fallback 成 `POSIX`/C locale——於是 shell 的行編輯器把輸入當單位元組處理，配上 unicode 字元的 prompt 就重繪成一個字母重複好幾次的累加亂碼。判讀方式是在遠端跑 `locale`，看 `LANG` 是不是空的、`LC_CTYPE` 是不是 `POSIX`。修法是在 shell 設定裡強制一個合法的 UTF-8 locale（前提是該 locale 已生成，見 [安裝選項判讀](../install-option-decisions/) 的 locale 段）：

```bash
export LANG=en_US.UTF-8
export LC_CTYPE=en_US.UTF-8
```

第二個是 terminfo。現代終端機會把 `TERM` 設成自己的值（Ghostty 是 `xterm-ghostty`、Kitty 是 `xterm-kitty`），而一台剛裝好的 Linux 的 terminfo 資料庫沒有這些條目，shell 的行編輯器做「清行重繪」時找不到對應的控制序列、就把畫面畫壞。判讀方式是在遠端 `echo $TERM` 看是哪個值、`toe | grep <值>` 看遠端認不認得。修法有兩條：把你終端機的 terminfo 灌進遠端（保留完整功能），或退而求其次強制一個遠端一定有的 `TERM`：

```bash
# 把本機終端機的 terminfo 灌進遠端的 ~/.terminfo（推薦）
infocmp -x "$TERM" | ssh remote 'tic -x -'

# 或：連線時強制遠端一定有的 TERM（功能略降，但保證能用）
ssh -t remote 'TERM=xterm-256color exec zsh -l'
```

這兩個問題的共同點是：它們在你裝了 unicode 較重的互動 shell 之後才浮現，而陽春的 shell（ASCII prompt）即使 locale 跟 terminfo 都不對也照樣能用。所以排查時，先確認是不是這層、而不是去懷疑剛裝的 shell 配置壞了。

## 連入、傳輸、安裝的順序

這三件事有一個固定的先後，順序錯了會在中間卡住。先把 sshd 跑起來、從本機連入，取得一個能貼上、可捲動的 session；再把 dotfile 弄進機器（公開 repo 走 HTTPS clone、私有或本地走傳輸）；最後在機器上跑 install.sh 完成安裝。SSH key 是讓「連入」從每次打密碼變成免密碼的優化，可以在任何時候補，不是這條鏈的必要環節、也不是 bootstrap 的前置。

[模組零的操作順序指引](/linux/dotfile/00-dotfile-mindset/setup-order-guide/) 把「生成 SSH key、部署公鑰」列為標準流程的一環，那是預設你會建 key 的主路徑。這篇補的是它沒展開的另一面：當你手上還沒有 key、或這台機器的 dotfile 根本不需要 key 就能取得時，怎麼一樣把 bootstrap 跑完。

## 下一步

連入、傳輸、安裝都跑通之後，真正的考驗是當 install.sh 中途失敗時——而它遲早會撞到失敗——你能不能快速看出哪裡錯了。這取決於安裝腳本有沒有把可觀測性內建進去，[可除錯的 bootstrap](../observable-bootstrap/) 談的就是怎麼內建。
