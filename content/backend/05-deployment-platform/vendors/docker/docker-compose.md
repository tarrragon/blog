---
title: "Docker Compose：多 service dev 環境編排"
date: 2026-07-06
description: "一個 app 要好幾個 container(DB / cache / web)、手動 docker run 串不起來、或 compose 起來後 app 連不到 DB 或 DB 還沒 ready 就被連時回來讀 — 多 service 怎麼宣告式編排"
weight: 20
tags: ["backend", "deployment", "docker", "docker-compose"]
---

一個 app 要好幾個 container（app + DB + cache）一起跑、彼此連通，是單一 image 的 Dockerfile（[Dockerfile 設計](/backend/05-deployment-platform/vendors/docker/dockerfile-design/)）之上的下一層問題。如果你正納悶「為什麼是好幾個 container、不是一個大 container 全塞」，先讀 [一容器一職責](/backend/knowledge-cards/container-per-service/)——這篇假設你已經接受一服務一容器，往下講怎麼把它們串起來。上游是 [Docker vendor overview](/backend/05-deployment-platform/vendors/docker/)。

## 手動串三個 container 的痛

一個典型的 web app 開發環境要三個 container：PHP-FPM 跑程式、MySQL 存資料、nginx 收 HTTP。用 `docker run` 手動串，你得記住：先開一個 network、按順序啟動、每個都帶一長串 `-v` 掛 volume、`--network` 接網路、`-e` 設環境變數、`-p` 對 port，還要記得 nginx 要能用名字找到 PHP。換一台機器、或同事要跑，整套指令重來一次，漏一個 flag 就連不起來。

Docker Compose 解決的就是這個：把「這個 app 需要哪些 container、怎麼連、掛什麼」寫成一個宣告式的 `docker-compose.yml`，`docker compose up` 一次拉起整套。

## 核心概念：一個檔描述整個拓樸

Compose 的核心是「用一份宣告式檔案描述多 service 的完整拓樸」。你寫的是**期望的最終狀態**（要哪些 service、各自的 image / network / volume），Compose 負責把它變成現實：

- **service 是編排單位**：每個 service 對應一個（或多個 replica）container，Compose 管它們的生命週期。
- **network 預設自動建**：同一個 compose 檔的所有 service 自動進同一個 network，彼此用 **service name 當 hostname** 互連——nginx 連 `php:9000`、PHP 連 `db:3306`，不需要知道 IP。
- **volume 讓資料活過 container**：container 是可拋棄的，要保留的資料（DB 檔）放 named volume，`down` 再 `up` 資料還在。

## 配置：三件套逐段

以下是一個實際跑起來的 PHP 7.2 + MySQL 5.7 + nginx 組合（版本凍結的 dev runtime），逐段拆解。

```yaml
services:
  php:
    build: ./php              # 用本地 Dockerfile build
    volumes:
      - ./src:/var/www/html   # bind mount：改 code 立即反映進 container
    depends_on:
      - db

  web:
    image: nginx:1.18         # 直接用 registry image，釘版本
    ports:
      - "8080:80"             # host 8080 → container 80
    volumes:
      - ./src:/var/www/html
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - php

  db:
    image: mysql:5.7
    platform: linux/amd64     # arm64 主機上跑無原生 image 的舊 MySQL（見故障演練）
    environment:
      MYSQL_ROOT_PASSWORD: secret
      MYSQL_DATABASE: app
    volumes:
      - db-data:/var/lib/mysql # named volume：DB 資料活過 container 重建

volumes:
  db-data:
```

幾個決策點：

- **`build` vs `image`**：php service 用 `build: ./php` 從本地 Dockerfile 建（你要客製），web / db 用 `image:` 直接拉現成的。同一個 compose 檔可以混用。
- **bind mount vs named volume**：`./src:/var/www/html` 是 bind mount，把 host 的原始碼目錄掛進 container，改 code 立即生效、適合 dev；`db-data:/var/lib/mysql` 是 named volume，由 Docker 管理、適合要保留但不需要人去看的資料。兩者用途不同，不要混。
- **`depends_on`**：宣告啟動順序（db 先於 php 先於 web）。這條有個重要邊界，見故障演練。
- **`ports` 只在 web 開**：只有 web 需要對外，php 跟 db 不開 `ports`——它們透過內部 network 被 web / php 用 service name 連到，不必也不該暴露到 host。

這份是聚焦編排結構的最小版：web 掛的 `nginx/default.conf` 最小內容就是把 `.php` 請求 `fastcgi_pass` 到 `php:9000`；要對齊 prod 還得補時區（db 的 `TZ` + MySQL `default-time-zone`）、`sql_mode` 等設定。完整可跑並附 parity 驗證的版本見 [對齊 prod 的 runtime container](/linux/dotfile/10-prod-parity/prod-parity-runtime/)。

