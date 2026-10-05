---
title: "伺服器上的 PHP 執行模型"
date: 2026-10-05
description: "PHP 直譯器與 web 伺服器之間的那一層：SAPI 與請求生命週期、CGI、mod_php、FastCGI、PHP-FPM、OPcache、容器裡的 Nginx 與 PHP-FPM，以及常駐 worker 模型"
weight: 1
tags: ["php", "deployment"]
---

這個模組整理 PHP 直譯器與 web 伺服器之間的那一層：一個請求進來，PHP 在哪個程序裡、什麼時候被啟動，請求結束時哪些狀態被清掉、哪些資源留在程序裡。

## 推導源頭

各篇都用同一組問題比較執行模型，定義在第一篇〈請求生命週期與 SAPI〉：

1. PHP 直譯器住在哪裡（web 伺服器的程序裡 / 另一個程序 / 某個程序的執行緒）
2. 執行它的程序活多久（一個請求 / 很多個請求）
3. 應用程式的狀態活多久（一個請求 / 很多個請求）

每一篇是這組問題的一組答案，或是某一個答案的後果（OPcache 是第二題的後果，容器篇是第一題的部署面）。各篇的判斷標準都能折算回這三題。

## 章節

| 章節                                                                          | 回答                                                                                     |
| ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| [請求生命週期與 SAPI](/php/01-server-runtime/request-lifecycle-and-sapi/)     | 程序層與請求層各做什麼、shared-nothing 的範圍、SAPI 與三個問題                           |
| [CGI](/php/01-server-runtime/cgi/)                                            | 每請求一程序的成本、OPcache 為零命中、suEXEC 的隔離、CVE-2012-1823 的邊界                |
| [mod_php](/php/01-server-runtime/mod-php/)                                    | prefork 與 ZTS、每個子程序都帶著 PHP、共用執行帳號、`.htaccess` 的 `php_value` 遷移      |
| [FastCGI](/php/01-server-runtime/fastcgi/)                                    | 常駐程序的協定、`SCRIPT_FILENAME` 由 web 伺服器決定、`cgi.fix_pathinfo` 的三道防線       |
| [PHP-FPM](/php/01-server-runtime/php-fpm/)                                    | pool、pm、max_children 排隊、max_requests 與 worker 記憶體、逾時與 slowlog、status、訊號 |
| [OPcache](/php/01-server-runtime/opcache/)                                    | 快取與程序壽命、worker 共用、大小估算、部署時的 validate_timestamps                      |
| [容器裡的 Nginx 與 PHP-FPM](/php/01-server-runtime/nginx-php-fpm-containers/) | 官方映像檔的預設值、拆成兩個容器的程式碼位置、同一個容器的程序監看與停機訊號             |
| [常駐 worker 模型](/php/01-server-runtime/long-running-workers/)              | FrankenPHP worker、Octane、跨請求殘留的狀態與記憶體、要避開的寫法                        |

## 各篇的可動項

改寫或新增篇目時對照這張表；可動項是本篇模型裡換掉之後結論會變的那幾項。

| 篇                        | 可動項                                                              |
| ------------------------- | ------------------------------------------------------------------- |
| 請求生命週期與 SAPI       | 直譯器位置、程序壽命、狀態壽命                                      |
| CGI                       | 程序壽命（換成常駐 → FastCGI）、執行身分（換成共用帳號 → mod_php）  |
| mod_php                   | 直譯器位置（移出 web 伺服器 → FastCGI）、MPM（換執行緒 → 需要 ZTS） |
| FastCGI                   | 程序管理者（→ PHP-FPM）、`SCRIPT_FILENAME` 的決定者                 |
| PHP-FPM                   | 並發上限、worker 壽命、單請求逾時、停機等待時間                     |
| OPcache                   | 程序壽命（CGI → 零命中）、檔案變動檢查（validate_timestamps）       |
| 容器裡的 Nginx 與 PHP-FPM | 容器切法（一個 / 兩個）、誰負責程序監看                             |
| 常駐 worker 模型          | 狀態壽命、worker 壽命（max-requests）                               |

## 實測環境

文中的輸出都在 macOS（Apple Silicon）加 OrbStack 上以官方 Docker 映像檔實測：`php:8.5-fpm-alpine`、`php:8.5-apache`、`php:8.5-cli`、`httpd:2.4`、`nginx:1.30-alpine`、`dunglas/frankenphp`（FrankenPHP 1.13）、Laravel 13 與 Octane 2.20。
