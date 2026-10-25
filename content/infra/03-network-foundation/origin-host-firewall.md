---
title: "CDN 後面的源站主機防火牆：只放行 CDN 來源的位置與套用時機、Docker 發佈連接埠的封包路徑、出站 DNS 的限制與地理封鎖"
date: 2026-10-25
description: "網站放在 CDN（例如 Cloudflare）後面時，源站主機的入站與出站限制：請求避開 CDN 直連源站的成因、來源限制放在雲端防火牆、主機防火牆或 CDN 端驗證的差別、只放行 CDN 位址的套用時機與同機混用不經 CDN 的服務、Docker 發佈的連接埠繞過 ufw 與 firewalld 的路徑，以及不發佈、只發佈在本機位址、DOCKER-USER 鏈、firewalld 的 StrictForwardPorts、掛在位址轉換之前的 nftables 表、雲端防火牆與 Cloudflare Tunnel 各自擋得住什麼、出站 DNS 只准送往指定解析器的效果與漏洞、地理封鎖放在 CDN 邊緣的理由"
weight: 5
tags: ["infra", "network", "firewall", "cdn", "cloudflare", "docker", "security"]
---

這篇整理網站放在 [CDN](/infra/knowledge-cards/cdn/)（內容遞送網路，content delivery network：代替源站接收使用者連線、在邊緣做快取與過濾的服務，例如 Cloudflare）後面時，源站主機的防火牆要限制什麼、限制放在哪裡：請求避開 CDN 直接連到源站的成因（源站位址從 DNS 歷史紀錄、憑證透明度紀錄與其他記錄外洩）、來源限制放在雲端防火牆、主機防火牆或 CDN 端驗證時各自擋得住什麼、只放行 CDN 位址的規則什麼時候套上去、管理通道與同一台主機上不經 CDN 的服務怎麼處理、Docker 發佈的連接埠為什麼不受 `ufw` 與 `firewalld` 的一般規則約束，以及不發佈、只發佈在本機位址、`DOCKER-USER` 鏈、firewalld 的 `StrictForwardPorts`、掛在位址轉換之前的 nftables 表、雲端防火牆與 Cloudflare Tunnel 這幾種做法、出站的 DNS 只准送往指定解析器擋得住與擋不住的部分，以及地理封鎖放在 CDN 邊緣的理由。

機制以 Linux 主機、Cloudflare 與以 root 執行的 Docker（預設的 iptables 後端；compose 發佈連接埠的方式與 `docker run -p` 相同）說明。其他 CDN 對應的是它公佈的、連回源站時使用的位址清單與它的回源驗證功能。Podman、rootless 模式的 Docker 與 Kubernetes 的 NodePort 轉送連接埠的方式各有差異，判斷的依據相同（容器執行環境有沒有在主機防火牆之前改寫封包的目的地），各自的規則沒有在這篇驗證。

指令與輸出逐步記在 [源站防火牆只放行 Cloudflare 位址的實測紀錄：firewalld、Docker 發佈的連接埠、DOCKER-USER、nftables 表與出站 DNS](/infra/03-network-foundation/hands-on/origin-firewall-walkthrough/)：那一篇在 Oracle Linux 10 的 firewalld 2.4.3 與 Docker 29.9.2 上，用一個位址落在 Cloudflare 範圍內、一個落在範圍外的兩個測試來源，量了每一種限制寫法擋不擋得住，以及規則在 firewalld 重新載入、dockerd 重啟與重開機之後還在不在。下文寫「實測」的地方都出自那一篇。管理員登入主機那條通道的設計另見 [伺服器管理通道的設計：網路可達性、通道授權、主機登入驗證三層的做法與選擇，以及救援入口](/infra/03-network-foundation/management-access-channel/)，請求從 DNS 到應用經過哪幾層見 [流量入口層 — 請求怎麼從使用者到達應用](/infra/03-network-foundation/traffic-entry-layer/)，CDN 本身的分發責任見 [5.9 邊緣分發與靜態資源（CDN / Origin Protection）](/backend/05-deployment-platform/edge-cdn-static-distribution/)（那一篇的 origin protection 指的是快取未命中時保護源站的負載，跟這篇的安全限制是兩件事）。

## 主機前面有 CDN 時連到源站的路徑：經由 CDN、直連公開 IP 與管理通道

源站（origin server）是實際跑網站程式的主機，CDN 收到使用者的請求之後，從自己的機房連回源站取回應，這個動作叫回源。網域的 DNS 記錄設成經由 CDN 代理時，使用者解析網域拿到的是 CDN 的位址，請求先到 CDN，CDN 再用它自己的位址連到源站。這時連得到源站的路徑有三條：

