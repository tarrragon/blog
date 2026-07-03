---
title: "nginx 實務配置"
date: 2026-07-03
description: "用 nginx 當反向代理配 upstream、負載分散方法、健康檢查與 timeout 時，特別是要知道開源版的主動健康檢查限制與 proxy header 陷阱時回來讀"
weight: 3
tags: ["devops", "nginx", "load-balancing", "reverse-proxy", "upstream"]
---

nginx 當反向代理的核心是一個 `upstream` 區塊加 `proxy_pass`：`upstream` 定義後端群組跟分散策略，`proxy_pass` 把請求轉過去。最小配置很短，但真正決定線上行為的是三個判讀點——用哪種負載分散方法、健康檢查怎麼配、timeout 怎麼串。其中開源 nginx 有一個最容易踩的限制：主動健康檢查是商業版功能，這一點不知道會讓人以為配了主動探測、實際上根本沒生效。

以下配置在 nginx 1.30.3（stable）上以 `nginx -t` 驗證過語法。

## upstream 與負載分散方法

`upstream` 區塊列出後端伺服器，並用一個指令選負載分散方法。預設是 round-robin（不寫任何方法指令就是它）；`least_conn` 送給當前連線數最少的後端；`ip_hash` 依 client IP 固定分配；`hash $key consistent` 是加了 `consistent` 參數的一致性雜湊。這些方法對應 [負載分散演算法](/devops/01-load-balancing/load-balancing-algorithms/) 講的選擇，nginx 只是把它們寫成一行指令。

```nginx
upstream api {
    least_conn;
    server 10.0.1.11:8080 max_fails=3 fail_timeout=15s;
    server 10.0.1.12:8080 max_fails=3 fail_timeout=15s;
    server 10.0.1.13:8080 backup;
    keepalive 32;
}
```

`server` 行上的參數各有用途。`backup` 標記的後端平時不接流量，只在其他後端都不可用時才頂上——當降級備援用。`keepalive 32` 讓 nginx 對後端維持一個連線池、重用連線，省下每個請求都重新握手的成本；高流量下這個設定對延遲影響明顯。`weight=N`（未在上例）給規格不同的後端配權重，對應加權輪流。

## 被動健康檢查：開源版的健康檢查

開源 nginx 的健康檢查是被動的，靠 `server` 行上的 `max_fails` 跟 `fail_timeout` 兩個參數。語意是：在 `fail_timeout` 這段時間內，轉發給某個後端的請求失敗達到 `max_fails` 次，nginx 就把這個後端標記為不可用、停送 `fail_timeout` 秒，之後再試探性地放流量回去。上例的 `max_fails=3 fail_timeout=15s` 表示 15 秒內失敗 3 次就暫停這個後端 15 秒。

被動的特性是它不額外發探測請求，而是從真實流量的失敗學到後端壞了。代價是要先犧牲幾個真實請求（達到 `max_fails`）才會摘除——後端壞掉的當下，是幾個真實使用者撞到錯誤，nginx 才反應過來。這跟主動探測的差別、以及兩者盲點，在 [健康檢查路由設計](/devops/01-load-balancing/health-check-routing/) 有完整對照。

## gotcha：主動 health_check 是商業版功能

想在 nginx 上配主動健康檢查（定時對後端 `/healthz` 探測、不靠真實流量），會發現 `health_check` 這個指令在開源版根本不存在。在 nginx 1.30.3 上放一個 `health_check` 指令跑 `nginx -t`，直接報 `[emerg] unknown directive "health_check"`、配置測試失敗——它是 nginx Plus（商業訂閱）才有的指令。這個限制不知道的話，很容易照著某些教學把 `health_check` 寫進去、以為配了主動探測，實際上配置根本載入不了，或在別處抄來的 Plus 配置直接讓 nginx 起不來。

開源版要主動探測有兩條路：一是裝第三方模組（如 `nginx_upstream_check_module`），要重新編譯 nginx，維護成本較高；二是不在 nginx 內做，改用外部探測——一個獨立的定時器對後端探測，探到不健康就從服務發現或配置裡摘掉。多數情況下，被動的 `max_fails` 加上外部的主動探測，就覆蓋了「後端回應了但一直出錯」跟「後端整個沒回應」兩種失效，不必為了主動探測上商業版。

## proxy header 陷阱：後端看到的來源 IP

`proxy_pass` 轉發時，如果不主動設 header，後端看到的來源 IP 會是 nginx 的 IP、而不是真實客戶端的——因為連線是 nginx 發起的。這會讓後端的存取日誌、限流、地理判斷全部失準，全世界的請求看起來都來自 nginx 那台。修法是明確把原始資訊放進 header：

```nginx
location / {
    proxy_pass http://api;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_connect_timeout 5s;
    proxy_read_timeout 30s;
    proxy_next_upstream error timeout http_502 http_503;
}
```

`proxy_set_header Host $host` 保留原始的 host header（否則後端收到的 Host 會是 upstream 名稱，依 host 分辨虛擬主機的後端會錯亂）。`X-Forwarded-For $proxy_add_x_forwarded_for` 把真實客戶端 IP 附進去、且保留鏈上前面的代理紀錄，後端要讀真實 IP 就從這個 header 取。

## timeout 與重試

`proxy_connect_timeout` 是 nginx 連到後端的逾時、`proxy_read_timeout` 是等後端回應的逾時。這兩個要放進 [反向代理職責](/devops/01-load-balancing/reverse-proxy-responsibilities/) 講的 timeout 層級串聯裡看——nginx 這層的 timeout 要大於它後面的應用層、小於它前面的客戶端層，否則會出現外層先放棄、內層還在做白工。

`proxy_next_upstream` 決定一個後端失敗時要不要把請求重試到下一個後端。上例的 `error timeout http_502 http_503` 表示連線錯誤、逾時、後端回 502/503 時自動重試下一台。這個機制對讀請求很有用（一台壞了自動換一台），但對非冪等的寫請求要謹慎——如果一個 POST 已經被後端處理了、只是回應在傳輸中逾時，重試會讓這個 POST 執行第二次。要重試非冪等請求前，得先確認後端有冪等保護（例如靠 idempotency key 去重），否則把 `POST` 放進 `proxy_next_upstream` 的重試條件會製造重複寫入。

## 下一步路由

- 這些方法各適合什麼流量型態 → [負載分散演算法](/devops/01-load-balancing/load-balancing-algorithms/)
- 被動與主動健康檢查的完整對照、閾值怎麼定 → [健康檢查路由設計](/devops/01-load-balancing/health-check-routing/)
- timeout 為什麼要由外到內遞減 → [反向代理的職責](/devops/01-load-balancing/reverse-proxy-responsibilities/)
- 雲端 LB 上等價的 listener、target group、健康檢查怎麼用 IaC 描述 → [infra：入口上 IaC](/infra/05-core-services/loadbalancer-alb/)
