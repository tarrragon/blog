---
title: "Environment Separation（環境分離）"
date: 2026-06-26
description: "把同一套基礎設施定義複製成多份隔離的執行實例，各有獨立 state 與故障半徑"
weight: 9
tags: ["infra", "knowledge-cards", "environment"]
aliases: ["/infra/knowledge-cards/environment-separation/"]
---

環境分離的核心職責是讓 dev 的實驗、staging 的驗證、production 的真實流量彼此不可見也不可達 — 在 dev 跑壞一個資料庫、套錯一條 [security group](/devops/infra/knowledge-cards/security-group/) 規則時，production 完全無感。

## 跟其他概念的關係

環境分離在 infra 成熟度階梯上對應第三階。它建立在宣告式 [IaC](/devops/infra/knowledge-cards/iac/)（第二階）的基礎上 — 有了 state 追蹤和模組化描述之後，才能用「同一份 code、不同參數」的方式複製出多個隔離環境。

分離的實作方式有一條隔離強度光譜：從帳號級（不同雲端帳號，最強隔離）到目錄級（同一 repo 內各環境一個目錄，各自持有 state）到 workspace 級（同一份 code 用執行期切換 state，隔離最弱）。多數早期團隊在目錄級落腳，因為它在顯式邊界與維運成本之間取得平衡。

## 可觀察訊號

以下狀況指向環境分離不足：

- 在 staging 測試的變更意外影響了 production 的資源 — dev 跟 prod 共用同一份 state
- 某人的 `terraform apply` 把另一個環境的資源改掉了 — workspace 的隱性狀態切換導致打錯環境
- dev 與 prod 的設定差異散落在 code 裡的 `if env == "prod"` 判斷 — 環境差異沒有集中在參數值裡

## 判斷條件與後果

環境分離失效的典型形態是一次 `terraform apply` 改到了另一個環境的資源。下面三項設定各自決定一條通往這種失效的路徑是否存在：

- **隔離層級**：workspace 級在執行期切換 state，切換不出現在指令上，忘了切就把 dev 的變更套到 prod；目錄級讓每個環境各有目錄與 state，打錯環境要先進錯目錄，路徑寫在指令上看得見；帳號級連憑證都分開，dev 的憑證碰不到 prod 的資源，代價是多個帳號的權限與帳單要分別管理。合規要求環境之間連權限都不能互通時，只有帳號級做得到；團隊人少、維運餘裕小時，目錄級用較低的管理成本換到顯式的邊界
- **參數化邊界**：dev 與 prod 的差異寫成 module 裡的 `if env == "prod"` 判斷時，差異散在程式碼各處，改一個環境的行為要讀懂每一個分支，漏改一處就讓兩個環境走同一條路；差異全部寫成參數值（instance size、multi-AZ、backup retention）時，兩個環境的差別集中在參數檔，比對參數檔就看得到
- **state 位址**：兩個環境的 state backend 位址相同時，它們共用同一份 state，任一環境的 apply 都可能改到另一個環境的資源；位址各自獨立時，apply 只看得到自己環境的資源

## 鄰卡

- [IaC](/devops/infra/knowledge-cards/iac/) — 環境分離的前提是有可重用的 IaC 描述
- [State](/devops/infra/knowledge-cards/state/) — 每個環境持有獨立的 state 檔
- [Drift](/devops/infra/knowledge-cards/drift/) — 環境分離降低 drift 的跨環境影響範圍
