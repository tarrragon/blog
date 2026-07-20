---
title: "流量入口層 — 請求怎麼從使用者到達應用"
date: 2026-07-20
description: "自管環境要決定請求從使用者到應用經過哪幾層入口、每層承擔什麼——TLS 終結的位置、動靜分離、單機 reverse proxy 與雲端負載平衡器的選擇"
weight: 3
tags: ["infra", "network", "reverse-proxy", "load-balancer", "dns"]
---

流量入口層是一條請求從使用者鍵入網址到抵達應用程式所經過的責任鏈。每一段各自承擔一件事：把域名解析成位址、把流量分到還活著的後端、在後端前面終結加密與分流、最後才由應用處理業務邏輯。這條鏈的存在是為了把「對外的穩定介面」跟「對內的可變後端」分開——後端可以增減、替換、搬家，使用者連的入口位址不變。

共享主機時代這條鏈是隱形的。cPanel 或 Plesk 把域名、憑證、web server、應用執行環境全部包在同一台機器、同一套面板後面，使用者只需要在面板點幾下綁定網域、開啟 AutoSSL，整條入口鏈就「自己接好了」。接手一個自管環境（VPS 或雲端）之後，這些原本被面板吸收掉的步驟，每一個都變回一個要自己下的決定：DNS 指向哪裡、要不要一層負載平衡、TLS 在哪一層解開、靜態檔案誰來回。

這篇文章要建立的判斷力是「我的服務需要幾層入口、每層放什麼」，而不是某一種 web server 的配置語法。責任鏈的每一段先講清楚它承擔什麼、什麼訊號代表它出問題，再把兩個核心的架構選擇（TLS 終結放哪層、單機 [reverse proxy](/infra/knowledge-cards/reverse-proxy/) 還是雲端負載平衡器）展開成可操作的判準。runtime 的調校（負載分散演算法、健康檢查參數、timeout 串接）是[運維 模組一：負載平衡與反向代理](/operations/01-load-balancing/)的範圍，這裡先把入口層的地圖畫出來。

## 從一個網址到一個回應：責任鏈的四次交棒

一條 HTTP 請求從使用者到應用，中間經過最多四段獨立的責任，每一段把處理好的結果交棒給下一段。理解入口層就是理解這四次交棒各自完成了什麼。

第一段是 [DNS](/infra/knowledge-cards/dns/) 解析：使用者的瀏覽器拿著域名去問 DNS，換回一個可連線的位址。第二段是負載平衡：流量抵達入口位址後，由一層負載平衡器從多台後端裡挑一台還健康的送過去。第三段是 reverse proxy：在後端應用前面，由它解開 HTTPS 加密、依 URL 決定送到哪個服務、把靜態檔案直接回掉。第四段才是應用伺服器：跑業務邏輯、查資料庫、產生真正的回應。回應再沿原路逐段交棒回使用者。

這四段不是每個服務都要各配一台獨立設備。它們是四種責任，可以分散在四層設備上，也可以壓縮到同一台機器。共享主機就是把後三段壓縮到一台 Apache 上——同一個 process 收 HTTPS、跑 PHP、回靜態圖片，DNS 則由面板或域名商代管。壓縮成一層在單機、低流量時完全合理；責任鏈之所以要展開成多層，是因為可用性與流量規模長大之後，把它們分開才能各自獨立擴縮、獨立故障、獨立收斂。判斷「需要幾層」的核心，就是判斷這條鏈該在哪幾個交棒點切開。

這條鏈的最前面還可以再疊一層本文不展開的入口——CDN（內容遞送網路）。需要就近服務地理分散的使用者、或要在邊緣吸收 DDoS 並回應靜態內容時，DNS 會指向 CDN 而不是直接指向源站入口，由 CDN 在邊緣終結 TLS、回應快取命中的靜態資源，只把 cache-miss 與動態請求回源到下面這條鏈。CDN 承擔的是邊緣遞送與快取，跟本文聚焦的源站入口鏈是不同層的責任；這裡先把源站這條鏈畫清楚，邊緣層另屬 CDN 的主題。四次交棒是源站側的完整責任集合，不是「使用者到應用」的唯一路徑。

## DNS：責任鏈的門牌，不承載流量

