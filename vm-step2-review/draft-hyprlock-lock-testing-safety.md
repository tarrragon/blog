DRAFT — 待使用者 review + multi-round-review，未過寫作品質關，勿直接發布

建議落點（二選一，使用者決定）：

- A. 新 knowledge-card：`content/dotfile/knowledge-cards/session-lock.md`（atomic 概念卡：ext-session-lock 兩層鎖）
- B. 併進 `content/dotfile/06-rice-design/color-system-theming.md` 的 Hyprlock 段，當「測試與恢復」子段

下面是草稿內文（未套 frontmatter，發布前依落點補）。

---

## 鎖屏是「compositor 持有的安全狀態」，不是一個可隨手關掉的視窗

鎖屏工具（Hyprlock、Swaylock）跟一般應用程式的生命週期不同：它一旦啟動，桌面的「鎖定」狀態就由 compositor 透過 Wayland 的 `ext-session-lock-v1` 協議持有，唯一的正常出口是鎖屏 client 通過認證後主動呼叫 `unlock_and_destroy` 解鎖。理解這條，才不會把鎖屏當成「砍掉 process 就回到桌面」的普通視窗——砍掉它反而讓畫面卡在 compositor 的失效保護狀態。

這個責任邊界在自動化測試、VM 演練、遠端操作時最容易出事，因為這些情境常用「殺 process」當「關掉一個東西」的通用手段。

## 兩層鎖是不同的東西

判讀鎖屏狀態時要分清楚兩個獨立的層，它們的值可以不一致：

| 層            | 由誰持有           | 怎麼看                                     | 代表什麼                         |
| ------------- | ------------------ | ------------------------------------------ | -------------------------------- |
| logind 會話鎖 | systemd-logind     | `loginctl show-session <id> -p LockedHint` | 會話的鎖定提示，給 DM/螢幕保護用 |
| 合成器會話鎖  | Wayland compositor | 畫面是否進得去、鎖屏 surface 是否在最上層  | 實際擋住畫面的那層               |

實測會遇到 `LockedHint=no`（logind 那層說沒鎖）但畫面仍進不去的矛盾——因為擋住畫面的是 compositor 的 `ext-session-lock`，跟 logind 的提示是兩回事。只看 `LockedHint` 會誤判成「已解鎖」。要判斷畫面到底進不進得去，看 compositor 層，不是看 logind 層。

## 砍掉鎖屏 client 會掉進失效保護畫面

鎖屏 client 在持有鎖的狀態下死掉（被 `kill`、crash），compositor 不會自動解鎖——它沒有「認證通過」這個信號，只能維持鎖定並顯示失效保護畫面，告訴使用者「鎖屏 app 死了、但畫面還鎖著」。Hyprland 的失效保護畫面會直接給恢復指令：

```text
hyprctl --instance 0 'keyword misc:allow_session_lock_restore 1'
hyprctl --instance 0 'dispatch exec hyprlock'
```

`allow_session_lock_restore` 的作用是允許「新的鎖屏 client 接管既有的鎖」，否則新 client 會因為「已經鎖了」而被拒。接管後是一個乾淨的鎖屏 prompt，使用者用密碼正常解鎖。

## 操作判準

- **測試前先想好怎麼回得來**：鎖屏的唯一正常出口是認證解鎖。動手測之前，先確認自己知道密碼，或準備好走 restore 路徑（另一個 TTY + `allow_session_lock_restore`）。
- **別用殺 process 當「關掉鎖屏」**：那不是解鎖，是讓畫面卡進失效保護。
- **判讀鎖定狀態看 compositor 層**：`LockedHint` 是 logind 的提示、可能跟畫面實際狀態不一致。
- **沒有密碼就無法完整解鎖是設計、不是故障**：鎖屏的價值就在這裡。自動化流程若會啟動鎖屏，要把「畫面會留在鎖定、需人工解鎖」算進代價，別預期能程式化解開。
- **下一步路由**：鎖屏配置本身（背景、輸入框、時鐘 label）見 rice 模組的鎖屏段；會話與登入管理見對應的桌面維運主題。

## 反例與邊界

並非所有「鎖屏死掉」都需要 restore 路徑：若鎖屏是被正常認證解鎖（走 `unlock_and_destroy`）後才結束，compositor 已回到非鎖定狀態，不會有失效保護。失效保護只在「持鎖中非正常結束」時出現。另外，不同 compositor 對「鎖屏 client 死掉」的處理策略可能不同——這裡描述的是 Hyprland 的行為，換 compositor 要重新確認，但「鎖是 compositor 持有、解鎖要認證」這條是 `ext-session-lock` 協議層的共通約束。
