---
title: "Caelestia 配置"
date: 2026-06-29
description: "安裝完 Caelestia 後要客製化設定時回來讀"
weight: 5
tags: ["dotfile", "rice", "caelestia", "quickshell", "hyprland"]
---

`~/.config/caelestia/` 下有兩類檔案：使用者層的 JSON 配置（`shell.json`、`cli.json`）控制功能和外觀，token 層（`shell-tokens.json`）控制細部視覺數值——間距、圓角、字型大小、動畫曲線。`shell.json` 修改後 Quickshell 自動 reload、不需要重啟（VM 實測：跑著的實例會即時吃到檔案變更、驗證後重新序列化回檔案）。配色（scheme）的熱套用是另一個獨立的 watcher、有啟動時序前提，見下方配色段。

## 配置檔路徑

| 路徑                                                    | 用途                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| `~/.config/caelestia/shell.json`                        | 主配置（使用者自建，不會自動產生）                       |
| `~/.config/caelestia/shell-tokens.json`                 | 進階視覺 token（rounding、spacing、padding、字型、動畫） |
| `~/.config/caelestia/monitors/<name>/shell.json`        | 每螢幕覆寫（螢幕名稱用 `hyprctl monitors` 查）           |
| `~/.config/caelestia/monitors/<name>/shell-tokens.json` | 每螢幕 token 覆寫                                        |
| `~/.config/caelestia/hypr-user.lua`                     | 自定義 Hyprland 設定（Lua 格式）                         |
| `~/.config/caelestia/hypr-vars.lua`                     | Hyprland 變數覆寫                                        |
| `~/.config/caelestia/cli.json`                          | CLI 工具配置（主題目標、icon theme、workspace toggle）   |
| `~/.config/caelestia/templates/`                        | 自定義色彩模板，語法 `{{ primary.hex }}`                 |
| `~/.face`                                               | 個人頭像（Dashboard 用）                                 |
| `~/Pictures/Wallpapers`                                 | 預設桌布目錄（可在 paths section 改）                    |

`shell.json` 不會在安裝時自動產生——預設行為由 Caelestia 內建值決定。你只需要建立這個檔案、寫入你想覆寫的 section。未寫的 section 使用預設值。

## shell.json 結構

shell.json 的 top-level section 對應桌面 shell 的各個元件和全域設定：

### 全域設定

| Section      | 控制什麼                                                              |
| ------------ | --------------------------------------------------------------------- |
| `enabled`    | 各元件的啟用 / 停用主開關                                             |
| `appearance` | 全域視覺：deformScale、rounding、spacing、padding、字型、動畫、透明度 |
| `general`    | Logo 圖片路徑、app 路徑、閒置逾時秒數、低電量警告門檻                 |
| `services`   | 天氣服務、時間格式、GPU 類型（AMD/NVIDIA/Intel）、音訊後端            |
| `paths`      | 桌布目錄、歌詞目錄、assets 目錄的自定義路徑                           |

### 元件設定

| Section      | 控制什麼                                                         |
| ------------ | ---------------------------------------------------------------- |
| `bar`        | 狀態列：persistent toggle、工作區顯示、active window、tray、時鐘 |
| `background` | 桌布設定、桌面時鐘、音訊視覺化                                   |
| `dashboard`  | 媒體播放器、效能指標（CPU/GPU/RAM）、天氣                        |
| `launcher`   | 應用程式搜尋、動作列表、桌布選擇                                 |
| `lock`       | 鎖屏：指紋認證開關、logo 重新配色                                |
| `notifs`     | 通知：過期時間、分組邏輯                                         |
| `osd`        | 音量 / 亮度變更的螢幕顯示                                        |
| `session`    | 登出 / 關機 / 重啟選單                                           |
| `sidebar`    | hover 行為、快速開關（WiFi、藍牙、暗色模式）                     |
| `nexus`      | 設定介面                                                         |
| `utilities`  | Toast 通知、VPN 開關、其他快速操作                               |
| `border`     | 視窗邊框：thickness、rounding、smoothing                         |

### 範例：常見客製化

```json
{
    "bar": {
        "persistent": true,
        "workspaces": {
            "shown": 9
        },
        "clock": {
            "format": "%H:%M"
        }
    },
    "notifs": {
        "expiration": 8000
    },
    "paths": {
        "wallpapers": "~/Pictures/MyWallpapers"
    },
    "services": {
        "gpu": "amd",
        "time": {
            "format24h": true
        }
    }
}
```

