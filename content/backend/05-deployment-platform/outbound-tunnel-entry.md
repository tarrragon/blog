---
title: "5.10 Outbound Tunnel 入口與生命週期"
date: 2026-06-16
description: "整理 cloudflared、Tailscale 這類反向隧道入口：家用主機用 Proxied 紀錄或 Cloudflare Tunnel 接上 Cloudflare 時各自要求的網路條件、經過 Cloudflare 代理要接受的限制、公開網站與管理服務分給 Tunnel 與 mesh VPN 的取捨、只聽本機的 HTTP 服務用 tailscale serve 給 tailnet 連的實測與代價、入口的生命週期合約、重連與冗餘、分層的故障判讀與認證的疊法"
weight: 10
tags: ["backend", "deployment", "tunnel", "tailscale", "cloudflare"]
---

outbound tunnel 是一種入口形態：本機的程序主動往外連到 tunnel 服務商的邊緣節點（edge）並維持這條連線，外部的請求經由這條連線送回本機，路由器不必開任何入站的連接埠。它跟 load balancer 入口的差別在連線方向：LB 入口的前提是 instance 有對外可達的位址、流量從外網路由進來；tunnel 由本機往外連，所以主機沒有固定 IP、或架設的人不想或不能在路由器開連接埠時，家用主機與個人自架工具常用它。這篇整理的內容是：選這種入口的前提；家用主機要對外提供網站時，接上 Cloudflare 的兩種方式（Proxied 紀錄指向主機的公開 IP，以及 Cloudflare Tunnel）各自要求的網路條件，以及兩種方式下訪客的請求經過 Cloudflare 的路徑；經過 Cloudflare 代理時家用主機要接受的限制，與 Tunnel 連 HTTP 以外協定的方式；同一台主機的公開網站與管理服務分給 Tunnel 與 mesh VPN 的取捨、讓管理服務只給 tailnet 連的做法（監聽 `tailscale0` 的位址、主機防火牆只放行 `tailscale0`、只聽本機再由 `tailscale serve` 轉送，含 serve 的實測與它 HTTPS 模式的代價）、VPN 與救援入口的差別、給少數認識的人用的服務依連線方的形態接在哪一種入口，以及分開之後 `cloudflared` 與兩家帳號留下的風險；tunnel 入口的連線、就緒、啟停順序與認證合約；隧道的穩態、重連與多連線冗餘；故障的分層判讀；認證疊在 tunnel 之後的做法與常見誤區。源站在 CDN 後面時防火牆怎麼只放行 CDN 的位址，寫在 [CDN 後面的源站主機防火牆：只放行 CDN 來源的位置與套用時機、Docker 發佈連接埠的封包路徑、出站 DNS 的限制與地理封鎖](/devops/infra/03-network-foundation/origin-host-firewall/)；單人遠端操作自己主機的 shell 時 Tailscale 與 Cloudflare Tunnel 的比較，寫在 [7.C11 選型：單人遠端 Shell — Tailscale vs Cloudflare Tunnel](/backend/07-security-data-protection/cases/remote-shell-access-tailscale-vs-cloudflare-tunnel/)。

## 選 outbound tunnel 當入口的前提與典型場景

選 outbound tunnel 的前提是「要被外部觸及、但不想暴露公網入口」。典型場景：手機遠端操作自有主機、家庭網路內的服務對外、開發環境臨時對外驗證。服務本身值不值得自建、見 [0.21 交付形態選型](/backend/00-service-selection/delivery-mode-selection/) 的個人自架工具段;這裡只處理「入口形態選了 tunnel 之後」的部署合約。

cloudflared（綁 Cloudflare 邊緣與網域）、Tailscale（綁私有網路 / Funnel 對外）、Boundary 各有定位差異，但入口生命週期的判讀框架相同。

## 家用主機對外提供網站時接上 Cloudflare 的兩種方式：Proxied 紀錄指向公開 IP 與 Cloudflare Tunnel

網站放在 Cloudflare 後面時，訪客的請求先到 Cloudflare 的節點，Cloudflare 再把請求送到源站（origin，實際跑網站程式的主機）。把源站接上 Cloudflare 有兩種方式，兩者的差別在 Cloudflare 怎麼連到源站：

- **Proxied 紀錄**：管理者在網域的 A 紀錄填入源站的公開 IP，並把這筆紀錄的 Proxy status 設成 Proxied（Cloudflare 主控台上紀錄旁的雲朵圖示是橘色），下文把這種紀錄稱為 Proxied 紀錄。Proxy status 控制 Cloudflare 回給訪客哪一個位址：Proxied 時回 Cloudflare 自己的位址，訪客的請求先到 Cloudflare；另一個值 DNS only（灰色雲朵）回源站的公開 IP，訪客直接連源站，請求不經過 Cloudflare 的 WAF 與快取。DNS only 服務的是 Cloudflare 不代理的那些服務：Cloudflare 的〈Network ports〉寫明，跑在代理清單以外連接埠上的服務（例如 SSH）要用 DNS only 的紀錄；新增紀錄時開關的初始狀態沒有查證，看主控台上那個開關的位置。要讓網站的請求經過 Cloudflare 時，設成 Proxied。訪客解析網域時拿到的是 Cloudflare 的位址，Cloudflare 收到請求之後，自己對源站的公開 IP 建一條新連線（Cloudflare 的〈Encryption modes〉把這兩段稱為訪客到 Cloudflare 與 Cloudflare 到源站的兩條連線）。所以源站要有一個從網際網路連得進來的位址，並在 Cloudflare 代理的連接埠上接受連線。〈Network ports〉列出代理的 HTTP 連接埠是 80、8080、8880、2052、2082、2086、2095，HTTPS 連接埠是 443、2053、2083、2087、2096、8443。
- **Cloudflare Tunnel**：源站上常駐 Cloudflare 提供的連線程式 `cloudflared`，由它主動往外連到 Cloudflare 的網路並維持連線，Cloudflare 的〈Cloudflare Tunnel〉稱這是只有出站連線的模型（outbound-only connection model）。網域的紀錄是一筆 CNAME，指向 Cloudflare 替這條 tunnel 產生的 `<UUID>.cfargotunnel.com`（〈DNS records〉；`<UUID>` 是建立 tunnel 時取得的識別碼，依各人的 tunnel 而不同）。訪客的請求到了 Cloudflare 之後，經由那條往外建好的連線送進源站，源站不需要公開 IP，也不必再接受入站連線。

