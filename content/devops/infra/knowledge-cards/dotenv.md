---
title: ".env"
date: 2026-06-26
description: "存放環境變數的純文字檔案，把機密值從程式碼分離出來"
weight: 26
tags: ["infra", "knowledge-cards"]
aliases: ["/infra/knowledge-cards/dotenv/"]
---

`.env` 是一個純文字檔案，每行一組 `KEY=VALUE` 的環境變數定義。它的用途是把機密值（資料庫密碼、API key、SMTP 存取憑證）和環境專屬設定（資料庫 host、debug 模式開關）從程式碼分離出來，讓同一份程式碼在不同環境（開發、staging、production）用不同的設定值，而且機密值不進版本控制。PHP 專案裡執行期設定的另一層在 [php.ini / .user.ini](/devops/infra/knowledge-cards/php-ini/)。

## 跟其他概念的關係

`.env` 是跨語言的設定分離慣例。PHP 用 [Composer](/devops/infra/knowledge-cards/composer/) 安裝的 `vlucas/phpdotenv` 套件讀取、Node.js 用 `dotenv` 套件、Python 用 `python-dotenv`、Go 用 `godotenv`。這些套件的行為相同：程式啟動時讀 `.env` 檔案，把裡面的變數載入到執行環境的環境變數裡，讓程式碼用 `$_ENV['KEY']`（PHP）或 `process.env.KEY`（Node）存取。

## 可觀察訊號

站台根目錄有 `.env` 或 `.env.production` 檔案；`.gitignore` 裡有 `.env` 這一行；repo 裡有 `.env.example` 或 `.env.sample` 列出所有需要的變數但不填實際值。如果接手的專案沒有 `.env` 但 `config.php` 裡直接寫了資料庫密碼，代表設定分離還沒做——這是接手後應該處理的事。

## 判斷條件與後果

`.env` 是否進版本控制、該放哪些值，取決於裡面的值屬於哪一類：不能被看到的值、換一個環境就要改的值，或兩者都不是的設定。

**`.env` 進了 Git**：裡面的明文密碼跟著每一次 clone、fork、CI 快取擴散。之後刪掉那一行，密碼仍然留在 history 的舊版裡，所以已經進過 Git 的密碼全部要輪替；`.gitignore` 從一開始就排除 `.env`，這件事才不會發生。

**repo 裡沒有範本檔**：`.env` 不進 Git，新接手的人看不到程式需要哪些變數，只能等程式讀不到值時才發現缺了哪一個。repo 裡放一份 `.env.example`，列出全部必要的變數名、不填實際值，接手的人複製成 `.env` 再填自己環境的值。

**功能開關、UI 設定、feature flag 放進 `.env`**：這些值沒有機密性，而 `.env` 不進版本控制，放進去之後改動沒有紀錄，各環境的值也無從比對。`.env` 只放換環境要改的值與不能被看到的值，其餘設定進版本控制。

## 鄰卡

- [php.ini / .user.ini](/devops/infra/knowledge-cards/php-ini/)：`.env` 管應用程式設定、php.ini 管 PHP runtime 設定
