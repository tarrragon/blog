---
title: "環境與系統升級：帶電施工的遷移操作"
date: 2026-06-26
description: "系統在升級過程中要持續服務 — runtime 版本升級、平台遷移、資料庫大版本升級、OS 更換、架構轉型的共通操作框架與各類型的專屬風險"
weight: -3
tags: ["infra", "upgrade", "migration", "platform"]
---

環境與系統升級跟從零建置的差別在於：從零建置時可以先建好再上線，升級時系統已經在服務客戶，每一步操作都要在不中斷（或可控中斷）的前提下完成。這個約束決定了升級的操作模式——不是「拆掉重建」，而是「在旁邊建一個新的、驗證通過後切過去、確認沒問題再拆舊的」。

這個模組處理的是升級的操作框架與各類型的專屬風險，跟[成熟度階梯](/infra/00-infra-mindset/)平行而非串行——升級可能發生在任何成熟度階段。跟[接手維運](/infra/takeover/)的關係是：接手後的下一步常常就是升級（接手一個 PHP 5.6 的站台，穩定維運後第一個任務就是升 PHP 版本）。

## 章節文章

| 文章                                                          | 主題                                                            |
| ------------------------------------------------------------- | --------------------------------------------------------------- |
| [升級的共通操作框架](/infra/upgrade/upgrade-framework/)       | 評估差異、建平行環境、分批切換、退役舊環境的四階段模型          |
| [Runtime 版本升級](/infra/upgrade/runtime-version-upgrade/)   | PHP / Node / Python 大版本升級的相容性評估、測試策略、分批部署  |
| [平台遷移](/infra/upgrade/platform-migration/)                | FTP 面板主機 → VPS → 雲端的遷移路徑、DNS 切換、資料同步         |
| [資料庫大版本升級](/infra/upgrade/database-major-upgrade/)    | MySQL / PostgreSQL 大版本升級的相容性、備份、平行驗證、切換策略 |
| [OS 與基礎軟體更換](/infra/upgrade/os-base-software-upgrade/) | EOL OS 的遷移、套件相容性、服務重新部署                         |

## 跟其他模組的關係

- → [接手維運](/infra/takeover/)：接手後穩定維運的下一步常是升級
- → [模組負一：還沒有 infra 的環境](/infra/before-infra/)：升級過程中建立的操作紀律可以對齊這裡
- → [模組一：最小可行 IaC](/infra/01-minimal-iac/)：升級是導入 IaC 的好時機——新環境用 IaC 建、舊環境手動退役
- → [模組五：核心服務上 IaC](/infra/05-core-services/)：資料庫和運算平台的升級涉及 stateful 資源的特殊處理
