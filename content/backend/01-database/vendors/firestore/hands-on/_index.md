---
title: "Firestore Hands-on 操作路線"
date: 2026-06-16
description: "用 Firebase Emulator Suite 在本地演練 Firestore：emulator quickstart、Security Rules 單元測試、distributed counter 分片計數，全程零雲端成本、可重跑、產出可驗證 artifact"
tags: ["backend", "database", "firestore", "hands-on", "emulator"]
---

Firestore hands-on 操作路線的核心責任是把 deep article 的機制判讀轉成可在本地演練的操作。這一層全程跑在 [Firebase Emulator Suite](https://firebase.google.com/docs/emulator-suite) 上——本地、免費、不碰雲端專案、不產生計費，讓讀者能建立資料、寫規則測試、跑分片計數，並取得 query output、測試結果與 artifact，而不只停在概念。

## 為什麼用 emulator

Firestore 的 client 直連模型讓「在本地驗證」變得重要：規則寫錯是資安漏洞、查詢設計錯是成本事故，這些都該在進雲端前用真實求值引擎驗過。Emulator Suite 提供與雲端一致的 Firestore 行為與 Security Rules 求值引擎，是規則測試的官方推薦環境。要留意的邊界是——emulator 模擬功能行為，但不模擬計費與部分 production 規模限制（單 document 寫入軟上限、連線天花板）。涉及成本與規模的判讀仍以雲端為準，emulator lab 會在對應處標明。

## 章節列表

| 章節                                                    | 主題                                                              | 產出 artifact                                      |
| ------------------------------------------------------- | ----------------------------------------------------------------- | -------------------------------------------------- |
| [Local emulator quickstart](local-emulator-quickstart/) | emulator 啟動、`firestore.rules`、admin seed、query baseline      | emulator config、seed script、query output         |
| [Security Rules test lab](security-rules-test-lab/)     | `@firebase/rules-unit-testing`、放行 / 拒絕斷言、CI 整合          | rules 測試檔、pass / fail 結果、emulators:exec log |
| [Distributed counter lab](distributed-counter-lab/)     | 分片計數寫入、shard 分佈、讀取彙總、contention 的 production 邊界 | counter script、shard 分佈 output、彙總驗證        |

## 設計原則

Firestore hands-on 章節以「進雲端前先驗」為中心。操作指令只在能產出 artifact 時出現；每篇都要回答 emulator 在哪裡跑、需要哪些 input、怎麼知道操作成功（query output / 測試斷言 / shard 分佈），以及哪些 production 特性（計費、寫入上限）emulator 不負責、要回雲端確認。

## 引用路徑

- 上游：[Firestore overview](/backend/01-database/vendors/firestore/)
- Deep article：[Security Rules 授權建模](/backend/01-database/vendors/firestore/security-rules-authz-modeling/) / [distributed counter 高頻寫入](/backend/01-database/vendors/firestore/distributed-counter-high-frequency-write/)
- 發布證據：[6.8 release gate](/backend/06-reliability/release-gate/)（規則測試接進 gate）
- 官方：[Emulator Suite](https://firebase.google.com/docs/emulator-suite)、[Connect to Firestore emulator](https://firebase.google.com/docs/emulator-suite/connect_firestore)
