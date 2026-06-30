---
title: "最小安裝後的工具驗證與補足"
date: 2026-07-01
description: "最小化安裝的 Linux 裝完發現連 sudo 或 which 都沒有、bootstrap 腳本第一行就炸、需要先確認系統缺哪些必要工具再補時回來讀"
weight: 2
tags: ["dotfile", "linux", "install", "bootstrap"]
---

最小化安裝給你的是一台能開機的系統，但「能開機」跟「能用」之間隔著一組「大家都假設存在」但其實沒被裝進去的工具。最小安裝（多數發行版的 `base` 之類的套件組）刻意只裝開機與基本運作所需的東西，把工具的選擇權留給你。代價是許多你以為理所當然會在的指令——`sudo`、`which`、`rsync`——一個都沒有。驗證它們在不在，比假設它們在安全。

這層落差最常在你跑自動化腳本時引爆。一支 bootstrap script 的第一行可能就是 `sudo pacman -S ...`，在一台連 `sudo` 都沒有的機器上，它連第一步都跨不過去。所以裝好系統後、跑任何自動化之前，先過一輪工具驗證，把缺的補上。

## sudo：先有雞還是先有蛋

`sudo` 是最容易被假設存在、卻最常缺席的工具，而且它的缺席有一個結構性的麻煩：補它的動作本身需要 root 權限。最小安裝通常不含 sudo。某些安裝程式（如本例的 archboot）即使你勾了「把這個使用者設為管理員」，那個動作也往往只是把使用者加進 `wheel` 群組，並沒有真的裝上 sudo、也沒有啟用 sudoers 裡 wheel 群組的授權行。結果就是使用者「名義上是管理員」，但系統裡並沒有 sudo 這支指令。

這形成一個先有雞還是先有蛋的關卡：bootstrap script 要靠 sudo 來裝套件，但 sudo 自己得先存在。它的解法不能是「把 sudo 寫進套件清單」——那份清單正是靠 sudo 來安裝的。sudo 只能是「跑 bootstrap 之前的前置」，用 root 身分手動補上：

```bash
su -                                          # 切到 root（輸入 root 密碼）
pacman -S --needed sudo                        # root 身分裝 sudo，不需要 sudo
echo '%wheel ALL=(ALL:ALL) ALL' > /etc/sudoers.d/10-wheel   # 啟用 wheel 群組授權
chmod 440 /etc/sudoers.d/10-wheel
visudo -c                                      # 驗證 sudoers 語法，印 parsed OK 才安全
exit
```

切回一般使用者後用 `sudo -v` 確認——能輸入密碼、沒報「不在 sudoers 檔」就成。這一步揭示一條通則：凡是 bootstrap 自身要依賴的工具，都不能由 bootstrap 來裝，必須當成前置先備好。`sudo` 是這類前置最典型的一個。

上面的指令以 Arch 的 `pacman` 為例。Fedora 用 `dnf`、Debian/Ubuntu 用 `apt`；而 Debian 系的桌面與伺服器映像多半預設就裝了 sudo、也設好了授權，這個缺口主要出現在刻意精簡的 minimal 安裝。換句話說「sudo 是前置」這條判讀軸跨發行版成立，但「你這台到底缺不缺」要靠驗證、不是假設。

## which：腳本裡的隱形地雷

`which` 是另一個最小系統常缺、卻被腳本大量引用的指令，它的缺席會以一種隱晦的方式讓腳本出錯。很多腳本用 `$(which zsh)` 之類的寫法取一支程式的完整路徑；在沒有 `which` 的系統上，這個命令替換會吐出空字串，而下游拿到空字串的指令可能不會立刻報「找不到 which」，而是報一個看似無關的錯。實測中就遇過 `chsh -s "$(which zsh)"` 因為 `which` 不存在而變成 `chsh -s ""`，最後報的是 `chsh: shell must be a full path name`——錯誤訊息完全沒提到真正的元兇。

正確的做法是用 `command -v` 取代 `which`。`command -v` 是 POSIX 規範的 shell 內建，不依賴任何外部套件，在最小系統上一定存在。

```bash
command -v zsh        # 印出 /usr/bin/zsh；找不到則回傳非零、不印東西
```

這條判讀對你自己寫的腳本是「把 `which` 全換成 `command -v`」，對別人的腳本是「在缺 `which` 的系統上，先補 `which` 套件或改腳本」。它跟 sudo 的差別在於：`which` 的缺席會悄悄製造一個誤導性的下游錯誤，而不是當場大聲報錯，所以更值得在驗證階段主動排掉。

## 其他常缺的工具

