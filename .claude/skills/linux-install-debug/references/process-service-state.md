# 程序、服務與狀態怎麼判

判「某東西現在是什麼狀態」最常判錯，多半是問錯來源。每個狀態對到權威來源與正確工具。

## 程式活著沒：比對正確 comm 名

行程表是權威、`pgrep`/`ps` 是對的工具，成敗在**正確的 comm 名**。實測坑：可執行檔叫 `quickshell`、透過 symlink `qs` 啟動時 comm 是 `qs`，`pgrep quickshell` 找不到 → 誤判掛了。

- 先確認實際 comm：`ps -eo pid,comm | grep -i <關鍵字>` 或看啟動指令。
- 精確比對：`pgrep -x <comm>` 或 `pgrep -af <pattern>`（連命令列比對）。
- 別用「你以為的名字」掃過去下生死結論 —— 行程表沒騙你，查詢條件錯。

### 進程活著 ≠ 內部子系統活著

`pgrep` 有輸出只證明「進程存在」，不證明「它在正常運作」。實測坑：一個圖形 shell（如 Quickshell/caelestia）進程活著（`pgrep` 找得到、STAT 正常 `S`、在 `poll`、CPU 不高），但它的 QML scene 因上游錯誤（渲染 pipeline 建失敗）某物件變 null，負責互動的模組全失效 —— bar 畫得出來卻點不動、keybind 叫不出東西，但焦點視窗打字正常。`pgrep` 這時會騙你說「在跑」。

- 權威不是行程表，是**程式自己的 log**，且常不在 `journalctl` / 猜的路徑，要用該程式專屬 log 指令（如 `<shell> -l`）。log 裡 `TypeError: Cannot read property 'X' of null` 類訊息才定案。
- 更精準的活性探針：程式的 **IPC 回不回真實狀態**（正常回資料、子系統死回空）。例：`<shell> ipc call drawers list` 回空 = 子系統死。
- 修法是重啟該 shell 讓 scene 重建（`<shell> -k` + `<shell> -d`）；**驗證看 IPC 回真實資料 + log 不再噴 null，不是看 `pgrep` 又有輸出**（重啟後進程一定在）。
- 上游常是渲染：VM / GL 不足時 shader pipeline 建不起來（log 噴 `Failed to build graphics pipeline state`），非致命地存在、卻可能打斷一次 scene 初始化把互動接線弄死。VM 要確認 GPU 提供的 GL/GLSL 版本夠（virtio-gpu 走 mesa/zink 給 GL 3.3+）。

### 重啟有沒有真的發生：比對 pid + 起始時間

「kill 指令沒報錯 + 之後程式在跑」不等於重啟成功——kill 可能靜默失敗（app 自帶的 `-k`/`stop` 子指令壞掉、錯誤又被 `2>/dev/null` 吃掉），接著新起的實例偵測到舊實例存在就自行退出，結果「重啟前後」一直是同一個 process。實測連錯兩次判斷（把 idle 事件當成重啟後行為）才被拆穿。權威驗證一條：

```bash
ps -o pid,lstart -p $(pgrep -x <comm>)   # 重啟前後各跑一次、pid 與 STARTED 都要變
```

殺不掉時退回通用手段：`pkill -x <comm>`（先 `pgrep -x` 確認 comm 名），再確認新 pid。

## 服務由誰提供：問註冊表

D-Bus name / 監聽 socket 是權威，不是畫面。`org.freedesktop.Notifications` 這種 D-Bus name 同一時間只有一個擁有者（兩個通知 daemon 不能共存，誰先註冊誰佔著）。

```bash
owner=$(busctl --user call org.freedesktop.DBus /org/freedesktop/DBus \
  org.freedesktop.DBus GetNameOwner s org.freedesktop.Notifications | awk '{print $2}' | tr -d '"')
pid=$(busctl --user call org.freedesktop.DBus /org/freedesktop/DBus \
  org.freedesktop.DBus GetConnectionUnixProcessID s "$owner" | awk '{print $2}')
ps -o comm= -p "$pid"
```

