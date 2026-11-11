---
title: "Drift（設定漂移）"
date: 2026-06-26
description: "IaC 的 state 與雲端實際狀態之間的不一致，通常因為有人繞過 IaC 直接在 Console 改設定"
weight: 3
tags: ["infra", "knowledge-cards", "drift", "iac"]
aliases: ["/infra/knowledge-cards/drift/"]
---

Drift 指的是 IaC 的 [state](/devops/infra/knowledge-cards/state/) 記錄與雲端上的實際資源狀態之間的不一致。最常見的來源是有人繞過 IaC、直接在 Console 手動修改資源設定——state 不知道這次改動發生了，下一次 `plan` 時工具會把手動改的設定判定為「不在我的記憶裡、要修正回程式碼的版本」。

Drift 的代價會延遲浮現。手動改的當下看起來沒問題——設定改了、服務正常。問題出在後續某次不相關的 `apply`：工具用過時的 state 去比對，把手動改的設定覆蓋掉，服務因此斷線，而且在 PR 裡看不到這件事發生過。Drift 累積越多，每次 `apply` 的不確定性越高，最終團隊會開始害怕跑 `apply`，IaC 名存實亡。

## 跟其他概念的關係

Drift 是 Console 唯讀鐵律存在的根本理由。[模組一：Console 唯讀鐵律](/devops/infra/01-minimal-iac/console-readonly-minimal-viable/)用權限機制（人類身分唯讀、寫入權限留給自動化身分，見 [IAM](/devops/infra/knowledge-cards/iam/)）讓「在 Console 改不動」成為預設狀態，從源頭消除 drift 的產生。

## 可觀察訊號

Drift 存在的訊號：`terraform plan` 在沒人改過程式碼的情況下顯示變更（代表有人在 Console 動了東西）、團隊開始說「跑 plan 前先看看有沒有奇怪的差異」、某次例行 apply 意外改掉了不該改的設定。

偵測 drift 的主動方式是定期跑 `terraform plan` 但不 apply，把 diff 輸出當成 drift 偵測的報告。plan 只比對 state 裡有的資源：有人在主控台另外新增、不在 state 裡的資源（例如寫成獨立資源的一條防火牆規則），plan 照樣回報 `No changes`，範圍見 [多台主機的維護清單：值的分層與合併的位置、用 Ansible 的 inventory 與範本產生每台的清單、由 Terraform 的輸出產生 inventory、跨主機執行的 exit code，以及單台清單的適用範圍](/devops/operations/09-host-lifecycle/multi-host-manifest/)〈清單裡要到主控台確認的項目與 terraform plan 的比對範圍〉（從比對機制推論，沒有實測）。Terraform Cloud 有內建的 drift detection 功能，定期比對 state 與雲端現實。

## 判斷條件與後果

Drift 的修正方向取決於 Console 上那次手動修改的性質。手動修改是失誤時，程式碼仍是正確的版本，`apply` 把雲端改回程式碼的版本；手動修改是有理由的修正時，`apply` 會把那個修正覆蓋掉，原本修好的狀況再發生一次，所以要把那次改動寫回 HCL，讓程式碼跟上雲端。

偵測頻率決定 drift 在被發現之前累積多久。只在 PR 觸發 plan 時，沒有人開 PR 的模組可以一直帶著 drift，直到某次不相關的 apply 把手動設定覆蓋掉；定期排程跑 plan 時，drift 最晚在下一次排程被發現。

Drift 的來源是 Console 上的寫入權限。人類身分只有唯讀權限、寫入只經過有 review 的 CI gate 時，手動修改從源頭就做不到，偵測與修正要處理的 drift 跟著變少。

## 鄰卡

- [State](/devops/infra/knowledge-cards/state/) — drift 是 state 與現實的落差
- [IaC](/devops/infra/knowledge-cards/iac/) — drift 破壞 IaC 的 source of truth 地位
- [Configuration Management（組態管理）](/devops/infra/knowledge-cards/configuration-management/) — 主機內部的套件與設定檔跟宣告不一致，由組態管理工具處理
