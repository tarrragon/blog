---
title: "模組一：Go 基礎概念"
date: 2026-04-22
description: "Go 專案結構、變數、控制流程、package、檔案拆分、函式、應用啟動與日常 tooling"
weight: 1
---

本模組帶你建立閱讀 Go 程式需要的基本模型。重點不是背語法，而是理解 module、變數、控制流程、package、檔案拆分、函式、入口程式與 Go tooling 如何組成日常開發流程。

## 章節列表

| 章節                           | 主題                      | 關鍵收穫                                                         |
| ------------------------------ | ------------------------- | ---------------------------------------------------------------- |
| [1.1](modules/)                | Go 專案結構與 module      | 理解 module 與 import path                                       |
| [1.2](variables-zero-values/)  | 變數、零值與短變數宣告    | 理解 Go 如何宣告與初始化資料                                     |
| [1.3](control-flow/)           | 控制流程：if、for、switch | 掌握 Go 的基本流程控制                                           |
| [1.4](packages/)               | package、檔案與可見性     | 看懂 `package main` 與大小寫可見性                               |
| [1.5](growing-files-packages/) | 從單檔到多檔案            | 理解 Go 程式如何從 `main.go` 長成多檔案與多 package              |
| [1.6](functions-methods/)      | 函式、方法與 receiver     | 區分函式、建構函式與物件方法                                     |
| [1.7](main-flow/)              | 從入口程式看應用啟動流程  | 建立 Go 應用啟動地圖                                             |
| [1.8](go-tooling-workflow/)    | Go tooling 與日常開發流程 | 用 `go run`、`go test`、`go fmt`、`go mod tidy` 建立基本工作節奏 |

## 本模組使用的範例主題

- module 宣告與依賴
- 變數、零值與流程控制
- 單檔、多檔案與跨 package 呼叫
- 入口點與應用啟動
- 建構函式與方法
- receiver 與狀態方法
- Go command、format、test、module tidy

## 預備知識

- 基本變數、函式、條件判斷
- 知道命令列程式或 HTTP server 的基本概念

## 學習時間

預計 140-170 分鐘