DNS 承擔的是把域名解析成入口位址這一件事，它是責任鏈的第一段，但它不承載後續的請求流量。瀏覽器向 DNS resolver 問一次 `example.com` 的位址，拿到結果後就直接對那個位址建立連線，後面的 HTTP 請求與回應都不再經過 DNS。這個「只在連線前查一次」的性質，把 DNS 的判讀重點落在指向與切換這兩件事上，效能不是它的判讀軸。

DNS 在自管環境的關鍵決策是指向哪裡。共享主機時代，域名商或面板把一筆 A record 指向那台主機的固定 IP 就結束了。自管之後，入口設施的位址可能會變——雲端負載平衡器重建後換一個 hostname、VPS 抽換後換一個 IP。穩健的做法是讓 DNS 指向一個穩定的別名，而不是易變的原始位址：雲端環境用 [ALB](/infra/knowledge-cards/alb/) 前面掛一筆 Route 53 alias record，對外暴露的是自己的網域、內部指向會變的 ALB hostname 由 alias 自動追蹤。

判讀訊號：DNS 切換的生效速度由 TTL 決定，而 TTL 是遷移與回退時唯一能提前準備的槓桿。平常 TTL 設 3600 秒足夠；要切換入口（遷移平台、換 IP）之前先把 TTL 降到 300 秒，讓各地 resolver 的舊快取快速過期，切換才能在分鐘級生效、出問題也能快速回退。這條在[平台遷移](/infra/upgrade/platform-migration/)的 DNS 切換段有完整的操作步驟與 Route 53 指令。DNS 只負責「域名對到哪個入口」，至於流量抵達入口後怎麼分，是負載平衡層的職責。

## 負載平衡：L4 與 L7 的分界

負載平衡層承擔的是把抵達入口的流量分配到多台後端、並把不健康的後端從輪替裡摘除。它存在的前提是後端有多台——單一後端沒有「分配」的問題。這一層最基本的判斷是它讀到請求的哪一層資訊來做決定——L4 與 L7 的分界看的是讀取層級，而不是 vendor 招牌。

L4 負載平衡器工作在傳輸層，只看 IP 與埠。它不拆開封包內容、不理解 HTTP，收到一條 TCP 連線就依規則轉給某台後端，全程不碰加密內容。因為不解析應用層，它的轉發成本極低、吞吐極高，也能承載任何 TCP/UDP 協定（不限 HTTP）。AWS 的 Network Load Balancer（NLB）是這一類。

L7 負載平衡器工作在應用層，讀得懂 HTTP。它看得到 host header、URL path、cookie，因此能依「`/api` 導到 API 後端、`/` 導到前端」這種規則分流，也能在這一層終結 TLS、做應用層的健康檢查。AWS 的 [ALB](/infra/knowledge-cards/alb/) 是這一類。代價是它要解析每個請求，單位成本高於 L4。

| 面向       | L4（如 NLB）                                        | L7（如 ALB）                                          |
| ---------- | --------------------------------------------------- | ----------------------------------------------------- |
| 讀取層級   | 傳輸層（IP、埠）                                    | 應用層（HTTP host、path、header）                     |
| 路由依據   | 目標埠與轉發規則                                    | URL path、host header、cookie                         |
| TLS        | 通常透傳到後端、或在 L4 卸載                        | 在入口終結（讀 HTTP 需要先解密）                      |
| 適用協定   | 任何 TCP / UDP                                      | HTTP / HTTPS / gRPC                                   |
| 選它的訊號 | 非 HTTP 協定、極高吞吐、要保留來源 IP、要端到端加密 | 依路徑或網域分流、在入口終結 TLS、HTTP 感知的健康檢查 |

選 L7 的典型情境是多個 HTTP 服務共用一個網域、靠 path 或 host 分流，而且希望在入口就把 HTTPS 解掉讓後端只收 HTTP——這涵蓋了大多數 web 應用。選 L4 的情境更專門：後端跑的是非 HTTP 協定（資料庫協定、遊戲的自訂 TCP、MQTT）、需要極致吞吐而不能付應用層解析成本、或合規要求加密必須端到端不能在入口解開（讓 TLS 透傳到後端自己終結）。這一層挑好之後，怎麼在多台健康後端之間分配下一個請求（round-robin、least-connection、雜湊）是[負載分散演算法](/operations/01-load-balancing/load-balancing-algorithms/)的主題。

