---
title: "7.1 資料庫 transaction 與 schema migration"
date: 2026-04-22
description: "把 repository 邊界延伸到資料庫交易、migration 與一致性語意"
weight: 1
---

資料庫整合的核心責任是讓持久化行為符合 application 的狀態規則。Repository port 決定 usecase 需要哪些資料能力；transaction、schema migration 與 isolation level 則決定這些能力在資料庫中如何保持一致。

## 前置章節

- [Go 入門：如何新增 repository port](../../go/06-practical/repository-port/)
- [Go 入門：狀態管理的安全邊界](../../go/07-refactoring/state-boundary/)
- [Go 進階：Source of Truth：狀態邊界](../04-architecture-boundaries/source-of-truth/)

## 後續撰寫方向

1. Repository method 如何表達交易語意，而不是暴露 SQL 細節。
2. 一個 usecase 需要多筆寫入同時成功或失敗時，transaction boundary 應放在哪裡。
3. Migration 如何維持向前相容，避免新舊程式版本互相破壞資料。
4. Isolation level、unique constraint 與 application-level validation 如何分工。
5. Contract test 如何保護 memory repository 與 database repository 的一致行為。

## 本章不處理

本章不會選定特定資料庫或 ORM。真正的重點是 Go application 如何定義資料一致性責任，讓 SQLite、PostgreSQL 或其他儲存技術都能成為可替換 adapter。