**Key 要對著實際版本驗**：caelestia-shell 啟動時會改寫 shell.json、丟掉 schema 不認得的 key、只留有效子集（VM 實測 2.1.0：某次測試輸入裡 `bar.clock.format`、`notifs.expiration`、`services.*` 被丟掉；`bar.persistent`、`workspaces.shown`、`sidebar`、`general.idle` 屬有效 key 而留下——留下的集合視你寫進去的 key 而定、不是固定兩個）。寫覆寫檔後啟動 shell、再回頭看檔案剩什麼，就是這個版本的有效 schema——被丟掉的 key 代表該功能在這版不存在或搬了位置，去 token 或別的 section 找。schema 的權威來源是安裝進來的 `/usr/lib/qt6/qml/Caelestia/Config/caelestia-config.qmltypes`（config 編在 C++ plugin 裡、QML 原始碼查不到）。

一個經 2.1.0 驗證的實用例——idle 鎖屏時間（預設 3 分鐘鎖、10 分鐘關螢幕）延長到 2 小時：

```json
{
    "general": {
        "idle": {
            "timeouts": [
                {
                    "timeout": 7200,
                    "idleAction": "lock"
                }
            ]
        }
    }
}
```

## Token 系統

`shell-tokens.json` 控制的是比 `shell.json` 更細粒度的視覺數值：

- 每個元件的 rounding（圓角半徑）
- 各區域的 spacing 和 padding
- 各類別文字的 font size
- 動畫的 duration 和 easing curve
- 元件的固定尺寸

官方的說法是：「Do NOT change any of these options if you do not know what you are doing.」這個警告的實際意義是——token 之間有隱含的依賴關係（某個 padding 值跟某個 rounding 值配合才好看），隨意改一個可能讓整體視覺走樣。而且 token 的名稱和結構可能在版本更新時變動，沒有向後相容承諾。

務實的做法是先不動 token，用 `shell.json` 做功能層面的客製化。等到你有明確的視覺需求（例如想把所有圓角改更大），再查 token 文件做精確調整。

## 自定義 Hyprland 設定

Caelestia 管理自己的 Hyprland 配置。你的自訂設定放在 `hypr-user.lua`（不是直接改 hyprland.lua）：

```lua
-- ~/.config/caelestia/hypr-user.lua

-- 額外的 keybind
hl.bind("SUPER", "Return", "exec", "foot")

-- monitor 配置
hl.config({
    monitor = {
        "DP-1, 2560x1440@144, 0x0, 1",
        "HDMI-A-1, 1920x1080@60, 2560x0, 1",
    },
})

-- 額外的 window rules
hl.config({
    windowrule = {
        "workspace 8, class:^(firefox)$",
    },
})
```

**這裡的 Lua 是 Caelestia 的封裝、不是 Hyprland 本體**：Hyprland 本體用的是自有的 hyprlang `.conf` 格式（`monitor = , preferred, auto, 1` 那種），並沒有改成 Lua。Caelestia 在上面加了一層 Lua wrapper（`hl.bind` / `hl.config`）來管理 Hyprland 設定，所以自訂才寫在 `hypr-user.lua`。如果手上有舊的 `hypr-user.conf`，要轉成 Caelestia 這層的 Lua 格式；轉換工具 `hyprlang2lua`（Go）或 `hyprconf2lua`（Python pip）。直接改 `~/.config/hypr/hyprland.conf` 那套 hyprlang 語法在 Caelestia 的封裝下不會生效。

## 配色與主題

Caelestia 的配色系統用 Material Design 3 的動態取色——從桌布圖片自動提取色彩，產生一套 primary / secondary / surface / error 色系，套用到所有元件。

```bash
# 設定桌布並觸發動態取色
caelestia wallpaper -f ~/Pictures/Wallpapers/mountain.jpg

# 手動切換配色方案
caelestia scheme set -n dynamic    # 動態（從桌布取）
caelestia scheme set -n catppuccin # 如果有對應 template
```

自定義配色模板放在 `~/.config/caelestia/templates/`，用 `{{ primary.hex }}`、`{{ surface.hex }}` 等變數。Caelestia 會在切換桌布時用新的色系填入這些變數，產生對應的配置檔。

