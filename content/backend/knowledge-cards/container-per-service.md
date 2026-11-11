---
title: "Container-per-Service（一容器一職責）"
date: 2026-07-06
description: "第一次發現一個 web app 要開好幾個 container、不懂為什麼不塞一個大 container、或不確定什麼該獨立成一個 container 時回來讀 — 一容器一職責的理由與邊界"
weight: 130
tags: ["backend", "deployment", "docker", "container", "knowledge-cards"]
---

一容器一職責是「一個 container 只承擔一個服務職責」的設計原則。它承接 [Container](/backend/knowledge-cards/container/) 的「交付單位」概念，再往前一步回答「一個 app 要好幾個服務時，該塞進一個 container 還是拆成多個」——答案是各服務各一個 container，而不是一個大 container 全包。一個典型 web app 因此常是三個：web server 收 HTTP、application runtime 跑程式、database 存資料。

## 跟其他概念的關係

一容器一職責位在「image 設計」與「多服務編排」之間：它把 [Container](/backend/knowledge-cards/container/) 的交付單位往上一步，決定一個系統被切成幾個 container，是 [Docker Compose](/backend/05-deployment-platform/vendors/docker/docker-compose/) 或 Kubernetes 編排的前提。切錯了（把多個服務塞一個 container），後面的編排、擴縮、重啟都會卡住。

## 為什麼各服務各一個 container

把 nginx、PHP-FPM、MySQL 拆成三個 container，而不是一個裡面全跑，理由是每一條都靠「職責分離」成立：

- **獨立生命週期**：改 nginx 設定重啟它，不會順手殺掉 MySQL、斷掉正在進行的連線。三個各自崩潰、各自重啟、各自升級。
- **各用最適 image**：MySQL 用官方 `mysql`、PHP 用 `php:fpm`、nginx 用 `nginx`，各自的最佳 base、版本與更新節奏；不必用一個 image 硬塞三套環境。
- **一個主進程等於乾淨的 PID 1**：container 的「活著」等於它主進程活著。塞兩個主進程，平台無法判斷「這個 container 該算健康還是該重啟」，信號處理與 zombie reaping（回收已結束的子進程）也變複雜（見 [Container](/backend/knowledge-cards/container/) runtime 的 PID 1 討論）。
- **獨立擴縮**：線上可能要 3 個 web + 1 個 database。綁在一起就無法只擴 web。
- **可替換**：把 MySQL 換成 MariaDB、nginx 換成 Caddy，只動那一個 container，其餘不受影響。

## 可觀察訊號

系統該拆成多 container 的訊號是「這幾個東西的重啟、升級、擴縮節奏不同」。web server 常改設定重載、database 幾乎不動、application 隨每次部署更新——三種節奏不同，就是三個 container。反過來，如果你發現一個 container 的 Dockerfile 裡 `apt install` 了 nginx + php + mysql、`CMD` 要用 shell 同時起三個服務，那就是把該拆的塞進了一個。

## 接近真實網路服務的例子

線上的服務拓樸本來就是分離的：nginx 在自己的 container / pod、app 在自己的、database 是託管服務或獨立 container。dev 環境用三個 container 對齊這個拓樸，「本機能跑」才接近「線上能跑」（這正是 [prod parity](/linux/dotfile/knowledge-cards/prod-parity-principle/) 的一環——連服務怎麼切都對齊）。用 Compose 把這三個串起來的實作見 [Docker Compose](/backend/05-deployment-platform/vendors/docker/docker-compose/)。

## 判斷條件與後果

一個 container 該不該拆，看裡面跑的是一個職責還是幾個服務。一個主進程帶著它自己 fork 出的子進程（php-fpm 的 worker、nginx 的 worker）屬於同一個職責，放在同一個 container 裡，重啟、升級與擴縮的節奏都一致；web、app、database、cache 是不同的服務，各是一個職責，放進同一個 container 時，上面列的獨立生命週期、獨立擴縮與可替換就一起失去。nginx 與 PHP-FPM 拆成兩個容器時程式碼要兩邊都有，放進同一個容器時要自己做程序監看，兩種切法的做法與陷阱見 [容器裡的 Nginx 與 PHP-FPM](/programming/php/01-server-runtime/nginx-php-fpm-containers/)。

dev 環境把全部塞進一個 container 也跑得起來，代價是失去上面每一條好處，也偏離線上拓樸；這跟 [prod parity](/linux/dotfile/knowledge-cards/prod-parity-principle/) 的取捨一致，是否值得取決於本機與線上的拓樸差異會不會讓問題只在線上出現。sidecar 這類「一個主服務加一個輔助容器（log 收集、proxy）」的模式，刻意讓兩個 container 綁同一個生命週期，屬進階編排；兩個 container 各自仍是單一職責，符合這個原則。