停舊 daemon 前擁有者是舊的、停後換新的 = 接管成功。「新的裝了沒作用」常是舊的還佔著名字、新的靜默註冊失敗（只在 log 留 warning）→ 先停舊的。監聽 socket 類似：`ss -lntp` / `lsof -i` 看誰在聽。

## systemd 服務 failed 怎麼判

「服務怪怪的」時，`is-active` 只告訴你 active/inactive，不夠——要看它為什麼失敗、是不是在 restart loop。

- `systemctl status <unit>`：看 `Active:`（`failed` / `activating (auto-restart)` = restart loop）、`Main PID` 的 exit code、最近幾行 log。
- `systemctl is-failed <unit>`：明確判失敗（比 is-active 直接）。
- `journalctl -u <unit> -e`：failed 的真正原因在這（exit code 只是結果）。
- restart loop 徵兆：`status` 顯示 `activating (auto-restart)` 反覆、或 `journalctl` 一直重複同一段啟動→崩潰。根因看 log，不是一直 `restart`。
- `systemctl list-units --failed`：一次列出所有 failed 的 unit（開機後系統怪怪的、先掃這個）。

判讀：服務問題的權威是 `journalctl -u` 的日誌 + `status` 的 exit code / Result，不是「重啟看看好不好」。

### 不想肉眼盯：把失敗變成推播（OnFailure）

被問「服務掛了要不要肉眼看 / 能不能自動告警」時：不用肉眼。systemd 已在追蹤每個 unit 狀態（`systemctl --failed` 是權威清單），監控就是訂閱狀態變化、變壞就推播。分層：

- **原生 `OnFailure` 鉤子（零額外 daemon）**：unit 進 failed 時觸發另一個 unit。做法：`alert@.service`（template、`ExecStart=... %i`）+ 送出腳本（curl ntfy / email）+ 在目標 unit 加 `OnFailure=alert@%n.service`（或放 `service.d/` top-level drop-in 套所有 service）。實測要點：(1) 全域 drop-in 會套到 `alert@` 自己 → 給它清空 `OnFailure=` 擋遞迴；(2) systemd service 環境下 `hostname` 可能回空、用 `uname -n`。
- **先重啟才告警**：`Restart=on-failure` + `StartLimitBurst`/`StartLimitIntervalSec` 先自動重試。實測坑：`OnFailure` **每次失敗都觸發**（含 auto-restart 中途、不是只在放棄時；一個重試 3 次的 crash 觸發 4 次告警）。要「只在終局告警」，送出腳本開頭 gate 掉中途：`state=$(systemctl show <unit> -p ActiveState --value); [ "$state" = failed ] || exit 0`（auto-restart 中途是 `activating`、撞上限才 `failed`）。config 管重試次數、handler gate 管只在終局吵。
- **hung 偵測**：`OnFailure` 抓 crash/exit，抓不到「進程活著但不回應」（systemd 看它還 `active`——同本檔「進程活著 ≠ 子系統活著」）。補一個外部探針：timer 定時 curl 服務的 `/health` 設逾時，逾時 = 那個 check 自己 failed → 一樣走 `OnFailure` 告警。systemd 抓進程死、探針抓進程 hung、兩層互補。
- **canary 驗管線**：養一個可控假服務（極簡 HTTP：`/health` 正常、`/crash` 退出、`/hang` 進程活著不回應）當監控靶子——故意弄掛驗證「失敗→告警」整條通、不必拿 sshd 冒險；它無故告警 = 告警系統本身還活著。防「出事才發現監控早就不會叫」。
- **整台機器死掉的盲點**：`OnFailure` 靠 systemd 觸發，機器當掉 systemd 自己沒了、發不出告警。要體外心跳（dead-man switch：定時 curl healthchecks.io / Uptime Kuma，訊號停由體外告警）。體內方案報不了自己這台的死。
- **推送管道安全**：ntfy 公共站（ntfy.sh）無認證、topic 名就是唯一存取控制——用長隨機字串（猜得到 = 別人能讀你告警 + 發假告警）；敏感或正式用自架（開源、Go binary/docker、可加帳號 ACL）。
- **要指標/門檻**（CPU/磁碟/趨勢，非只 up/down）：Netdata（單機開箱）、Prometheus+Alertmanager（多機）、Monit（每服務檢查+自動動作）。

