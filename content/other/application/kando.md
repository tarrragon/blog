---
title: "Kando 滑鼠手勢選單的應用場景"
date: 2026-06-28
draft: false
description: "Kando 圓盤選單的適用判準、macOS 工程師的應用場景排序、以及可套用的 menus.json 設定範例。"
tags: ["kando", "工作流", "macos", "效率工具"]
---

## Kando 是什麼

Kando 是一個跨平台的**圓盤選單（pie menu / marking menu）**工具：綁一個快捷鍵後，選單會在游標位置彈出，用滑鼠往某個方向滑動或點擊就能選到項目。每個項目可以執行指令、模擬快捷鍵、開啟網址/檔案、貼上文字或串成巨集。

- 專案：<https://github.com/kando-menu/kando>
- 使用說明：<https://kando.menu/usage/>

它最關鍵的特性是**標記模式（marking mode）**：選單結構固定後，可以靠肌肉記憶往某個方向「甩」一下盲選，不需要看著選單找項目。這跟「打字找東西」的啟動器（Raycast / Alfred / Spotlight）是不同的互動範式。

---

## 適用判準（先判斷再設計）

Kando 補的是一個特定空缺：**手已經在滑鼠/觸控板上、不想切回鍵盤、而且動作有空間對應**。它跟鍵盤快捷鍵或啟動器是並存關係，不是替代。判斷一個動作該不該交給 Kando，用以下三條：

1. **動作數量超過快捷鍵好記的上限**。同類動作一旦超過七八個，組合鍵就開始互相打架、記不住；圓盤選單用空間位置取代記憶。
2. **當下手在滑鼠、切回鍵盤是中斷**。瀏覽、看文件、看設計稿時，打字啟動器反而要先把手移開；圓盤選單原地彈出。
3. **動作有方向語意，盲操作就能命中**。例如「左半邊視窗」往左滑、「下一個螢幕」往外圈滑。有方向對應的動作練熟後可以完全不看選單。

三條不必同時滿足，但命中越多越適合。反過來說，低頻、無方向語意、又需要打字輸入參數的動作，留在啟動器或 CLI 比較好。

---

## macOS 工程師的應用場景

以下幾組依「契合 Kando 的程度」排序，越前面方向語意越強、回報越快。

### 1. 視窗排版（最契合）

方向天然對應位置，這是 Kando 比 Rectangle 純快捷鍵更直覺的地方：

- 往左滑放左半螢幕、往右放右半、往上全螢幕、往下置中浮動
- 對角線放四分之一角落
- 外圈再包一層：丟到下一個螢幕、移到上一個 Space

底層用 simulate hotkey 去觸發 Rectangle 或 yabai。練熟後完全盲操作，不用記「左半邊是哪組三鍵組合」這種反直覺對應。

### 2. 瀏覽器內「當前頁面接我的工作流」

看 PR、issue、文件時手在滑鼠上，這時甩一下選單把當前頁面導進後續流程：

- 複製當前 URL 成 Markdown 連結
- 把選取文字丟進 AI（觸發 Raycast AI / ChatGPT 的 hotkey，或貼到剪貼簿）
- 存進筆記軟體
- 在編輯器開對應的 local repo

### 3. 開發環境一鍵啟動（巢狀選單）

用 run command，適合放每天重複開的那幾個專案：

- 外圈按專案分
- 內圈每個專案：用 IDE 開、開 terminal 到該目錄、開 PR 頁、開 CI dashboard、`docker compose up`

### 4. 常用 snippet / 樣板貼上

用 paste text，放那些「記不得但常用」的東西：

- Email 簽名、PR 描述模板、commit message 前綴
- 常用 emoji / 符號
- 長的 shell one-liner

### 5. 系統狀態切換

toggle 類，平常要進設定點半天的：

- 勿擾模式、深色/淺色主題、防睡眠、切換音訊輸出裝置、螢幕錄製/截圖

### 6. Git / 容器 context 切換

git 日常走 CLI，但**切 context** 這種低頻又記不住名字的適合放選單：

- `kubectl` context / namespace 切換
- AWS profile 切換
- docker 清理、重啟某個 compose service

---

## 建構自己模式的起步建議

別一次設計大選單。先只做視窗排版那組，因為方向對應最直覺、回報最快、最容易養成「想到就甩一下」的習慣。等這個習慣固定了，再依「這禮拜我重複做了什麼、又懶得記快捷鍵」逐步往其他組長。一開始就塞滿，反而會因為記不住結構而棄用。

---

## 設定範例：視窗排版（Magnet 版）

底層用 `hotkey` 型項目去打 Magnet 的預設快捷鍵（Magnet 的修飾鍵是 Control+Option，Option 在按鍵碼裡是 `AltLeft`）。八個項目用 `angle` 釘死在八個方向，方向語意對齊位置：左滑放左半、右滑放右半、上滑最大化、下滑置中、四個對角放四分之一角落。練熟後可以盲操作。

