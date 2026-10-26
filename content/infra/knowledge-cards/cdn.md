---
title: "CDN（內容遞送網路）"
date: 2026-10-25
description: "網站要放到 Cloudflare 這類服務後面、看到回應標頭帶著 CDN 的標記、或要判斷源站看到的來源位址是誰時，查 CDN 代替源站接收連線的方式、回源與它對源站防火牆的影響"
weight: 66
tags: ["infra", "knowledge-cards", "cdn", "network"]
---

CDN（content delivery network，內容遞送網路）是一組分散在各地機房的伺服器，代替網站的源站（實際跑網站程式的主機）接收使用者的連線：使用者連到離自己近的 CDN 機房，CDN 能用快取回應的就直接回，不能的再從自己的機房連回源站取回應，這個動作叫回源。決定使用者連到哪裡的是網域的 [DNS](/infra/knowledge-cards/dns/) 記錄：記錄設成經由 CDN 代理時，解析網域拿到的是 CDN 的位址。

## 概念位置

CDN 排在請求路徑的最前面，在源站的 [Reverse Proxy](/infra/knowledge-cards/reverse-proxy/) 與應用之前，承擔的是邊緣的遞送、快取與過濾（[WAF](/backend/knowledge-cards/waf/) 規則、速率限制、依國家封鎖）。這些過濾只對經過 CDN 的請求作用：源站的位址一旦被知道，請求可以跳過 CDN 直接連源站，所以 CDN 後面的源站要另外在雲端的 [Security Group](/infra/knowledge-cards/security-group/) 或主機防火牆上只放行 CDN 的位址。CDN 回源時用的是它自己機房的位址，經由 CDN 送來的請求，源站看到的連線來源因此是 CDN 的位址，使用者真正的位址放在 CDN 加上的 HTTP 標頭裡（Cloudflare 是 `CF-Connecting-IP`）。

## 可觀察訊號與例子

- **回應標頭帶著 CDN 的標記**：Cloudflare 代理的網站回應帶 `cf-ray` 與 `server: cloudflare`。看到它代表這一次請求經過了 CDN，不代表所有訪客都經過：其他訪客的 DNS 快取可能還指向源站的舊位址。
- **源站的存取記錄裡全是同幾段位址**：那是 CDN 機房的位址；要記錄使用者的位址，反向代理要設定成只信任來自 CDN 位址段的 `CF-Connecting-IP`（nginx 的 `set_real_ip_from` 加 `real_ip_header`）。這個設定擋得下不經 CDN 的直連偽造，擋不下從 CDN 位址送來的偽造：任何帳號的 Cloudflare Worker 都從 Cloudflare 的位址送出、標頭可以自己寫，實測見 [Cloudflare 回源的實測紀錄：Oracle Cloud NSG 只放行 Cloudflare 位址與規則數上限、回源的來源位址、Authenticated Origin Pulls、Worker 偽造 CF-Connecting-IP 與 Tunnel 的出站連接埠](/infra/03-network-foundation/hands-on/cloudflare-origin-pull-walkthrough/)。
- **CDN 公佈的位址清單**：Cloudflare 在 `https://www.cloudflare.com/ips-v4` 與 `ips-v6` 公佈回源用的位址段，2026-10-25 是 15 段 IPv4 與 7 段 IPv6；源站的防火牆規則就是拿這份清單寫的。

## 判讀方式

判斷一條請求經不經過 CDN，看的是使用者解析網域拿到的位址，而不是網站有沒有開 CDN：子網域沒有設成代理、或舊記錄還在快取裡時，那些請求直接到源站，CDN 上的規則管不到它們。CDN 的位址由所有客戶共用，只放行 CDN 位址擋得住不經過 CDN 的直連，擋不住別人用自己的 CDN 帳號指向這台源站；要分得出，要用 CDN 端的回源驗證（Cloudflare 的 Authenticated Origin Pulls 用自己上傳的憑證，或 Tunnel）。源站防火牆的位置、套用時機與 Docker 的陷阱見 [CDN 後面的源站主機防火牆：只放行 CDN 來源的位置與套用時機、Docker 發佈連接埠的封包路徑、出站 DNS 的限制與地理封鎖](/infra/03-network-foundation/origin-host-firewall/)。「origin protection」在快取的語境裡指的是快取未命中時保護源站的負載，見 [Origin Protection](/backend/knowledge-cards/origin-protection/)，跟這裡的源站安全是兩件事。