判準：先分「單一 service 死活 / 整台機器死活 / 資源趨勢」——別拿體內 `OnFailure` 去蓋機器當機（那是它盲點）。

## session 鎖沒鎖：認清是哪一層的鎖

畫面有密碼框 ≠ 鎖了（可能是內嵌鎖屏樣式 widget 的儀表板）。鎖分層、查錯層得誤導答案：

- **logind 層**：`loginctl show-session <id> -p LockedHint`。
- **Wayland 合成器層（`ext-session-lock`）**：跟 logind 獨立，`loginctl` 的 `LockedHint` **查不到**（不是沒鎖，是查錯層）。權威來源是 compositor 的 session-lock 狀態 / 那個 shell 自己的 log（有沒有載入鎖屏模組、idle 計時器有沒有觸發）。

「`loginctl` 沒 LockedHint + `pgrep` 找不到鎖屏程式」不足以斷定沒鎖：合成器層鎖不歸 logind、鎖屏可能由主程式行程內畫（無獨立 process）。

**鎖屏程式死掉的死局 + 復原**：`ext-session-lock` 安全設計 —— 持鎖程式崩潰 / 被殺時 compositor **保持鎖定**（否則殺鎖屏 = 繞過鎖漏洞）。畫面卡在「lockscreen app died」提示。復原（Hyprland）：

1. `hyprctl keyword misc:allow_session_lock_restore 1`（允許新 client 接管孤兒鎖）。
2. `hyprctl dispatch exec hyprlock`（起新鎖屏接管）。
3. 輸密碼解鎖。

紀律：測鎖屏 / `pkill` 持鎖程式時預期它把 session 卡在鎖定 —— 是安全設計不是 bug。無人值守流程避免在持鎖狀態殺鎖屏程式。

## 應用無聲：sink 在不在、stream 有沒有 active

「無聲」的權威來源是音訊伺服器的 graph（`wpctl status`），不是應用有沒有報錯——音訊棧缺件時多數應用**靜默無聲、不報錯**。兩段判讀：

1. **Sinks 段有沒有輸出裝置**：空的 Sinks 常見根因是 pipewire 被依賴鏈拉進來、但 session manager（wireplumber）是獨立套件沒跟著裝——daemon 在跑、graph 卻沒人建。實測：補 `wireplumber pipewire-pulse pipewire-alsa` 後 sink 立刻出現。「pipewire process 活著」不代表音訊棧完整。
2. **Streams 段有沒有該應用的 stream 且 `[active]`**：這是「現在有沒有真的在播」的定案來源——比聽喇叭可靠（喇叭沒聲可能是 host / 硬體側），比看播放器 UI 可靠（UI 在播、stream 沒掛上 = 路由問題）。

把「管線通不通」跟「應用會不會播」拆開驗證：先用本機音檔 `pw-play <file>` 打通管線（stream 出現 `[active]` = guest 側音訊路徑無誤），再驗應用層。應用層失敗就跟管線無關——往 codec / DRM / 應用自己的 log 查。

## 多工器 session 存活

`zellij ls` / `tmux ls` 是權威（多工器常駐遠端、SSH 斷不影響）。機器沒重開 → `attach` 接回；機器重開過 / session 因資源不足（磁碟滿連鎖）被殺 → 顯示 `EXITED` / 不存在，接不回。