兩種方式在訪客那一端的路徑相同，請求都先到 Cloudflare，差別只在 Cloudflare 到源站的那一段。所以經由 Tunnel 送進來的請求同樣經過 Cloudflare，那個主機名稱在 Cloudflare 上的設定也作用在這些請求上：〈DNS records〉的〈Cloudflare settings〉寫明，經由 Tunnel 發佈的應用程式沿用那個主機名稱的 Cloudflare 設定，包括快取規則、WAF 規則與其他 Rules 設定（原文：Published applications inherit the Cloudflare settings for their hostname, including cache rules, WAF rules, and other Rules configurations），速率限制規則在 Cloudflare 屬於 WAF 底下的一種規則。Tunnel 決定的是 Cloudflare 怎麼連到源站，服務是公開的還是只給特定的人用，由那個網址前面是否疊上認證決定（〈認證必須疊在 tunnel 之後〉；在 Cloudflare 上限定身分用的是 Access，Access 與 Tunnel 在 Cloudflare 產品線裡的關係見 [Zero Trust（零信任）](/backend/knowledge-cards/zero-trust/)）。沒有疊認證的 Tunnel 網址任何人都連得到，跟 Proxied 紀錄的網站一樣是對外的服務。

Proxied 紀錄要求源站從網際網路連得進來；Tunnel 要求的是主機連得出去，而且出站要能連到 Cloudflare 的 7844 連接埠（UDP 給預設的 QUIC，TCP 給 http2；只放行 TCP 時要把 `cloudflared` 的協定指定成 http2，實測在 [Cloudflare 回源的實測紀錄：Oracle Cloud NSG 只放行 Cloudflare 位址與規則數上限、回源的來源位址、Authenticated Origin Pulls、Worker 偽造 CF-Connecting-IP 與 Tunnel 的出站連接埠](/devops/infra/03-network-foundation/hands-on/cloudflare-origin-pull-walkthrough/)）。下面依家用網路的條件，寫出兩種方式各自接不接得上：

- **電信業者級 NAT（carrier-grade NAT，CGNAT：電信業者讓多戶共用同一個公開 IPv4 位址，判讀方式見 [CGNAT](/devops/infra/knowledge-cards/cgnat/) 卡）**：家裡的路由器拿到的是電信業者內部的位址，網際網路上沒有一個 IPv4 位址連得到這台主機，A 紀錄沒有可填的值。在家裡的路由器設連接埠轉送（port forwarding）也沒有作用：入站的封包到了電信業者的 NAT，因為那裡沒有對應這台主機的轉送規則而被丟棄。Tunnel 不受影響。家用網路同時有 IPv6 時，主機可能有一個連得進來的 IPv6 位址、可以填進 AAAA 紀錄；這是依 IPv6 不經 NAT 的機制推論，沒有實跑。
- **浮動的公開 IP**：電信業者重新分配位址之後，A 紀錄還指著舊位址，要另外跑動態 DNS（dynamic DNS）的程式在位址改變時更新紀錄，更新之前訪客的請求送不到源站。Tunnel 的 CNAME 指向 tunnel 的識別碼，紀錄裡沒有源站的位址，位址改變之後 `cloudflared` 重新連上 Cloudflare，訪客的請求又送得到源站。
- **電信業者不讓住宅方案在 80 與 443 接受入站連線**：這類限制依電信業者與方案而不同，查法是讀方案的服務條款，或從家裡以外的網路對自己的公開 IP 連一次這兩個連接埠。這兩個連接埠的入站連線被擋時，用 Proxied 紀錄的管理者可以讓源站改聽一個沒被擋的連接埠，再用 Cloudflare 的 Origin Rules 覆寫回源的目的連接埠，訪客照樣連 443、網址不必改（依 Cloudflare〈Origin Rules〉的說明，沒有實跑）；不用 Origin Rules 時，源站要改聽代理清單裡的其他連接埠，訪客的網址也要帶上那個連接埠。Tunnel 不受影響。
- **路由器已設連接埠轉送（公開 IP 固定，或浮動而靠動態 DNS 更新）**：兩種方式都接得上。用 Proxied 紀錄時，源站留著一條直連路徑（origin bypass，[CDN](/devops/infra/knowledge-cards/cdn/) 卡寫了這個概念）：知道源站位址的人可以跳過 Cloudflare 直接連進來，Cloudflare 上的 [WAF](/backend/knowledge-cards/waf/) 規則對這條路徑不起作用。管理者要靠源站的防火牆只放行 Cloudflare 的位址，並用 Authenticated Origin Pulls（Cloudflare 回源時出示用戶端憑證，源站只接受帶憑證的連線）驗證請求是 Cloudflare 替這個網站的網域送來的、不是別的 Cloudflare 帳號經由同一批位址送來的。Authenticated Origin Pulls 用 Cloudflare 共用憑證的版本有實測，只證明請求來自 Cloudflare 的網路；自己上傳憑證、分辨得出網域的版本沒有實跑；做法在 [CDN 後面的源站主機防火牆](/devops/infra/03-network-foundation/origin-host-firewall/)。
- **原本設過連接埠轉送、從 Proxied 紀錄改用 Tunnel 時**：源站不必再收入站連線，但原本為 Proxied 紀錄開的直連路徑還在，管理者要做完兩件事它才關閉：關掉路由器上的連接埠轉送（路由器開著 UPnP 時，也要看它的轉送表，有些程式會經由 UPnP 自己開轉送，這是依 UPnP 的機制推論），以及讓網站程式只聽本機位址（跑在容器裡時，不發佈連接埠或只發佈在 `127.0.0.1`）。關掉轉送與只聽本機位址都做完，直連路徑才不存在；任一件沒做，直連路徑照樣開著（〈CDN 後面的源站主機防火牆〉的〈Docker 發佈的連接埠：封包路徑與限制的寫法〉裡 Cloudflare Tunnel 那一項，同一項也寫了 `cloudflared` 要常駐、主機要能出站與入口綁在 Cloudflare 一家這幾項代價）。

## 經過 Cloudflare 代理時家用主機要接受的限制：TLS 終結、上傳大小上限、影片與大型檔案的條款，以及 Tunnel 連 HTTP 以外協定的方式

源站（實際跑網站程式的主機）接上 Cloudflare 的兩種方式，Proxied 紀錄（DNS 紀錄設成讓訪客先連到 Cloudflare）與 Cloudflare Tunnel（源站上的 `cloudflared` 往外連到 Cloudflare），訪客的請求都經過 Cloudflare 的代理，所以代理帶來的限制兩種都有。下面的 TLS 終結、上傳上限與影片條款這幾項，因為不想開連接埠而選 Tunnel 時，選的同時也就接受了：

