---
title: "PHP 伺服器執行模型"
date: 2026-10-05
description: "PHP 在伺服器上怎麼被執行：從 CGI、mod_php、FastCGI 與 PHP-FPM 到常駐 worker，每一種執行模型的程序與狀態壽命、成本與部署陷阱"
weight: 33
tags: ["php"]
---

這個分類整理 PHP 在伺服器上的執行方式：一個 HTTP 請求怎麼變成一次 PHP 執行，以及從 CGI 到常駐 worker，各種執行模型在程序壽命、狀態壽命、成本與部署上的差異。

讀者定位：寫過 PHP、部署經驗停在 Apache 加 mod_php 或共享主機（FTP 上傳、`.htaccess`、`php.ini`）的工程師，懂 HTTP、程序與 Linux 基本操作，沒用過 PHP-FPM，多半在容器或 Nginx 環境第一次碰到它。PHP 語法與框架用法不在範圍內。

## 模組

| 模組                                               | 內容                                                                                  |
| -------------------------------------------------- | ------------------------------------------------------------------------------------- |
| [伺服器上的 PHP 執行模型](/php/01-server-runtime/) | SAPI、CGI、mod_php、FastCGI、PHP-FPM、OPcache、容器裡的 Nginx 與 PHP-FPM、常駐 worker |
| [PHP 知識卡](/php/knowledge-cards/)                | SAPI、shared-nothing、mod_php、ZTS、PHP-FPM、OPcache 的術語定義                       |

## 跨分類的相關內容

- [Infra 知識卡](/infra/knowledge-cards/)：[CGI](/infra/knowledge-cards/cgi/)、[Apache MPM](/infra/knowledge-cards/apache-mpm/)、[nginx](/infra/knowledge-cards/nginx/)、[.htaccess](/infra/knowledge-cards/htaccess/)、[php.ini / .user.ini](/infra/knowledge-cards/php-ini/)
- [接手舊系統](/infra/takeover/)：共享主機與舊 PHP 站台的接手、遷移與安全稽核
- [Container per Service](/backend/knowledge-cards/container-per-service/)：一個容器一個職責的慣例，對應 Nginx 與 PHP-FPM 要不要拆成兩個容器

## Backlog

| 項目                                                                                             | 類型   | 前置條件               | 規模 |
| ------------------------------------------------------------------------------------------------ | ------ | ---------------------- | ---- |
| Apache 搭配 PHP-FPM（`mod_proxy_fcgi` 與 event MPM）的設定與遷移                                 | 主章   | 無                     | 中   |
| FastCGI 知識卡                                                                                   | 知識卡 | 無                     | 小   |
| PHP-FPM 與 Octane 在同一負載下的壓測比較（含 `max_children` 調校）                               | 案例   | 需要固定規格的壓測機器 | 中   |
| Swoole 與 RoadRunner 各自的執行模型（協程、goridge）                                             | 主章   | 無                     | 中   |
| serverless PHP（Bref on AWS Lambda）在執行模型上的位置：執行環境跨呼叫重用、每個環境一次一個請求 | 主章   | 無                     | 中   |
| suEXEC 知識卡                                                                                    | 知識卡 | 無                     | 小   |
| PHP-FPM 其餘旋鈕：`emergency_restart_*`、`rlimit_files`、`listen.backlog` 與負載下的 502         | 主章   | 無                     | 小   |
