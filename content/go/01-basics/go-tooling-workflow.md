---
title: "1.8 Go tooling 與日常開發流程"
date: 2026-04-22
description: "用 go run、go test、go fmt、go mod tidy 建立 Go 專案的基本工作節奏"
weight: 8
---

Go tooling 的核心價值是讓日常開發流程標準化。`go run`、`go test`、`go fmt`、`go mod tidy`、`go build` 是 Go 專案最基本的協作語言。

## 預計補充內容

1. `go run`、`go build` 與入口 package 的關係。
2. `go test ./...` 如何成為最小回歸檢查。
3. `go fmt` 與 `go vet` 在團隊協作中的角色。
4. `go mod tidy` 如何維持依賴描述乾淨。
5. 本機開發、CI 與教學範例使用同一組命令。

## 與 Backend 教材的分工

本章只處理 Go toolchain。CI pipeline、container build、部署前 gate 與 release artifact 會放在 [Backend：可靠性驗證流程](../../backend/06-reliability/) 與 [Backend：部署平台與網路入口](../../backend/05-deployment-platform/)。