## reverse proxy：橫切關注點的集中點

reverse proxy 承擔的是代替後端應用接收外部請求、再依規則轉發給內部服務。它坐在應用前面，把幾件「每個後端都需要、但不該每個後端各做一份」的橫切關注點收攏到一層：終結 TLS、依 URL 分流、把靜態檔案直接回掉、加安全標頭、限流。使用者連的永遠是 reverse proxy，它背後有幾台應用、跑什麼語言、在哪個 subnet，使用者不需要知道。

[nginx](/infra/knowledge-cards/nginx/) 是單機環境最常見的 reverse proxy 實作。它以集中的設定檔取代 Apache 分散的 `.htaccess`，用 `proxy_pass` 把請求轉給後端的應用伺服器（PHP-FPM、Node.js、Python WSGI）。在雲端，L7 負載平衡器（ALB）本身就內建了大部分 reverse proxy 的職責——TLS 終結、path 路由、健康檢查——所以雲端環境不一定需要另一層獨立的 nginx。這兩者的關係是本文後段「單機 nginx vs 雲端 ALB」要展開的核心選擇。

[動靜分離](/infra/knowledge-cards/static-dynamic-separation/)是 reverse proxy 這一層最具體的判斷。靜態資源（圖片、CSS、JS、字型）不需要應用邏輯就能回應，讓 reverse proxy 直接從檔案系統回掉，動態請求才轉發給應用伺服器。這樣做把應用伺服器的工作量集中在真正需要它的請求上——一個載入 50 個靜態資源、只有 1 個動態 API 呼叫的頁面，應用伺服器只需要處理那 1 個。共享主機時代 Apache 加 mod_php 把動靜都吃在同一個 process 裡，動靜分離是隱形的預設；自管的 nginx 要在設定裡明確劃出「哪些路徑走檔案、哪些路徑走 `proxy_pass`」。reverse proxy 四類職責（TLS 終結、路由、負載分散、健康檢查）的設計邊界與 timeout 由外到內遞減的紀律，在[反向代理的職責](/operations/01-load-balancing/reverse-proxy-responsibilities/)展開。

## TLS 終結放在哪一層

TLS 終結指的是責任鏈上由哪一層解開 HTTPS 加密，這個位置決定了鏈上哪幾段是密文、哪幾段是明文。共享主機時代這個決定由面板的 AutoSSL 代掉，使用者不會意識到「憑證裝在哪、加密在哪解」。自管之後，終結點變成一個明確的架構選擇，落在下面幾種安排。

終結在負載平衡器是雲端環境的預設做法。ALB 的 HTTPS listener 掛一張 ACM（AWS Certificate Manager）簽發的憑證，ALB 解密後把明文 HTTP 交給後端，後端不必各自持有憑證、不必各自做加解密。憑證由 ACM 搭配 [DNS](/infra/knowledge-cards/dns/) 驗證自動續期，整條「簽發、續期、掛載」進 IaC 版本控制。這套 ALB 加 ACM 的完整 IaC 描述在[模組五：入口上 IaC](/infra/05-core-services/loadbalancer-alb/)。

終結在 reverse proxy 是單機環境的對應做法。nginx 掛一張 [SSL/TLS](/infra/knowledge-cards/ssl-tls/) 憑證（VPS 上常用 Let's Encrypt 搭配 certbot 自動續期），解密後把請求轉給同機或內網的應用。共享主機遷到 VPS 後的憑證續期驗證在[平台遷移](/infra/upgrade/platform-migration/)的 SSL 段有具體指令。

後端這段也要加密時有兩種不同的安排，差別在入口層有沒有看到明文。透傳到後端（TLS passthrough）是入口層完全不解密，把加密流量原封轉給後端由後端自己終結——它保證中間沒有任何一跳是明文，代價是入口層看不到 HTTP 內容，無法做 path 路由與應用層健康檢查，等於退回 L4。重新加密（TLS re-encryption，又稱 TLS bridging）則是入口層先解密（因此讀得到 HTTP、能做 path 路由與健康檢查），處理完再對後端開一條新的 TLS 連線把流量重新加密送過去。兩者都讓後端這段是密文，但透傳全程不解密、放棄 L7 能力，重新加密在入口解一次、對後端再加一次、L7 路由與端到端加密都保住，代價是入口多付一次加解密成本。合規要求內網也不得明文、但入口又需要依 path 或 host 分流時，選的是重新加密而不是透傳。

