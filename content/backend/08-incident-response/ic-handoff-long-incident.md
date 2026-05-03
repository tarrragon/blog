---
title: "8.12 IC Handoff 與長事故跨班次協調"
date: 2026-05-01
description: "把 24h+ / 跨 timezone 事故的接班節奏變成可重複流程"
weight: 12
---

## 大綱

- 為何長事故需要獨立節點：8.2 角色分工假設單班次、長事故需要 handoff 協議
- handoff 的核心：context、open decision、外部承諾、現場狀態
- 接班 checklist：incident state、active mitigations、stakeholder commitments、open hypothesis
- timezone follow-the-sun：班次邊界、值班池、跨區語言差異
- 疲勞管理：強制換班門檻、決策權移轉、休息保護
- 跨班次的決策一致性：避免新班次推翻前班次方向
- 跟 [8.2 command roles](/backend/08-incident-response/incident-command-roles/) 的延伸：8.2 是角色、8.12 是時序
- 跟 [8.4 communication](/backend/08-incident-response/incident-communication/) 的整合：接班同時對外通訊節奏不可斷
- 反模式：[incident command system](/backend/knowledge-cards/incident-command-system/) 連續工作 12h+ 才換班；接班用口頭交接、無書面 state；新班次重做已驗證假設

## 概念定位

[handover protocol](/backend/knowledge-cards/handover-protocol/) 是把長事故的 context、未決策事項與外部承諾安全交接給下一班的流程，責任是讓事故在跨班次後仍維持同一條推進線。
在本章語境中，`IC handoff` 指的是 `[incident command system](/backend/knowledge-cards/incident-command-system/)` 的交接流程，不是一般輪班交接。

這一頁處理的是時序延續。沒有 handoff，長事故最容易在交班時失去 momentum，甚至回到已排除的假設。

## 核心判讀

判讀 handoff 時，先看資訊是否完整，再看新班次是否能延續決策。

重點訊號包括：

- 接班 checklist 是否固定
- open decision / open hypothesis 是否有明確記錄
- stakeholder commitments 是否會隨班次延續
- 疲勞管理是否真的觸發換班

## 案例對照

- [GitHub](/backend/08-incident-response/cases/github/_index.md)：平台級事故常跨班次推進。
- [Roblox](/backend/08-incident-response/cases/roblox/_index.md)：大流量事故的持續協調很依賴接班品質。
- [Slack](/backend/08-incident-response/cases/slack/_index.md)：跨時區團隊需要很強的 handoff discipline。

## 下一步路由

- 08.2 command roles：角色定義
- 08.4 communication：跨班次對外節奏
- 08.6 drills：handoff 演練
- 08.5 [post-incident review](/backend/knowledge-cards/post-incident-review/)：長事故 [incident timeline](/backend/knowledge-cards/incident-timeline/) 還原

## 判讀訊號

- 長事故 [incident command system](/backend/knowledge-cards/incident-command-system/) 連續超過 8h 仍未換班
- 接班後重複跑前班次已排除的假設
- 跨區團隊事故無人擁有「現在誰是 [incident command system](/backend/knowledge-cards/incident-command-system/)」的單一答案
- handoff 後 stakeholder 收到矛盾訊息
- 班次邊界事故進度停滯、無 forward momentum

## 交接路由

- 08.2 command roles：角色定義
- 08.4 communication：跨班次對外節奏
- 08.6 drills：handoff 演練
- 08.5 [post-incident review](/backend/knowledge-cards/post-incident-review/)：長事故 [incident timeline](/backend/knowledge-cards/incident-timeline/) 還原