- **經由 CDN 回源**：使用者連 CDN，CDN 連源站的 80 或 443。源站看到的來源位址是 CDN 機房的位址，使用者真正的位址放在 CDN 加上的 HTTP 標頭裡（Cloudflare 是 `CF-Connecting-IP`）。
- **直連源站的公開 IP**：知道源站位址的人跳過 CDN，直接對源站的 80、443 或其他對外的連接埠送請求。CDN 上設定的 [WAF](/backend/knowledge-cards/waf/)（Web 應用程式防火牆：依規則檢查 HTTP 請求內容並攔下可疑請求的元件）規則、速率限制與地理封鎖都在 CDN 那一端執行，這條路徑上沒有任何一條會作用。
- **管理通道**：管理員登入主機的 SSH，或經由雲端業者的代理（Oracle Cloud 的 Bastion、GCP 的 IAP）。這條路徑跟網站流量無關，CDN 也不經手。

CDN 帶來的保護只對經由 CDN 回源那條路徑成立。一個漏洞公開之後，掃描程式會對網際網路上的主機送出探測請求；源站主機的防火牆對全網開放 80 與 443 時，這些請求可以走直連公開 IP 那條路徑送到源站，CDN 上為這個漏洞加的每一條規則都碰不到它們。直連那條路徑開著還有一個影響：直連的人可以自己在請求裡寫一個假的 `CF-Connecting-IP`，源站的存取記錄、速率限制與依國家的判斷照這個標頭做時都會被騙；只有經由 CDN 的請求連得進來時，源站才能信任這個標頭的值（反向代理的設定裡只信任來自 CDN 位址段的這個標頭，nginx 是 `set_real_ip_from` 加 `real_ip_header`）。

## 讓請求避開 CDN 的成因：源站位址從哪裡外洩

直連源站要先知道源站的位址，而這個位址的來源比網域的 A 記錄多。Cloudflare 的〈Protect your origin server〉列出的外洩來源有：接上 CDN 之前的 DNS 歷史紀錄（DNS 歷史查詢服務保留了網域過去解析到的位址，接上 CDN 之後舊記錄仍查得到）、沒有經由 CDN 代理的記錄（`mail`、`ftp` 這類子網域的 A 記錄，以及寫著 IP 的 SPF、TXT 記錄；SPF 是寫在 TXT 記錄裡、列出允許替這個網域寄信的主機的設定），以及跟網站同一台主機收發郵件時，退信會帶出主機的位址。Cloudflare 那一頁沒有列、但同樣公開的另一個來源是憑證透明度紀錄（certificate transparency log）：每一張公開簽發的 TLS 憑證都記在公開的日誌裡，源站曾經用自己的位址對外提供 HTTPS 時，掃描服務把憑證上的網域與當時回應的位址對起來。另外，網際網路上的掃描程式不必先知道網域：它們對整段 IP 位址逐一連 80 與 443，碰到回應的主機就送出探測請求，所以位址從未外洩的源站一樣會被掃到。

源站的位址因此要當成已經公開，防護要直接寫在源站能被連到的位置上：只有經由 CDN 的請求連得進來，直連公開 IP 那條路徑才會關上。Cloudflare 那一頁另外建議接上 CDN 之後更換源站的 IP，讓歷史紀錄裡的位址失效。

## 限制放在哪一層：雲端防火牆、主機防火牆與 CDN 端的驗證

「只讓 CDN 連進來」可以寫在三個位置，它們擋的範圍與失效的方式不同：

