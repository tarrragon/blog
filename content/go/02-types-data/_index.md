---
title: "模組二：型別、資料與介面"
date: 2026-04-22
description: "用 struct、interface、slice、map、常數、embedding、generics 與 JSON tag 表達 Go 資料"
weight: 2
---

Go 的型別系統不追求複雜，而是讓資料形狀、行為需求與程式邊界能被清楚看見。本模組用一般資料處理、設定檔、API message 與狀態資料說明資料如何被定義、序列化、傳遞、組合、泛型化與保護。

## 章節列表

| 章節                          | 主題                          | 關鍵收穫                               |
| ----------------------------- | ----------------------------- | -------------------------------------- |
| [2.1](/go/02-types-data/struct-json/)           | struct 與 JSON tag            | 用 struct 定義 API schema              |
| [2.2](/go/02-types-data/slices-maps/)           | slice 與 map                  | 掌握 Go 最常用的集合型別               |
| [2.3](/go/02-types-data/interfaces/)            | interface：用行為定義依賴     | 用小介面降低耦合                       |
| [2.4](/go/02-types-data/constants/)             | 常數與 typed string           | 管理狀態值與訊息類型                   |
| [2.5](/go/02-types-data/pointers-copy/)         | 指標與資料複製邊界            | 避免外部修改共享狀態                   |
| [2.6](/go/02-types-data/embedding-composition/) | struct embedding 與組合式設計 | 分辨欄位提升、方法提升與依賴組合       |
| [2.7](/go/02-types-data/generics-basics/)       | generics 入門：型別參數與約束 | 在重複資料結構與 helper 中使用最小泛型 |

## 本模組使用的範例主題

- 設定檔與資料列 model
- API request/response model
- 狀態資料 model
- 查詢與寫入介面
- embedding 與小型泛型 helper

## 學習時間

預計 130-170 分鐘
