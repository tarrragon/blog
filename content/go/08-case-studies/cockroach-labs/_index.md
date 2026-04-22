---
title: "8.7 Cockroach Labs：分散式 SQL 資料庫"
date: 2026-04-23
description: "看 Go 如何支撐分散式資料庫與高一致性系統"
weight: 7
---

Cockroach Labs 的案例適合放在 Go 教材裡，因為它把 Go 的工程價值推到很高的門檻：分散式 SQL、交易一致性、可水平擴展、容錯與長期可維護。官方案例直接提到，Go 的 performance、garbage collection 與低入門門檻，是 CockroachDB 的重要選擇原因。

## 你應該看什麼

- [Why Go was the right choice for CockroachDB](https://www.cockroachlabs.com/blog/why-go-was-the-right-choice-for-cockroachdb/)
- [Why CockroachDB?](https://www.cockroachlabs.com/docs/stable/why-cockroachdb)

## 這個案例告訴我們什麼

1. Go 不只適合 API，也適合超大型資料系統。
2. 大型系統裡，語言的可讀性與團隊進入門檻很重要。
3. Go 在複雜系統中的優勢，常常是讓工程複雜度可控。

## 可對照的公開原始碼

- [cockroachdb/cockroach](https://github.com/cockroachdb/cockroach)
- [cockroachdb/cockroach-go](https://github.com/cockroachdb/cockroach-go)

這是本模組最值得讀的 repo 之一。你可以對照第七模組的 package 邊界、接口設計與 composition root，理解大型 Go 系統如何組織。

