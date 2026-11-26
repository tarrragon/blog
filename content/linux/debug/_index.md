---
title: "Linux 除錯與診斷"
date: 2026-07-02
description: "遠端或本地除錯 Linux 時，一個現象看起來像 A 卻可能是 B，想建立一套先讀權威狀態再下判斷的紀律、按症狀分流到對的檢查與工具時回來讀"
weight: 2
tags: ["linux", "debugging", "diagnosis"]
---

這個系列處理機器裝好、能連入之後出問題時怎麼判。核心是一套判讀紀律：先讀權威狀態，不靠肉眼猜表象——因為 Linux 上一個現象看起來像 A 卻常常是 B，看畫面就下結論容易猜錯。系列特別涵蓋遠端使用與本地除錯兩種情境，因為遠端看不到畫面，反而逼出「只信權威狀態」的好紀律。

內容來自一次完整的 Arch Linux / Hyprland VM 實測與除錯：SSH 連不上、終端機噴亂碼、虛擬機開不起來、螢幕鎖定狀態判錯、服務歸屬搞混——每個卡關點都被記錄下來，蒸餾成可重用的判讀路由，不綁特定發行版。量測對外連線品質那一篇另外涵蓋 Windows 用戶端的工具，因為對外連線的量測常從使用者的 Windows 電腦做起。

## 從哪篇開始

先讀 [診斷心法](diagnosis-read-authoritative-state/) 建立判讀紀律（讀權威狀態、四步流程），再依症狀進對應情境。

## 文章

| 文章                                                                        | 主題                                                                                                                          | 回答什麼問題                                                                      |
| --------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| [診斷心法：讀權威狀態，不靠肉眼猜表象](diagnosis-read-authoritative-state/) | 貫穿所有除錯的判讀紀律：每種問題的權威狀態來源、讀程式自己的 log、四步流程                                                    | 一個現象看起來像 A 卻可能是 B，怎麼不猜錯                                         |
| [遠端連線與終端機問題](ssh-and-terminal-troubleshooting/)                   | SSH 斷線後終端機噴亂碼、遠端打字亂碼（locale/terminfo）、從 SSH 操控圖形桌面                                                  | 連上了但終端機或 session 狀態不對怎麼修                                           |
| [機器連不到或起不來](machine-unreachable/)                                  | SSH 突然連不上（ARP 診斷）、虛擬機開不起來（guest vs 宿主側）、磁碟滿的連鎖                                                   | 一台機器連不到或開不了機，從哪一層往下查                                          |
| [程序、服務與狀態怎麼判](process-service-state-diagnosis/)                  | 程式活著沒（pgrep 陷阱）、服務由誰提供（busctl）、session 鎖沒鎖、多工器 session 存活                                         | 判某個東西的狀態時，該讀哪個權威來源                                              |
| [服務掛了怎麼自動知道](service-failure-monitoring/)                         | 從手動 systemctl 到 OnFailure 主動告警、先重啟才告警、hung 偵測、canary、機器死掉的體外心跳                                   | 不想肉眼盯服務死活，怎麼自動監控並推播                                            |
| [ntfy：推送通知服務](ntfy-push-notification-service/)                       | ntfy 的 pub-sub 模型、開源 vs 標準、公共站 vs 自架、topic 就是密碼的安全模型、同類對照                                        | 用 ntfy 推告警、想搞懂它是什麼、該不該自架                                        |
| [AUR 建置失敗的分層判讀](aur-build-failure-triage/)                         | 建置失敗的分層：資源、`-bin` 二進位漂移、烤入路徑、架構宣告缺失、`-git` 依賴衝突                                              | AUR 套件裝不起來，是哪一層壞了                                                    |
| [對外服務連線品質的量測](external-service-connection-quality/)              | 延遲、掉包、頻寬與應用層回應時間的區分；ICMP 與 TCP 經過的關卡；ping、tracert、pathping、psping、mtr、iperf3、curl 各量哪一層 | ping 的結果跟服務對不上、或連得上但很慢時，該用哪一種量測、量到的數字是否代表服務 |

## 依症狀的讀法