- **TLS 在 Cloudflare 終結（TLS termination，跟 [Reverse Proxy](/devops/infra/knowledge-cards/reverse-proxy/) 終結 TLS 是同一件事）**：訪客的瀏覽器跟 Cloudflare 建立 TLS 連線，Cloudflare 解密之後才讀得到 HTTP 的內容，WAF 比對規則、快取判斷回應能不能存，都要讀這些內容；Cloudflare 再用另一條連線送到源站（〈Encryption modes〉寫明這是兩條連線；Cloudflare 讀得到明文是從 WAF 與快取的運作推論，該頁沒有逐字寫出）。服務的內容要求只有訪客與源站兩端讀得到時，經過代理的兩種方式都不符合，要改走不經 Cloudflare 代理的路徑，各有前提：

  - **DNS only 紀錄**：訪客直接連源站，前提是源站有連得進來的位址、開著入站連接埠，正是選 Tunnel 想避開的條件。
  - **mesh VPN**（每台裝置裝用戶端、裝置之間以私有位址加密互連的 VPN，見〈同一台家用主機的公開網站與管理服務〉）：不經第三方解密，前提是每一位使用者的裝置都裝用戶端，所以只適用於自己與少數認識的人。
  - **Tailscale Funnel**：讓沒裝 Tailscale 的訪客也連得到 tailnet 裡的一個服務，主機不開入站連接埠；Tailscale 的〈Funnel〉寫明 Funnel 的中繼伺服器不解密流量，TLS 在自己的裝置上終結。代價是只能用 443、8443、10000 這幾個連接埠，入口綁在 Tailscale 一家，前面沒有 WAF 與快取；頻寬限制沒有查證。
- **單一請求的上傳大小**：Cloudflare 的〈Error 413〉寫明經過代理的請求，上傳上限依網域的方案而定：Free 與 Pro 是 100 MB，Business 是 200 MB，Enterprise 最高 5 GB。超過上限的請求，Cloudflare 回 413，請求到不了源站。自架的相簿、檔案同步這類要上傳大檔的服務，要在程式裡把檔案切成小於上限的片段上傳，或讓上傳改走 DNS only 紀錄、mesh VPN 或 Tailscale Funnel 這幾條不經 Cloudflare 代理的路徑（各自的前提寫在 TLS 終結那一項）。
- **影片與大型檔案**：Cloudflare 的〈Service-Specific Terms〉（頁面標示 2026 年 9 月 28 日更新）在 CDN 那一節寫明，使用 Free、Pro、Business 方案的帳號要經由 CDN 傳送影片與其他大型檔案，必須搭配 Cloudflare 的付費服務（條款舉的例子是 Developer Platform、Images 與 Stream）；沒有搭配時，Cloudflare 可以停用或限制這個帳號使用 CDN。條款原文寫的是經由 CDN 傳送，沒有提到 Tunnel；自架的影音串流服務（Jellyfin、Plex 這類）經由 Tunnel 對外時也落在這一條的範圍裡，是依〈DNS records〉寫的「Tunnel 發佈的應用程式沿用主機名稱的快取規則」推論：這些流量經過同一層代理與 CDN。什麼算大型檔案，以條款原文為準。
- **HTTP 以外的協定**：Cloudflare 對 Proxied 紀錄只代理〈Network ports〉列出的 HTTP 與 HTTPS 連接埠，SSH 的 22 不在其中；同一頁寫明其他連接埠要經過 Cloudflare 時，帳號要另購 Spectrum。依 Cloudflare〈Spectrum〉的各方案協定表，Pro 與 Business 加購之後只有 SSH、Minecraft（Business 另有 RDP）各一個應用程式能經過 Cloudflare，任意的 TCP 與 UDP 連接埠只限 Enterprise 方案。經由 Tunnel 連 SSH 時，Cloudflare 的〈SSH〉列了幾種做法，只有在瀏覽器裡開 Cloudflare 呈現的終端機這一種，連線的人不必在自己的裝置另外安裝 Cloudflare 的元件；其餘做法要在用戶端裝 `cloudflared`（在 ssh 設定裡用 `ProxyCommand` 執行 `cloudflared access ssh`）或 Cloudflare One Client，或讓用戶端所在的網路經由 Cloudflare WAN 接上 Cloudflare。資料庫、檔案分享這類協定也一樣，一般訪客的瀏覽器直接連不了（這一點是推論，沒有逐一核對各協定的用戶端需求）。所以 HTTP 以外、要給不特定訪客用的公開服務（UDP 的遊戲伺服器這類），在 Free 到 Business 方案上，Proxied 紀錄不代理它的連接埠，Tunnel 要訪客裝元件，兩種方式都接不上（從〈Network ports〉與〈SSH〉推論）。

## 同一台家用主機的公開網站與管理服務：分給 Tunnel 與 mesh VPN 的取捨，與分開之後仍然存在的風險

一台家用主機常同時有兩類要從外面連進來的服務：給任何訪客用的公開網站，以及只有管理者自己用的管理服務（SSH、NAS 的管理介面、資料庫、監控儀表板，屬於 [Management Plane](/backend/knowledge-cards/management-plane/) 的那一類入口）。管理者連到管理服務的那條路，站上稱為管理通道（[伺服器管理通道的設計：網路可達性、通道授權、主機登入驗證三層的做法與選擇，以及救援入口](/devops/infra/03-network-foundation/management-access-channel/)）。兩類服務的使用者不同，對入口的要求也不同：

