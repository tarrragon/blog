---
title: "Drift（設定漂移）"
date: 2026-06-26
description: "IaC 的 state 與雲端實際狀態之間的不一致，通常因為有人繞過 IaC 直接在 Console 改設定"
weight: 3
tags: ["infra", "knowledge-cards", "drift", "iac"]
---

Drift 指的是 IaC 的 [state](/infra/knowledge-cards/state/) 記錄與雲端上的實際資源狀態之間的不一致。最常見的來源是有人繞過 IaC、直接在 Console 手動修改資源設定——state 不知道這次改動發生了，下一次 `plan` 時工具會把手動改的設定判定為「不在我的記憶裡、要修正回程式碼的版本」。

Drift 的代價會延遲浮現。手動改的當下看起來沒問題——設定改了、服務正常。問題出在後續某次不相關的 `apply`：工具用過時的 state 去比對，把手動改的設定覆蓋掉，服務因此斷線，而且在 PR 裡看不到這件事發生過。Drift 累積越多，每次 `apply` 的不確定性越高，最終團隊會開始害怕跑 `apply`，IaC 名存實亡。

## 概念位置

Drift 是 Console 唯讀鐵律存在的根本理由。[模組一：Console 唯讀鐵律](/infra/01-minimal-iac/console-readonly-minimal-viable/)用權限機制（人類身分唯讀、寫入權限留給自動化身分，見 [IAM](/infra/knowledge-cards/iam/)）讓「在 Console 改不動」成為預設狀態，從源頭消除 drift 的產生。

## 可觀察訊號

Drift 存在的訊號：`terraform plan` 在沒人改過程式碼的情況下顯示變更（代表有人在 Console 動了東西）、團隊開始說「跑 plan 前先看看有沒有奇怪的差異」、某次例行 apply 意外改掉了不該改的設定。

偵測 drift 的主動方式是定期跑 `terraform plan` 但不 apply，把 diff 輸出當成 drift 偵測的報告。Terraform Cloud 有內建的 drift detection 功能，定期比對 state 與雲端現實。

## 設計責任

處理 drift 時要決定：

- 偵測頻率：每次 PR 觸發 plan（被動偵測）vs 定期排程 plan（主動偵測）
- 修正方向：把雲端改回程式碼的版本（`apply`），還是把程式碼改成雲端的版本（更新 HCL）——取捨在「程式碼是 source of truth」vs「手動改的設定有它的理由」
- 預防機制：Console 唯讀權限、CI gate 攔截未經 review 的 apply

## 鄰卡

- [State](/infra/knowledge-cards/state/) — drift 是 state 與現實的落差
- [IaC](/infra/knowledge-cards/iac/) — drift 破壞 IaC 的 source of truth 地位
