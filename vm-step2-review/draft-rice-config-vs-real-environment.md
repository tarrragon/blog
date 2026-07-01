DRAFT — 待使用者 review + multi-round-review，未過寫作品質關，勿直接發布

建議落點：併進 `content/dotfile/06-rice-design/desktop-shell-components.md`。多數是「修正既有範例 + 補一段環境前提」，不是新文章。逐項標了它對應該文的哪一段。

下面每一塊是一個獨立修正建議。

---

## 修正一：範例字型名要對齊實際裝的字族（對應 Waybar / Mako 的 font 設定）

狀態列、通知、鎖屏的 icon glyph 來自 Nerd Font，但 config 裡的字型名必須跟「系統實際裝進來的字族名」逐字相符，否則 icon 不是 fallback 成別的字、而是直接變豆腐方塊——Nerd Font 的圖示落在 Unicode 私有區（PUA），只有那支字帶這些 glyph，指定一個沒裝的字族，文字排版引擎找不到 PUA glyph 就畫不出來。

該文現行範例用 `JetBrainsMono Nerd Font`，但 dotfile 的套件清單裝的是 `ttf-meslo-nerd`，實際字族名是 `MesloLGS Nerd Font`。兩者要對齊——範例字型改成清單裝的那支，或清單改裝範例用的那支，不能教材一套、套件另一套。確認實裝字族名的指令：

```bash
fc-list | grep -i meslo
# MesloLGSNerdFont-Regular.ttf: "MesloLGS Nerd Font":style=Regular
```

`fc-list` 印的引號內字串就是 config 該填的字族名。

## 修正二：Nerd Font 不含 CJK，中文要另裝 fallback（對應字型前提段，亦關聯模組三字型段）

Nerd Font（MesloLGS、JetBrainsMono 等）的字符集是 Latin + Powerline + 圖示，不含中日韓。桌面上任何 CJK 文字——通知內文、視窗標題、應用程式名、本地化的鎖屏日期——若系統沒有任何 CJK 字型可 fallback，就會整片變豆腐方塊。狀態列的純英數 + icon 不受影響，所以這個坑容易等到「跳出一則中文通知」才現形。

判讀有沒有可用的 CJK 字：

```bash
fc-match ":lang=zh-tw"
# 回一支不含中文的字（如 Adwaita Mono）= 沒有可用的 zh-tw 字、會豆腐
# 回 Noto Sans CJK = fontconfig 有 CJK glyph 可 fallback
```

修法是裝一套 CJK fallback（如 `noto-fonts-cjk`）。裝完不必改各工具 config——文字排版引擎走 fontconfig fallback 自動補字。但有個時序陷阱：**已經在跑的 client 不會自動看到新裝的字型**。像 mako 這類 daemon 在啟動時就把 Pango/fontconfig 的 font map 快取住，`makoctl reload` 只重讀設定檔、不重建 font map，所以「先啟動 daemon、之後才補裝字型」的情況下 reload 完仍是豆腐，得**重啟 daemon**（`pkill mako && mako`）才吃得到新字。正常開機不會遇到——`exec-once` 是在字型都裝好之後才拉 daemon；這個坑只在「系統已在跑、中途補裝字型」的當下除錯時序出現。

一個細節：`fc-match :lang=zh-tw` 可能回 Noto Sans CJK 的韓文排序（KR）優先，靠 Han 統一多數字能顯示，要精確拿到特定地區字形變體得再設 fontconfig 的語言優先序。

## 修正三：通知 daemon 只負責顯示，產生通知要 libnotify（對應 Mako 段）

Mako（以及 Dunst、SwayNC）是通知的「顯示端」——它監看 D-Bus 上的 `org.freedesktop.Notifications` 介面、把收到的通知畫出來，但它自己不產生通知。實際發通知的是應用程式，它們透過 `libnotify` 送上 D-Bus。所以一套能用的通知鏈需要兩半：daemon（顯示）+ libnotify（產生與遞送），缺了 libnotify，連命令列自測的 `notify-send` 都沒有、應用程式也發不出通知。

自測時若手邊沒有 `notify-send`，可用 `gdbus` 直接打介面確認 daemon 端正常：

```bash
gdbus call --session --dest org.freedesktop.Notifications \
  --object-path /org/freedesktop/Notifications \
  --method org.freedesktop.Notifications.Notify \
  "test" 0 "" "標題" "內文" "[]" "{}" 5000
```

但正解是把 `libnotify` 列進套件清單。

## 修正四：Waybar 模組對缺少的硬體自動退化（對應 Waybar 段）

同一份 Waybar config 能同時服務筆電、桌機與 VM，靠的是模組對「缺對應硬體/服務」的自動退化：`battery` 在沒有電池的機器直接隱藏該模組、不報錯也不留空位；`pulseaudio` 在沒有音訊服務時顯示為空；`network` 顯示當下實際在用的介面（VM 裡是有線 `enp0s1`）。所以不必為不同機器維護多份 config——把可能用到的模組都列上，用不到的那台自己消失。判讀依據是 Waybar 啟動 log：

```text
[warning] No batteries.        ← battery 模組自動隱藏
[info] Bar configured (width: 1280, height: 32) for output: Virtual-1
```

附帶一個無害的 log：`Unable to receive desktop appearance: GDBus...ServiceUnknown` 是 Waybar 想透過 portal 問系統的淺/深色偏好、但沒跑 `xdg-desktop-portal`。只影響自動深淺色切換，寫死配色時可忽略。

## 修正五：grim 截圖複製到剪貼簿要明指型別（對應截圖工具段）

`grim - | wl-copy` 把截圖的 PNG bytes 從 stdout 餵給剪貼簿時，`wl-copy` 預設要靠 `xdg-utils` 推斷型別；最小環境沒裝 `xdg-utils` 時，它把 PNG 誤標成 `text/plain`，貼進影像應用程式就拿不到圖。不必為此多裝一個套件，明確告知型別即可：

```bash
grim - | wl-copy --type image/png
wl-paste --list-types   # 應印出 image/png
```

截圖綁定鍵建議直接寫死 `--type image/png`，少一個對環境的隱性依賴。