**Scheme 熱套用的啟動時序前提**（兩台 VM 各實測一次、行為一致）：shell 對 `~/.local/state/caelestia/scheme.json` 的 file watcher 只在**啟動當下檔案已存在**時建立。首次安裝、從未 `scheme set` 過的機器上，第一個 shell 實例啟動時 state 檔還不存在——之後下 `scheme set` 會寫入 state、CLI 回報也正確，但跑著的 UI 不變色。修法：`scheme set` 建好 state 檔後重啟一次 shell；那之後同一實例的配色切換都即時生效、不用再重啟。

**重啟 shell 用 `pkill -x qs`**：`caelestia shell -k` 可能靜默失敗（實測 CLI 1.1.1：指令回傳正常但 process 沒死、新起的實例偵測到舊實例就自行退出——看起來重啟了、實際同一個實例一直活著）。驗證重啟是否真的發生，比對 `ps -o pid,lstart -p $(pgrep -x qs)` 的 pid 與起始時間，別只看指令沒報錯。process 名是 `qs`（`/usr/bin/qs` 是 quickshell 的 symlink）、`pgrep caelestia` 找不到它。

## 不要改 AUR 安裝的檔案

AUR package（`caelestia-shell`）安裝的檔案在系統路徑下，更新時會被覆蓋。所有客製化都應該放在 `~/.config/caelestia/`，Caelestia 會優先讀取使用者路徑的配置，沒有的才 fallback 到系統預設。

## 已知問題

**Config 靜默破壞**：Caelestia 的 token 名稱和配置結構可能在版本更新時變動，不會事先通知。更新後如果 shell 行為異常，先檢查 `shell-tokens.json` 裡的 key 是否還存在。

**Notification backlog**：Shell 可能因為積累大量通知而變卡。清除：

```bash
caelestia shell notifs clear
```

**quickshell-git 必須**：穩定版的 quickshell 缺少 Caelestia 需要的 API。如果裝了穩定版，shell 會啟動失敗或功能不完整。確認用的是 `quickshell-git`：

```bash
pacman -Q quickshell-git
```

**工作區切換卡頓**：在某些 GPU / 驅動組合下報告過隨機卡頓。排查方向：關閉 VRR（`vrr = 0`）、減少 blur passes、檢查 GPU 驅動版本。

## Dotfile Repo 結構對應

Caelestia 的配置只追蹤覆寫用的檔案（`shell.json`、`cli.json`、`hypr-user.lua`），AUR package 安裝的原始檔案不進 repo：

```text
~/dotfiles/
└── caelestia/
    └── .config/
        └── caelestia/
            ├── shell.json
            ├── shell-tokens.json   # 如果有自訂
            ├── cli.json
            ├── hypr-user.lua
            ├── hypr-vars.lua       # 如果有自訂
            └── templates/          # 如果有自訂配色模板
```

monitor 專屬的覆寫（`monitors/<name>/`）是硬體相關的，跟 [Hyprland 的 monitor 設定](/linux/dotfile/05-hyprland-config/hyprland-core-config/)一樣，可能需要排除在 Git 外或用 template/local 機制處理。

**Runtime 寫入會穿透 stow 的目錄 symlink 弄髒 repo**：用 stow 部署時 `~/.config/caelestia` 常是折疊的目錄 symlink、指向 repo 裡的 package 目錄，而 caelestia-shell 會在執行期往自己的 config 目錄寫（啟動時建 `monitors/`、改寫 `shell.json`）——這些寫入直接落進 dotfiles repo、`git status` 變髒（btop 往 `themes/` 寫也是同一型）。配套：repo 的 `.gitignore` 把「app 會自己寫的路徑」列入（`caelestia/.config/caelestia/monitors/` 等），shell.json 被改寫後 diff 一下、把有效 schema 的版本 commit 回去。

## VM 測試 vs 實機測試

> **[VM 可測試]** shell.json 配置語法、各 section 的效果（bar 模組顯示、launcher 搜尋行為、通知過期邏輯）、CLI 指令執行、hypr-user.lua 載入、配色方案切換指令。

> **[需實機測試]** token 微調的視覺效果（間距和圓角的差異在軟體渲染下難以判讀）。動畫流暢度、blur 效能、動態取色品質、多螢幕佈局、日常穩定性等視覺與效能項目見 [Caelestia 安裝](/linux/dotfile/06-rice-design/caelestia-installation/)的對應段落。