- **雲端防火牆**（Oracle Cloud 的 security list 與 NSG（network security group，套在網卡上的一組放行規則）、AWS 的 [security group](/infra/knowledge-cards/security-group/)、GCP 的 VPC 防火牆規則，位置與合併方式見 [網路：subnet、私有 IP、公開 IP 與防火牆規則](/infra/cloud-providers/vm-options/networking/) 的〈防火牆規則的位置與合併方式〉）：規則在業者的網路上執行，被擋的封包到不了主機，主機上跑什麼程式、程式怎麼改寫主機的防火牆都不影響它。要評估的是規則數：Cloudflare 在 2026-10-25 公佈的是 15 段 IPv4 與 7 段 IPv6，一條規則能放幾段來源、一組規則能放幾條，每一家業者的配額不同，要用「段數 × 要放行的連接埠數」跟自己那一家的上限比；清單變動時也要有人改規則。
- **主機防火牆**（`firewalld`、`ufw`、`nftables`）：在主機的核心裡執行，可以用 ipset（核心裡的一個位址集合，一條規則比對整個集合）一次放進整份清單，也能寫出只對某個連接埠生效的規則。它管不到的是在它之前就改寫封包目的地的程式，Docker 是最常見的一個，機制見〈Docker 發佈的連接埠：封包路徑與限制的寫法〉。
- **CDN 端的驗證**：源站確認請求是 CDN 替這個網域送來的，而不只是來自 CDN 的位址。Cloudflare 的做法有兩種：Authenticated Origin Pulls 讓 Cloudflare 回源時出示用戶端憑證，源站的 TLS 設定只接受帶這張憑證的連線；Cloudflare Tunnel 由源站上的 `cloudflared` 主動往外連到 Cloudflare，請求經由這條往外建好的連線送進來（[outbound tunnel](/backend/knowledge-cards/outbound-tunnel/) 的一種）。Authenticated Origin Pulls 用 Cloudflare 預設的共用憑證時，〈Protect your origin server〉寫明它只保證請求來自 Cloudflare 的網路；要分得出是不是自己的網域送來的，要改用自己上傳的用戶端憑證（設在 Cloudflare 的 zone 層級，也就是一個網域的設定單位，或每個主機名稱各一張）。

雲端防火牆與主機防火牆比對的是來源位址，而 CDN 的位址由所有客戶共用。別人也可以用自己的 Cloudflare 帳號，把一個網域指向這台源站的位址；這些請求同樣從 Cloudflare 的位址送來，通過只放行 CDN 位址的規則，而源站擁有者在自己帳號上設的 WAF 規則管不到別人帳號送來的請求。這一點是從位址共用的機制推出來的，沒有實測。把這一類稱為**經由別的 CDN 帳號送來的請求**：只放行位址的規則與共用憑證的 Authenticated Origin Pulls 都擋不住它，擋住它要用自己上傳憑證的 Authenticated Origin Pulls 或 Tunnel。只放行位址的規則擋下的是不經過 CDN 的直連，漏洞公開後對整段位址的掃描就屬於這一類。三個位置可以疊加，例如雲端防火牆只放行 CDN 位址到 80 與 443，源站的 TLS 設定再驗證自己上傳的用戶端憑證，主機防火牆則管住雲端防火牆碰不到的出站流量與主機上的其他連接埠。

## 只放行 CDN 位址的套用時機、範圍與清單的維護

只放行 CDN 位址的規則一套上去，不經過 CDN 的連線全部連不進來。規則的效果與失效的方式，依它在什麼時候套上、套在哪些連接埠而不同：

- **時機：網域的 DNS 記錄已經經由 CDN 代理，舊記錄的快取也過期了**。還沒接上 CDN、或記錄設成只做 DNS 解析（Cloudflare 的 DNS only）時，使用者直接連源站，規則一套上，所有訪客都連不進網站：規則寫在雲端防火牆或丟棄封包的規則上時，瀏覽器等到連線逾時；寫在 firewalld 的 zone 上時，firewalld 以 ICMP 回拒，瀏覽器立即顯示連線失敗（兩種結果的分辨見 [Connection Refused vs. Timeout（連線被拒與逾時）](/linux/dotfile/knowledge-cards/connection-refused-vs-timeout/)）。網站回應的標頭帶著 CDN 的標記（Cloudflare 會加 `cf-ray`），只代表管理員自己這一次的請求經過了 CDN；其他訪客的解析器可能還快取著舊的 A 記錄（指向源站），換成 Cloudflare 的 nameserver 時，舊的 NS 記錄也有快取（2026-10-25 查 `.com` 上層伺服器回的 NS 記錄，TTL 是 172800 秒，也就是兩天；`dig +noall +authority <網域> @a.gtld-servers.net` 查得到自己網域的值）。所以套規則的時間點在舊記錄的快取全部過期之後：只改了 A 記錄時，等舊 A 記錄的 TTL；換了 nameserver 時，等舊 NS 記錄與舊 A 記錄兩者 TTL 中較長的那一個。在那之前套上，快取著舊記錄的訪客連不進網站。
- **接上 CDN 之前就能做的限制**：管理通道改走白名單或代理、資料庫與內部服務的容器不發佈或只發佈在本機位址、關掉 80 與 443 以外對外開著的連接埠、出站 DNS 的限制，這幾項不依賴 DNS 記錄的狀態，可以先做。只放行 CDN 位址到 80 與 443 這一項，要等上一項的時機。
- **範圍：管理通道不在這條規則裡**。規則只套在網站的 80 與 443 上，SSH 走 [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/) 裡的那一條（來源 IP 白名單、Bastion、IAP 或 VPN），兩者分開設定。把整台主機的入站都改成只放行 CDN 位址時，管理員自己的 SSH 會一起被擋在外面；Cloudflare 的 DNS 代理轉送的是網站的 HTTP 與 HTTPS，SSH 要經由 Cloudflare 時另外架 Tunnel。
- **範圍：同一台主機上還有不經 CDN 的服務**。例如網站經由 Cloudflare，而同一台主機的 443 也直接對外提供一個 API 子網域。防火牆只看位址與連接埠，分不出同一個連接埠上的兩個網域（那要看 TLS 的 SNI 或 HTTP 的 Host），所以對 443 套「只放行 CDN」，API 就斷線；不套，網站的直連路徑就開著，而 API 子網域的 A 記錄本身就公開了源站的位址。可行的分法有：API 也改經由 CDN 代理；API 改用另一個公開 IP 或另一個連接埠，各自套各自的規則；或在反向代理依網域分流，網站的網域只接受來自 CDN 位址的請求。這幾種做法沒有實跑。