- **公開網站**的訪客是任何人，一般的瀏覽器要能直接連到入口，入口前面要有擋攻擊的元件。經由 Tunnel 接上 Cloudflare 時，訪客不必另外安裝軟體，請求經過 Cloudflare 的 WAF 與快取，主機不開入站的連接埠。
- **管理服務**的使用者是管理者自己，他從自己的幾台裝置連線，可以在每台裝上用戶端。mesh VPN（每台裝置裝用戶端、裝置之間以私有位址加密互連的 VPN，Tailscale 是一例；它跟集中式 VPN 的差別見 [Mesh VPN](/devops/infra/knowledge-cards/mesh-vpn/) 卡）在每台裝置上建立一個 VPN 的網路介面；管理者讓管理服務只接受這個介面上的連線之後，公開網路上沒有任何位址連得到它們。管理者可以把服務的監聽位址設成這個介面的位址（Tailscale 在 Linux 上建立的介面是 `tailscale0`，位址是它分配的那一個），這時服務要排在 `tailscaled` 之後啟動，否則開機時綁不上那個位址而啟動失敗（依 bind 的行為推論，沒有實跑），用 systemd 時在服務的 unit 裡設定啟動順序；或讓服務照樣聽所有位址，在主機防火牆上只放行來自 `tailscale0` 的連線；或讓 HTTP 服務只聽 `127.0.0.1`，由 `tailscale serve` 在 tailnet 上接收連線再轉給它，實測與代價寫在這一節最後的〈用 tailscale serve 讓只聽本機的 HTTP 服務給 tailnet 連：實測、限制與 HTTPS 模式的代價〉。服務直接在 `tailscale0` 上接受連線時，SSH、SMB 這些 HTTP 以外的協定直接可用；裝置之間的流量由兩端的 WireGuard 金鑰加密，Tailscale 的〈DERP servers〉寫明經由它的 DERP 中繼轉送時，中繼伺服器也解不開。Tailscale 的連線同樣由裝置主動往外建立，但管理服務仍然在 VPN 介面上接受入站連線，所以本篇照 [伺服器管理通道的設計](/devops/infra/03-network-foundation/management-access-channel/) 的歸類把 Tailscale 當成 VPN，跟 Cloudflare Tunnel 對照。Tailscale 在 CGNAT 與浮動 IP 之下怎麼維持裝置之間的連線，見 [Tailscale 深入：tailnet、MagicDNS、直連與 DERP 中繼](/linux/tools/remote/tailscale-tailnet-and-relay/)。

管理服務的入口有兩種做法：走 mesh VPN；或也走 Tunnel，再用 Cloudflare Access 限定只有管理者連得到。Cloudflare Zero Trust 方案裡的 Access 只負責驗證身分，管理服務接上 Cloudflare 的連線仍然靠 Tunnel（兩者的關係見 [Zero Trust（零信任）](/backend/knowledge-cards/zero-trust/)）。兩種做法的差別：

- **管理服務走 mesh VPN**：管理服務在公開網路上沒有網址，網際網路上的掃描程式連它的登入頁都碰不到；`cloudflared` 停掉、Tunnel 的設定改壞或 Cloudflare 的邊緣出事故時，管理者仍然經由 VPN 連得進主機去修；管理者連 SSH 這類協定時，也不必在用戶端另裝 `cloudflared`。
- **管理服務也走 Tunnel 加 Access**：管理服務有公開的網址，掃描程式碰得到 Access 的登入頁，碰不到管理服務本身。管理者連進主機的唯一路徑就是 Tunnel，Tunnel 壞掉時這條路徑跟著斷，要修 Tunnel 得另找一條不經 Tunnel 的路徑。

VPN 是獨立於 Tunnel 的第二條管理通道，不是救援入口：主機的網路設定或 `tailscaled` 本身壞掉時，管理者經由 VPN 也連不進去，這時靠的是不經主機作業系統網路設定的救援入口。家用主機的救援入口是接上螢幕與鍵盤的實體主控台，要人在主機旁才用得到；管理者人在外地時，要等回到主機旁才修得了，遠端的救援方式見〈伺服器管理通道的設計〉的〈救援入口：管理通道斷掉時的備用路徑〉。

兩種做法可以並存：管理服務平時走 mesh VPN，另外開一個 Tunnel 加 Access 的瀏覽器終端機，給裝不了用戶端的裝置用。並存時 Tunnel 壞掉還有 VPN 可以進主機，代價是多一個公開的登入頁，Cloudflare 帳號被別人拿到時暴露的範圍也跟著變大。

介於公開網站與管理服務之間的，是給少數認識的人用的服務（家人共用的相簿、智慧家居的控制台）。這類服務的落點看連線方是什麼形態，因為 mesh VPN 要求連線方的裝置裝用戶端，而 Access 的身分檢查要求連線方在瀏覽器裡登入：

- **每一位使用者的裝置都能裝 mesh VPN 的用戶端**：走 mesh VPN，流量不經第三方解密，也不受 Cloudflare 的上傳上限與影片條款限制。家人的裝置加進管理者的 tailnet 時，Tailscale 預設讓 tailnet 裡的裝置全部互通，家人的裝置也連得到管理服務，所以要用存取規則把他們的裝置限定在那一個服務的連接埠（存取規則的寫法見 [7.43 兩個網路之間的連線安全](/backend/07-security-data-protection/cross-network-connection-security/) 的〈WireGuard 與 Tailscale 的金鑰與控制平面〉）。服務與管理介面是同一個程式、同一個連接埠時，存取規則用連接埠分不開兩者。
- **連線方是瀏覽器裡的人，而有人裝不了用戶端**：走 Tunnel，在網址前面疊 Access 限定身分，同時接受〈經過 Cloudflare 代理時家用主機要接受的限制〉列的幾項。
- **連線方是外部雲端服務的回呼（語音助理、webhook）**：回呼不會在瀏覽器裡登入，疊上要求身分的 Access 規則之後回呼會被擋下；要讓它通過，只能替那一條路徑設 Access 的 Bypass 規則，而 Cloudflare〈Access policies〉寫明 Bypass 不執行任何 Access 的安全控制、請求也不留紀錄（原文：Bypass does not enforce any Access security controls and requests are not logged）。那一條路徑等於公開，要靠服務自己驗證回呼帶來的簽章或 token。
- **連線方是原生 App（相簿 App、檔案同步程式、電視上的播放程式）**：App 走的是 API，過不了瀏覽器的 Access 登入；先查 App 支不支援 Access 的 service token 或用戶端憑證，不支援時只剩 mesh VPN，裝置也裝不了 VPN 用戶端時（多數電視），這兩種入口都接不上，剩下的是 Tailscale Funnel 或 DNS only 紀錄這類對外公開、靠服務自己認證的入口（各 App 的實際行為沒有查證）。

