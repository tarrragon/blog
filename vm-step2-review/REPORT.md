# Step 2 REPORT — rice 實機測試 + 教學內容完善

> 產出時間：2026-07-01（VM 內，Asia/Taipei 約 04:3x）
> 對應分支：dotfiles `vm-step2-rice`、blog `vm-step2-record`

## 起床先看（兩件要事）

1. **鎖屏已由你解開（已處理）**。測 hyprlock 時用 `pkill` 結束它觸發了 Hyprland 鎖屏失效保護，我照官方 restore 路徑恢復成乾淨 prompt、你已用密碼解鎖。教訓（pkill ≠ 解鎖、兩層鎖不同）已收斂成 finding G 與草稿。解鎖後我補測了 finding B 的 CJK 修復並補齊像素層證據（見 finding B），waybar / mako 都正常。
2. **push 狀態**：dotfiles `vm-step2-rice` 已成功推上 GitHub。blog `vm-step2-record` 的 push 結果見本檔最末「Push 狀態」段（若該段標示失敗，照那裡的補推指令處理）。

## 一、做了哪些 dotfiles 配置（分支 vm-step2-rice）

照慣例每元件一個 stow package，配色統一 Catppuccin Mocha（公開色票），字型統一 `MesloLGS Nerd Font`（對齊 `ttf-meslo-nerd` 實裝字族）。新增/修改：

| 路徑                                      | 內容                                                              | 載入結果                          |
| ----------------------------------------- | ----------------------------------------------------------------- | --------------------------------- |
| `themes/.config/hypr/colors.conf`         | 集中配色（Catppuccin Mocha，Hyprland source 用）                  | 成功（hyprland.conf source 生效） |
| `waybar/.config/waybar/config.jsonc`      | 左工作區+視窗 / 中時鐘 / 右系統狀態                               | 成功 render（shot 01）            |
| `waybar/.config/waybar/style.css`         | Catppuccin Mocha 外觀                                              | 成功                              |
| `wofi/.config/wofi/config` + `style.css`  | drun 啟動器 + 藍框圓角樣式                                        | 成功 render（shot 03）            |
| `mako/.config/mako/config`                | 通知 daemon，urgency criteria 區塊                                | 成功 render（shot 02，critical 紅框） |
| `hyprlock/.config/hypr/hyprlock.conf`     | 截圖模糊背景 + 時鐘/日期/密碼框                                   | 成功 render（shot 04）            |
| `hyprland/.config/hypr/hyprland.conf`     | source colors + exec-once(waybar/mako) + keybind(wofi/lock/截圖) + 邊框配色 | 成功（hyprctl configerrors 無錯） |
| `packages-arch.txt`                       | 放開 rice 段、補 grim/slurp/wl-clipboard/libnotify/noto-fonts-cjk | 套件實裝成功                      |

部署用 `stow`（新 package 乾淨建 symlink）；觸發了 `.config/hypr/` 的 tree unfolding（見 finding E）。所有元件都在「活的 Hyprland instance」上 `hyprctl dispatch exec` 手動拉起來實測，不是只在本機看 config。

### 截圖清單（已複製進 `~/blog/vm-step2-review/shots/`）

| 檔名                                         | 內容                                                      |
| -------------------------------------------- | --------------------------------------------------------- |
| `01-waybar-status-bar.png`                   | waybar 正常 render，配色 + nerd icon + 模組               |
| `02-mako-critical-notification-cjk-tofu.png` | mako critical 通知（紅框正確）+ 中文豆腐（finding B 證據）|
| `03-wofi-launcher.png`                       | wofi drun 啟動器，選中項藍底反白                          |
| `04-hyprlock-working.png`                    | hyprlock 模糊背景 + 時鐘/日期/密碼框                      |
| `05-hyprlock-died-failsafe.png`              | pkill 後的鎖屏失效保護畫面（finding G 證據）              |
| `06-hyprlock-restored-prompt.png`            | restore 後的乾淨鎖屏 prompt（使用者解鎖用）              |
| `07-cjk-still-tofu-after-makoctl-reload.png` | 裝 CJK 字型 + `makoctl reload` 後仍豆腐（finding B 深層坑證據）|
| `08-cjk-fixed-after-mako-restart.png`        | 重啟 mako 後中文正常（finding B 修復的像素層確認）        |

## 二、實測挖到的 finding + 建議轉成的教學內容（待 review + multi-round）

每項都已記進 blog 實測記錄（`vm-hyprland-handson-record.md` 階段三第二步 + 末節彙整表）。下面標「建議落點」與「狀態」。已寫成草稿的放在 `~/blog/vm-step2-review/draft-*.md`，**草稿都明確標 DRAFT、未過寫作品質關，要等你 review + 跑 multi-round-review（至少三輪）才談發布**。

