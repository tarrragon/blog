---
title: "image 版本管理與升級：不動舊的、建新的"
date: 2026-07-06
description: "有一個跑著的 stack 要升版（PHP / MySQL 升級）、不想弄壞現在能跑的、又不確定多個版本的 image 跟 Dockerfile 怎麼管時回來讀 — image 不可變下的升級與版本管理"
weight: 40
tags: ["backend", "deployment", "docker", "upgrade", "versioning"]
---

這篇假設你會寫 Dockerfile 與 compose（[Dockerfile 設計](/backend/05-deployment-platform/vendors/docker/dockerfile-design/)、[Docker Compose](/backend/05-deployment-platform/vendors/docker/docker-compose/)），處理一個很常見的需求：手上有一個跑著的 stack，要升版（PHP 7.2 → 8.2、MySQL 5.7 → 8.0），但不想弄壞現在能跑的那個。上游是 [Docker vendor overview](/backend/05-deployment-platform/vendors/docker/)。

## 「怎麼升級 image、又不動原本的」是個錯位的問法

第一次要升版時，常見的問法是：「怎麼在不動原本 image 的前提下升級它？」這個問法裡藏了一個誤解——它假設「升級一個 image」是一個動作、而且會動到原本的 image。兩個假設都不成立。

[image 是不可變的](/backend/knowledge-cards/immutable-image/)：你改 Dockerfile（`FROM php:8.2-fpm`）、`docker build`，得到的是一個**全新的 image、新的 tag**。原本的 image 動不到——不是你努力「不動它」，是它按設計就改不了。所以「不動原本映象」不是要小心維護的條件，是預設狀態。真正要花力氣的地方相反：怎麼**標清楚新舊、留得住舊版的定義、需要時切回去**。這篇講的就是這個管理面。

## 升級的實際步驟：複製、改 FROM、並跑對照

以一個實際跑過的升級為例——把 PHP 7.2 / MySQL 5.7 的 stack 升成 PHP 8.2 / MySQL 8.0：

1. **複製整個 stack 目錄到新版本名**：`php72-mysql57/` → `php82-mysql8/`。兩個目錄都留著、都是獨立可跑的 stack。
2. **只改 `FROM` 與服務 tag**，其餘 config 依相容性調整：

   ```dockerfile
   # 舊：FROM php:7.2-fpm-buster
   FROM php:8.2-fpm-bookworm
   ```

   ```yaml
   # 舊：image: mysql:5.7 + platform: linux/amd64
   db:
     image: mysql:8.0
   ```

3. **build 成新 tag、用不同 port 起**，讓新舊並跑：

   ```bash
   cd php82-mysql8
   docker compose up -d --build     # 新版在 8081，舊版還在 8080
   ```

4. **用同一支 probe 逐行對照**：新舊 stack 各跑一份 `src/index.php`，印出版本 / 時區 / 擴充 / sql_mode，逐行比對哪裡變了、哪裡該一致。舊版原封不動，你隨時能回去比。

## 故障演練：升級會踩的（都是實跑撞到的）

升級不是把 tag 數字加一那麼簡單。以下是 PHP 7.2 → 8.2、MySQL 5.7 → 8.0 實測撞到的：

### MySQL 8 換了預設認證，只升一半會 auth 炸

MySQL 8.0 把預設認證外掛從 `mysql_native_password` 換成 `caching_sha2_password`（probe 實測 `auth plugin : caching_sha2_password`）。這牽動客戶端相容性：**夠舊的客戶端**（PHP 7.2.8 之前的 mysqlnd、或用舊 mysql 函式庫 / 別的語言舊驅動的 app）不認得它，連線會報 `The server requested authentication method unknown to the client` 之類的錯；PHP 7.2.8 之後的 mysqlnd 才支援（實測 PHP 8.2 連得上、這個 stack 的 7.2.34 其實也支援）。這是升級最典型的版本相依陷阱：升 MySQL 前要確認客戶端夠新、或把兩個元件一起升，不能只看 MySQL 那半。

### 升級有時反而移掉一個 workaround