Kando 的角度規則是 `0` 在正上方、順時針遞增（`90` 右、`180` 下、`270` 左）。每個 `hotkey` 都設 `delayed: true`，讓按鍵在選單關閉後才送出，這樣 Magnet 作用的是「開選單前那個聚焦視窗」而不是 Kando 的 overlay。

```json
{
  "menus": [
    {
      "root": {
        "type": "submenu",
        "name": "視窗排版",
        "icon": "grid_view",
        "iconTheme": "material-symbols-rounded",
        "children": [
          {
            "type": "hotkey",
            "data": { "hotkey": "ControlLeft+AltLeft+Enter", "delayed": true },
            "name": "最大化",
            "icon": "fullscreen",
            "iconTheme": "material-symbols-rounded",
            "angle": 0
          },
          {
            "type": "hotkey",
            "data": { "hotkey": "ControlLeft+AltLeft+KeyI", "delayed": true },
            "name": "右上",
            "icon": "north_east",
            "iconTheme": "material-symbols-rounded",
            "angle": 45
          },
          {
            "type": "hotkey",
            "data": { "hotkey": "ControlLeft+AltLeft+ArrowRight", "delayed": true },
            "name": "右半",
            "icon": "east",
            "iconTheme": "material-symbols-rounded",
            "angle": 90
          },
          {
            "type": "hotkey",
            "data": { "hotkey": "ControlLeft+AltLeft+KeyK", "delayed": true },
            "name": "右下",
            "icon": "south_east",
            "iconTheme": "material-symbols-rounded",
            "angle": 135
          },
          {
            "type": "hotkey",
            "data": { "hotkey": "ControlLeft+AltLeft+KeyC", "delayed": true },
            "name": "置中",
            "icon": "filter_center_focus",
            "iconTheme": "material-symbols-rounded",
            "angle": 180
          },
          {
            "type": "hotkey",
            "data": { "hotkey": "ControlLeft+AltLeft+KeyJ", "delayed": true },
            "name": "左下",
            "icon": "south_west",
            "iconTheme": "material-symbols-rounded",
            "angle": 225
          },
          {
            "type": "hotkey",
            "data": { "hotkey": "ControlLeft+AltLeft+ArrowLeft", "delayed": true },
            "name": "左半",
            "icon": "west",
            "iconTheme": "material-symbols-rounded",
            "angle": 270
          },
          {
            "type": "hotkey",
            "data": { "hotkey": "ControlLeft+AltLeft+KeyU", "delayed": true },
            "name": "左上",
            "icon": "north_west",
            "iconTheme": "material-symbols-rounded",
            "angle": 315
          }
        ]
      },
      "shortcut": "Control+Shift+Space",
      "shortcutID": "",
      "centered": false,
      "anchored": false,
      "hoverMode": false
    },
    {
      "root": {
        "type": "submenu",
        "name": "視窗進階",
        "icon": "view_column",
        "iconTheme": "material-symbols-rounded",
        "children": [
          {
            "type": "hotkey",
            "data": { "hotkey": "ControlLeft+AltLeft+KeyD", "delayed": true },
            "name": "左三分之一",
            "icon": "first_page",
            "iconTheme": "material-symbols-rounded"
          },
          {
            "type": "hotkey",
            "data": { "hotkey": "ControlLeft+AltLeft+KeyF", "delayed": true },
            "name": "中三分之一",
            "icon": "vertical_align_center",
            "iconTheme": "material-symbols-rounded"
          },
          {
            "type": "hotkey",
            "data": { "hotkey": "ControlLeft+AltLeft+KeyG", "delayed": true },
            "name": "右三分之一",
            "icon": "last_page",
            "iconTheme": "material-symbols-rounded"
          },
          {
            "type": "hotkey",
            "data": { "hotkey": "ControlLeft+AltLeft+KeyE", "delayed": true },
            "name": "左三分之二",
            "icon": "align_horizontal_left",
            "iconTheme": "material-symbols-rounded"
          },
          {
            "type": "hotkey",
            "data": { "hotkey": "ControlLeft+AltLeft+KeyT", "delayed": true },
            "name": "右三分之二",
            "icon": "align_horizontal_right",
            "iconTheme": "material-symbols-rounded"
          },
          {
            "type": "hotkey",
            "data": { "hotkey": "ControlLeft+AltLeft+MetaLeft+ArrowLeft", "delayed": true },
            "name": "上一個螢幕",
            "icon": "arrow_circle_left",
            "iconTheme": "material-symbols-rounded"
          },
          {
            "type": "hotkey",
            "data": { "hotkey": "ControlLeft+AltLeft+MetaLeft+ArrowRight", "delayed": true },
            "name": "下一個螢幕",
            "icon": "arrow_circle_right",
            "iconTheme": "material-symbols-rounded"
          },
          {
            "type": "hotkey",
            "data": { "hotkey": "ControlLeft+AltLeft+Backspace", "delayed": true },
            "name": "還原",
            "icon": "settings_backup_restore",
            "iconTheme": "material-symbols-rounded"
          }
        ]
      },
      "shortcut": "Control+Shift+Alt+Space",
      "shortcutID": "",
      "centered": false,
      "anchored": false,
      "hoverMode": false
    }
  ]
}
```