判讀的核心是入口到後端這段網路可不可信。多數設計讓入口終結、後端收明文，因為後端住在 [private subnet](/infra/knowledge-cards/subnet/)、只接受來自入口 [security group](/infra/knowledge-cards/security-group/) 的流量，這段內網被視為可信；只有當合規把「這段也必須加密」寫成硬要求時，才付出重新加密或透傳的成本，並在兩者之間按「還需不需要 L7 分流」選擇。這個位置決策本身、以及它和後端信任模型的關係，在[反向代理的職責](/operations/01-load-balancing/reverse-proxy-responsibilities/)的 TLS 終止段有更完整的討論。

## 健康檢查與摘除：入口層怎麼知道後端還活著

健康檢查是入口層持續探測後端能不能服務、並把不能服務的後端從輪替裡摘除的機制。這個能力在單機環境不存在——只有一台應用，它活著就有服務、死了就整站掛，沒有「從輪替摘除」的餘地。責任鏈展開成多後端之後，入口層才需要一個判斷「這台還能不能接流量」的依據，讓請求不會落到一台已經壞掉的後端上。

摘除的語意是：健康檢查連續失敗到閾值，入口層就把那台後端標記為 unhealthy、停止分配新請求給它，流量自動重導到其餘健康的後端。這條路徑在部署時最容易出狀況——滾動部署把舊的服務實例停掉、新實例還沒通過健康檢查的那個空窗，target group（ALB 登記後端的分組清單、健康檢查與流量分配都以它為單位）裡沒有任何健康後端，使用者會看到 503。這也是為什麼健康檢查的路徑要用應用層的專屬 health endpoint（真的能反映應用狀態）而不是根路徑，閾值要在「太寬鬆把壞後端留在輪替」與「太嚴格在部署瞬間誤判」之間取平衡。ALB 的健康檢查參數、502 與 503 的分辨在 [ALB 卡](/infra/knowledge-cards/alb/)有可觀察訊號的對照；被動觀察與主動探測的差別、interval 與 threshold 的設計、flapping 的成因在[健康檢查路由設計](/operations/01-load-balancing/health-check-routing/)展開。

## 單機 nginx vs 雲端 ALB：選擇條件

單機 reverse proxy 與雲端受管負載平衡器之間的選擇，取決於服務對可用性的要求與運維的規模，而不是哪一個「比較先進」。兩者都能扮演入口，差別在於誰承擔跨可用區冗餘、誰承擔設備本身的運維、以及固定成本的形狀。這是自管環境接手後最實際的一個入口層決策。

| 面向         | 單機 nginx                         | 雲端 ALB                                                     |
| ------------ | ---------------------------------- | ------------------------------------------------------------ |
| 誰運維設備   | 自己（裝、配、reload、修）         | 雲端受管，設備本身不用維護                                   |
| 跨可用區     | 單機、單一可用區                   | 跨可用區冗餘，單區故障自動轉移                               |
| 健康檢查摘除 | 開源版只有被動、主動探測是商業功能 | 內建主動健康檢查與自動摘除                                   |
| TLS 續期     | 自己配 certbot / Let's Encrypt     | ACM 自動續期，進 IaC                                         |
| 成本形狀     | 一台機器的固定月費                 | 固定每小時費 + 按用量的 LCU（Load Balancer Capacity Unit）費 |
| 前置依賴     | 一台 VPS 就能跑                    | 需要規劃好的 VPC、public / private subnet                    |

單機 nginx 適合單一節點或低流量、且運維能力有限的服務。它的優點是輕、便宜、一台 VPS 就能跑起來，配置與問題排查都在自己手上。它的邊界是單機即單點——這台機器或它所在的可用區掛了，整個入口就斷了；而且開源 nginx 的主動健康檢查是商業版功能，只配開源版時拿到的是被動健康檢查（靠實際請求失敗才發現後端壞掉），不是主動探測，這一點不知道會誤以為配了主動探測、實際上沒生效（見[nginx 實務配置](/operations/01-load-balancing/nginx-configuration/)）。

