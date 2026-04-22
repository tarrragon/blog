---
title: "3.9 flag、os/env 與設定邊界"
date: 2026-04-22
description: "用標準庫讀取設定，並把外部輸入轉成 config struct"
weight: 9
---

設定讀取的核心責任是把外部字串轉成程式內部的 typed config。環境變數、命令列 flag、設定檔與預設值都只是輸入來源；application 應依賴已驗證的 config struct。

## 預計補充內容

1. `flag` package 的基本用法。
2. `os.Getenv`、`os.LookupEnv` 與預設值處理。
3. 把字串設定轉成 int、duration、bool 與 enum。
4. 在 `main` 或 composition root 完成設定驗證。
5. 測試時用明確 config struct 取代全域環境讀取。

## 與 Backend 教材的分工

本章只處理 Go 程式內的設定邊界。secret manager、Kubernetes ConfigMap、container environment、遠端動態設定與部署平台 rollout 會放在 [Backend：部署平台與網路入口](../../backend/05-deployment-platform/)。