- **連不上、開不了機**：機器 SSH 連不到、或虛擬機開不起來 → [機器連不到或起不來](machine-unreachable/)。
- **連得上但很慢、或 ping 的結果跟服務對不上**：ping 通而服務慢、ping 不通而服務正常、要量到外部服務的延遲、掉包或頻寬 → [對外服務連線品質的量測](external-service-connection-quality/)。
- **終端機行為怪**：SSH 斷線後終端機噴亂碼、遠端打字亂碼、要從 SSH 操控圖形桌面 → [遠端連線與終端機問題](ssh-and-terminal-troubleshooting/)。
- **某個狀態判不準**：程式活著沒、服務歸誰、鎖沒鎖、session 還在不在 → [程序、服務與狀態怎麼判](process-service-state-diagnosis/)。
- **AUR 套件裝不起來**：helper 自己壞掉、編譯叫錯工具、makepkg 拒建 → [AUR 建置失敗的分層判讀](aur-build-failure-triage/)。
- **git push / clone 卡認證**：私有 repo 操作回 `could not read Username` 或 `403 Write access not granted`（`gh api` 回 404）→ [在 container 裡跑 Claude Code](../tools/remote/claude-code-container-and-hooks/) 的 GitHub 認證段，區分「根本沒存取憑證」與「fine-grained token 認證通了、只是 scope 不含此 repo」。
- **不想手動盯服務死活**：想讓 service 掛掉時主動推播、或擔心整台機器當掉沒人知道 → [服務掛了怎麼自動知道](service-failure-monitoring/)。
- **想建立通用紀律**：想要一套適用各種症狀的「不猜錯」判讀方法 → [診斷心法](diagnosis-read-authoritative-state/)。
- **接手一台陌生機器、還沒出問題**：機器在跑但不是你裝的，想先盤清楚上面有什麼再動手 → [接手陌生機器的盤點](../install/inventory-unknown-machine/)——同一套「讀權威狀態」紀律用在盤點而非除錯。

## Backlog

| 項目                                                                                                                                                                                                                                                                              | 類型 | 前置條件                                       | 規模                                     |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ---------------------------------------------- | ---------------------------------------- |
| `machine-unreachable.md`〈網路通、但域名解析不了〉與 `../install/package-and-network-troubleshooting.md` 把 `ping 8.8.8.8` 當成 IP 層的權威檢查：在兩處補「所在網路擋 ICMP 時 ping 不通不代表 IP 層斷，改對已知服務的 TCP port 確認」並連到 `external-service-connection-quality` | 主章 | 無                                             | 2 處（小）                               |
| `../tools/remote/tailscale-tailnet-and-relay.md` 在 relay 判讀句後連回 `external-service-connection-quality` 的 VPN 環境段                                                                                                                                                        | 主章 | 無                                             | 小                                       |
| `external-service-connection-quality` 的 traceroute 讀法補 MPLS 骨幹裡 ICMP 經 LSP 尾端折回、一串跳顯示相同 RTT 的情形，以及它對「延遲從某一跳開始升高」定位的影響                                                                                                                | 主章 | 需要一份 MPLS 骨幹的實際 traceroute 輸出當例子 | 小                                       |
| `external-service-connection-quality` 補第一跳（本機到閘道）的延遲與掉包代表區網或 Wi-Fi，跟外面的路徑分開判讀                                                                                                                                                                    | 主章 | 無                                             | 小                                       |
| 新篇：從用戶端量服務的連線時間（App／瀏覽器端的請求計時回報），以及 NAT、CGNAT、負載平衡器的閒置逾時讓重用的連線失效造成的偶發逾時；寫完後 `external-service-connection-quality` 末段改連過去                                                                                     | 主章 | 無                                             | 1 篇（中，一篇完整文章，不需要獨立排期） |

## 跟其他模組的交叉引用

- [Linux 安裝與機器初始化](../install/)——本系列的上游；把機器裝好、連入之後才輪到除錯。其中 [可除錯的 bootstrap](../install/observable-bootstrap/) 談怎麼讓腳本產生可診斷的 log，與診斷心法的「讀程式自己的 log」一體兩面。
- [Linux 工具選單](../tools/)——除錯要用的工具（CLI / 圖形桌面 / 遠端）有哪些選擇。
- [模組七：日誌判讀與診斷工具](/linux/dotfile/07-desktop-maintenance/log-reading-diagnostic-tools/)——桌面環境層的日誌判讀，與這裡的通用診斷紀律呼應。