套用方式：

1. 先**完全結束 Kando**（Kando 會在離開時把記憶體裡的設定寫回檔案、開著編輯會被覆蓋）。
2. 編輯 macOS 的設定檔 `~/Library/Application Support/kando/menus.json`。若已有自訂選單，把 `menus` 陣列裡的兩個物件貼進去、不要整檔覆蓋。
3. 重新開 Kando。觸發鍵 `Control+Shift+Space`（進階組 `Control+Shift+Alt+Space`）若跟既有快捷鍵衝突，直接在 Kando 設定 GUI 改最保險。

對照表（方向 → Magnet 動作 → 快捷鍵）：

| 方向 | 動作   | Magnet 快捷鍵 |
| ---- | ------ | ------------- |
| 上   | 最大化 | ⌃⌥↵           |
| 右   | 右半   | ⌃⌥→           |
| 下   | 置中   | ⌃⌥C           |
| 左   | 左半   | ⌃⌥←           |
| 右上 | 右上角 | ⌃⌥I           |
| 右下 | 右下角 | ⌃⌥K           |
| 左下 | 左下角 | ⌃⌥J           |
| 左上 | 左上角 | ⌃⌥U           |

---

## 設定範例：自訂腳本叫出 Ghostty 執行（command 型）

`command` 型項目直接把指令交給作業系統執行，它本身不開終端機視窗。要「叫出 Ghostty 並在裡面跑腳本」，得用 Ghostty 的 `-e` 旗標開一個新視窗執行指定指令。下面這組放兩個需要看畫面的磁碟工具：`mole`（互動式清理 TUI）跟 [`disk-report`](/other/macos_disk_space_diagnosis/)（印出硬碟空間報告，安裝方式見該篇）。

兩個寫法的共同骨架是 `ghostty -e zsh -lc "<腳本>; exec zsh"`：

- **`zsh -lc`**：用 login shell 執行，載入 `.zprofile` / `.zshrc` 的 PATH（[PATH 設定見新機基礎建設](/other/macos_new_machine_setup/)），`mole` 跟 `~/.local/bin` 底下的腳本才解析得到。少了這層，Kando 走 `/bin/sh`、沒有自訂 PATH，會找不到指令。
- **`; exec zsh`**：腳本結束後把視窗留在一個互動 shell。mole 退出或 disk-report 印完，畫面都還在，不會瞬間關掉。

```json
{
  "root": {
    "type": "submenu",
    "name": "磁碟工具",
    "icon": "hard_drive",
    "iconTheme": "material-symbols-rounded",
    "children": [
      {
        "type": "command",
        "data": {
          "command": "/Applications/Ghostty.app/Contents/MacOS/ghostty -e zsh -lc \"mole; exec zsh\"",
          "delayed": false,
          "isolateProcess": false
        },
        "name": "mole 清理",
        "icon": "cleaning_services",
        "iconTheme": "material-symbols-rounded"
      },
      {
        "type": "command",
        "data": {
          "command": "/Applications/Ghostty.app/Contents/MacOS/ghostty -e zsh -lc \"disk-report; exec zsh\"",
          "delayed": false,
          "isolateProcess": false
        },
        "name": "硬碟空間報告",
        "icon": "monitoring",
        "iconTheme": "material-symbols-rounded"
      }
    ]
  },
  "shortcut": "Control+Shift+KeyD",
  "shortcutID": "",
  "centered": false,
  "anchored": false,
  "hoverMode": false
}
```

把上面這個物件加進 `menus.json` 的 `menus` 陣列（跟前面視窗那兩個並排，逗號分隔）。

兩個延伸調整：

- **純背景、不用看畫面的腳本**：不必開 Ghostty，`command` 直接寫 `zsh -lc "$HOME/.local/bin/某腳本"` 就好，腳本在背景跑完無聲結束。
- **若 `ghostty` 二進位路徑直接呼叫沒反應**（Ghostty 已在執行時偶有此狀況）：改用 `open -na Ghostty --args -e zsh -lc "mole; exec zsh"`，強制由 `open` 帶起一個新視窗。

---

## 我的自訂模式紀錄

（待補：實際用了一段時間後保留與淘汰的項目、其他組選單的 JSON、踩到的坑。）
