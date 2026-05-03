---
title: "8.14 Multi-incident Coordination"
date: 2026-05-01
description: "把同時多事故的優先序、資源分配與 incident command system pool 協調變成可執行流程"
weight: 14
---

## 大綱

- 為何需要獨立節點：8.2 假設單事故、規模化組織同時 3+ 事故是常態
- 衝突資源：[incident command system](/backend/knowledge-cards/incident-command-system/) pool、subject expert、stakeholder communication channel
- 優先序判準：[impact scope](/backend/knowledge-cards/impact-scope/)、[blast radius](/backend/knowledge-cards/blast-radius/)、不可逆性、復原成本
- meta-[incident command system](/backend/knowledge-cards/incident-command-system/) 角色：協調多事故 [incident command system](/backend/knowledge-cards/incident-command-system/)、分配資源、防止 cascading
- 共通根因檢測：兩個 incident 是否同源、避免重複 IR
- 跟 [8.2 command roles](/backend/08-incident-response/incident-command-roles/) 的延伸：8.2 是單事故、8.14 是事故組合
- 跟 [8.10 stakeholder](/backend/08-incident-response/stakeholder-communication/) 的整合：多事故對外通訊不可矛盾
- 反模式：多事故各自開戰情室、無協調；同事被 page 到不同事故；meta-[incident command system](/backend/knowledge-cards/incident-command-system/) 角色缺失、靠 senior 臨時補位

## 概念定位

Multi-incident coordination 是把同時多事故的優先序、資源分配與 [incident command system](/backend/knowledge-cards/incident-command-system/) pool 協調變成可執行流程，責任是避免組織在高壓下把有限的人力切碎。

這一頁處理的是事故之間的協調，而不是單一事故處理。當 active incident 數量上升，沒有協調層就會出現資源互搶與對外訊息互相衝突。

## 核心判讀

判讀多事故協調時，先看是否能先排優先序，再看是否能共用資源而不互相拖累。

重點訊號包括：

- 是否能快速分辨哪個事故的 [impact scope](/backend/knowledge-cards/impact-scope/) 最大
- [incident command system](/backend/knowledge-cards/incident-command-system/) pool 是否有可替補與輪換
- 同一 SME 被 page 到多事故時是否有分流規則
- 對外通訊是否由單一協調面統一

## 案例對照

- [Slack](/backend/08-incident-response/cases/slack/_index.md)：多渠道通訊很容易在多事故時互相打架。
- [Datadog](/backend/08-incident-response/cases/datadog/_index.md)：監控與協調平台失效時，多事故處理會同步劣化。
- [GitHub](/backend/08-incident-response/cases/github/_index.md)：平台級事故常伴隨多條工作流同時受影響。

## 下一步路由

- 08.1 severity：跨事故優先序判準
- 08.2 command roles：meta-[incident command system](/backend/knowledge-cards/incident-command-system/) 角色定義
- 08.10 stakeholder：多事故對外節奏
- 08.13 repeated：同源事故合併判讀

## 判讀訊號

- 同時 3+ active incident 時、沒人能說「最嚴重的是哪個」
- 同 SME 被 page 到多事故、靠人力切換
- 多事故對外通訊出現矛盾資訊
- 共通根因事故被當獨立 IR 處理、重複工
- [incident command system](/backend/knowledge-cards/incident-command-system/) pool 不足、事故等待 incident commander 啟動

## 交接路由

- 08.1 severity：跨事故優先序判準
- 08.2 command roles：meta-[incident command system](/backend/knowledge-cards/incident-command-system/) 角色定義
- 08.10 stakeholder：多事故對外節奏
- 08.13 repeated：同源事故合併判讀