雲端 ALB 適合多後端、要求跨可用區高可用、且已經有網路地基的服務。它的優點是受管——跨可用區冗餘、主動健康檢查與自動摘除、ACM 憑證續期都由平台承擔，不必自己維護設備。它的邊界是前置依賴與成本形狀：ALB 要掛在 public subnet、把流量導向 private subnet 的後端，這條前提要求先有規劃好的網路（見[網路地基](/infra/03-network-foundation/vpc-subnet-security-group/)）；成本是固定每小時費加按用量的 LCU 費，低流量時單位成本不見得比一台小 VPS 划算。

兩者也常常疊用而非二選一。大型部署常見的形狀是 ALB 在最外層承擔跨可用區分流與 TLS 終結，每台後端節點上再跑一個 nginx 承擔應用專屬的路由與靜態檔案回應。這時 ALB 與 nginx 是責任鏈上相鄰的兩段、各守一段職責——ALB 做 L7 入口與冗餘，nginx 做貼著應用的動靜分離與 rewrite。

什麼情境不需要多層入口，是這個選擇的反面。一個單節點的內部工具、一個還在驗證需求的 MVP、一個流量穩定在單機容量內的小站，一台 nginx（甚至應用框架內建的 HTTP server）就是完整的入口，硬加一層 ALB 加多可用區只是把成熟階段才需要的可用性成本提前付掉，換不到對應的價值。這呼應[模組零](/infra/00-infra-mindset/)的成熟度階梯：入口層的層數該跟著可用性要求與流量規模長，而不是為了架構看起來完整而堆疊。

## 我的服務需要幾層入口

入口層的層數由可用性要求與流量形狀決定，把這條責任鏈在剛好夠用的交棒點切開，就是這篇要帶走的判斷。層數不是愈多愈好——每多切一層，就多一層要運維、要監控、要付固定成本的設備。

判讀從三個問題收斂。第一，後端是單台還是多台：單台就沒有負載平衡與健康檢查摘除的需求，一個 reverse proxy（單機 nginx）或直接讓應用對外就夠；多台且要求單點故障不中斷，才需要一層負載平衡器承擔分流與摘除。第二，流量是 HTTP 還是其他協定：HTTP 且需要依 path / host 分流、在入口終結 TLS，選 L7（ALB）；非 HTTP、要極致吞吐、或要端到端加密透傳，選 L4（NLB）。第三，TLS 要在哪裡解開：內網可信就終結在入口讓後端收明文，合規要求全程加密才做重新加密或透傳。

實際的入口配置指令——nginx 的 `try_files` 動靜分離與 `proxy_pass` 轉發、`.htaccess` 規則怎麼轉成 nginx、Route 53 的 DNS 切換——在[平台遷移](/infra/upgrade/platform-migration/)有可對照的範例；ALB 的 listener、target group、TLS 與健康檢查怎麼寫成 IaC 在[模組五：入口上 IaC](/infra/05-core-services/loadbalancer-alb/)。入口設施該落在哪個 subnet、它的 security group 只開哪些埠，是[網路地基](/infra/03-network-foundation/vpc-subnet-security-group/)已經鋪好的地圖——ALB 掛 public subnet、後端住 private subnet、對外只有 80 / 443 合理開向 `0.0.0.0/0`。入口層的責任鏈規劃好之後，核心服務怎麼落進這些 subnet、負載平衡器怎麼上 IaC，是[模組五：核心服務上 IaC](/infra/05-core-services/)的主題。

## 跨分類引用

- → [網路地基 — VPC、subnet 分層與 security group 設計](/infra/03-network-foundation/vpc-subnet-security-group/)：入口設施落在哪層 subnet、security group 只開哪些埠
- → [平台遷移](/infra/upgrade/platform-migration/)：`.htaccess` 轉 nginx、DNS 切換與 SSL 續期的具體指令
- → [模組五：入口上 IaC](/infra/05-core-services/loadbalancer-alb/)：ALB 的 listener、target group、TLS 與健康檢查的完整 IaC
- → [運維 模組一：負載平衡與反向代理](/operations/01-load-balancing/)：負載分散演算法、健康檢查參數、timeout 串接的 runtime 調校
- → [接手維運：無 SSH 的 FTP 環境](/infra/takeover/legacy-ftp-no-ssh/)：共享主機環境的盤點，入口鏈自管化的起點
