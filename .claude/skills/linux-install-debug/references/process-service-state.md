# 程序、服務與狀態怎麼判

判「某東西現在是什麼狀態」最常判錯，多半是問錯來源。每個狀態對到權威來源與正確工具。

## 程式活著沒：比對正確 comm 名

行程表是權威、`pgrep`/`ps` 是對的工具，成敗在**正確的 comm 名**。實測坑：可執行檔叫 `quickshell`、透過 symlink `qs` 啟動時 comm 是 `qs`，`pgrep quickshell` 找不到 → 誤判掛了。

- 先確認實際 comm：`ps -eo pid,comm | grep -i <關鍵字>` 或看啟動指令。
- 精確比對：`pgrep -x <comm>` 或 `pgrep -af <pattern>`（連命令列比對）。
- 別用「你以為的名字」掃過去下生死結論 —— 行程表沒騙你，查詢條件錯。

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

## 多工器 session 存活

`zellij ls` / `tmux ls` 是權威（多工器常駐遠端、SSH 斷不影響）。機器沒重開 → `attach` 接回；機器重開過 / session 因資源不足（磁碟滿連鎖）被殺 → 顯示 `EXITED` / 不存在，接不回。

**順序紀律**：session 可能已死 + 裡面有在意的產出時，**先確認產出已保存再處理 session**。任務在改 git repo → 先 `git -C <repo> status` + `git log @{u}..`（本地有遠端沒有的 commit）確認 / 推送，再 `zellij delete` 清死 session。搞反順序可能失去唯一記得那些改動的地方。

## 卡住是資源還是相容：先看資源

耗時操作停住時別直接跳「不相容 / 跑不起來」（昂貴結論）。先讀最廉價的權威：`df -h`（磁碟滿？）、`free`（記憶體？）。實測：原始碼編譯停在半路，是宿主磁碟寫滿把 build 打斷，清空間後同份 source 接著編就過，跟相容性無關。先排除資源，再懷疑相容。

## 快速路由

| 判斷         | 權威來源 / 工具                                                 |
| ------------ | --------------------------------------------------------------- |
| 程式活著沒   | `pgrep -x <正確 comm>` / `pgrep -af`                            |
| 服務歸誰     | `busctl` GetNameOwner→PID→comm / `ss -lntp`                     |
| 鎖沒鎖       | logind：`loginctl LockedHint`；合成器層：compositor / shell log |
| 鎖屏死局     | `allow_session_lock_restore 1` + 起新鎖屏接管                   |
| session 存活 | `zellij ls` / `tmux ls`；先保產出再清                           |
| 卡住原因     | `df -h` / `free` 先排資源，再懷疑相容                           |
