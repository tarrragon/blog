---
title: "3.9 flag、os/env 與設定邊界"
date: 2026-04-22
description: "用標準庫讀取設定，並把外部輸入轉成 config struct"
weight: 9
---

設定讀取的核心責任是把外部字串轉成程式內部的 typed config。環境變數、命令列 flag、設定檔與預設值都只是輸入來源；application 應依賴已驗證的 config struct。

## 預計補充內容

這些設定邊界會在下列章節展開：

- [Go 進階：composition root 與依賴組裝](../../07-refactoring/composition-root/)：設定讀取的真正用途，是在啟動層把外部輸入轉成可驗證的依賴。
- [Go 入門：從入口程式看應用啟動流程](../../01-basics/main-flow/)：先看主程式怎麼啟動，才知道設定應該在哪裡完成驗證。
- [Backend：部署平台與網路入口](../../../backend/05-deployment-platform/)：像 secret manager、ConfigMap 與 rollout 這類平台責任應該留給 Backend。

## 與 Backend 教材的分工

本章只處理 Go 程式內的設定邊界。secret manager、Kubernetes ConfigMap、container environment、遠端動態設定與部署平台 rollout 會放在 [Backend：部署平台與網路入口](../../../backend/05-deployment-platform/)。

## 和 Go 教材的關係

這一章承接的是入口流程與 composition root；如果你要先回看語言教材，可以讀：

- [Go：從入口程式看應用啟動流程](../../01-basics/main-flow/)
- [Go：composition root 與依賴組裝](../../07-refactoring/composition-root/)
- [Go：testing 基礎](../../05-error-testing/testing-basics/)
- [Go：flag、os/env 與設定邊界](./)