公開網站與管理服務分開時，管理者付出的是兩家服務商、兩組帳號與兩組憑證要管理，兩邊事故的影響範圍也不同：Cloudflare 的邊緣不可用時，訪客全部連不到公開網站；Tailscale 的協調伺服器（coordination server）不可用時，新裝置加入與新連線的金鑰交換受影響，已經建立的 WireGuard 連線仍然存活（[7.C11 選型：單人遠端 Shell — Tailscale vs Cloudflare Tunnel](/backend/07-security-data-protection/cases/remote-shell-access-tailscale-vs-cloudflare-tunnel/) 的〈核心選型維度〉）。管理者要從裝不了用戶端的裝置（借來的電腦、公司管控的筆電）連進管理服務時，mesh VPN 用不了，管理服務要放在 Tunnel 加 Access 後面，用瀏覽器裡的終端機連線；代價是 Tunnel 壞掉時，管理者連進主機的路徑跟著斷，修 Tunnel 要等回到主機旁。

公開網站與管理服務分開之後，`cloudflared` 仍然跑在同一台主機上，主機連得到的位址它都連得到，是主機上一個連得到全部內部服務的起點（[Lateral Movement](/backend/knowledge-cards/lateral-movement/)）。Tunnel 由 Cloudflare 主控台管理設定時（Cloudflare〈Useful terms〉稱為 remotely-managed tunnel，設定存在 Cloudflare、可以從主控台或 API 修改），〈Create a tunnel (dashboard)〉讓管理者替每個網址填要轉送到的服務位址（例子是 `http://localhost:8000`），Cloudflare 帳號因此是改得到可達範圍的 [Control Plane](/backend/knowledge-cards/control-plane/)。Cloudflare 帳號被別人拿到的話，對方可以刪掉或放寬 Access 規則，讓走 Tunnel 加 Access 的服務直接公開，也可以新增一個網址，轉送到主機連得到的任何服務，包括只聽 VPN 介面的那些（從這兩頁推論，沒有實跑；設定改由主機上的設定檔管理的 locally-managed tunnel，沒有查證主控台是否改得了它的轉送）。Tailscale 的帳號是同一類位置：拿到 Tailscale 管理主控台的人可以把自己的裝置加進 tailnet、改存取規則，直接連到只聽 VPN 介面的管理服務（從機制推論）。所以兩家的帳號都要開多因素驗證、收窄權限；Tailscale 的控制平面還有哪些防護（Tailnet Lock 這類），見 [7.43 兩個網路之間的連線安全](/backend/07-security-data-protection/cross-network-connection-security/) 的〈WireGuard 與 Tailscale 的金鑰與控制平面〉，tailnet 預設互通時一台被入侵的裝置連得到哪裡，見同一篇的〈連線清單上各台的可達範圍與假設入侵〉。

### 用 tailscale serve 讓只聽本機的 HTTP 服務給 tailnet 連：實測、限制與 HTTPS 模式的代價

管理服務要給 tailnet（同一個 Tailscale 帳號底下互連的裝置所組成的網路，見 [Mesh VPN](/devops/infra/knowledge-cards/mesh-vpn/) 卡）裡的裝置連，又不想在任何對外的網路介面上接受連線、也不想處理綁定 `tailscale0` 時的開機順序時，可以讓服務只聽 `127.0.0.1`，由 `tailscale serve` 轉送。`tailscale serve` 是 Tailscale 內建的[反向代理](/devops/infra/knowledge-cards/reverse-proxy/)：Tailscale 在主機上的常駐程式 `tailscaled` 在 tailnet 上接收連線，再轉給本機的那個服務，其他主機經由任何網路介面都連不到服務本身。下面的結果是在一台 macOS 主機上（Tailscale 1.104.5）實測，測試服務是只聽 `127.0.0.1:18080` 的 HTTP 伺服器。實測時 tailnet 裡其他裝置都離線，每一項的連線方都是這台主機自己，經由它自己的 tailnet 名稱與位址連；從 tailnet 裡另一台裝置連的結果沒有實測。這一節寫出的內容是：指令與參數、用名稱與用 `100.x` 位址連的差別（用位址連回 404）、服務停掉時的 502、服務看到的來源位址與 serve 加上的標頭（含偽造的標頭會怎樣）、tag 裝置與 Funnel 的請求不帶身分標頭、tailnet 的存取規則對 serve 的作用、這種做法的代價，以及 HTTPS 模式的前提、名稱公開與它跟 `tailscale funnel` 共用連接埠的風險。

```bash
tailscale serve --bg --http=8080 http://127.0.0.1:18080   # 在 tailnet 的 8080 接收，轉給本機 18080
tailscale serve status                                    # 列出目前的轉送設定
tailscale serve --http=8080 off                           # 移除這一條轉送
```

`--http=8080` 是 tailnet 這一端接收連線的連接埠，最後那個引數是轉送的目的地，填服務實際聽的本機位址與連接埠。這次實測的是 macOS 的 App 版本，指令不必加 `sudo`；依〈Tailscale Serve〉，在 Linux 與 macOS 的開源版用戶端上要用 `sudo` 執行（沒有實測）。不帶 `--http` 時，serve 預設用 HTTPS 模式在 443 接收（`--help` 寫的是 default mode）。HTTPS 模式會替機器申請 Let's Encrypt 憑證，所以這個預設對應的是要讓瀏覽器拿到有效憑證的用法（這是從自動申請憑證推論的，Tailscale 的〈Tailscale Serve〉沒有寫預設 HTTPS 的意圖），代價見本節最後一段；這次改成 `--http`，因為只要 tailnet 裡連得到，不需要瀏覽器信任的憑證。

`--bg` 控制 serve 是不是在背景持續執行。不帶 `--bg` 時，serve 跟著這條指令在前景執行，指令結束轉送就停，適合臨時試一次；要讓轉送在關掉終端機之後繼續存在時帶 `--bg`，移除要另外下 `off`。依〈Tailscale Serve〉，帶 `--bg` 的設定在主機重開機與 `tailscale down`、`up` 之後自動恢復（這次沒有實測重開機）。

實測看到的行為：

