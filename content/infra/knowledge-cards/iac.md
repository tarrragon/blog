---
title: "Infrastructure as Code (IaC)"
date: 2026-06-26
description: "用程式碼描述基礎設施的最終狀態，由工具負責收斂現實與描述的差異"
weight: 1
tags: ["infra", "knowledge-cards", "iac"]
---

Infrastructure as Code（IaC）的核心概念是用版本控制的程式碼描述基礎設施應該長什麼樣，再由工具負責比對「程式碼描述的目標狀態」與「雲端上的實際狀態」，算出差異並收斂。這個機制把基礎設施從「某個人在 Console 手動點出來的東西」變成「可版本控制、可 review、可重建的描述」——最常見的落地語言是 [HCL](/infra/knowledge-cards/hcl/)。

IaC 工具分兩條路線：宣告式 DSL（Terraform / OpenTofu，用 [HCL](/infra/knowledge-cards/hcl/) 描述資源）與程式語言（AWS CDK / Pulumi，用 TypeScript / Python / Go 生成資源）。兩者都能達成「用程式碼描述、由工具收斂」的目標，差別在閱讀門檻與抽象能力。

## 概念位置

IaC 是 infra 系列的根概念，貫穿所有模組。[成熟度階梯](/infra/00-infra-mindset/infra-responsibility-maturity/)的第二階（宣告式 IaC）是 IaC 正式生效的起點，第三階（[環境分離](/infra/knowledge-cards/environment-separation/)）和第四階（PR 流程治理）都建立在 IaC 之上。沒有 IaC，後續所有模組的能力都無法落地。

## 可觀察訊號

需要 IaC 的訊號是規模與協作的函數：環境數量超過一套、多人同時改資源、環境事故頻率上升、外部稽核要求變更紀錄。詳見[模組負一：該開始導入 IaC 的訊號](/infra/before-infra/manual-environment-baseline/)。

## 設計責任

採用 IaC 時要決定的核心問題：

- 工具選型：宣告式 DSL vs 程式語言，取捨在審查透明度 vs 抽象複用能力
- [State](/infra/knowledge-cards/state/) 的存放：remote backend 的選擇與保護
- Console 唯讀紀律：所有寫入操作回到程式碼，Console 只作觀察
- 納管範圍：哪些資源先進 IaC、哪些暫時留在手動

## 鄰卡

- [State](/infra/knowledge-cards/state/) — IaC 工具追蹤現實的記憶機制
- [Drift](/infra/knowledge-cards/drift/) — state 與現實不一致時的狀態
- [環境分離](/infra/knowledge-cards/environment-separation/) — 同一份 IaC 描述套用到多環境
