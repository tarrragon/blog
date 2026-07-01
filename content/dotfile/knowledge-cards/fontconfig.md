---
title: "fontconfig — 字型搜尋、匹配與 fallback 服務"
date: 2026-07-01
description: "不確定 fc-list / fc-match / fc-cache 各做什麼、或 fontconfig fallback 機制怎麼運作時回來讀"
weight: 16
tags: ["dotfile", "font", "fontconfig", "knowledge-cards"]
---

fontconfig 是 Linux 上統一管理字型搜尋、匹配與 fallback 的底層服務。應用程式透過 fontconfig 的 API 查詢可用字型，而非自行掃描字型目錄——無論是終端機、狀態列、通知 daemon 還是瀏覽器，底層都走同一套查詢介面。

## fc-* 工具分工

fontconfig 附帶一組命令列工具，各自負責一件事：

| 工具         | 用途                                       | 常用情境                                     |
| ------------ | ------------------------------------------ | -------------------------------------------- |
| `fc-list`    | 列出系統已知的所有字型（字族名、檔案路徑） | 確認某支字型有沒有裝、查實際字族名           |
| `fc-match`   | 查詢指定條件的最佳匹配結果                 | 確認 config 裡寫的字族名會匹配到哪支字       |
| `fc-cache`   | 重建 fontconfig 的系統快取                 | 手動放字型檔後更新快取（套件安裝通常自動跑） |
| `fc-pattern` | 印出字型的完整屬性（除錯用）               | 查字型支援的語言、字重、字形變體             |

`fc-list` 和 `fc-match` 每次執行都是新 process，讀到的是當下最新的系統快取。這跟已啟動的長駐程式不同——長駐程式的字型清單是啟動時的快照，詳見 [font-availability-at-startup](/dotfile/knowledge-cards/font-availability-at-startup/)。

```bash
fc-list | grep -i meslo
# 確認 MesloLGS Nerd Font 有沒有裝、實際字族名是什麼

fc-match "MesloLGS Nerd Font"
# 查 config 裡寫的名字會匹配到哪支字型檔

fc-match ":lang=zh-tw"
# 查系統有沒有可用的繁體中文字型
```

## Fallback chain

應用程式在 config 裡指定字族名（如 `MesloLGS Nerd Font`），fontconfig 依以下順序處理：

1. 在已知字型中找**完全匹配**的字族
2. 找不到就沿 fallback chain 往下找候選——fontconfig 的預設 fallback 規則定義在 `/etc/fonts/conf.d/` 的 XML 設定檔中
3. CJK fallback 依語言優先序決定——`fc-match ":lang=zh-tw"` 回的是 fontconfig 認為最適合該語言的字型

Nerd Font（MesloLGS、JetBrainsMono 等）只含 Latin 字元與圖示 glyph，CJK 字元靠 fallback 到另一支字型（如 `noto-fonts-cjk`）補齊。fontconfig 的 fallback 對應用程式透明——應用程式只指定主字型，缺字時 fontconfig 自動補。

## 系統快取

fontconfig 把字型目錄的掃描結果存成快取檔，避免每次查詢都重新掃描整個檔案系統：

- 系統層快取：`/var/cache/fontconfig/`
- 使用者層快取：`~/.cache/fontconfig/`

套件管理器安裝字型時，post-install hook 會自動執行 `fc-cache` 更新系統快取（pacman 安裝完會印 `Updating fontconfig cache`）。手動把字型檔放進 `~/.local/share/fonts/` 時需要自己跑 `fc-cache`——不跑的話 fontconfig 看不到新字型。

`fc-cache -f` 的 `-f` 是 force，忽略時間戳全部重建；不加 `-f` 只更新有變動的目錄。兩者都只動系統快取層——已啟動的 process 記憶體中的字型清單不受影響，那是另一個層級的問題（見 [font-availability-at-startup](/dotfile/knowledge-cards/font-availability-at-startup/)）。

## 下一步路由

- 字型安裝方式：[終端機與編輯器](/dotfile/03-terminal-ecosystem/)的字型管理段
- 裝了字型但應用程式還是看不到：[font-availability-at-startup](/dotfile/knowledge-cards/font-availability-at-startup/)（process 啟動時快照的時序問題）
