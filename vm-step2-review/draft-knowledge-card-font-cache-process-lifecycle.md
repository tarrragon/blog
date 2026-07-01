DRAFT — 待使用者 review + multi-round-review，未過寫作品質關，勿直接發布

建議落點：新 knowledge-card `content/dotfile/knowledge-cards/font-availability-at-startup.md`，
歸在 `knowledge-cards/_index.md` 的「系統概念」分類，並在該表格加一列。
weight 接在既有系統概念卡之後遞增。

適用範圍：這張卡跨 rice 範圍——任何「裝了字型但畫面還是豆腐/還是舊字」的情境都用得到，
不限 mako。source 是 step 2 rice 實測（見 vm-hyprland-handson-record 階段三第二步 finding B）。

下面是草稿內文（含建議 frontmatter，發布前依落點微調）。

---

```yaml
title: "字型的可用集合在 process 啟動時決定"
date: 2026-07-01
description: "裝了字型但應用程式 / 狀態列 / 通知還是看不到、還是豆腐時回來讀"
weight: 8
tags: ["dotfile", "font", "fontconfig", "knowledge-cards"]
```

一個 process 能用哪些字型，是在它**啟動的當下**由 fontconfig 決定並載入記憶體的。之後往系統裝新字型，不會回頭改變已經在跑的 process——它手上那份字型清單是啟動時的快照。所以「裝了字型卻還是豆腐」通常不是字型沒裝好，而是**顯示它的程式是在裝字型之前啟動的**。

## 兩層要分清楚

「字型能不能用」牽涉兩個獨立的快取層，除錯時要知道自己在看哪一層：

| 層                     | 存在哪                          | 誰更新                                   | 更新後誰看得到           |
| ---------------------- | ------------------------------- | ---------------------------------------- | ------------------------ |
| fontconfig 系統快取    | `~/.cache/fontconfig`、系統快取 | `fc-cache`（套件安裝後的 hook 通常會跑） | 之後**新啟動**的 process |
| process 內的字型資料庫 | 各 process 的記憶體             | 只有該 process **重啟**時重建            | 只有那個 process 自己    |

裝字型時，套件管理器的 post-install hook 一般已經幫你更新了 fontconfig 系統快取（例如 pacman 會印 `Updating fontconfig cache`）。所以用 `fc-match` 這種**每次都是全新 process** 的指令去查，會正確看到新字型——這容易讓人誤判「系統已經有這字了，怎麼還豆腐」。差別在於：`fc-match` 是新 process、讀到的是最新快取；那個還在豆腐的狀態列 / 通知 daemon 是**舊 process**、拿的是它啟動時的舊快照。

## 判讀與操作

- **判讀訊號**：`fc-match ":lang=zh-tw"`（或對應語言）在命令列回得出正確字型，但某個一直開著的程式仍顯示豆腐 → 幾乎可確定是「那個程式啟動早於裝字型」，不是字型問題。
- **修法是重啟那個 client，不是 reload**：`reload` 類指令（如 `makoctl reload`、送 SIGHUP）多半只重讀**設定檔**，不重建記憶體裡的字型資料庫。要讓程式看到新字型得真正**重啟 process**（結束再開）。
- **重啟的層級**：只影響單一程式（通知 daemon、狀態列）就重啟那一個；由 compositor `exec-once` 拉起的一票元件要一起吃到新字型，最乾淨的是重登入 / 重開 session，讓它們全部重新啟動。
- **風險 / 邊界**：正常開機順序不會踩到——字型在開機早期就裝好，`exec-once` 的元件是之後才啟動、一開始就看得到。這個坑集中在「系統已經在跑、中途才補裝字型」的當下除錯時序。
- **下一步路由**：Nerd Font 不含 CJK、要另裝 fallback 的具體案例見 rice 模組的桌面 shell 元件與配色章節；字型安裝本身見終端機模組的字型段。

## 反例

不是所有「看不到新東西」都是這個原因。若連 `fc-match` 這種新 process 都查不到剛裝的字型，那是 fontconfig 系統快取沒更新（少數手動放字型檔、沒跑 `fc-cache` 的情況），這時該做的是更新系統快取而不是重啟應用程式——兩個層別的修法不同，先用 `fc-match` 分辨是哪一層。另外，少數應用程式支援執行期重新掃描字型（自己重建字型資料庫），那類就不需要重啟；但這是例外，GUI 工具鏈的預設行為是啟動時載入一次。