- 開 serve 之前，連主機 tailnet 位址的 18080，連線被拒絕。開了之後，用 MagicDNS（Tailscale 替 tailnet 裡的裝置解析名稱的功能，這次的 tailnet 有開；它的代價見 [Tailscale 深入：tailnet、MagicDNS、直連與 DERP 中繼](/linux/tools/remote/tailscale-tailnet-and-relay/) 的〈MagicDNS：用主機名而非 IP〉）的完整名稱（`http://<機器名稱>.<tailnet 名稱>.ts.net:8080/`），或只寫機器名稱的短名稱（`http://<機器名稱>:8080/`），都連得到服務的內容。機器名稱在 `tailscale status` 查得到，完整名稱在 `tailscale status --json` 的 `Self.DNSName` 查得到。
- 改用主機的 tailnet 位址（Tailscale 分配給每台裝置的 `100.x` 位址）連 8080，serve 回 404，請求沒有送到服務。Tailscale 原始碼（`ipn/ipnlocal/serve.go` 的 `getServeHandler`）用請求的 Host 標頭查轉送設定：Host 是短名稱時先補上 `.<tailnet 名稱>.ts.net` 再查，所以短名稱查得到；Host 是 `100.x` 位址時查不到對應的設定，所以連線方要用名稱連。
- 連主機區網位址的 8080，連線被拒絕；serve 只在 tailnet 上接收連線。
- 服務停掉之後，用名稱連，serve 回 502。
- 服務收到的 TCP 連線，來源都是 `127.0.0.1`。請求裡多了 serve 加上的標頭：`X-Forwarded-For` 是連線方的 tailnet 位址，`X-Forwarded-Host` 是連線方用的名稱，`Tailscale-User-Login`、`Tailscale-User-Name`、`Tailscale-User-Profile-Pic` 是連線方裝置登入的使用者。連線方自己在請求裡帶偽造的 `Tailscale-User-Login` 或 `X-Forwarded-For` 時，serve 把它換成實際的值再轉送，不是附加在後面。請求的 Host 標頭保留連線方用的名稱，不會改成 `127.0.0.1:18080`，依 Host 組出網址的服務組出來的是 tailnet 上的名稱。
- 以 tag 認證的裝置（伺服器這類不屬於某個使用者、用標籤加入 tailnet 的裝置）送來的請求，依〈Tailscale Serve〉不帶這三個身分標頭，經由 Funnel 從網際網路進來的請求也不帶（兩者都沒有實測）；依身分標頭授權的服務收到沒有身分標頭的請求時，要把它當成沒有通過認證。
- 這次的 tailnet 沒有開啟 HTTPS 憑證（`tailscale status --json` 的 `CertDomains` 是空的），管理介面上也沒有為 Serve 做任何設定，HTTP 模式照樣可用；〈Tailscale Serve〉寫的是 Serve 需要先開啟 HTTPS 憑證，沒有區分模式，實測的 1.104.5 只在 HTTPS 模式要求開啟。

「tailnet 裡連得到」的範圍由 tailnet 的存取規則決定：〈Tailscale Serve〉寫明存取規則對 serve 跟對其他服務一樣作用（沒有實測）。Tailscale 預設的規則讓 tailnet 裡的裝置全部互通，家人或其他伺服器的裝置也連得到 serve 的 8080；要限定只有管理者的裝置連得到這個連接埠，存取規則的寫法見 [7.43 兩個網路之間的連線安全](/backend/07-security-data-protection/cross-network-connection-security/) 的〈WireGuard 與 Tailscale 的金鑰與控制平面〉。

這種做法換到的是服務不必綁 `tailscale0` 的位址，所以啟動順序不必排在 `tailscaled` 之後，也不必寫主機防火牆規則（這兩項是依綁定 `127.0.0.1` 的機制推論，開機順序沒有實測）。付出的代價從來源位址開始：服務只看 TCP 連線的來源位址時，所有請求都來自 `127.0.0.1`，依來源位址做的限制與存取紀錄分不出是 tailnet 裡哪一台送來的；請求都經過 serve 時，服務改讀 `X-Forwarded-For` 或身分標頭就分得出來。HTTP 模式只轉送 HTTP，SSH、SMB 這類協定要改用 `--tcp` 轉送原始的 TCP 連線，或改由服務直接在 `tailscale0` 上接受連線（`--tcp` 沒有實測）；SSH 另有 Tailscale SSH，由 tailnet 的身分與存取規則取代 sshd 自己的金鑰驗證，見 [Tailscale SSH](/backend/07-security-data-protection/vendors/tailscale-ssh/)。服務自己把 HTTP 轉址到 HTTPS 時，HTTP 模式下連線方會被導到 tailnet 上沒有接收的 443 而連不上，這類服務要關掉自己的轉址或改用 HTTPS 模式；目的地的 `127.0.0.1` 由 `tailscaled` 所在的網路環境解讀，`tailscaled` 跑在容器裡時，它的 `127.0.0.1` 是那個容器自己，跟服務的容器沒有共用網路命名空間（compose 的 `network_mode: service:<Tailscale 那個服務的名稱>`）就轉不到服務（這兩項是從機制推論，沒有實測）。服務只聽 `127.0.0.1` 時，同一台主機上的每一個程式都連得到它，包括 `cloudflared`：〈同一台家用主機的公開網站與管理服務〉最後寫的那一項風險（Cloudflare 帳號被別人拿到時，對方可以新增一個網址轉送到主機上的任何服務）不因此消失。服務若依 `Tailscale-User-Login` 決定誰能登入，這項風險變成冒用身分：實測直接連 `127.0.0.1:18080`、送出偽造的 `Tailscale-User-Login`，服務原封不動收到，因為只有經過 serve 的請求才會被換掉。綁在 `127.0.0.1` 的連接埠，沒辦法限定只有 serve 連得到；serve 的 `--help` 也接受 Unix socket 當轉送目的地，用檔案權限限制誰連得到 socket 是一種可能的做法（沒有實測）。所以依身分標頭授權的服務，不讓 `cloudflared` 或其他反向代理轉送到同一個連接埠，同一台主機上其他程式偽造得了標頭這一點，要算進信任範圍。

HTTPS 模式要先在 tailnet 的管理介面開啟 Serve 與 HTTPS 憑證。沒有開啟時，實測的 `tailscale serve --bg --https=8443 …` 印出「Serve is not enabled on your tailnet」與一個管理介面的連結，之後停著等待，不會自己結束。依 Tailscale 的〈Enabling HTTPS〉，開啟之後，Tailscale 替用到 HTTPS 的機器向 Let's Encrypt 申請憑證，憑證上的完整網域名稱（機器名稱加 tailnet 名稱）會寫進公開的 Certificate Transparency 紀錄，任何人查得到，之後關掉也刪不掉；這次沒有開啟，開啟之後的行為都沒有實跑。HTTPS 模式預設用 443，而 443 也是 `tailscale funnel` 能用的連接埠：依〈Tailscale Serve〉，同一個連接埠同時只能給 serve 或 funnel 其中一個，以最後一次設定它的指令為準，所以在 443 用 serve 開給 tailnet 的管理服務之後，有人在同一個連接埠下了 `tailscale funnel`，那個服務就對網際網路公開（沒有實測）。`tailscale serve status` 在每一條轉送後面標出範圍，這次實測 HTTP 模式時標的是 `(tailnet only)`。公開的是名稱，不是存取權：名稱透露這個 tailnet 有哪些機器，取名透露用途時（`nas`、`vaultwarden`）也透露跑了什麼。tailnet 裡的流量本來就由 WireGuard 加密，HTTPS 模式換到的是瀏覽器把這個網址當成安全來源，需要 HTTPS 模式的是只在 HTTPS 下開放的瀏覽器功能（passkey、Service Worker、網頁存取相機與麥克風）與拒絕明文 HTTP 的服務；只是讓自己的機器互連時，HTTP 模式就夠了。讓沒裝 Tailscale 的人也連得到的是另一個指令 `tailscale funnel`，〈經過 Cloudflare 代理時家用主機要接受的限制〉寫了它的連接埠與代價。

