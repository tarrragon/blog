---
title: "反向代理的職責"
date: 2026-07-03
description: "釐清反向代理在單一入口後面承擔哪些職責、TLS 終止與路由怎麼設計、以及一條請求路徑上的 timeout 為什麼要由外到內遞減時回來讀"
weight: 1
tags: ["devops", "reverse-proxy", "load-balancing", "tls", "routing"]
---

反向代理是擋在使用者與後端服務之間的單一入口：使用者連的永遠是它，它再決定把每個請求送給後面哪個服務實例。這一層存在的理由是把「對外的穩定介面」跟「對內的可變拓撲」分開——後端實例可以增減、替換、搬家，使用者看到的入口位址不變。少了這一層，每個後端實例的位址都會外露，換一台機器就要通知所有客戶端改連線。

反向代理承擔四類職責：TLS 終止、路由、負載分散、健康檢查。負載分散怎麼選演算法是 [負載分散演算法](/operations/01-load-balancing/load-balancing-algorithms/) 的主題，健康檢查怎麼設計是 [健康檢查路由設計](/operations/01-load-balancing/health-check-routing/) 的主題；這一章先把四類職責的邊界劃清楚，並展開 TLS 終止、路由、以及貫穿它們的連線管理。

## TLS 終止：把加密收在入口

TLS 終止指反向代理在入口解開 HTTPS 加密，後端拿到的是解密後的 HTTP。這樣設計把憑證管理跟加解密的成本集中在一個地方——憑證只需要裝在入口這一層，後端實例不必各自持有憑證、不必各自做加解密。要新增一個後端實例時，它不需要知道任何 TLS 的事，入口已經把加密處理掉了。

集中的代價是入口到後端這段變成明文。這段通常跑在私有網路內（後端住在 private subnet、只接受來自入口的流量），威脅模型是「這段網路是可信的」；若這段也要加密（例如合規要求端到端加密），就要做 TLS 重新加密或 mTLS，那是把成本換回分散。入口該接受哪些 TLS 版本、憑證怎麼簽發與續期，在雲端 LB 上是 IaC 的描述範圍，[infra 的 ALB 篇](/infra/05-core-services/loadbalancer-alb/) 有 `ssl_policy`、ACM 簽發與 DNS 驗證的完整 IaC；這一章關注的是「終止在入口」這個職責決策本身。

## 路由：一個入口分流到多個服務

路由指反向代理依請求的特徵（host header、路徑）把流量分到不同的後端群組。這讓多個服務共用一個入口——`/auth/*` 導向認證服務、`/api/*` 導向 API 服務，各自是獨立的後端群組，但對外只有一個網域、一個入口。路由的收斂價值在成本與管理面：共用一個入口、用路由規則分流，省下每個服務各開一個入口的固定成本。

分流的邊界要看服務之間的差異。流量特徵、安全等級接近的服務適合共用入口，用路由規則分開就夠；當某個服務需要獨立的防火牆規則、獨立的流量隔離時，替它開獨立入口才合理。路由規則本身是聲明式的（哪個 host 或 path 對到哪個後端群組），複雜的路由邏輯（依 header、依權重、依版本做灰度）會把入口從單純的分流變成流量控制面，那牽涉到部署切換的節奏，屬於 [backend 的流量配置控制面](/backend/05-deployment-platform/traffic-config-control-plane-boundary/) 的範圍。

## 負載分散與健康檢查：這裡先劃邊界

負載分散是反向代理把流量分攤到同一個後端群組內多個實例的職責，健康檢查是它判斷某個實例還能不能接流量的職責。這兩者關係緊密——負載分散只把流量分給健康檢查認為健康的實例。演算法怎麼選（誰接下一個請求）在 [負載分散演算法](/operations/01-load-balancing/load-balancing-algorithms/) 展開，健康怎麼判（被動觀察還是主動探測、多久判一次）在 [健康檢查路由設計](/operations/01-load-balancing/health-check-routing/) 展開。這一章只確立它們是反向代理的職責、且互相依賴。

## 連線管理：timeout 要由外到內遞減

反向代理夾在使用者與後端之間，兩側的連線都由它管，其中最容易設錯的是 timeout。一條請求路徑上有多層 timeout——瀏覽器、CDN、反向代理、應用、資料庫，每層各有預設值。設計原則是由外到內遞減：外層（離使用者近）的 timeout 要大於內層（離資料源近）。

| 層級             | 典型 timeout 範圍 | 設定位置                          |
| ---------------- | ----------------- | --------------------------------- |
| Client / Browser | 30-120 秒         | 前端 fetch / SDK 設定             |
| CDN edge         | 5-30 秒           | CDN vendor 設定                   |
| 反向代理 / LB    | 30-60 秒          | LB idle timeout / request timeout |
| Application      | 5-30 秒           | HTTP server read/write timeout    |
| Database / Cache | 1-5 秒            | 連線池 query / connect timeout    |

遞減的理由是避免「外層先放棄、內層還在做白工」。如果反向代理 timeout 設 30 秒、應用設 60 秒，代理會在 30 秒回 504 給使用者，但應用仍持有連線等資料庫回應——佔用連線資源卻交付不了結果。這類失誤最常見的版本是只調反向代理這一層：使用者回報 timeout，就把代理的 timeout 從 30 秒調到 120 秒。結果是慢請求佔用連線更久、連線池被慢請求填滿、正常請求也開始排隊。穩定的做法是先在應用或資料庫層找出延遲根因，而不是放大外層 timeout 去「等更久」。

## 反向代理是部署與事故的決策點

把反向代理當成「只做轉發」的元件，會低估它在部署與事故裡的決策角色。它的設定定義了流量怎麼切換、回退可不可行、故障擴散多快——TLS 收在哪、路由怎麼分、timeout 怎麼串、健康怎麼判，每一項都在正常時無感、在事故時決定損失大小。這一層的完整合約（routing、health、connection、drain 四部分怎麼協同）在 [backend 的 load balancer 合約](/backend/05-deployment-platform/load-balancer-contract/) 展開。

## 下一步路由

- 入口層的整體地圖（DNS → 負載平衡 → reverse proxy → 應用的責任鏈、TLS 終結位置、單機與雲端入口的選擇條件）→ [infra：流量入口層](/infra/03-network-foundation/traffic-entry-layer/)
- 流量分給哪個實例、依什麼演算法 → [負載分散演算法](/operations/01-load-balancing/load-balancing-algorithms/)
- 在 nginx 上把 upstream、健康檢查、timeout 配起來 → [nginx 實務配置](/operations/01-load-balancing/nginx-configuration/)
- 健康怎麼判、多久判一次、判錯的後果 → [健康檢查路由設計](/operations/01-load-balancing/health-check-routing/)
- 反向代理的 IaC 描述（listener、target group、TLS、健康檢查）→ [infra：入口上 IaC](/infra/05-core-services/loadbalancer-alb/)