跑起來：

```bash
docker compose up -d --build   # build + 背景啟動整套
docker compose ps              # 看三個 service 狀態
docker compose logs -f db      # 追某個 service 的 log
docker compose down -v         # 停掉並清掉（-v 連 named volume 一起清）
```

## 故障演練：起得來卻連不通

### depends_on 不等於「服務 ready」

最常見的誤解：以為 `depends_on: db` 會等 MySQL 可以接受連線才啟動 php。實際上 `depends_on` 只等到 db container **啟動了**（process 起來），不等它**服務 ready**。MySQL container 起來後還要幾秒到幾十秒初始化資料目錄，這段期間 php 連過去會吃到 `Connection refused` 或 `Lost connection`。

徵兆是 `docker compose up` 後 app 立刻報連不到 DB，但過一下手動連又通了。兩種修法：

其一，用 healthcheck + `condition: service_healthy` 讓 Compose 真的等到 DB 健康（healthcheck 作為通用的服務健康判讀見 [Health Check](/backend/knowledge-cards/health-check/)）：

```yaml
  db:
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 5s
      retries: 10
  php:
    depends_on:
      db:
        condition: service_healthy
```

其二，在應用層做連線重試（開機時連不上就 backoff 重試）。實務上兩者常一起用——healthcheck 處理啟動順序、應用層重試處理執行期間 DB 短暫重啟。應用層重試更穩健，因為 DB 在服務跑起來之後也可能短暫斷線。

### arm64 主機跑無原生 image 的舊服務

在 Apple Silicon（arm64）主機上 `docker compose up`，mysql:5.7 可能報 image 找不到對應架構、或直接不啟動。根因是 MySQL 5.7 官方 image 只出 amd64、沒有 arm64 原生版。修法是明確宣告 `platform: linux/amd64`，讓它透過模擬跑：

```yaml
  db:
    image: mysql:5.7
    platform: linux/amd64
```

代價是模擬有效能損耗、啟動較慢。這本身也是一種環境對齊——dev 是模擬 amd64、prod 是原生 amd64，架構一致。為什麼沒有原生 image 就得靠模擬、`exec format error` 怎麼來，見 [QEMU binfmt 跨架構模擬](/backend/knowledge-cards/qemu-binfmt-emulation/)；跨平台 build 的完整配置見 [BuildKit 與跨平台 build](/backend/05-deployment-platform/vendors/docker/buildkit-cross-platform/)。

### service 間連線用 service name，不是 localhost

在 php container 裡連 MySQL，連線字串要用 `db`（service name）不是 `localhost`：

```php
$pdo = new PDO('mysql:host=db;dbname=app', 'root', 'secret');
```

每個 container 有自己的 network namespace，`localhost` 指的是 container 自己、不是別的 service。Compose 的自動 network 讓 service name 解析成對的 container IP。寫成 `localhost:3306` 會連到 php container 自己的 3306（沒東西在聽）→ `Connection refused`。這是從「單機所有東西都在 localhost」搬進容器時最常見的錯。

### down 不帶 -v，資料還在

`docker compose down` 停掉並移除 container、network，但**保留 named volume**。所以 `down` 再 `up` 之後 DB 資料還在——這通常是你要的。但如果你想要一個全新的 DB（例如改了初始化 SQL、要重跑），必須 `down -v` 把 volume 也清掉，否則舊資料還在、初始化腳本不會重跑（MySQL image 只在資料目錄空的時候跑初始化）。徵兆是「我改了 init.sql 但 compose 起來沒生效」——因為 volume 裡的舊資料還在。

## 容量：compose 到哪裡為止

Compose 的定位是 **single-host 的多 container 編排**，適用範圍要清楚：

- **適合**：本機 dev 環境、CI 裡起依賴服務跑整合測試、單機小型部署（一台 VM 跑幾個 container 的內部工具）。
- **不適合**：多 host、需要自動擴縮、rolling update、self-healing 的 production。這些是 orchestrator 的職責。

界線的訊號是「你開始想要跨機器調度、或要 replica 自動補」——那是該換 [Kubernetes](/backend/05-deployment-platform/kubernetes-deployment/) 的訊號。好消息是 image 不用變，換的是編排層（compose → K8s manifest），Dockerfile build 出的 image 兩邊通用。

## 整合與下一步

- compose 裡 `build:` 指向的 Dockerfile 怎麼設計，見 [Dockerfile 設計](/backend/05-deployment-platform/vendors/docker/dockerfile-design/)。
- 一個完整的「用 compose 對齊 client 線上舊環境」實作（含 parity probe 驗證），見 [對齊 prod 的 runtime container](/linux/dotfile/10-prod-parity/prod-parity-runtime/)。
- 從 compose 搬到 production 編排，見 [Kubernetes deployment](/backend/05-deployment-platform/kubernetes-deployment/)。
