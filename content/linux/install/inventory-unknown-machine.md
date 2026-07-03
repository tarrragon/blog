---
title: "接手陌生機器的盤點：先讀清楚它在跑什麼"
date: 2026-07-03
description: "接手一台別人裝好、已在跑服務的 Linux 機器，要在動手改任何設定之前盤清楚上面跑什麼、誰能進來、設定與 secret 落在哪時回來讀"
weight: 10
tags: ["linux", "inventory", "takeover", "sysadmin"]
---

這篇處理的情境跟本系列其他篇相反：機器已經裝好、已經在跑，裝它的人可能已離職、可能只留下一句「都在上面了」。系列主線教你把一台空機器變成能跑活的機器；這篇教你把一台「不知道在跑什麼的機器」變成「盤點清楚、敢動手維護的機器」。對照 infra 樹，這篇是 [拿到雲端帳號的第一天](/infra/00-infra-mindset/first-day-with-cloud-account/) 的 OS 層對等篇——那篇盤點的是雲端帳號裡有什麼資源，這篇盤點的是單一台 Linux 機器裡有什麼狀態。

核心紀律只有一條：**盤點期間只讀不改**。這跟 [診斷心法](../../debug/diagnosis-read-authoritative-state/) 的「讀權威狀態」是同一個紀律的不同應用——診斷是出問題後讀狀態找根因，盤點是還沒出問題時讀狀態建立現況清單。改動留到盤點完成、你能回答「這台機器停掉會影響誰」之後。本篇所有指令都是唯讀查詢，照著跑不會改變機器狀態；少數需要 root 權限的會標明。

盤點的產出是一份清單，建議直接開一個文字檔邊查邊記。這份清單之後會變成把機器收斂進版本控制的依據——terminal 捲動紀錄留不住，清單留得住。

## 這台是什麼機器

盤點的第一層是機器的身分：發行版、架構、實體還是虛擬、活多久了。這層決定後面每一步用什麼指令——套件管理器、服務管理方式、log 位置全由發行版決定，判讀邏輯見 [平台與發行版差異的判讀地圖](../platform-divergence-map/)。

```bash
cat /etc/os-release        # 發行版與版本
uname -a                   # kernel 版本與架構（x86_64 / aarch64）
systemd-detect-virt        # 虛擬化偵測：kvm / vmware / none（實體機）
uptime                     # 活多久、負載
hostnamectl                # 主機名與上面幾項的整合視圖
```

`uptime` 的天數是一個重要訊號：跑了四百天的機器代表它從沒被重開驗證過——上面的服務能不能在重開機後自己回來，沒人知道。這會影響你後面對「開機自啟清單」那段的重視程度。

## 誰能進來

第二層是存取面：有哪些帳號、誰有 sudo、誰的 key 被授權登入。接手的機器上常有前人留下的帳號與 key，這些是你動手維護前必須知道的存取路徑——不知道誰能進來，就無法判斷一個改動是不是「只有你會做」。

```bash
# 有登入 shell 的帳號（排除 nologin / false 的系統帳號）
grep -vE '(nologin|false)$' /etc/passwd

# 誰有 sudo：主檔 + drop-in 目錄都要看（需要 root）
sudo cat /etc/sudoers
sudo ls /etc/sudoers.d/ && sudo cat /etc/sudoers.d/*

# 每個真人帳號的 SSH 授權 key
cat ~/.ssh/authorized_keys
sudo cat /home/*/.ssh/authorized_keys

# 最近誰登入過
last -20
```

`authorized_keys` 每行結尾的 comment（通常是 `user@hostname`）是判斷 key 主人的線索。無法對應到在職人員的 key 記進清單——盤點期間先不刪，但接管後的第一批改動應該包含輪替它們。sudoers 的 `NOPASSWD` 條目也記下來：它可能是前人為無人值守任務設的，判斷它還需不需要存在的依據見 [讓機器跑無人值守的長任務](../unattended-remote-work/) 對這個取捨的展開。

## 跑什麼服務、誰開機自啟

第三層是這台機器的「工作內容」：現在跑著哪些服務、重開機後哪些會自己回來。這兩份清單常常對不上，而對不上的地方就是接手後的地雷。