## tunnel contract 組成

tunnel 入口合約跟 [load balancer contract](/backend/05-deployment-platform/load-balancer-contract/) 對照、差異集中在連線方向與就緒語意：

1. connection contract：本機進程主動對邊緣建立並維持反向隧道、無入站 port;隧道斷線的重連策略決定外部可達性的恢復速度。
2. readiness contract：對外可達 = 隧道已建立 **且** 後端服務已可服務。兩個條件任一不成立、外部請求就拿到 502 / 連線中斷。
3. ordering contract：啟動順序是後端服務先就緒、tunnel 再宣告 ready;關閉順序相反、tunnel 先收斂停止帶入新流量、後端再退出。
4. auth contract：tunnel 只負責把流量帶回來、本身不是認證。隧道網址是位址、不是密碼 — 任何拿到網址的人都可達後端、所以認證必須疊在 tunnel 之後（見下）。

## 生命週期與 readiness 對齊

tunnel 入口的就緒判讀比 LB 多一層。LB 的 health check 打後端 instance、通過代表可接流量;tunnel 場景下、「後端 health check 通過」不等於「外部可達」 — 還要隧道本身連上邊緣。readiness 要同時涵蓋兩者、否則會出現「服務自己覺得健康、外面卻連不進來」的盲區。

啟動順序錯位的後果具體：tunnel 比後端早 ready、邊緣開始導流量進來、後端還沒起、外部看到一批 502。所以 startup 階段 tunnel 的 ready 訊號要 gate 在後端 [readiness](/backend/knowledge-cards/readiness/) 之後。關閉時序則相反、先讓 tunnel 停止帶入新連線、給在途請求收斂窗口、後端再 [graceful shutdown](/backend/knowledge-cards/graceful-shutdown/);這層責任跟 [5.6 Platform Lifecycle Contract](/backend/05-deployment-platform/platform-lifecycle-contract/) 的 startup / readiness / drain 一致、只是 drain 的對象從 LB 摘流量換成 tunnel 收斂。

## 穩態維持與重連策略

隧道建立後進入穩態：tunnel 進程與邊緣之間維持長連線，邊緣用心跳（keepalive）偵測連線是否存活。心跳間隔與超時由供應商決定（cloudflared 預設每 5 秒心跳、連續失敗觸發重連；Tailscale 由 WireGuard 層的 persistent keepalive 維持 NAT 映射）。穩態下不需要額外操作，但要理解一個語意：邊緣側判定「連線已斷」到本機進程偵測到斷線之間有延遲，這段時間外部請求會 timeout 而非立即拿到錯誤。

連線中斷後 tunnel 進程自動重連，重連策略的關鍵是 backoff：首次斷線立即重試、連續失敗拉長間隔、避免在邊緣側故障時打滿重連請求。重連成功後 readiness 要重新驗證——隧道恢復不等於後端仍然健康，特別是斷線期間後端可能已經被別的事件影響。

### 隧道多連線與冗餘

cloudflared 預設對每個 tunnel 建立 4 條連線到不同邊緣節點（Cloudflare 在不同 data center 的 edge server）。單條連線斷線時，流量自動切到其餘連線，外部使用者感受不到中斷。4 條連線全部斷開才會觸發完全不可達。

Tailscale 的冗餘模型不同：WireGuard tunnel 是點對點連線，沒有多邊緣節點分散。Tailscale 的高可用靠 DERP relay server 做中繼——直連失敗時退到 relay，延遲增加但可達性維持。

這個差異在穩定性預期上很重要：cloudflared 的可達性依賴 Cloudflare 邊緣網路的多點冗餘，Tailscale 的可達性依賴直連品質與 DERP 中繼。選擇時要問「我的網路環境是否穩定到不需要多連線冗餘」。

## 故障模式：network 層與 application 層的分離

tunnel 斷線跟 LB health check 失敗是不同層的故障。LB health check 失敗多半是 application 層（後端掛了、依賴不通）；tunnel 斷線常是 network 層（邊緣連線中斷、本機外連受阻、供應商側問題）、而後端服務本身完全健康。事故判讀要先分清這兩層：後端 log 一切正常、但外部全部連不進來、第一個要看的是 tunnel 進程的連線狀態、不是後端。

這也改變監控訊號的設計。LB 場景看後端 5xx 與 latency 就能覆蓋多數入口問題；tunnel 場景要額外監控隧道本身的連線狀態與重連次數——隧道靜默斷掉時、後端指標一片祥和、唯一的訊號在 tunnel 進程那邊。

### 故障分類與判讀順序

tunnel 環境下的故障可按層級分類，判讀順序從外到內：

| 層級        | 症狀                               | 判讀第一步                         |
| ----------- | ---------------------------------- | ---------------------------------- |
| 供應商邊緣  | 所有 tunnel 用戶同時受影響         | 查供應商 status page               |
| 本機外連    | 單一 tunnel 斷線、其他外連也有問題 | 查本機網路、NAT、防火牆            |
| tunnel 進程 | tunnel 進程 crash 或 hang          | 查 tunnel 進程 log 與 restart 狀態 |
| 後端服務    | tunnel 正常但外部拿到 502          | 查後端服務 readiness               |
| 認證閘道    | tunnel + 後端正常但外部拿到 403    | 查認證設定（token / ACL 過期）     |

判讀順序的重點是「先確認 tunnel 層是否正常、再往內看」。如果跳過 tunnel 層直接排查後端，會在後端 log 一切正常的情況下浪費時間。

## 認證必須疊在 tunnel 之後

