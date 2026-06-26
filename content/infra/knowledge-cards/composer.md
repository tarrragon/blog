---
title: "Composer"
date: 2026-06-26
description: "PHP 的套件管理工具，管理專案的第三方依賴、版本鎖定與安全掃描"
weight: 42
tags: ["infra", "knowledge-cards", "php", "package-manager"]
---

Composer 是 PHP 的套件管理工具，角色等同於 Node.js 的 npm、Python 的 pip、Go 的 go mod。它負責宣告專案需要哪些第三方套件、鎖定每個套件的確切版本、以及把套件安裝到專案目錄裡。

## 概念位置

接手 PHP 專案時，Composer 是判斷「專案依賴了什麼、版本有沒有已知漏洞」的入口。專案根目錄通常有三個 Composer 相關的檔案：

| 檔案            | 角色                                   | 進 Git？                                          |
| --------------- | -------------------------------------- | ------------------------------------------------- |
| `composer.json` | 宣告依賴（套件名稱 + 版本範圍）        | 是                                                |
| `composer.lock` | 鎖定確切版本（含所有 transitive 依賴） | 是                                                |
| `vendor/`       | 安裝的套件目錄                         | 否（.gitignore 排除、由 `composer install` 重建） |

## 可觀察訊號

接手專案時如果根目錄有 `composer.json` 但沒有 `vendor/`，代表需要先跑 `composer install` 才能讓專案運作。如果連 `composer.lock` 都沒有，代表套件版本沒有鎖定——每次安裝可能拿到不同版本。

## 設計責任

兩個常用指令的差別：

- `composer install`：按 `composer.lock` 安裝確切版本。用於部署和接手——確保每台機器安裝的版本一致。
- `composer update`：重新解析 `composer.json` 的版本範圍、更新到最新的符合版本、改寫 `composer.lock`。用於主動升級依賴。

接手時的關鍵操作：

- `composer audit`：掃描已安裝套件的已知安全漏洞
- `composer outdated`：列出可更新的套件及其最新版本

## 鄰卡

- [.env](/infra/knowledge-cards/dotenv/)：Composer 管套件、.env 管設定值，兩者都是 PHP 專案的基礎設施
- [php.ini / .user.ini](/infra/knowledge-cards/php-ini/)：Composer 需要 PHP CLI 執行，php.ini 的 memory_limit 和 max_execution_time 會影響 Composer 能不能跑完
