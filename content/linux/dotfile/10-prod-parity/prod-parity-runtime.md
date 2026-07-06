---
title: "對齊 prod 的 runtime container"
date: 2026-07-06
description: "要開發一個線上跑 PHP 7.2 / MySQL 5.7 舊環境的專案、或要在本機重現線上事故時回來讀 — 對齊哪些維度、怎麼從線上抄設定、什麼時候值得"
weight: 2
tags: ["dotfile", "prod-parity", "docker", "php", "mysql"]
---

這篇的目的是建一個跟 client 線上逐項對齊的 runtime，讓「本機能跑」直接等於「線上能跑」。做法的核心是刻意把環境退回線上那個凍結的舊形狀，而非維持最新最乾淨——為什麼方向跟直覺相反、要對齊哪些維度，見 [Prod Parity 原則](/linux/dotfile/knowledge-cards/prod-parity-principle/)。Dockerfile 與 compose 本身怎麼運作（指令、layer、多 service 編排），見 Docker vendor 的 [Dockerfile 設計](/backend/05-deployment-platform/vendors/docker/dockerfile-design/) 與 [Docker Compose](/backend/05-deployment-platform/vendors/docker/docker-compose/)。這裡只講怎麼判讀跟一個實測過的基線。

## 對齊的載體是 image tag 跟 config，不是主機

Parity 不靠「把主機裝成跟 prod 一樣」達成——你的主機是 Arch 或 macOS 都無所謂。對齊的載體是 container 的 image tag 跟掛進去的 config：

- **image tag 釘到 OS 世代**：用 `php:7.2-fpm-buster` 而不是 `php:7.2-fpm`，把 PHP 版本連同底層 Debian 世代一起凍結（見 [Image Tag Pinning](/linux/dotfile/knowledge-cards/image-tag-pinning/)）。
- **別為了省體積換 libc**：prod 是 Debian（glibc）就別用 `php:7.2-alpine`（musl），DNS 與原生擴充行為會分岔（見 [glibc 與 musl](/linux/dotfile/knowledge-cards/glibc-vs-musl/)）。
- **服務設定抄 prod**：MySQL 的 `sql_mode`、時區，PHP 的擴充清單與 `php.ini`，都從線上的權威來源抄、不憑印象填。SSH 進 prod 後用 `mysql -N -e "SELECT @@sql_mode"` 抓 sql_mode、`php -m` 列擴充、`php -i`（或 web 端存一支 `<?php phpinfo();`）看 `php.ini` 值；抄回來分別填進 db 的 `my.cnf`（`sql_mode` / 時區）、Dockerfile 的 `docker-php-ext-install` 清單（對照 `php -m`）、掛進去的 `php.ini`。

主機不變、只有這幾樣對齊——這是 parity 能在任何工作站上重現的原因。

## 要逐項比對的維度

跑起來後，用一個 probe 印出 runtime 的每個 parity 維度，跟 prod 逐行比對。每一行對應一個會影響行為的維度：

- PHP 主版 + patch 版
- 時區（PHP 與 MySQL 各一份，跨時區的 `NOW()` 是常見隱形 bug）
- 擴充清單（要相等、不是涵蓋；多裝的擴充讓本機能跑、prod 掛掉）
- MySQL 版本與 `sql_mode`（5.7 預設開 `ONLY_FULL_GROUP_BY`，舊 app 的 `SELECT ... GROUP BY` 未列全欄位會回 error 1055）

## 實測基線

dotfiles repo 的 `runtimes/php72-mysql57/` 是一個跑得起來的 variant（PHP-FPM + MySQL 5.7 + nginx，docker-compose 組合）。`docker compose up -d --build` 起來後 `curl http://localhost:8080/`——probe 是一支 `src/index.php`、由 nginx 服務，逐行印出每個 parity 維度。arm64 macOS 實測（2026-07）輸出：

```text
PHP version : 7.2.34
timezone    : Asia/Taipei
MySQL ver   : 5.7.44
sql_mode    : ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,...
db timezone : +08:00
```

版本、時區、`sql_mode` 都跟 config 逐項對齊——這就是 parity 達成的樣子。

## 凍結舊環境的兩個稅

實跑會撞到兩個「照官方 docs 寫會 build 不起來、只有實機才知道」的問題，兩個都是凍結舊環境特有的：

- **Debian buster 已 EOL**：套件庫從主 mirror 移到 `archive.debian.org`，Dockerfile 裡不改 apt source 直接 `apt-get update` 就 404（exit 100）。要改指 archive 並關掉過期檢查。
- **mysql:5.7 無 arm64 原生 image**：在 Apple Silicon 主機上要 `platform: linux/amd64` 走模擬（機制見 [QEMU binfmt 跨架構模擬](/backend/knowledge-cards/qemu-binfmt-emulation/)）。這本身也是一種 parity——dev 是模擬 amd64、prod 是原生 amd64，架構對齊。

這兩個稅是 [Prod Parity 原則](/linux/dotfile/knowledge-cards/prod-parity-principle/) 講的「對齊凍結環境要付的代價」的具體形態：凍結舊版意味著也繼承了它 EOL 與架構支援退場的後果。

## 什麼時候值得做到逐項

Parity 是有成本的紀律，不是每個專案都要做到逐項——值得與可放寬的完整判準見 [Prod Parity 原則](/linux/dotfile/knowledge-cards/prod-parity-principle/) 的判讀訊號段。這篇的 PHP 7.2 場景屬「值得」那一類：有原生擴充、MySQL 嚴格模式、時區邏輯都在，本機不對齊就會在線上才發現行為不同。

## 下一步

runtime 對齊好之後，你會想在 container 裡用順手的 shell 跟 editor——但那不能直接塞進這個 image，否則 image 就不再等於 prod。怎麼把 ergonomics 帶進來又不污染 parity，見 [dotfile 跨進 runtime container](/linux/dotfile/10-prod-parity/container-ergonomics/)。