舊 stack 的 compose 為了在 arm64 主機跑 `mysql:5.7`（沒有 arm64 原生 image）要加 `platform: linux/amd64` 走模擬。升到 `mysql:8.0` 後，8.0 有 arm64 原生 image（實測直接跑在 `linux/arm64`、沒走模擬），那行 `platform` 可以拿掉、還跑得更快。升級不總是「多背東西」，有時是把舊版本為了相容性堆的 workaround 清掉。

### 新 base 讓舊的稅消失

舊 stack 用 `php:7.2-fpm-buster`，buster 已 EOL、Dockerfile 要改 apt source 指 `archive.debian.org` 否則 `apt-get update` 404。升到 `php:8.2-fpm-bookworm`，bookworm 還在支援期，那段 archive workaround 直接不需要。base image 世代跟著升，前一代的 EOL 稅就消失了。

### 首次初始化更慢，depends_on 更不可靠

MySQL 8.0 首次啟動的初始化比 5.7 久（做更多設定）。實測升級後 probe 在 4 秒就打，還吃到 `Connection refused`——因為 DB 還在初始化。`depends_on` 只等 container 起來、不等服務 ready 的老問題（見 [Docker Compose](/backend/05-deployment-platform/vendors/docker/docker-compose/)）在升級後更明顯，healthcheck 或應用層重試更該補上。

### 別把要修的 deprecation 藏起來

PHP 7.2 → 8.2 跨了好幾個大版本，有移除的語法與大量 deprecation。升級時 `php.ini` 的 `error_reporting` 要開到看得見 deprecation（`E_ALL`），而不是沿用舊環境「遮掉 deprecated」的設定——那些警告正是升級要修的清單，藏起來只會讓問題延到線上才爆。

## 版本管理：怎麼管多個 stack 的 Dockerfile

- **一個目錄一個版本化 stack**：`php72-mysql57/`、`php82-mysql8/` 各自完整、各自可跑。比「一份 Dockerfile 用 `ARG PHP_VERSION` 切」更適合「要精確留住舊版」的場景——參數化雖然 DRY，但舊版要重現得記得當時的 ARG 組合；獨立目錄一眼可 diff、直接可跑。
- **舊版靠 git 重現，不用存 image 檔**：Dockerfile 在 git，任何一版隨時 `git checkout` 舊目錄 + rebuild 就一模一樣長回來。留的是「精確可重現的定義」，不是備份一堆 image tar。
- **tag 策略**：自用可讀性優先，用 stack 描述 tag（`app:php8.2-mysql8`）；要嚴謹再加 [digest](/backend/knowledge-cards/immutable-image/) 釘死。線上部署則常用 git commit SHA 當 tag，讓每個 tag 唯一對應一次 build。
- **什麼時候留平行、什麼時候取代**：升級驗證期間新舊並存（能隨時比對、隨時切回）；新版穩定服務一段時間、確定不用回退，再把舊目錄退役（但 git 歷史裡永遠找得回）。

## 容量：這篇到哪為止

這篇講的是**自用 / 小規模的版本升級**——建新的、並跑對照、切換。它刻意不碰「線上服務不中斷的帶電升級」：那涉及在流量中把舊版逐步排空、新版逐步接手、出錯即時回退，是另一個量級的工程，見 [Infra 環境與系統升級](/infra/upgrade/)。判準很簡單：自用能接受「切換時停一下」就用這篇的做法；線上不能停就走 infra 的 zero-downtime 遷移。

## 整合與下一步

- image 為什麼改不了、tag vs digest 的差別，見 [不可變 Image](/backend/knowledge-cards/immutable-image/)。
- tag 精確度與可重現性，見 [Image Tag Pinning](/linux/dotfile/knowledge-cards/image-tag-pinning/)。
- 這個升級的實際 artifact（`runtimes/php72-mysql57/` 與 `runtimes/php82-mysql8/` 兩版並存）是 [Dotfile 模組十 Prod Parity](/linux/dotfile/10-prod-parity/) 的延伸——凍結版跟升級版是同一套版本管理紀律的兩個方向。
- 線上不中斷的帶電升級，見 [Infra 環境與系統升級](/infra/upgrade/)。