規則寫在主機本身程式收連線的路徑上（firewalld 的 zone、ufw 的入站規則）時，寫成「放行 CDN 位址到 80 與 443」就夠：zone 的預設動作已經回拒未列出的連線（firewalld 的 `public` zone 是回拒），放行清單之外的來源自然被擋下。zone 的預設回拒只作用在主機本身收連線的那條路徑上。Docker 發佈的連接埠走的是另一條路徑：封包的目的地先被改寫成容器，再由主機轉送過去，這條轉送路徑上沒有對應的預設拒絕，那裡的規則要寫成「來源不在 CDN 清單裡就丟棄」，寫法見〈Docker 發佈的連接埠：封包路徑與限制的寫法〉的 `DOCKER-USER` 與 nftables 表。

網域有經由 CDN 代理的 AAAA 記錄、而主機也有 IPv6 位址時，CDN 會經由 IPv6 回源。這時漏寫 IPv6 的後果依規則的寫法而不同：

- **放行式**（只放行清單，其餘交給預設回拒）只寫了 IPv4 的清單：CDN 經由 IPv6 回源的連線被預設回拒擋下，網站對 IPv6 回源失效。
- **丟棄式**（來源不在清單裡就丟棄）的比對只寫了 IPv4 位址（nftables 的 `ip saddr`、iptables）：IPv6 的連線不受這條規則限制，經由 IPv6 直連源站的路徑照舊開著。Docker 的〈Port publishing〉寫明 `-p 8080:80` 同時發佈在 IPv4 與 IPv6，所以主機有 IPv6 時，Docker 發佈的連接埠也要有 IPv6 的那一份規則（ip6tables 的 `DOCKER-USER`，或 nftables 的 `ip6 saddr`）。

兩種寫法都要另寫一份 IPv6 清單（Cloudflare 的 `ips-v6`）。

CDN 的位址清單會變動。Cloudflare 的〈Cloudflare IP addresses〉寫明清單不常變，新的位址段會先加進公佈的清單再投入使用，沒有寫會另外通知。規則裡的清單沒有跟著更新時，Cloudflare 從新位址段回源的請求會被擋下，所以清單要定期從 `https://www.cloudflare.com/ips-v4` 與 `ips-v6`（或 Cloudflare 的 API）取回、跟規則比對。規則用位址集合（firewalld 的 ipset、nftables 的 set）寫時，更新只換集合的內容，規則本身不動，排程一支取回清單、換掉集合內容的程式就能維護；這個做法沒有實跑。

## Docker 發佈的連接埠：封包路徑與限制的寫法

容器用 `docker run -p 8081:80` 發佈連接埠時，Docker 在 iptables 的 nat 表寫一條目的位址轉換規則（[DNAT](/infra/knowledge-cards/dnat/)，destination NAT：把封包的目的地改寫成另一個位址與連接埠），在封包剛進主機的 prerouting 階段，就把目的地從「主機的 8081」改成「容器的 80」。改寫之後，核心判定這個封包要轉送給另一個網路介面（容器網路在主機上的 bridge 介面：預設網路是 docker0，compose 建的自訂網路是 `br-` 開頭的介面，容器接在它後面），它走的是轉送（forward）路徑，不經過管主機本身入站連線的 input 路徑。

