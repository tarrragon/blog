---
title: "8.6 演練與值班能力建設"
date: 2026-04-23
description: "用演練與值班訓練提升事故反應品質"
weight: 6
---

## 大綱

- [game day](/backend/knowledge-cards/game-day/) design
- scenario library
- [on-call](/backend/knowledge-cards/on-call/) training
- [readiness](/backend/knowledge-cards/readiness/) [metrics](/backend/knowledge-cards/metrics/)

## 概念定位

演練與值班能力建設是把事故反應從個人經驗變成團隊能力的流程，責任是讓 [on-call](/backend/knowledge-cards/on-call/) 在真事故來臨前先看過類似情境。

這一頁處理的是反應能力，不是單次知識傳遞。沒有演練，交接會停在「知道有這件事」，不會變成「知道怎麼做」。

## 核心判讀

判讀 [readiness](/backend/knowledge-cards/readiness/) 時，先看 [game day](/backend/knowledge-cards/game-day/) 是否接近真實情境，再看升級路徑是否可執行。

重點訊號包括：

- drills 是否涵蓋常見事故型態
- shadowing 是否讓新人接觸真實決策節奏
- [escalation policy](/backend/knowledge-cards/escalation-policy/) tree 是否有可達性與最新 owner
- 演練結果是否回寫成改善項

## 案例對照

- [Google](/backend/06-reliability/cases/google/_index.md)：可靠性文化常先從演練習慣建立。
- [Netflix](/backend/06-reliability/cases/netflix/_index.md)：大規模系統需要把故障反應變成肌肉記憶。
- [Slack](/backend/08-incident-response/cases/slack/_index.md)：訊息平台的 oncall 需要熟悉高壓通訊節奏。

## 下一步路由

- 08.2 [incident command system](/backend/knowledge-cards/incident-command-system/) / role分工：演練時的責任分派
- 08.4 通訊與狀態：演練時 update cadence
- 08.12 [handover protocol](/backend/knowledge-cards/handover-protocol/)：長事故接班節奏

## 判讀訊號

- [game day](/backend/knowledge-cards/game-day/) 一年一次、無常態演練節奏
- 新值班無 onboarding、靠生事故學
- scenario library 過期、跟現況架構脫鉤
- [readiness](/backend/knowledge-cards/readiness/) metric 不存在、值班品質靠主觀評斷
- drill 結束後無 action items、學習未沉澱回 runbook

## 交接路由

- 06.7 DR / rollback rehearsal：DR 演練回饋值班訓練
- 08.12 [handover protocol](/backend/knowledge-cards/handover-protocol/)：handoff 演練
- 08.16 runbook lifecycle：演練是 runbook 有效性證明
