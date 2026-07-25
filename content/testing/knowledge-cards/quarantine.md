---
title: "Quarantine（隔離）"
date: 2026-07-17
description: "把已知 flaky 的測試從主要執行路徑移開、保留修復壓力的治理機制；與 skip 的語意差異在於 quarantine 有負責人和回收期限"
weight: 11
tags: ["testing", "quarantine", "flaky", "governance"]
---

Quarantine 是把已知 flaky 的測試從主要執行路徑移開的治理機制：讓它的紅燈不污染 CI 的通過訊號，同時用負責人和回收期限維持修復壓力。與直接 skip 的分界在語意——skip 是「不跑」，quarantine 是「隔離觀察、排定回收」。時序型 flaky（如 [fire-and-forget 編排](/testing/knowledge-cards/fire-and-forget-orchestration/)的斷言時點落差）是進入隔離區的常客。[Flaky test 團隊治理](/testing/05-test-design-judgment/flaky-team-governance/)完整描述了 quarantine 的觸發條件、責任分配、re-admit（修復後重新排入主線）流程。

## 概念位置

[根因分類](/testing/05-test-design-judgment/flaky-test-root-cause/)回答「怎麼修」，quarantine 回答「修好之前怎麼擋」——兩者的分工是動作次序而非層次高低：先擋住紅燈污染、再依根因排修復優先序。實務上進入隔離區的常客是時序型 flaky，成因多為 [fire-and-forget 編排](/testing/knowledge-cards/fire-and-forget-orchestration/)與[流程測試](/testing/knowledge-cards/flow-test/)的斷言時點落差。

## 可觀察訊號與例子

quarantine 佔比持續增長、平均停留時間不下降——代表回收機制失效，測試進得去、出不來。這個指標的行動閾值在[治理章](/testing/05-test-design-judgment/flaky-team-governance/)的「可視化」段描述。

## 設計責任

實作通常用 test tag（`@quarantine`）配 runner 的排除參數。隔離後的三項紀律：指定負責人、設回收期限、到期未修強制 triage（修復 / 刪除 / 重新設計覆蓋目標）。同一條測試若被隔離超過兩次，修復方向從測試層轉向被測程式碼的設計層。
