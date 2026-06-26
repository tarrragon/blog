---
title: "php.ini / .user.ini"
date: 2026-06-26
description: "PHP 的執行期設定檔，控制記憶體上限、上傳大小、錯誤報告等 runtime 行為"
weight: 27
tags: ["infra", "knowledge-cards"]
---

`php.ini` 是 PHP 的全域設定檔，控制 PHP 的 runtime 行為——記憶體上限、檔案上傳大小、最大執行時間、錯誤報告層級、時區、session 處理方式。`.user.ini` 是 PHP 5.3 之後支援的目錄層級覆寫機制，放在站台目錄裡可以覆寫部分 `php.ini` 的設定，不需要伺服器管理員權限。

## 概念位置

`php.ini` 由伺服器管理員管理，租用主機的使用者通常不能直接修改。`.user.ini` 是使用者層級的設定覆寫——功能上類似 `.htaccess` 對 Apache 的角色，但只管 PHP 設定。在 cPanel 環境裡，部分設定也可以透過「PHP 選擇器」的圖形介面調整。

## 可觀察訊號

PHP 行為異常時要檢查的第一個地方。常見的情境：上傳檔案失敗（`upload_max_filesize` 太小）、長時間運算被中斷（`max_execution_time` 太短）、記憶體不足錯誤（`memory_limit` 太低）、看不到錯誤訊息（`display_errors` 關閉）。用 `phpinfo()` 可以看到每一項設定的目前值和來源（`php.ini` / `.user.ini` / `.htaccess`）。

## 設計責任

接手維運時要知道的關鍵設定：

| 設定                  | 作用                  | 常見預設值 | 接手時要確認的事                                 |
| --------------------- | --------------------- | ---------- | ------------------------------------------------ |
| `memory_limit`        | PHP 程式的記憶體上限  | 128M       | 大型操作（匯出、圖片處理）是否夠用               |
| `upload_max_filesize` | 單檔上傳大小上限      | 2M         | 是否符合業務需求                                 |
| `post_max_size`       | POST 請求的總大小上限 | 8M         | 要大於 upload_max_filesize                       |
| `max_execution_time`  | PHP 腳本最大執行秒數  | 30         | 長時間操作（備份、匯入）是否需要加長             |
| `error_reporting`     | 顯示哪些層級的錯誤    | E_ALL      | 開發時開到 E_ALL、production 時關 display_errors |
| `display_errors`      | 是否在頁面上顯示錯誤  | Off        | production 應該關閉（錯誤寫 log 不顯示給使用者） |

`.user.ini` 的修改不需要重啟 Apache/nginx，但有快取時間（預設 300 秒）——改完後要等最多 5 分鐘才生效。`php.ini` 的修改在多數環境需要重啟 web server。

## 鄰卡

- [.htaccess](/infra/knowledge-cards/htaccess/)：`.htaccess` 管 Apache 行為（URL rewrite、存取控制），`.user.ini` 管 PHP 行為（記憶體、執行時間），兩者互補
- [.env](/infra/knowledge-cards/dotenv/)：`.env` 管應用程式設定（DB 密碼、API key），`php.ini` 管 PHP runtime 設定（記憶體、上傳大小）
