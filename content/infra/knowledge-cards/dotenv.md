---
title: ".env"
date: 2026-06-26
description: "存放環境變數的純文字檔案，把機密值從程式碼分離出來"
weight: 26
tags: ["infra", "knowledge-cards"]
---

`.env` 是一個純文字檔案，每行一組 `KEY=VALUE` 的環境變數定義。它的用途是把機密值（資料庫密碼、API key、SMTP 憑證）和環境專屬設定（資料庫 host、debug 模式開關）從程式碼分離出來，讓同一份程式碼在不同環境（開發、staging、production）用不同的設定值，而且機密值不進版本控制。

## 概念位置

`.env` 是跨語言的設定分離慣例。PHP 用 `vlucas/phpdotenv` 套件讀取、Node.js 用 `dotenv` 套件、Python 用 `python-dotenv`、Go 用 `godotenv`。這些套件的行為相同：程式啟動時讀 `.env` 檔案，把裡面的變數載入到執行環境的環境變數裡，讓程式碼用 `$_ENV['KEY']`（PHP）或 `process.env.KEY`（Node）存取。

## 可觀察訊號

站台根目錄有 `.env` 或 `.env.production` 檔案；`.gitignore` 裡有 `.env` 這一行；repo 裡有 `.env.example` 或 `.env.sample` 列出所有需要的變數但不填實際值。如果接手的專案沒有 `.env` 但 `config.php` 裡直接寫了資料庫密碼，代表設定分離還沒做——這是接手後應該處理的事。

## 設計責任

使用 `.env` 時有三個紀律：

**不進 Git**：`.env` 包含明文密碼，進了 Git 就跟著每一次 clone、fork、CI 快取擴散。`.gitignore` 必須排除 `.env`。如果 `.env` 已經在 Git 歷史裡，刪掉那一行不夠——密碼留在 history 裡，要輪替所有外洩的密碼。

**範本檔進 Git**：repo 裡放一份 `.env.example`，列出所有必要的環境變數但不填實際值。新接手的人複製 `.env.example` 成 `.env`，再填入自己環境的值。

**不用 `.env` 管非機密設定**：應用程式的功能開關、UI 設定、feature flag 不屬於 `.env`——這些設定沒有機密性、應該進版本控制。`.env` 只放「換一個環境就要改的值」和「不能被看到的值」。

## 鄰卡

- [php.ini / .user.ini](/infra/knowledge-cards/php-ini/)：`.env` 管應用程式設定、php.ini 管 PHP runtime 設定