tunnel 把後端的可達性開到了外部、但它不認證。隧道網址可能從瀏覽器紀錄、分享連結、Referer 外洩、不該被當成安全機制。所以 tunnel 之後必須疊認證閘道、且預設拒絕 — 未通過認證的流量不該觸及後端。

常見的疊法是邊緣與本機各一層：邊緣層（cloudflared 配 Cloudflare Access service token、Tailscale 配 ACL）讓未授權流量在邊緣就被擋、根本到不了本機;本機層（反向代理驗共享密鑰 / basic auth）作為邊緣萬一失效的縱深。入口威脅建模見 [7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/);單人自用工具的裝置綁定認證見 [7.2 單人裝置認證模型](/backend/07-security-data-protection/identity-access-boundary/#單人裝置認證模型)。

## tunnel 入口的判讀訊號：外部連不進來、啟動後的 502、頻繁重連、網址被直接連用、530 與部署切換時的中斷

| 訊號                            | 判讀重點                              | 對應動作                                                              |
| ------------------------------- | ------------------------------------- | --------------------------------------------------------------------- |
| 外部全部連不進來、後端 log 正常 | 故障在 network 層、隧道斷線           | 先查 tunnel 進程連線狀態、不是後端                                    |
| 啟動後短時間外部拿到一批 502    | tunnel 比後端早 ready、導流量進空服務 | 把 tunnel ready gate 在後端 readiness 後                              |
| 隧道頻繁重連、外部間歇中斷      | 本機外連不穩或邊緣側抖動              | 查 cloudflared / tailscaled 的重連 log、確認 backoff 間隔是否正常拉長 |
| 拿到網址的人直接連到後端        | 認證沒疊在 tunnel 之後、網址被當密碼  | 補邊緣 / 本機認證閘道、預設拒絕                                       |
| 外部拿到 530、一直重試 QUIC     | 出站擋了 UDP 7844                     | 放行 UDP 與 TCP 7844，或改用 http2                                    |
| 部署切換隧道時對外中斷拉長      | 關閉順序錯位、tunnel 未先收斂         | 先停 tunnel 帶入新連線、再退後端                                      |

「外部拿到 530」那一列是 quick tunnel 的實測：出站擋掉 UDP 7844、TCP 7844 開著時，cloudflared 一直重試 QUIC 而沒有自動改用 http2，以 `--protocol http2` 啟動之後改走 TCP 7844 連上，見 [Cloudflare 回源的實測紀錄：Oracle Cloud NSG 只放行 Cloudflare 位址與規則數上限、回源的來源位址、Authenticated Origin Pulls、Worker 偽造 CF-Connecting-IP 與 Tunnel 的出站連接埠](/devops/infra/03-network-foundation/hands-on/cloudflare-origin-pull-walkthrough/) 的〈Cloudflare Tunnel：源站不開入站，以及出站要放行的連接埠〉；具名的 tunnel 預設的協定選擇沒有測。

## tunnel 入口的常見誤區：網址當密碼、後端健康當外部可達、常駐入口與供應商不停機的假設

把 tunnel 網址當密碼、是最常見也最危險的誤判。網址不好猜不代表是祕密、它會從各種地方外洩、認證要靠 tunnel 之後的閘道、不是靠網址難猜。

把「後端健康」當成「外部可達」、忽略隧道本身是獨立的失效點。tunnel 場景的可達性是後端健康與隧道連線的交集、監控要覆蓋兩者。

把 tunnel 當「永久掛著」的常駐入口、放大暴露窗。自用場景常更適合用時起、用完關 — 暴露窗壓到最小;要常駐時、認證閘道與監控的投資等級要隨之上調。

把 tunnel 供應商視為零停機、不設本機降級預案。tunnel 依賴外部供應商的邊緣網路與協調伺服器，供應商事故期間本機服務完全健康但外部無法觸及。有降級需求的場景要準備替代入口路徑，路徑依網路條件而定：主機有連得進來的公開 IP 時，可以臨時開 port + 反向代理；在 CGNAT 後面時開 port 沒有作用，管理用的替代路徑改用 mesh VPN（〈家用主機對外提供網站時接上 Cloudflare 的兩種方式〉的 CGNAT 那一項），或接受供應商 SLA 決定自身可用性。

## 跨模組路由：生命週期合約、入口威脅建模、隧道憑證、隧道監控、管理通道與 mesh VPN 的帳號防護

1. 與 [5.6 Platform Lifecycle Contract](/backend/05-deployment-platform/platform-lifecycle-contract/) 的交接：tunnel 的 startup / readiness / drain 對齊生命週期合約、只是 drain 對象換成隧道收斂。
2. 與 [7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/) 的交接：tunnel 作為對外入口的威脅建模與認證疊法。
3. 與 [7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/) 的交接：tunnel 存取憑證與認證閘道密鑰的保管與輪替。
4. 與 [4 觀測](/backend/04-observability/) 的交接：隧道連線狀態與重連次數要進監控、否則 network 層故障無訊號。
5. 與 [伺服器管理通道的設計：網路可達性、通道授權、主機登入驗證三層的做法與選擇，以及救援入口](/devops/infra/03-network-foundation/management-access-channel/) 的交接：管理服務不走 Tunnel 時，管理者連進主機的通道怎麼分成網路可達性、通道授權與主機登入驗證三層設計，以及通道全部斷掉時的救援入口。
6. 與 [Tailscale 深入：tailnet、MagicDNS、直連與 DERP 中繼](/linux/tools/remote/tailscale-tailnet-and-relay/) 的交接：管理服務走 mesh VPN 時，裝置在 CGNAT 與浮動 IP 之下怎麼維持固定的位址，以及直接連線打不通時改經 DERP 中繼的判讀。
7. 與 [7.43 兩個網路之間的連線安全](/backend/07-security-data-protection/cross-network-connection-security/) 的交接：mesh VPN 預設互通時存取規則怎麼收窄，以及 Tailscale 管理帳號與協調伺服器被盜或作惡時 Tailnet Lock 擋得住什麼。

## 延伸閱讀：生命週期合約、認證閘道與交付形態選型

要把 tunnel 入口放進整體生命週期、接著讀 [5.6 Platform Lifecycle Contract](/backend/05-deployment-platform/platform-lifecycle-contract/)。要把 tunnel 之後的認證做紮實、接著讀 [7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/) 與 [7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)。判斷服務是否屬於個人自架工具形態、回 [0.21 交付形態選型](/backend/00-service-selection/delivery-mode-selection/)。