**順序紀律**：session 可能已死 + 裡面有在意的產出時，**先確認產出已保存再處理 session**。任務在改 git repo → 先 `git -C <repo> status` + `git log @{u}..`（本地有遠端沒有的 commit）確認 / 推送，再 `zellij delete` 清死 session。搞反順序可能失去唯一記得那些改動的地方。

## 卡住是資源還是相容：先看資源

耗時操作停住時別直接跳「不相容 / 跑不起來」（昂貴結論）。先讀最廉價的權威：`df -h`（磁碟滿？）、`free`（記憶體？）。實測：原始碼編譯停在半路，是宿主磁碟寫滿把 build 打斷，清空間後同份 source 接著編就過，跟相容性無關。先排除資源，再懷疑相容。（區隔：只有「這一個操作」卡住 → 看這裡；「連線斷 + 任務失敗 + 服務怪」一串同時發生 → machine-unreachable 的磁碟滿 / fs 唯讀連鎖。）

## 權限被拒（EACCES）：讀是哪一層擋的，別一律 sudo

`Permission denied` / `EACCES` / `Operation not permitted` 有多個根因，`sudo` 蓋過去會掩蓋真正的層別、還可能在 home 留 root-owned 檔製造新問題。先讀哪一層：

- **檔案本身 mode / owner**：`ls -l`、`stat` 看 owner/group/mode；`id` / `groups` 看你在不在對的 group。
- **路徑中間某層無 x 權限**：`namei -l <path>` 逐段列出路徑每一層的權限——最常被忽略的坑（檔案本身可讀，但父目錄少 x，整條就進不去）。這是「讀權威狀態」對 permission 的專用工具，AI 幾乎不會主動用。
- **缺 sudo 授權**：`sudo -l` 看被允許跑什麼。
- **檔案系統唯讀**：只有寫入 EACCES → `mount | grep -w ro`（見 [machine-unreachable](machine-unreachable.md)）。
- **MAC（SELinux / AppArmor）擋**：mode/owner 都對卻 denied → `ausearch -m avc`（SELinux）/ `aa-status`（AppArmor）；Fedora/RHEL/Ubuntu 常見，Arch 預設無。
- **capability 不足**：`getcap <binary>`（如非 root 綁 port <1024）。

判讀：`namei -l` + `stat` + `id` 三個先分掉大部分；mode 全對卻還 denied 才往 MAC / capability 查。

## 被 kill / OOM / exit 137：查 kernel log

程式無錯誤訊息就消失、或 systemd 顯示 `Killed` / `OOMKilled` / exit code 137（128+9=SIGKILL），userspace log 看不到原因——權威在 kernel ring buffer：`dmesg -T | grep -iE 'killed process|oom'`、`journalctl -k -b`。OOM killer 殺行程、I/O error、段錯誤都在這裡。

## 快速路由

| 判斷         | 權威來源 / 工具                                                 |
| ------------ | --------------------------------------------------------------- |
| 程式活著沒   | `pgrep -x <正確 comm>` / `pgrep -af`                            |
| 進程活著但沒運作 | 程式自己的 log（專屬指令 `<shell> -l`、不在 journalctl）+ IPC 回真實狀態；別信 `pgrep` |
| 服務歸誰     | `busctl` GetNameOwner→PID→comm / `ss -lntp`                     |
| 鎖沒鎖       | logind：`loginctl LockedHint`；合成器層：compositor / shell log |
| 鎖屏死局     | `allow_session_lock_restore 1` + 起新鎖屏接管                   |
| session 存活 | `zellij ls` / `tmux ls`；先保產出再清                           |
| 卡住原因     | `df -h` / `free` 先排資源，再懷疑相容                           |
| 應用無聲     | `wpctl status`：Sinks 空 = 棧缺件；stream `[active]` = 真在播   |