```bash
# 現在在跑的服務
systemctl list-units --type=service --state=running

# 開機會自啟的（不只 service，也含 socket / timer）
systemctl list-unit-files --state=enabled

# 各使用者層的 user unit（--user 屬於各帳號、root 看不到全部）
systemctl --user list-units --type=service --state=running
ls /home/*/.config/systemd/user/ 2>/dev/null
```

兩份清單的差集各有含義。**在跑但沒 enable** 的服務，重開機就消失——它可能是有人手動 `systemctl start` 起來忘了 enable，也可能本來就該臨時。**enable 了但沒在跑**的服務，代表它啟動失敗過或被手動停掉，`systemctl status <unit>` 看它最後的狀態與退出原因。

systemd 之外還有一塊盲區：直接被人手動跑起來、或掛在終端機多工器 session 裡的長期進程。`ps aux` 全列太吵，用兩個角度收斂：

```bash
# 不是從 systemd 起的長期進程：看父進程鏈
ps -eo pid,ppid,user,etime,comm --sort=-etime | head -30

# 有沒有掛著的 tmux / zellij / screen session（要逐一以各使用者身分查）
tmux ls 2>/dev/null; zellij list-sessions 2>/dev/null
```

`etime`（運行時長）長但不在 systemd 清單裡的進程，多半是手動起的。掛在多工器 session 裡的服務是最脆的一種——機器重開就沒了、也沒有任何監控。判斷一個進程「活著」與「由誰提供」的精確方法（`pgrep` 的比對陷阱、busctl 查註冊表），見 [程序、服務與狀態怎麼判](../../debug/process-service-state-diagnosis/)。

## 排程任務藏在哪

第四層是排程：機器在沒人操作的時段自己做什麼。排程任務散落在多個落點，漏看一個就會在某天凌晨被一個「不知道哪來的」任務嚇到。

```bash
# systemd timer（現代發行版的主要排程方式）
systemctl list-timers --all

# cron：每個使用者各有一份 + 系統層多個目錄
sudo ls /var/spool/cron/ && sudo crontab -l -u <user>   # 逐一查每個使用者
cat /etc/crontab
ls /etc/cron.d/ /etc/cron.daily/ /etc/cron.weekly/ /etc/cron.monthly/ 2>/dev/null

# at 佇列（少用但存在）
atq 2>/dev/null
```

每條排程記三件事：跑什麼、多常跑、失敗了會怎樣。第三件通常沒有答案——cron 任務失敗預設只寄 local mail、沒人會看。這是接管後值得優先補的洞，補法見下面「有沒有在監控自己」段。

## 對外開了什麼

第五層是網路面：哪些 port 在聽、對誰開放。listening port 清單是「服務清單」的交叉驗證——一個在聽 port 的進程如果不在你前面盤出的服務清單裡，就是盤點有漏。

```bash
# 在聽的 TCP / UDP port 與對應進程（-p 需要 root 才看得全）
sudo ss -tlnp
sudo ss -ulnp

# 防火牆狀態：依發行版可能是其中一種
sudo nft list ruleset 2>/dev/null | head -50
sudo iptables -L -n 2>/dev/null | head -30
sudo ufw status 2>/dev/null; sudo firewall-cmd --list-all 2>/dev/null
```

判讀時把 listen address 分成三類：`127.0.0.1` 只服務本機、`0.0.0.0`（或 `*`）對所有介面開放、特定 IP 只綁那個介面。對外開放又不認得的 port 優先查——`ss -tlnp` 輸出的進程名回頭對服務清單。防火牆四個指令會有幾個查無結果，這正常：發行版各用不同框架，有輸出的那個才是這台在用的。

## 裝了什麼

第六層是套件面：哪些是刻意裝的、哪些繞過套件管理器直接放進系統。這份清單是之後重建這台機器的素材——[模組八的 bootstrap 套件清單](/linux/dotfile/08-sync-bootstrap/bootstrap-script-packages/) 假設你知道要裝什麼，接手的機器上這份「要裝什麼」得反向盤出來。

