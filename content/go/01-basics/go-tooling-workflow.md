---
title: "1.8 Go tooling 與日常開發流程"
date: 2026-04-22
description: "用 go run、go test、go fmt、go mod tidy 建立 Go 專案的基本工作節奏"
weight: 8
---

Go tooling 的核心價值是讓日常開發流程標準化。`go run`、`go test`、`go fmt`、`go mod tidy`、`go build` 是 Go 專案最基本的協作語言。

## 預計補充內容

這些工具使用邊界會在下列章節展開：

- [Go 入門：從入口程式看應用啟動流程](main-flow/)：先看 `go run` 與 `go build` 如何對應入口 package，才能理解 Go 專案真正的執行起點。
- [Go 入門：testing 基礎](../../go/05-error-testing/testing-basics/)：先建立最小回歸檢查的習慣，再談 `go test ./...` 在流程中的角色。
- [Backend：可靠性驗證流程](../../backend/06-reliability/)：CI 與自動化驗證的責任在這裡展開，不應塞進語言章節。
- [Backend：部署平台與網路入口](../../backend/05-deployment-platform/)：容器建置、發布門檻與平台合約屬於部署層，不是 toolchain 本身。

## 與 Backend 教材的分工

本章只處理 Go toolchain。CI pipeline、container build、部署前 gate 與 release artifact 會放在 [Backend：可靠性驗證流程](../../backend/06-reliability/) 與 [Backend：部署平台與網路入口](../../backend/05-deployment-platform/)。

## 和 Go 教材的關係

這一章承接的是入口流程、測試與設定讀取；如果你要先回看語言教材，可以讀：

- [Go：從入口程式看應用啟動流程](main-flow/)
- [Go：testing 基礎](../../go/05-error-testing/testing-basics/)
- [Go：flag、os/env 與設定邊界](../../go/03-stdlib/config-flags-env/)
- [Go：composition root 與依賴組裝](../../go/07-refactoring/composition-root/)
