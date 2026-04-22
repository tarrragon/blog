---
title: "7.7 composition root 與依賴組裝"
date: 2026-04-22
description: "把具體 adapter、config 與 usecase wiring 留在應用入口層"
weight: 7
---

# 7.7 composition root 與依賴組裝

composition root 的核心責任是集中建立具體依賴。domain 與 application 應依賴 port；`main` 或啟動層負責讀取 config、建立 adapter、組裝 usecase、註冊 handler 與啟動 server。

## 預計補充內容

1. 抽出 interface 後，具體實作應在哪裡建立。
2. `main`、`server.New`、`app.New` 的責任分工。
3. config struct 如何進入 adapter，而不是散落在 usecase。
4. 測試如何用 fake composition 取代 production composition。
5. 小型專案保持簡單，大型專案再拆 wiring package。

## 與 Backend 教材的分工

本章處理 Go 程式如何組裝依賴。資料庫連線池、Redis client、broker connection、container secret 與平台設定會放在 Backend 對應模組；Go 章節只保留「誰依賴誰」與「在哪裡組裝」的設計。