主機防火牆的一般規則寫在 input 路徑上，所以對發佈的連接埠沒有作用，`ufw status` 與 `firewall-cmd --list-all` 也都列不出這些連接埠（要用 `docker ps` 或 `ss -ltnp` 查）：

- **ufw**：Docker 的〈Packet filtering and firewalls〉寫明，送往發佈連接埠的流量在經過 ufw 的規則之前就被轉走，ufw 的設定對它等於不存在。網路上常見的解法是在 Docker 的設定裡關掉它的 iptables 管理（`"iptables": false`），同一頁寫明這樣做多半會讓容器的網路失效，發佈的連接埠也會變成區網內連得到。
- **firewalld**：firewalld 把網路介面分到 zone（一組介面共用一套入站規則，例如 `public`），zone 與 zone 之間轉送的流量由 policy 管（一條 policy 指定從哪些 zone 轉送到哪些 zone、帶一個優先序與預設動作）。Docker 啟動時建一個 target 為 ACCEPT 的 `docker` zone，把它的 bridge 介面放進去，再建一條 `docker-forwarding` policy，放行任何 zone 轉送到 `docker` zone 的流量。實測在 `public` zone 只開了 `ssh` 與 `dhcpv6-client`、沒有任何一條規則提到 8081 的主機上，位址落在 Cloudflare 範圍外的測試來源照樣拿到容器的回應。firewalld 的轉送鏈開頭還有一條 `ct status dnat accept`：在預設的 `StrictForwardPorts=no` 下，所有經過目的位址轉換的連線在任何 policy 之前就被接受，所以自己加一條「`public` 轉送到 `docker` 只放行 CDN 位址」的 policy 也擋不住，實測加上之後範圍外的來源仍然連得到。

Docker 會保留封包原本的來源位址，容器裡的程式看到的是真正的連線來源（實測容器的存取記錄裡，兩個測試來源的位址都原樣出現），所以來源限制在技術上做得到。做法從「讓連接埠不對外」到「在主機之外擋」依序是：

