---
title: "TLS Handshake（TLS 握手）的成本與連線重用"
date: 2026-10-28
description: "壓測量到的上限落在負載平衡器或反向代理的 CPU、Connect Time 隨負載上升，或要判斷負載工具該不該在每一輪重建連線時讀"
weight: 499
tags: ["backend", "performance", "load-test", "tls", "knowledge-card"]
---

TLS 握手（TLS handshake）是用戶端與伺服器在一條新的 TCP 連線上傳送應用資料之前做的協商：雙方決定協定版本與加密套件、伺服器出示數位憑證並用私鑰簽名、雙方交換金鑰算出這條連線的對稱金鑰。它在安全上負責的事見 [TLS / mTLS](/backend/knowledge-cards/tls-mtls/)；這張卡講它的成本：每建一條新連線就付一次，付在延遲與受測端的 CPU 上，而重用連線的程度決定了一個請求平均要分攤多少。

## 概念位置

一次完整的握手有兩種成本。延遲成本是來回的次數：TLS 1.3 的完整握手比 TCP 的三次握手多一趟來回，TLS 1.2 多兩趟；用戶端離伺服器越遠，每一趟越長。CPU 成本落在終結 TLS 的那一層，可能是負載平衡器、反向代理，也可能是應用程式本身：伺服器每次握手都要用憑證的私鑰做一次簽名，加上一次金鑰交換的運算，這兩項是非對稱加密，每次的運算量遠大於之後用對稱金鑰加解密一個請求。

連線建好之後，同一條連線上的後續請求不再握手，只付對稱加解密的成本。所以一個請求平均分攤的握手成本，等於握手次數除以請求數：用戶端用 HTTP keep-alive 或 HTTP/2 在一條連線上送很多請求時接近零，每個請求都開新連線時，每個請求各付一次；服務之間的呼叫用 [Connection Pool](/backend/knowledge-cards/connection-pool/) 保留建好的連線，就是在攤平這筆成本。連線斷掉之後重連，用戶端可以帶著上一次的 session 資訊做 session resumption（TLS 1.2 的 session ticket、TLS 1.3 的 PSK），跳過憑證與簽名那一段，CPU 成本比完整握手低；兩邊都要支援、而且 session 資訊還沒過期時才用得上。

## 可觀察訊號與例子

握手的成本在壓測裡最常以兩種樣子出現。一種是量到的上限落在 TLS 終結層：受測服務的應用程式 CPU 還低，負載平衡器或反向代理的 CPU 先滿，延遲上升；這時量到的 knee（延遲開始隨負載不成比例上升的那一級負載）反映的是那一層的握手能力，不是應用程式的容量。另一種是建立連線的時間隨負載上升：JMeter 的 Connect Time 包含 SSL 握手的時間（官方〈Glossary〉），負載逐級升高時它跟著上升、而受測服務入口量到的應用程式延遲持平時，多出來的時間花在建立連線上。

負載工具在什麼時候建新連線，各有預設值與設定：

- **JMeter**：每個 thread 有自己的 SSL context。內建 Thread Group 勾選 Same user on each iteration 時，連線跨輪保留；沒勾選時看 `httpclient.reset_state_on_thread_group_iteration`，它的預設值 `true` 代表每一輪開頭關掉連線、重設 SSL 狀態。Open Model Thread Group 每次抵達建立一個新 thread、跑完一輪就結束，每次抵達都握手一次。
- **k6**：預設連線在同一個 VU 的各輪之間重用；`noVUConnectionReuse` 讓每一輪重建，`noConnectionReuse` 連同一輪裡的 keep-alive 也關掉。
- **Gatling**：預設每個虛擬使用者有自己的連線池與 SSL context，模擬各自的瀏覽器；`shareConnections` 讓所有虛擬使用者共用連線。open model 下每個虛擬使用者跑完 scenario 就結束，每個使用者至少握手一次。
- **Locust**：`HttpUser` 預設每個使用者一個連線池，連線在同一個使用者的各個 task 之間重用（官方文件〈Writing a locustfile〉）；設了 `pool_manager` 時同一個 class 的使用者共用。

例子：一個面向手機 App 的 API 前面有負載平衡器。用 JMeter 的 Open Model Thread Group 探測，每次抵達都握手，knee 落在負載平衡器的 CPU 上；改用內建 Thread Group 勾選 Same user on each iteration 之後，同樣的到達率下負載平衡器的 CPU 只用了一小部分，knee 往後移到應用程式的資料庫連線池。兩次量到的都是各自那種連線方式下的實際上限，差在哪一種連線方式接近 production：App 的用戶端多半長時間重用連線，勾選 Same user on each iteration 的那一次比較接近；每次造訪都重新建立連線的短暫流量，Open Model Thread Group 的那一次比較接近。

## 設計責任

負載工具的連線設定要跟 production 的用戶端重用連線的方式一致，握手佔每個請求的比例才相同，所以設計壓測的人要先知道 production 怎麼重用連線（瀏覽器與 App 多半 keep-alive 加 HTTP/2，服務之間的呼叫多半有連線池，短暫造訪、爬蟲與每次重新登入的流量常常每次重建），才選得出工具的設定；把這次用的連線設定寫進壓測的執行條件，下一次比較時才知道兩次的握手比例相同。量到的上限落在 TLS 終結層時，容量結論寫明它是那一層在這個連線方式下的上限，要擴的是那一層（多開代理、換成簽名較便宜的 ECDSA 憑證、開 session resumption），不是應用程式的副本數。施壓端自己也要做握手的運算，每次都重建連線時施壓端的 CPU 也比較早到頂（[Load Generator Saturation](/backend/knowledge-cards/load-generator-saturation/)）；短連線大量建立時，施壓端的來源埠可能停在 TIME_WAIT 而用完。到達率與在線人數這兩種注入方式對連線的影響見 [Open and Closed Workload Model](/backend/knowledge-cards/open-closed-workload-model/)。
