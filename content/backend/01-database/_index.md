---
title: "模組一：資料庫與持久化"
date: 2026-04-22
description: "整理 SQL、transaction、migration 與 repository adapter 的後端實務"
weight: 1
---

資料庫模組的核心目標是說明 application 狀態進入持久化層後，如何維持一致性、可演進性與可測性。語言教材會先定義 repository port、protocol 或 interface；本模組負責說明具體資料庫 adapter 如何實作這些邊界。

## 暫定分類

| 分類               | 內容方向                                                            |
| ------------------ | ------------------------------------------------------------------- |
| SQLite             | embedded database、單機服務、migration、測試資料庫                  |
| PostgreSQL         | schema design、index、transaction、isolation level、connection pool |
| Migration          | versioned schema、rollback、expand/contract migration               |
| Transaction        | unit of work、transaction boundary、deadlock、retry                 |
| Repository adapter | SQL row mapping、contract test、錯誤轉換                            |

## 與語言教材的分工

語言教材處理 repository interface / protocol、取消與逾時、error wrapping、memory fake 與 contract test。Backend database 模組處理 SQL schema、migration tool、transaction isolation、connection pool 與資料庫錯誤語意。

## 相關語言章節

- [Go：如何新增 repository port](../../go/06-practical/repository-port/)
- [Go：狀態管理的安全邊界](../../go/07-refactoring/state-boundary/)
- [Go 進階：Source of Truth](../../go-advanced/04-architecture-boundaries/source-of-truth/)