- **不發佈**：同一個 compose 專案或同一個 Docker 網路裡的容器，以服務名稱互相連線，不需要發佈連接埠。資料庫、快取這類只給其他容器用的服務不寫 `ports`，主機外面就連不到它們；主機上的工具要連時，才發佈在本機位址。
- **只發佈在本機位址**（`-p 127.0.0.1:8082:80`）：外部來源連不到這個連接埠，實測兩個外部來源都被拒、主機本機連得到。這個結果有版本條件：Docker 的〈Port publishing〉寫明 28.0.0 以前，跟主機在同一個 L2 網段的其他主機連得到發佈在 127.0.0.1 的連接埠（實測用的是 29.9.2，`docker version` 查得到版本），共用網段的 VPS 或區網裡要先確認版本。對外改由反向代理（nginx、Caddy）收 80 與 443 再轉給容器；反向代理以主機上的程式或 host network 模式的容器執行時，它收連線走 input 路徑，主機防火牆的放行式規則對它有效，這是用 ufw、又沒有雲端防火牆可設的主機上規則最少的組合。反向代理自己也用 `-p 80:80 -p 443:443` 發佈時，它跟其他發佈的連接埠一樣走轉送路徑，要照下面幾種寫法限制。預設的發佈位址可以在 Docker 的設定裡改：`ip` 選項只作用於預設的 bridge 網路（dockerd 參考文件），compose 建的自訂網路要用網路選項 `com.docker.network.bridge.host_binding_ipv4`，或用 `default-network-opts` 套到之後新建的每一個 bridge 網路，已經建好的網路不受影響。這幾個設定都沒有實跑。
- **`DOCKER-USER` 鏈**：Docker 在 iptables 的 FORWARD 鏈最前面跳到這條鏈，裡面的規則由使用者自己寫，Docker 啟動與重啟時不清掉它（實測只重啟 dockerd 之後規則還在、照樣擋得住）。封包到這裡時目的地已經改寫成容器的位址與連接埠，所以要用連線追蹤（[conntrack](/infra/knowledge-cards/conntrack/)：核心記錄每一條連線的狀態與它原本的位址、連接埠的表）記下的原始目的連接埠比對（`-m conntrack --ctorigdstport 8081 --ctdir ORIGINAL`）。`--ctdir ORIGINAL` 讓規則只比對發起方向的封包；容器回覆的封包也帶著同一個原始目的連接埠，少了這個條件時這些回覆封包會被拿去比對來源而丟掉（依連線追蹤的機制推論，沒有拿掉這個條件實測）。實測範圍外的來源被擋下（連線逾時），範圍內的照常。它的弱點在規則的存續（防火牆重新載入、dockerd 重啟與重開機之後規則還在不在）：在 firewalld 的主機上、`FlushAllOnReload` 是預設的 `yes` 時，`firewall-cmd --reload` 執行之後，`DOCKER-USER` 裡自己加的規則與自建的鏈全部消失，dockerd 有沒有在跑結果都一樣；iptables 指令加的規則只存在執行中的核心裡，重開機之後也不在（依機制，沒有單獨實測）。要靠這條鏈，就要另外做重開機與 reload 之後重新寫入的機制，常見的有 iptables-services 或 netfilter-persistent 的開機載入、ufw 主機把規則寫進 `/etc/ufw/after.rules`、firewalld 已經棄用的 direct rule，這幾種都沒有實跑。另外，Docker 改用實驗性的 nftables 後端時，〈firewall-nftables〉寫明沒有 `DOCKER-USER` 這條鏈，自訂規則要寫在自己的 nftables 表裡，也就是下面「自己的 nftables 表」那一種。
- **firewalld 的 `StrictForwardPorts=yes`**：設定檔 `/etc/firewalld/firewalld.conf` 的這個選項（這次的 firewalld 2.4.3 有；它是 2024 年 11 月 firewalld 官方部落格〈Strict Forward Ports〉介紹的新功能，較舊的 firewalld 沒有）把轉送鏈開頭的 `ct status dnat accept` 換成只接受 firewalld 明確放行的連接埠。〈firewalld.conf〉與那篇部落格寫明，設成 `yes` 之後發佈的連接埠要用 firewalld 的 forward-port（firewalld 自己做的目的位址轉換規則）明確放行。實測它管得到「哪些發佈的連接埠可以從外面連」：設成 `yes` 之後兩個測試來源都被回拒，加了 forward-port 之後又都連得到；它管不到「誰可以連」：即使 forward-port 寫在限定來源的 rich rule（firewalld 可以同時寫來源、連接埠與動作的規則）裡，firewalld 在轉送鏈產生的放行規則也只比對原始目的連接埠（連線追蹤記下的、位址轉換之前的連接埠），沒有帶上來源條件，範圍外的來源也連得到。規則存在 firewalld 的永久設定裡，reload 與 dockerd 重啟之後都在。
- **自己的 nftables 表，掛在目的位址轉換之前**：在 nftables 建一張自己的表，鏈接在 prerouting 這個 hook（核心處理封包的流程上，讓規則掛上去執行的固定位置；prerouting 是封包剛進主機、還沒決定路由的那一個）上、優先序排在目的位址轉換之前（`priority dstnat - 10`），封包還沒被改寫時就用原本的目的連接埠比對來源，來源不在 CDN 清單裡就丟棄。實測範圍外的來源被擋下，`firewall-cmd --reload`、dockerd 重啟之後規則都還在；把表寫進 `nftables.service` 開機時載入的設定檔（RHEL 系是 `/etc/sysconfig/nftables.conf`，其他發行版看 `systemctl cat nftables` 的 `ExecStart`）並啟用這個服務之後，重開機也還在。代價有兩個。一是規則不在 firewalld 的管理介面裡，`firewall-cmd --list-all` 看不到它，接手的人要知道還有這一張表。二是 `nftables.service` 會清掉整個 nftables 規則集：RHEL 系的 unit 在停止、重新啟動與重新載入時執行 `nft flush ruleset`，而 Debian 系的預設設定檔第一行就是 `flush ruleset`（這一點沒有核對各版本），被清掉的包括 firewalld 的表，以及 Docker 經由 iptables-nft 寫的位址轉換與轉送規則；之後自建的表又被載回來，主機只剩這一張表，其他連接埠失去預設回拒、發佈的連接埠與容器的出站都斷線，要依序重新啟動 firewalld 與 dockerd 才會重建（依 unit 檔的內容推論，沒有實跑）。避開這個風險的做法是不經過 `nftables.service`，改用一個開機時只執行 `nft -f` 載入這一張表的 systemd unit。
- **雲端防火牆**：規則在主機之外執行，Docker 改寫的是主機自己的防火牆，碰不到它。只放行 CDN 位址到 80 與 443、其他連接埠一律不開時，主機上誤發佈的任何連接埠都連不進來。
- **Cloudflare Tunnel**：源站不需要任何入站放行。這個效果要管理員自己做到：移除雲端防火牆與主機防火牆上 80、443 的入站放行，網站容器不發佈連接埠（或只發佈在本機位址），讓 `cloudflared` 經由同一個 Docker 網路或本機位址連到網站；網站容器還用 `-p 80:80` 發佈時，直連路徑照樣開著。代價是 `cloudflared` 要常駐、主機要能出站連到 Cloudflare（出站限制成只放行清單時，要放行 Tunnel 用的連接埠，Cloudflare 的文件寫的是 7844；這一點沒有核對），而且網站的入口綁在 Cloudflare 一家。沒有出站路徑的主機（例如實測那台只有 service gateway 的私有 subnet 主機）用不了。這次沒有實跑 Tunnel。

