---
title: "Lua 腳本語言"
date: 2026-06-29
description: "在 Hyprland 或 Neovim 配置檔遇到 Lua 語法看不懂時回來讀 — 配置檔需要的最小 Lua 知識"
weight: 1
tags: ["dotfile", "lua", "knowledge-cards"]
---

Lua 是一個輕量級腳本語言，1993 年在巴西開發，名字是葡萄牙語的「月亮」。整個直譯器約 300KB，設計目標是**嵌入到其他程式當配置和擴展語言**，不是當獨立的通用語言。

Hyprland（v0.55+ 的配置格式）、Neovim（整個 plugin 和配置生態）、WezTerm（terminal emulator 配置）都用 Lua 作為配置語言。在 dotfile 管理的脈絡裡，Lua 是讀懂和寫好這些工具配置的前提知識。

## 配置檔用到的核心語法

### 變數和型別

```lua
local name = "hello"       -- 字串
local count = 42            -- 數字
local enabled = true        -- 布林
local nothing = nil         -- 空值（類似其他語言的 null）
```

`local` 宣告區域變數。沒有 `local` 的變數是全域的，配置檔裡幾乎都該用 `local`。

### Table：唯一的複合資料結構

Lua 只有一種複合型別——table，同時當 array 和 dictionary 用：

```lua
-- 當 array（index 從 1 開始，不是 0）
local fruits = { "apple", "banana", "cherry" }
print(fruits[1])  -- "apple"

-- 當 dictionary
local config = {
    gaps_in = 5,
    border_size = 2,
    layout = "dwindle",
}
print(config.gaps_in)  -- 5

-- 巢狀 table（配置檔最常見的形式）
local decoration = {
    rounding = 8,
    blur = {
        enabled = true,
        size = 5,
        passes = 2,
    },
}
```

Hyprland 的 `hl.config()` 接收的就是一個巢狀 table：

```lua
hl.config({
    general = {
        gaps_in = 5,
        gaps_out = 10,
    },
    decoration = {
        rounding = 8,
    },
})
```

### Function

```lua
local function greet(who)
    return "hello " .. who   -- .. 是字串串接
end

-- 匿名 function（Neovim 配置常見）
vim.keymap.set("n", "<leader>f", function()
    require("telescope.builtin").find_files()
end)
```

### 條件判斷

```lua
if hostname == "work-laptop" then
    -- 工作機設定
elseif hostname == "home-desktop" then
    -- 家裡桌機設定
else
    -- 預設
end
```

只有 `nil` 和 `false` 是 falsy。`0` 和 `""` 是 truthy（跟 Python 不同）。

### 迴圈

```lua
-- 數字 for（Hyprland 批次產生 workspace keybind）
for i = 1, 9 do
    hl.bind("SUPER", tostring(i), "workspace", tostring(i))
end

-- 遍歷 table
local tools = { "zsh", "git", "nvim", "tmux" }
for _, tool in ipairs(tools) do
    print(tool)
end
```

### 模組化（require）

```lua
-- hyprland.lua 裡載入同目錄的其他 .lua 檔
require("keybinds")     -- 載入 keybinds.lua
require("rules")        -- 載入 rules.lua
require("appearance")   -- 載入 appearance.lua
```

`require()` 是 Lua 原生的模組載入，取代了舊 Hyprland `.conf` 格式的 `source = ...` 指令。

## 為什麼配置工具選 Lua

Lua 被嵌入到配置層的原因是一組特定的 trade-off：

- **比 JSON/TOML/YAML 強**：有變數、迴圈、條件判斷。配置檔可以用 `for` 產生重複項目、用 `if` 處理機器差異，不需要外部 template engine
- **比 Python/JavaScript 輕**：300KB 的直譯器可以嵌入 C/C++ 程式，不需要拖一個完整的 runtime
- **沙盒化容易**：宿主程式可以控制 Lua 能存取哪些 API，限制配置檔的能力範圍

這也是 Neovim 從 VimScript 遷移到 Lua 的理由——plugin 生態需要一個真正的程式語言（有資料結構、有錯誤處理），但又不能讓配置檔變成一個安全隱患。

## 其他使用 Lua 的場景

| 場景            | 用法                                                   |
| --------------- | ------------------------------------------------------ |
| Neovim          | 整個配置和 plugin 生態基於 Lua                         |
| WezTerm         | terminal emulator 配置（`wezterm.lua`）                |
| Awesome WM      | X11 tiling WM 的配置和擴展                             |
| Redis           | `EVAL` 指令在 server 端執行 Lua script                 |
| Nginx/OpenResty | 用 Lua 寫高效能的 request 處理邏輯                     |
| 遊戲            | World of Warcraft UI mod、Roblox、很多遊戲引擎的腳本層 |

共同模式：一個用 C/C++ 寫的高效能核心，把 Lua 嵌入進去當配置和擴展語言。

## 跟 Python/JavaScript 的差異速查

| 項目             | Lua              | Python                           | JavaScript                              |
| ---------------- | ---------------- | -------------------------------- | --------------------------------------- |
| Array index 起始 | **1**            | 0                                | 0                                       |
| 字串串接         | `..`             | `+`                              | `+`                                     |
| 不等於           | `~=`             | `!=`                             | `!==`                                   |
| 邏輯運算         | `and` `or` `not` | `and` `or` `not`                 | `&&` `\|\|` `!`                         |
| 空值             | `nil`            | `None`                           | `null`/`undefined`                      |
| Falsy 值         | `nil`, `false`   | `None`, `False`, `0`, `""`, `[]` | `null`, `undefined`, `false`, `0`, `""` |
| 沒有 `+=`        | `x = x + 1`      | `x += 1`                         | `x += 1`                                |
| 註解             | `--`             | `#`                              | `//`                                    |
| 多行註解         | `--[[ ... ]]`    | `""" ... """`                    | `/* ... */`                             |

寫 Hyprland 或 Neovim 配置用到的 Lua 知識量很小——主要是 table（配置結構）、for loop（批次 keybind）、if-else（機器差異）、require（模組拆分）。不需要學 metatable、coroutine、metatmethod 這些進階功能。
