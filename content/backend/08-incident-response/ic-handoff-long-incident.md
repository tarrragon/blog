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
- 反模式：IC 連續工作 12h+ 才換班；接班用口頭交接、無書面 state；新班次重做已驗證假設

## 判讀訊號

- 長事故 IC 連續超過 8h 仍未換班
- 接班後重複跑前班次已排除的假設
- 跨區團隊事故無人擁有「現在誰是 IC」的單一答案
- handoff 後 stakeholder 收到矛盾訊息
- 班次邊界事故進度停滯、無 forward momentum

## 交接路由

- 08.2 command roles：角色定義
- 08.4 communication：跨班次對外節奏
- 08.6 drills：handoff 演練
- 08.5 postmortem：長事故 timeline 還原
