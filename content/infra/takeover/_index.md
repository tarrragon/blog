---
title: "接手維運：別人建的環境怎麼接管"
date: 2026-06-26
description: "接手前人的專案時，怎麼在不搞壞東西的前提下盤點現況、建立維運能力、逐步正規化 — 從共享主機 PHP 到有半套 IaC 的雲端環境都適用"
weight: -2
tags: ["infra", "takeover", "legacy", "migration"]
---

接手維運跟從零建置的差別在於：從零建置時每一個資源都是自己點的，知道它存在、知道為什麼存在；接手時面對的是一個不確定哪些東西還在用、不知道動什麼會壞的環境。第一個要解的問題不是「怎麼做 infra」，而是「現在到底有什麼、它還能不能跑、改了會怎樣」。

這個模組處理的是接管的操作流程，跟[成熟度階梯](/infra/00-infra-mindset/)平行而非串行 — 接手可能發生在任何成熟度階段：接手一個全手動的共享主機 PHP 站、接手一個有 SSH 但沒有 IaC 的雲端環境、接手一個有半套 IaC 但文件缺失的專案。每種情境的約束不同，但操作原則相通：先拍現況、再建維運能力、最後逐步正規化。

## 章節文章

| 文章                                                                                | 主題                                                                      |
| ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| [共享主機與 FTP 環境的接管](/infra/takeover/legacy-ftp-shared-hosting/)             | 沒有 SSH、沒有 CLI、只有 FTP 和 phpMyAdmin 的 legacy 環境怎麼接管（總覽） |
| [共享主機的資料庫備份與變更管理](/infra/takeover/legacy-database-backup-migration/) | phpMyAdmin 的限制與對策、備份策略、migration 紀律、還原演練               |
| [程式碼版控與 FTP 部署紀律](/infra/takeover/legacy-code-versioning-deployment/)     | 本地 Git 工作流、config 分離、FTP 部署風險控制、CI 化 FTP                 |
| [Legacy PHP 的安全盤點](/infra/takeover/legacy-php-security-audit/)                 | credential 掃描、PHP 版本風險、SQL injection/XSS 模式、.htaccess 防護     |
| [無 SSH 環境的監控與告警](/infra/takeover/legacy-external-monitoring/)              | 外部 HTTP check、錯誤追蹤、效能基線、流量異常偵測                         |
| [有 SSH 但沒有 IaC 的雲端環境接管](/infra/takeover/cloud-no-iac/)                   | 有 Console 和 CLI 存取、但資源全是手動建的雲端環境怎麼盤點和接管          |
| [有半套 IaC 但文件缺失的環境接管](/infra/takeover/partial-iac-no-docs/)             | IaC 覆蓋不完整、部分資源在 state 外、文件缺失的環境怎麼收斂（總覽）       |
| [State 修復與清理](/infra/takeover/partial-iac-state-repair/)                       | state 損壞診斷、orphaned entry 清理、state surgery、backend 搬遷          |
| [Drift 分類處理指南](/infra/takeover/partial-iac-drift-triage/)                     | plan 輸出分類、adopt vs revert 決策、stateful replacement 風險            |
| [Unmanaged Resource 批次 Import](/infra/takeover/partial-iac-bulk-import/)          | 優先序、import block、generated HCL review、批次策略                      |
| [兩套真相並存的過渡期操作](/infra/takeover/partial-iac-dual-truth-operation/)       | 操作規則、ownership 台帳、團隊溝通、import sprint、transition 完成判準    |

## 跟其他模組的關係

接手維運的終點是把環境帶到[模組負一](/infra/before-infra/)（可控的手動）或[模組一](/infra/01-minimal-iac/)（最小可行 IaC）的狀態。接手流程本身不做 IaC 導入 — 它的責任是讓接手者理解環境、建立維運能力、確認什麼能動什麼不能動。IaC 導入是接手完成之後的下一步。

- → [模組負一：還沒有 infra 的環境](/infra/before-infra/)：接手完成後，環境的操作紀律對齊這裡
- → [模組零：infra 是什麼](/infra/00-infra-mindset/)：成熟度階梯作為接手後評估現況的座標
- → [模組二：身分與憑證](/infra/02-identity-credentials/)：接手時的 credential 盤點與輪替
- → [模組八：治理好習慣](/infra/08-governance-habits/)：接手後的 tagging 與 secret 管理
