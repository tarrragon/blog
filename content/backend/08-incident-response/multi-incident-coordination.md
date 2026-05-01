---
title: "8.14 Multi-incident Coordination"
date: 2026-05-01
description: "把同時多事故的優先序、資源分配與 IC pool 協調變成可執行流程"
weight: 14
---

## 大綱

- 為何需要獨立節點：8.2 假設單事故、規模化組織同時 3+ 事故是常態
- 衝突資源：IC pool、subject expert、stakeholder communication channel
- 優先序判準：customer impact、blast radius、不可逆性、復原成本
- meta-IC 角色：協調多事故 IC、分配資源、防止 cascading
- 共通根因檢測：兩個 incident 是否同源、避免重複 IR
- 跟 [8.2 command roles](/backend/08-incident-response/incident-command-roles/) 的延伸：8.2 是單事故、8.14 是事故組合
- 跟 [8.10 stakeholder](/backend/08-incident-response/stakeholder-communication/) 的整合：多事故對外通訊不可矛盾
- 反模式：多事故各自開戰情室、無協調；同事被 page 到不同事故；meta-IC 角色缺失、靠 senior 臨時補位

## 判讀訊號

- 同時 3+ active incident 時、沒人能說「最嚴重的是哪個」
- 同 SME 被 page 到多事故、靠人力切換
- 多事故對外通訊出現矛盾資訊
- 共通根因事故被當獨立 IR 處理、重複工
- IC pool 不足、事故等待 IC 啟動

## 交接路由

- 08.1 severity：跨事故優先序判準
- 08.2 command roles：meta-IC 角色定義
- 08.10 stakeholder：多事故對外節奏
- 08.13 repeated：同源事故合併判讀
