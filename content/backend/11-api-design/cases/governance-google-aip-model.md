---
title: "11.C46 Google AIP：規範即提案系統的治理模式"
date: 2026-07-03
description: "編號提案制、狀態機、簽核門檻把 IETF RFC 流程內化到單一組織；中心化治理、社群貢獻是輸入"
weight: 46
tags: ["backend", "api-design", "case-study", "governance"]
---

這個案例的核心責任是記錄「規範即提案系統」的治理模式原型。

## 觀察

AIP-1 定義 AIP 為 API 開發的高階精簡設計文件、以 GitHub 維護、編號提案形式累積。治理採編輯團制（7 位 approver、editorship 採現任編輯邀請制）；提案進入 Reviewing 需 1 位編輯核可且無正式異議、進入 Approved 需 2 位非作者 approver 正式 signoff；TL 是流程的最終決策者與 escalation 終點。動機明言：Google API 生態擴張後需要一套可供 producer 與 reviewer 引用的文件語料。

## 判讀

AIP 把 API 規範治理做成有編號、狀態機、簽核門檻的提案系統 — 本質是把 IETF RFC 流程內化到單一組織、重點是決策可追溯與規範可演進、而非一次性文件。編輯邀請制加 TL 終審顯示它仍是中心化治理、社群貢獻是輸入不是決策權。

## 對應大綱

11.10 API 規範治理（anchor、與 Zalando Guild 制對照）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [AIP-1: AIP Purpose and Guidelines（Google AIP）](https://google.aip.dev/1)
