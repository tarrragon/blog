---
title: "Environment Separation（環境分離）"
date: 2026-06-26
description: "把同一套基礎設施定義複製成多份隔離的執行實例，各有獨立 state 與故障半徑"
weight: 9
tags: ["infra", "knowledge-cards", "environment"]
---

環境分離的核心職責是讓 dev 的實驗、staging 的驗證、production 的真實流量彼此不可見也不可達 — 在 dev 跑壞一個資料庫、套錯一條 [security group](/infra/knowledge-cards/security-group/) 規則時，production 完全無感。

## 概念位置

環境分離在 infra 成熟度階梯上對應第三階。它建立在宣告式 [IaC](/infra/knowledge-cards/iac/)（第二階）的基礎上 — 有了 state 追蹤和模組化描述之後，才能用「同一份 code、不同參數」的方式複製出多個隔離環境。

分離的實作方式有一條隔離強度光譜：從帳號級（不同雲端帳號，最強隔離）到目錄級（同一 repo 內各環境一個目錄，各自持有 state）到 workspace 級（同一份 code 用執行期切換 state，隔離最弱）。多數早期團隊在目錄級落腳，因為它在顯式邊界與維運成本之間取得平衡。

## 可觀察訊號

以下狀況指向環境分離不足：

- 在 staging 測試的變更意外影響了 production 的資源 — dev 跟 prod 共用同一份 state
- 某人的 `terraform apply` 把另一個環境的資源改掉了 — workspace 的隱性狀態切換導致打錯環境
- dev 與 prod 的設定差異散落在 code 裡的 `if env == "prod"` 判斷 — 環境差異沒有集中在參數值裡

## 設計責任

環境分離的設計要決定：

- **隔離層級**：帳號級、目錄級、還是 workspace 級。判斷依據是團隊規模、合規要求、與維運餘裕
- **參數化邊界**：dev 與 prod 之間的差異全部用參數表達（instance size、multi-AZ、backup retention），module 內部不寫環境判斷
- **state 位址分離**：每個環境的 state backend 位址獨立，互不交叉

## 鄰卡

- [IaC](/infra/knowledge-cards/iac/) — 環境分離的前提是有可重用的 IaC 描述
- [State](/infra/knowledge-cards/state/) — 每個環境持有獨立的 state 檔
- [Drift](/infra/knowledge-cards/drift/) — 環境分離降低 drift 的跨環境影響範圍
