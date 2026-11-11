---
title: "Infrastructure as Code (IaC)"
date: 2026-06-26
description: "用程式碼描述基礎設施的最終狀態，由工具負責收斂現實與描述的差異"
weight: 1
tags: ["infra", "knowledge-cards", "iac"]
aliases: ["/infra/knowledge-cards/iac/"]
---

Infrastructure as Code（IaC）的核心概念是用版本控制的程式碼描述基礎設施應該長什麼樣，再由工具負責比對「程式碼描述的目標狀態」與「雲端上的實際狀態」，算出差異並收斂。這個機制把基礎設施從「某個人在 Console 手動點出來的東西」變成「可版本控制、可 review、可重建的描述」——最常見的落地語言是 [HCL](/devops/infra/knowledge-cards/hcl/)。

IaC 工具分兩條路線：宣告式 DSL（Terraform / OpenTofu，用 [HCL](/devops/infra/knowledge-cards/hcl/) 描述資源）與程式語言（AWS CDK / Pulumi，用 TypeScript / Python / Go 生成資源）。兩者都能達成「用程式碼描述、由工具收斂」的目標，差別在閱讀門檻與抽象能力。

## 跟其他概念的關係

IaC 是 infra 系列的根概念，貫穿所有模組。[成熟度階梯](/devops/infra/00-infra-mindset/infra-responsibility-maturity/)的第二階（宣告式 IaC）是 IaC 正式生效的起點，第三階（[環境分離](/devops/infra/knowledge-cards/environment-separation/)）和第四階（PR 流程治理）都建立在 IaC 之上。沒有 IaC，後續所有模組的能力都無法落地。

## 可觀察訊號

需要 IaC 的訊號是規模與協作的函數：環境數量超過一套、多人同時改資源、環境事故頻率上升、外部稽核要求變更紀錄。詳見[模組負一：該開始導入 IaC 的訊號](/devops/infra/before-infra/manual-environment-baseline/)。

## 判斷條件與後果

IaC 要讓程式碼成為基礎設施的 source of truth，這個地位取決於程式碼用什麼寫、state 放在哪裡、誰還能繞過程式碼直接改，以及哪些資源已經納管：

- **工具選型**：宣告式 DSL 的 diff 直接讀得出資源會怎麼變，審查透明；程式語言的抽象與複用能力較強，代價是 reviewer 要在腦中執行程式碼，才知道會產生哪些資源
- **[State](/devops/infra/knowledge-cards/state/) 的存放**：state 是工具比對現實的依據。它只存在某個人的本機時，其他人跑的 plan 拿不到它；remote backend 沒有加密與存取控制時，讀得到 state 的人就看得到其中的敏感屬性
- **Console 的寫入權限**：人類身分在 Console 還能寫入時，手動改動繞過程式碼，產生 [Drift（設定漂移）](/devops/infra/knowledge-cards/drift/)，程式碼不再描述實際的基礎設施；Console 只留觀察用的唯讀權限，寫入才會全部經過程式碼
- **納管範圍**：還留在手動管理的資源不在程式碼裡，那一部分的變更沒有 review 也沒有紀錄；先納管哪些資源，就決定了 review 與變更紀錄先涵蓋哪些資源

## 鄰卡

- [State](/devops/infra/knowledge-cards/state/) — IaC 工具追蹤現實的記憶機制
- [Drift](/devops/infra/knowledge-cards/drift/) — state 與現實不一致時的狀態
- [環境分離](/devops/infra/knowledge-cards/environment-separation/) — 同一份 IaC 描述套用到多環境
- [Configuration Management（組態管理）](/devops/infra/knowledge-cards/configuration-management/) — IaC 建出主機之後，主機內部的套件、設定檔與服務由組態管理工具管
