---
title: "字型的可用集合在 process 啟動時決定"
date: 2026-07-01
description: "裝了字型但應用程式 / 狀態列 / 通知還是看不到、還是豆腐時回來讀"
weight: 14
tags: ["dotfile", "font", "fontconfig", "knowledge-cards"]
---

一個 process 能用哪些字型，是在它**啟動的當下**由 fontconfig（Linux 上統一管理字型搜尋與匹配的底層服務）決定並載入記憶體的。之後往系統裝新字型，不會回頭改變已經在跑的 process——它手上那份字型清單是啟動時的快照。「裝了字型卻還是豆腐」多數時候指向的是這個時序問題，而非安裝本身失敗。

這個機制發生在 fontconfig + process 記憶體層，跟顯示協議無關——Wayland 和 X11 下的行為相同。

## 同一時刻、兩種查詢結果

裝完新字型後，在終端機用 fontconfig 的查詢工具 `fc-match`（每次執行都是新 process）去查：

```bash
fc-match ":lang=zh-tw"
# Noto Sans CJK → 系統快取已有這支字
```

查得到。但同時間，一直開著的狀態列或通知 daemon 仍顯示豆腐。矛盾的根源是兩者的啟動時間不同：`fc-match` 剛啟動、讀到的是最新系統快取；那個豆腐的 daemon 是在裝字型**之前**啟動的，記憶體裡的字型清單沒有這支字。

套件管理器安裝字型時，post-install hook 通常已更新 fontconfig 的系統快取（pacman 會印 `Updating fontconfig cache`）。手動把字型檔放進 `~/.local/share/fonts/` 的情況下，需要自己跑 fontconfig 的快取重建工具 `fc-cache`：

```bash
fc-cache -fv
# -f 忽略時間戳、強制全部重建
# -v 印出處理了哪些目錄
```

`fc-cache` 只更新系統快取層——磁碟上的索引檔。它不會觸及任何已啟動 process 的記憶體，跑再多次也改變不了舊 process 的字型清單。

## 判讀與操作

**判讀訊號**：`fc-match` 在命令列回得出正確字型，但某個一直開著的程式仍顯示豆腐，幾乎可確定是「那個程式啟動早於裝字型」。

**修法是重啟該程式，不是 reload**。`reload` 類指令（如 `makoctl reload`、送 SIGHUP）重讀的是**設定檔**——能換到 daemon 啟動時已可見的字型（例如從 A 字族改成 B 字族），但看不到啟動後才新裝的字型檔。根源是 reload 不重建記憶體裡的字型清單，只有重啟 process 才會從系統快取重新載入。

**重啟的範圍**取決於受影響的程式數量。單一 daemon（通知、狀態列）重啟那一個即可；由 compositor `exec-once` 拉起的一批元件要同時吃到新字型，最乾淨的做法是重新登入，讓它們全部重新啟動。

**正常開機不會踩到這個坑**——字型在開機早期就裝好，`exec-once` 啟動的元件從一開始就看得到完整字型集合。這個時序問題集中在「系統已經在跑、中途才補裝字型」的除錯情境。

**延伸閱讀**：Nerd Font 不含 CJK、需另裝 fallback 字型的具體案例見[桌面 Shell 元件：狀態列、啟動器與通知](/linux/dotfile/06-rice-design/desktop-shell-components/)；字型安裝方式見[終端機與編輯器配置](/linux/dotfile/03-terminal-ecosystem/terminal-emulator-config/)的字型管理段。

## 邊界與例外

**fc-match 也查不到**：連新 process 都找不到剛裝的字型，問題在系統快取層（fontconfig 索引未更新），跑 `fc-cache -fv` 解決。兩層的修法不同，`fc-match` 是分辨在哪一層的第一步。

**部分應用程式支援熱載入**：瀏覽器等有獨立字型服務的程式可能在開新分頁時重新掃描字型，不需要重啟整個 process。長駐 daemon（mako、waybar）與狀態列預設是啟動時載入一次。

**Flatpak / Snap 的字型隔離是不同問題**：沙箱化應用程式看不到 host 的字型目錄，重啟 process 也無法解決——原因不是時序，而是沙箱的檔案系統隔離。需要透過 Flatpak 的 filesystem override 或把字型放進沙箱可存取的路徑。
