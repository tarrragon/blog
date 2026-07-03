---
title: "TUI 監控工具：btop、htop、k9s 的遠端使用與刷新率調校"
date: 2026-06-15
draft: false
description: "要在遠端 SSH 用全螢幕 TUI 看進程與資源（htop／btop／k9s）、或慢速連線下要調刷新率省頻寬時回來讀"
tags: ["cli", "tui", "monitoring", "btop", "htop", "k9s", "remote"]
---

TUI 監控工具負責把系統或叢集的即時狀態畫成全螢幕互動介面：即時呈現負載變化，並用鍵盤直接排序、過濾、送訊號，取代反覆敲 `ps`、`df`、`free` 再自行拼湊。在遠端 SSH 情境下，它的關鍵變數是刷新率與頻寬的取捨，因為全螢幕介面每次刷新都會重送整片畫面。

本文承接 [終端機圖形化工具總覽](/linux/tools/cli/cli-graphical-tools-overview/) 的 TUI 工具脈絡，聚焦系統監控這一支在遠端的實際使用與調校。git 線圖工具（`tig` / `lazygit` / `gitui`）雖然也是 TUI，但屬版控子題，獨立成 [遠端 CLI 開發的 git 線圖工具選型](/linux/tools/cli/git-line-graph-tools-for-remote-cli/)。

## htop：進程層的標準

htop 把進程清單畫成帶 CPU 與記憶體長條的全螢幕視圖，責任是即時看進程並直接操作。它用底部的功能鍵列引導操作，不必背指令。

| 按鍵  | 作用                     |
| ----- | ------------------------ |
| `F3`  | 搜尋進程                 |
| `F4`  | 過濾（只顯示符合的進程） |
| `F5`  | 樹狀檢視（看父子關係）   |
| `F6`  | 選排序欄位               |
| `F9`  | 送訊號（殺進程）         |
| `F10` | 離開                     |

遠端使用的關鍵是刷新延遲。htop 用 `-d` 設定刷新間隔，單位是十分之一秒，所以 `htop -d 30` 是每 3 秒刷新一次。慢速連線下把延遲調大換取畫面不卡、按鍵不延遲，可從 5 秒（`htop -d 50`）起步，順了再往下調。這個 5 秒是經驗起點、不是測得的閾值，實際依連線 RTT 與終端尺寸調整（後面 btop 與判讀段沿用此基準）。

## btop：多資源儀表板

btop 把 CPU、記憶體、網路、磁碟畫在同一畫面，並帶歷史曲線與滑鼠操作，責任是一眼總覽多個資源維度的趨勢。相較 htop 偏進程清單，btop 偏向整機儀表板。

刷新率是 btop 在遠端最該調的設定。它的刷新間隔由 `update_ms` 控制（預設 2000 毫秒），把間隔調短會讓全螢幕重畫更頻繁、在慢速連線吃掉頻寬。調整方式是按 `Esc` 開 Options 選單改 `update_ms`，或直接編輯設定檔 `~/.config/btop/btop.conf` 的 `update_ms` 值。判讀分界與 htop 相同：連線品質好可用較密的刷新換即時性，品質差就把間隔拉長，慢速連線可從 `update_ms 5000`（5 秒）起步。

## k9s：Kubernetes 叢集導航

k9s 把 `kubectl` 的查詢與操作做成全螢幕導航介面，責任是讓叢集管理不必逐條敲 `kubectl` 指令。它用冒號指令切換資源視圖，游標選中資源後用快捷鍵操作。

> 安裝與 `--refresh` 旗標已實機驗證；以下 `:pods` 等叢集操作需連到 k8s cluster，依官方用法、本機未實機驗證。

常見操作是輸入 `:pods` 看 pod 清單、`:svc` 看 service，游標停在某個 pod 上按 `l` 看 log、`d` 看 describe、`s` 進 container shell。對遠端管理叢集的情境，它把「查狀態到進去除錯」的流程收進同一畫面，省去反覆切換指令的負擔。k9s 同樣是全螢幕 TUI、會定期輪詢叢集狀態，慢速連線下導航延遲明顯時，可在啟動時用 `--refresh` 把輪詢間隔（秒）調長。

## 其他常用 TUI 監控

不同資源維度有各自的專用 TUI，責任聚焦在單一面向。

| 工具           | 監控對象 | 用途                                 |
| -------------- | -------- | ------------------------------------ |
| `ncdu` / `gdu` | 磁碟空間 | 掃描目錄並用長條顯示各目錄佔多少空間 |
| `ctop`         | 容器     | 即時看各 container 的資源佔用        |
| `dive`         | 映像層   | 逐層分析 Docker image 的大小組成     |

這些工具的共同特性是各管一個維度：磁碟爆了用 `ncdu` 找出是哪一包、容器資源異常用 `ctop` 定位、要拆解 image 肥在哪用 `dive`。遠端排查時依問題維度挑對應工具，比開一個大而全的儀表板更直接。

Docker 相關的兩個工具值得多記一筆。`dive` 除了 TUI，還有非互動的 `--ci` 模式：`dive <image> --ci` 會輸出 image 的 efficiency 與 wasted space，並依門檻判定 pass/fail，適合塞進 CI pipeline 擋住臃腫 image。`ctop` 的單一容器細節視圖（游標選中按 `Enter`）會把環境變數明文列出，含資料庫密碼這類敏感值，共享畫面或側錄時要留意。

## 遠端刷新率與頻寬的取捨

全螢幕 TUI 監控的遠端成本核心在於：每次刷新會重送整片字元矩陣，刷新越密、頻寬負擔越重。慢速連線下會看到畫面延遲、按鍵反應慢。對策是把刷新間隔調長（`htop -d`、btop 的 `update_ms`），用更新頻率換流暢度。

判讀分界落在刷新率與監控粒度：連線順暢時用 1–2 秒的密集刷新看即時變化；連線吃緊時把間隔拉到 5 秒以上，或當只盯單一指標時改用一次性的文字趨勢（見 [終端機文字圖表](/linux/tools/cli/ascii-charts-in-terminal/)）而非全螢幕儀表板。

## 下一步路由

- 把監控擺進可持久化的多工器：[tmux 基礎](/linux/tools/cli/tmux-persistence-and-basics/)，斷線後 reattach 回去監控還在跑。
- 一次性的文字趨勢圖（省頻寬的替代）：[終端機文字圖表](/linux/tools/cli/ascii-charts-in-terminal/)。
- 監控的是 web 請求而非系統資源：[終端機看 nginx 請求](/linux/tools/cli/web-server-log-monitoring/)（GoAccess / ngxtop）。
- TUI 監控在遠端工具分類中的定位：[終端機圖形化工具總覽](/linux/tools/cli/cli-graphical-tools-overview/)。