這些寫法可以疊加。業者的防火牆放得下整份 CDN 清單時，雲端防火牆加上不發佈或只發佈在本機位址的組合，不靠主機上任何一條會被重新載入或重開機清掉的規則：雲端防火牆擋住直連，不發佈與本機位址讓「某個容器不小心發佈在 `0.0.0.0`」這種錯誤不會變成對外開放。網站跑在主機上的程式（不是容器）時，雲端防火牆加上 firewalld zone 或 ufw 的放行式規則就夠，兩層各自擋一次直連。同一組規則要套在多台主機上時，雲端防火牆的規則可以套在一組網卡上共用（Oracle Cloud 的 NSG、AWS 的 security group），主機防火牆的寫法則要在每一台各自部署與維護。單台主機、網站流量、主機連得到外面時，Cloudflare Tunnel 可以取代入站的 CDN 位址清單，清單的維護與 Docker 繞過主機防火牆這兩件事都不必處理。

## 出站的 DNS 只准送往指定的解析器：擋得到與擋不到的部分

主機加固清單常見的一條是限制 DNS 只用 53，它有入站與出站兩種讀法。入站的讀法是主機有跑 DNS 伺服器時才開 53，沒有跑就不開；網站主機多半沒有跑 DNS 伺服器，所以入站的做法就是不把 53 放進放行清單。出站的讀法是主機與容器送出的 DNS 查詢只准送往指定的解析器（雲端業者的解析器，例如 Oracle Cloud 虛擬網路 VCN 裡的 `169.254.169.254`），送往其他位址的 53 一律拒絕。後一種的目的，是讓被植入的程式不能用自己指定的 DNS 伺服器查詢，或把資料編進查詢的網域名稱送出去。

出站限制在 firewalld 上寫成一條從 `HOST`（主機本身送出的流量）到 `ANY`（任何 zone）的 policy，裡面兩條 rich rule：放行送往指定解析器的 `dns` 服務那一條優先序較小、先比對，拒絕其餘 `dns` 的那一條排在它之後。實測它的效果與漏洞：

- **主機本身送出的查詢**：送往指定解析器的照常解析，送往其他位址的 53 被拒絕（`dig` 回 `connection refused`），對方收不到任何封包。
- **容器送出的查詢**：實測的容器在預設的 bridge 網路上，它的 DNS 設定是主機 `/etc/resolv.conf` 的副本，查詢直接從容器送出、走轉送路徑，不經過 `HOST`，所以這條 policy 對它無效，容器照樣把查詢送到外部的 53。這些查詢要在 `DOCKER-USER` 另寫一條（從容器網路的 bridge 介面進來、目的連接埠 53、目的地不是指定解析器的拒絕；預設網路的介面是 docker0，compose 的自訂網路是 `br-` 開頭的介面，iptables 可以寫成 `-i br-+`），而它有 `DOCKER-USER` 在 firewalld 重新載入後消失的問題，要一起處理。compose 的自訂網路上，容器先問 Docker 內建的解析器（`127.0.0.11`），內建解析器再往外查；Docker 的文件沒寫內建解析器往外查的封包從哪裡送出，所以這條 policy 與 `DOCKER-USER` 規則對自訂網路的容器有沒有效，要另外量，這次沒有測。
- **不走 53 的 DNS**：DNS over TLS 用專用的 853，再加一條拒絕出站 853 的規則就擋得下（沒有實跑）。DNS over HTTPS 把查詢包在送往 443 的 HTTPS 裡，連接埠的限制看不到它。實測時主機對外部 443 送出的一般 TCP 連線不受這條 policy 影響；沒有實際送 DNS over HTTPS 的查詢，它走同一個連接埠，結果依此推論。要擋這一種，出站就要改成只放行一份允許的目的地清單（套件庫、業者的 API），這在 443 上會連帶影響每一個需要連外的功能，成本遠高於限制 53。