除了 sudo 與 which，最小系統還常缺幾類在自動化裡會用到的工具，各有各的補法。它們不像 sudo 是硬前置，但缺了會在特定步驟卡住。

| 工具              | 缺了會怎樣                                             | 補法                                                      |
| ----------------- | ------------------------------------------------------ | --------------------------------------------------------- |
| `rsync`           | 從本機同步 dotfile 進機器時 `rsync: command not found` | 進套件清單；急用時改用 `tar` over SSH 過渡                |
| `ca-certificates` | HTTPS / 任何 TLS 連線在憑證驗證直接失敗（沒有信任根）  | 進套件清單；它是下一篇 HTTPS clone 的隱性前置             |
| `hostname`        | 某些腳本呼叫 `hostname` 取主機名時失敗                 | 補 `inetutils`，或改用 `hostnamectl` / 讀 `/etc/hostname` |
| 編譯工具鏈        | 從原始碼或社群套件庫編譯時缺 `gcc` / `make`            | 補發行版的開發工具組（如 `base-devel`）                   |

`rsync` 的缺席要特別點出，因為它常被當成理所當然的傳輸工具。最小系統沒有它時，第一次把檔案弄進機器可以用兩邊都有的 `tar` 搭配 SSH 過渡：

```bash
tar czf - --exclude '.git' . | ssh user@host 'mkdir -p ~/dest && tar xzf - -C ~/dest'
```

這條的好處是不依賴目標機有 rsync；缺點是它每次都傳全部、沒有 rsync 的增量。在反覆同步的工作流裡，值得早點把 rsync 補進套件清單換取增量傳輸。

`ca-certificates` 最容易在下一步咬人。最小系統可能沒有 CA 信任根，這時任何 HTTPS 連線——包括下一篇主推的「公開 repo 用 HTTPS clone」——會在 TLS 憑證驗證直接失敗，而錯誤訊息常指向 SSL handshake 而非「缺信任根」，容易誤判成網路問題。打算走 HTTPS 取得 dotfile 的機器，先確認 `ca-certificates` 在。`git` 與 `curl` 同理：它們是 bootstrap 取得程式碼的基本工具，下面的驗證迴圈也會檢查，最小系統若沒有要一併補。

剩下兩項的缺席各有觸發時機。`hostname` 只在腳本明確呼叫它取主機名時才會浮現缺失，而用 `hostnamectl` 或直接讀 `/etc/hostname` 可以繞過，所以它常被當成「補了省事、不補也有替代」的軟缺口。編譯工具鏈則是在你要從原始碼或社群套件庫編譯時才需要——純跑預編譯套件的機器可以不裝，但只要你的 dotfile 流程會編譯任何東西（例如從社群套件庫裝桌面元件），它就得進清單。

## 系統性的驗證

裝好系統後先跑一輪集中驗證、把缺口一次盤出來，比等腳本跑到一半才逐一踩雷省事。驗證的對象是「你接下來的流程會用到、但最小系統可能沒有」的工具。

```bash
for cmd in sudo git curl rsync tar zsh; do
  if command -v "$cmd" >/dev/null 2>&1; then
    echo "OK   $cmd"
  else
    echo "缺   $cmd"
  fi
done
```

這段刻意用 `command -v` 來檢查（而不是 `which`），因為要檢查的對象之一正是「外部工具在不在」，用一個一定存在的內建來檢查才不會自己先掛掉。盤出來的缺口分兩類處理：bootstrap 自身依賴的（如 sudo）當前置手動補；其餘的（如 rsync、編譯工具）進套件清單，交給 bootstrap 一起裝。

## 跟 Bootstrap 套件清單的界線

這篇的驗證跟 [模組八的 bootstrap script 設計](/dotfile/08-sync-bootstrap/bootstrap-script-packages/) 是兩件互補的事，界線在「假設」上。bootstrap script 的套件清單假設一個前提：機器已經有能力執行安裝（有 sudo、有 package manager、清單裡的東西都能被裝上）。這篇處理的正是那個前提成立之前的階段——最小系統到底有沒有滿足那些假設，缺的補上，讓 bootstrap 的假設變成事實。

換句話說，套件清單回答「這台機器最終要有哪些套件」，工具驗證回答「這台機器現在夠不夠資格開始跑那份清單」。把兩者分清楚，才不會把 sudo 這種前置誤塞進靠 sudo 安裝的清單裡。

## 下一步

工具補齊、機器有能力執行安裝之後，你還困在一個地方：擠在機器的主控台手打。怎麼從舒適的本機終端機操作它，以及還沒有 SSH key 時怎麼把 dotfile 弄進去，[外部連入、SSH key 與無 key 的 bootstrap 路徑](../ssh-keyless-bootstrap/) 處理這兩件事。