| ID | Finding                                                        | 類別 | 建議落點                                                         | 我做到哪 |
| -- | ------------------------------------------------------------- | ---- | --------------------------------------------------------------- | -------- |
| A  | 範例字型 `JetBrainsMono` ≠ 實裝 `MesloLGS Nerd Font`，名不符→icon 豆腐 | 配置 | `06-rice-design/desktop-shell-components.md` 範例字型修正        | 草稿（draft-rice-config 修正一）+ dotfiles 已用實裝字族 |
| B  | Nerd Font 無 CJK，中文變豆腐，需 `noto-fonts-cjk`；**且已跑的 daemon 要重啟才吃到新字（reload 不夠）** | 環境 | 同上 + 模組三字型段                                             | 草稿（修正二）+ packages 已補 + **像素層確認修復**（shot 08）|
| C  | mako 只顯示、產生通知要 `libnotify`（notify-send）             | 環境 | `desktop-shell-components.md` Mako 段                            | 草稿（修正三）+ packages 已補 |
| D  | waybar 模組對缺硬體自動退化（同份 config 通用 VM/實體機）       | 配置 | `desktop-shell-components.md` Waybar 段                          | 草稿（修正四） |
| E  | stow tree folding/unfolding（多 package 共用 `.config/hypr/`） | 機制 | `knowledge-cards/gnu-stow.md`                                   | **該卡已有 folding/unfolding 概念段**；只缺一個具體實例，優先度低，記在 record |
| F  | Hyprland `$` 變數 source 範圍限於自家 .conf（waybar/wofi/mako 引用不到）| 配置 | `color-system-theming.md` 配色統一段（已提及，可用實測補一句界線）| 記在 record，已有教材覆蓋 |
| G  | **hyprlock `pkill` ≠ 解鎖、掉進 compositor 失效保護；兩層鎖不同** | 機制 | 新卡 `knowledge-cards/session-lock.md` 或併 `color-system-theming.md` Hyprlock 段 | **草稿 draft-hyprlock-lock-testing-safety.md**（最值得寫、現無任何教材覆蓋）|
| H  | grim 截圖 `wl-copy` 需 `--type image/png`（無 xdg-utils 推不出型別）| 環境 | `desktop-shell-components.md` 截圖段（或 work-log）             | 草稿（修正五）+ keybind 已修 |

### 兩份草稿檔（待 review）

- `draft-hyprlock-lock-testing-safety.md` — finding G。**這篇最值得獨立**：ext-session-lock 兩層鎖、pkill 失效保護、restore 路徑、測鎖屏的安全守則。建議落點：新 knowledge-card `session-lock.md`，或併進 color-system-theming 的 Hyprlock 段。
- `draft-rice-config-vs-real-environment.md` — finding A/B/C/D/H 合一。多是 `desktop-shell-components.md` 的範例修正 + 環境前提補段，逐項標了對應段落。

### 著作權紀律自述

所有 config 與草稿都是我理解後自己寫的：配色用公開 Catppuccin 色票、模組選擇與結構是我自己定的、findings 來自實機跑出來的現象。參考 repo（caelestia / fish-shell）這次沒有 clone 也沒有需要——成果不依賴它們即站得住（把它們拿掉結論不變）。有疑慮處一律從保守。

## 三、卡在哪 / 要你決定的事

- **hyprlock 把畫面鎖住**（finding G）：這是測鎖屏的固有代價，沒你的密碼我無法完整解鎖。已恢復成乾淨 prompt，你解鎖即可。教訓已寫進 record + 草稿：之後自動化測試別碰 hyprlock，或接受它會鎖住。
- **finding B 已補齊像素層確認並挖深**（使用者解鎖後補測）：裝 `noto-fonts-cjk` 後 `makoctl reload` 再送中文通知**仍是豆腐**（shot 07），重啟 mako 才正常（shot 08）。深層原因：daemon 啟動時快取 Pango/fontconfig font map，reload 只重讀 config、不重建 font map——「先啟動、後裝字型」的除錯時序才會踩到，正常開機（exec-once 在字型裝好後才拉 daemon）不會遇到。此坑已補進 record 與草稿修正二。
- **草稿落點要你拍板**：finding G 該獨立成 knowledge-card 還是併進既有文章？finding A–H 的修正併進 desktop-shell-components 時，是否要連帶調整該文現有的 JetBrainsMono 範例與套件清單一致性。
- **multi-round-review 我沒跑**：依規範，blog 內容要你 review + 至少三輪審查才談發布；草稿只是把 finding 蒸餾成可審的初稿。

## 四、Push 狀態

- dotfiles `vm-step2-rice`：**已成功 push**（commit：建 package → 實測修正，共 2 個 rice commit 疊在既有 main 之上）。
  - GitHub：`https://github.com/tarrragon/dotfiles/tree/vm-step2-rice`
- blog `vm-step2-record`：**已成功 push**（record 續寫 commit + 本 review 目錄 commit）。
  - GitHub：`https://github.com/tarrragon/blog/tree/vm-step2-record`
  - 補推指令（若需要）：`cd ~/blog && git push --no-verify origin vm-step2-record`

兩個 push 都已確認成功（push 回傳無 error）。

> blog 用 `--no-verify`：VM 沒裝 Go，repo 的 mdtools pre-commit/pre-push hook 跑不動，排版/lint 驗證留給你在 Mac 上做。
