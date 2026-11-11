---
title: "Reverse Proxy"
date: 2026-06-26
description: "代替後端服務接收外部請求、再轉發到內部服務的中介層，承擔 TLS 終結、負載平衡與路由分流"
weight: 44
tags: ["infra", "knowledge-cards", "network", "proxy"]
aliases: ["/infra/knowledge-cards/reverse-proxy/"]
---

Reverse proxy 是一個坐在後端服務前面、代替它接收外部請求的中介層。外部 client 連的是 reverse proxy 的位址，reverse proxy 根據規則把請求轉發到實際處理的內部服務，再把回應傳回給 client。Client 不知道（也不需要知道）後面有幾台服務、跑在哪裡。實務上最常見的實作是 [nginx](/devops/infra/knowledge-cards/nginx/) 或 ALB。

## 跟其他概念的關係

nginx 和 [ALB](/devops/infra/knowledge-cards/alb/) 都扮演 reverse proxy 角色。差別在層級：nginx 通常部署在應用層（跟應用伺服器同一台或同一個 VPC 內），ALB 是雲端平台提供的受管服務。兩者的核心功能相同——接收外部流量、轉發到後端、回傳結果。

跟 forward proxy 的方向相反：forward proxy 代替 client 發送請求（client 在內網、proxy 幫它出去）；reverse proxy 代替 server 接收請求（server 在內網、proxy 幫它面對外部）。reverse proxy 在流量入口責任鏈裡的位置、跟 DNS 與負載平衡層的交棒關係，見[流量入口層](/devops/infra/03-network-foundation/traffic-entry-layer/)。

## 可觀察訊號

接手時如果 server 上跑著 nginx 但應用程式用的是 PHP-FPM 或 Node.js，nginx 多半扮演 reverse proxy——它接 HTTP/HTTPS 請求、轉發給後端的 application server。設定檔裡的 `proxy_pass`（nginx）或 `ProxyPass`（Apache）就是 reverse proxy 的轉發規則，用在講 HTTP 的後端（Node.js、Python 的 gunicorn 這類）。PHP-FPM 只講 FastCGI，nginx 轉給它用的是 `fastcgi_pass`，Apache 用 `mod_proxy_fcgi`；用 `proxy_pass` 指向 PHP-FPM 的埠不會成功，見 [FastCGI](/programming/php/01-server-runtime/fastcgi/)。

## 判斷條件與後果

reverse proxy 常承擔的功能：

| 功能         | 說明                                                         |
| ------------ | ------------------------------------------------------------ |
| TLS 終結     | HTTPS 的加解密在 proxy 層處理，後端服務只收 HTTP             |
| 負載平衡     | 把請求分配到多台後端（round-robin、least-connection）        |
| 路由分流     | 依 URL path 導到不同後端服務（/api → backend、/ → frontend） |
| 靜態檔案快取 | 圖片、CSS、JS 由 proxy 直接回應、不轉發到後端                |
| 安全過濾     | 擋掉異常請求、限制請求速率、加安全標頭                       |

接手一台前面有 reverse proxy 的服務時，判斷的對象是表格裡哪幾項功能由 proxy 執行、哪幾項仍由後端執行，以及 proxy 用哪一種協定轉給後端。TLS 在 proxy 終結時，後端收到的是 HTTP 請求，連線的來源位址是 proxy 自己；後端程式依連線判斷請求是否走 HTTPS、或記錄 client IP 時，拿到的是 proxy 到後端那一段連線的協定與位址，原因是 client 的原始連線只存在於 client 與 proxy 之間，後端要讀 proxy 加上的 `X-Forwarded-For`、`X-Forwarded-Proto` 標頭才拿得到。被 proxy 的安全過濾或靜態檔案快取處理掉的請求不會轉到後端，後端的 log 裡沒有這些請求，查這類請求要讀 proxy 的 log。轉發規則與後端講的協定對不上時（用 `proxy_pass` 指向只講 FastCGI 的 PHP-FPM），請求送到了後端的埠，而 nginx 收不到它讀得懂的回應，回給 client 的是 502。

## 鄰卡

- [ALB](/devops/infra/knowledge-cards/alb/)：雲端的受管 reverse proxy + 負載平衡器
- [nginx](/devops/infra/knowledge-cards/nginx/)：最常見的 reverse proxy 軟體
- [PHP-FPM](/programming/php/knowledge-cards/php-fpm/)：只講 FastCGI 的 PHP 後端，nginx 用 `fastcgi_pass` 而非 `proxy_pass` 轉給它