所以出站限制 53 擋下的是寫死了 DNS 伺服器位址、走 53 的程式，它讓主機與容器的名稱查詢集中到一個留有查詢紀錄的解析器；有意繞過的程式改走 443 就繞得過去。

## 地理封鎖：依國家比對來源的位置與 GeoIP 清單的成本

依國家封鎖連線，要先知道連線來自哪個國家，而源站在 CDN 後面時，源站看到的來源位址全是 CDN 機房的位址：主機防火牆照來源位址查國家，查到的是 CDN 機房所在的國家，不是使用者的。所以地理封鎖寫在 CDN 那一端（Cloudflare 的 WAF custom rule 依 `ip.src.country` 比對），那裡看得到使用者真正的位址；源站只需要擋掉不經過 CDN 的連線，只放行 CDN 位址的規則已經做到。源站要自己做時，條件是先只放行 CDN 位址，讓 `CF-Connecting-IP` 可信，再由反向代理依這個標頭查國家；防火牆這一層做不到，因為它看不到 HTTP 標頭。

主機防火牆做地理封鎖的機制跟只放行 CDN 位址相同（把一個國家的位址段放進 ipset），適用的情形是主機直接面對使用者、前面沒有 CDN，或同一台主機上不經 CDN 的服務。它的成本在清單：國家的位址段清單要從 GeoIP 資料庫（把 IP 位址段對應到國家的資料庫）取得並定期更新，資料庫對 VPN、行動網路與雲端業者的位址判斷常常不準，被誤擋的使用者只看到連線失敗（逾時或立即被拒，看規則是丟棄還是回拒），沒有任何頁面告訴他原因。CDN 端的封鎖可以回一個說明頁或改成驗證挑戰，誤判時使用者看得到發生了什麼。

## 防火牆限制與修補的關係

只放行 CDN 位址、在 CDN 上加 WAF 規則，縮小的是能連到有漏洞程式的來源範圍，漏洞本身還在。源站已經修補時，直連的掃描請求送到也攻不破；源站還沒修補時，經由 CDN 送來的同一種請求只要沒有被 WAF 規則認出來，照樣會送到程式。防火牆限制與修補各自關掉一條路徑：限制擋住不經過 CDN 的請求，修補處理經過 CDN 也會送到的那些。漏洞公開到修補完成之間的暫時緩解（WAF 規則、關閉功能）見 [7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/) 的〈修補窗口期內的暫時緩解〉。

## 延伸閱讀：實測紀錄、入口層、管理通道、CDN 的分發與兩個網路之間的連線

- [源站防火牆只放行 Cloudflare 位址的實測紀錄：firewalld、Docker 發佈的連接埠、DOCKER-USER、nftables 表與出站 DNS](/infra/03-network-foundation/hands-on/origin-firewall-walkthrough/)：firewalld 的 ipset 與 rich rule、Docker 發佈的連接埠繞過 firewalld、`DOCKER-USER` 在 reload 後消失而在 dockerd 重啟後還在、`StrictForwardPorts` 只管連接埠不管來源、nftables 表在 reload 與重開機之後的存續、出站 DNS 的 policy 對主機與容器的不同效果，每一步的指令與輸出
- [流量入口層 — 請求怎麼從使用者到達應用](/infra/03-network-foundation/traffic-entry-layer/)：DNS、負載平衡、反向代理與應用在責任鏈上的分工，TLS 終結放在哪一層，單機 nginx 與雲端負載平衡器的選擇條件
- [伺服器管理通道的設計：網路可達性、通道授權、主機登入驗證三層的做法與選擇，以及救援入口](/infra/03-network-foundation/management-access-channel/)：只放行 CDN 位址之後，管理員登入主機的那條通道的做法與選擇
- [5.9 邊緣分發與靜態資源（CDN / Origin Protection）](/backend/05-deployment-platform/edge-cdn-static-distribution/)：CDN 在分發與快取上的責任，以及它跟入口資安的交接
- [7.43 兩個網路之間的連線安全：可達範圍、連線方向與流入的資料、被入侵端改不到的限制、應用層認證、監控主機的位置、金鑰與控制平面、異地備份的寫入憑證與連線紀錄](/backend/07-security-data-protection/cross-network-connection-security/)：VPN 隧道介面上的 `DOCKER-USER` 規則與只放行回應的連線追蹤規則