```bash
# Arch：明確安裝的（排除被依賴帶進來的）
pacman -Qe
# Debian / Ubuntu
apt-mark showmanual

# 繞過套件管理器的落點
ls /usr/local/bin/ /opt/ 2>/dev/null

# 語言層的全域安裝
pip list --user 2>/dev/null; npm ls -g --depth=0 2>/dev/null
```

`/usr/local/bin` 與 `/opt` 是重點：套件管理器查不到來源的執行檔，只能靠檔名、`--version`、跟 `strings` 猜用途。這些手放的檔案在重裝時最容易遺失——記進清單時同時記「它被哪個服務或排程用到」，孤兒檔案接管後可以清。

## 設定與 secret 落在哪

第七層是設定面：改過哪些系統設定、secret 放在哪裡。這層決定「這台機器能不能被重建」——服務跟套件都能重裝，改過的設定跟 secret 沒盤到就永遠丟了。

```bash
# /etc 下最近被改過的檔案（排 mtime、抓人為改動的痕跡）
sudo find /etc -type f -mtime -365 -newer /etc/hostname 2>/dev/null | head -30

# systemd unit 的 drop-in 覆寫（前人客製服務行為的常見落點）
sudo find /etc/systemd/system -name "*.conf" -path "*.d/*"

# 常見 secret 落點（唯讀列出、內容先不看）
ls -la /home/*/.env /home/*/*/.env 2>/dev/null
ls /home/*/.ssh/ /root/.ssh/ 2>/dev/null
ls /home/*/.config/rclone /home/*/.aws /home/*/.docker 2>/dev/null
```

`/etc` 的 mtime 掃描是啟發式——套件更新也會動 `/etc`，輸出要人工過濾，但它能把「前人改過設定」的範圍從整棵樹縮到幾十個檔案。家目錄的 dotfile 另外看一件事：`ls -la ~ | grep '\->'` 檢查有沒有 symlink 指向某個 repo——有的話代表前人用 [stow 之類的工具](/linux/dotfile/01-dotfile-management/management-strategies/) 管理過設定，找到那個 repo 等於找到大半份文件。secret 的判讀與收斂策略（哪些能進 repo、哪些只能佔位）見 [同步策略與 secret 管理](/linux/dotfile/08-sync-bootstrap/sync-strategy-secret/)。

## 有沒有在監控自己

第八層是監控面：這台機器的服務掛掉時，有沒有人會知道。接手的機器常常答案是「沒有」——前人肉眼盯著，前人走了就沒人盯。

```bash
# 各服務有沒有掛 OnFailure 告警鉤子
systemctl show sshd -p OnFailure
for u in $(systemctl list-unit-files --state=enabled --type=service --no-legend | awk '{print $1}'); do
  echo "$u: $(systemctl show "$u" -p OnFailure --value)"
done

# 有沒有對外心跳（heartbeat timer、healthcheck 打點）
systemctl list-timers | grep -iE 'heart|health|canary'
```

輸出全空代表這台機器掛了不會通知任何人。盤點階段先記錄現況；接管後從最簡單的 OnFailure + 推播建起——至少把 sshd 掛上，它掛了機器就失聯。整套從零建法見 [服務掛了怎麼自動知道](../../debug/service-failure-monitoring/)。

## 盤點完之後

清單在手，用一個問題檢驗盤點品質：**「這台機器現在消失，我能靠這份清單把它重建出來嗎？」** 答不出來的段落回去補。能答之後，接手工作分兩條線走：

- **收斂進版本控制**：把盤出來的套件清單、設定改動、服務定義逐步收進 repo，讓機器狀態從「只存在於這台機器上」變成「可從 repo 重現」。這是 [模組零講的心智模型](/linux/dotfile/00-dotfile-mindset/) 應用在接手情境——差別在素材從盤點來、不是從零設計。
- **補監控與補文件**：監控空白的服務掛 OnFailure、無人知道的排程補失敗告警、盤點清單本身放進 repo 當文件。

機器在雲端的話，OS 層盤完還有帳號層——這台 instance 是誰開的、掛在哪個 VPC、security group 開了什麼，見 [infra 的接手維運模組](/infra/takeover/)。盤點過程中發現已經在壞的狀態（服務起不來、連線異常），從盤點模式切到除錯模式，入口是 [診斷心法](../../debug/diagnosis-read-authoritative-state/)。
