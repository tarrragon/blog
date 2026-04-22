---
title: "模組三：標準庫實戰"
date: 2026-04-22
description: "使用 fmt、time、encoding/json、net/http、log/slog、context、defer、flag 與 os/env 解決實務問題"
weight: 3
---

Go 的標準庫是理解 Go 精神的重要入口。它偏好清楚的小 API、明確錯誤處理與組合式設計。本模組從常見任務出發：格式化輸出、時間處理、JSON 編解碼、HTTP handler、結構化日誌、生命週期控制、資源清理與設定讀取。

## 章節列表

| 章節                     | 主題                          | 關鍵收穫                                     |
| ------------------------ | ----------------------------- | -------------------------------------------- |
| [3.1](fmt-strings/)      | fmt、strings 與基本文字處理   | 處理輸出、格式化與字串轉換                   |
| [3.2](time/)             | time：時間與 duration         | 表達時間點、時間差與 timeout                 |
| [3.3](files-io/)         | os/io：檔案與輸入輸出         | 讀寫檔案與理解 `io.Reader`                   |
| [3.4](json/)             | encoding/json：資料交換       | 在檔案、API 與訊息中使用 JSON                |
| [3.5](http-handler/)     | net/http 與 handler 設計      | 用 `http.HandlerFunc` 理解 Go 的組合風格     |
| [3.6](slog/)             | log/slog：結構化日誌          | 用欄位支援除錯與 grep                        |
| [3.7](context/)          | context：取消、逾時與生命週期 | 讓長時間工作可以停止                         |
| [3.8](defer-cleanup/)    | defer 與資源清理              | 用 `defer` 管理 close、unlock、recover 邊界  |
| [3.9](config-flags-env/) | flag、os/env 與設定邊界       | 用標準庫讀取設定，並把設定轉成 config struct |

## 本模組使用的範例主題

- 格式化輸出與錯誤訊息
- 字串處理與時間處理
- 檔案讀寫與 I/O 介面
- JSON 檔案與 API 資料
- HTTP handler
- 結構化日誌欄位
- 資源清理與基本設定讀取

## 學習時間

預計 3-4 小時
