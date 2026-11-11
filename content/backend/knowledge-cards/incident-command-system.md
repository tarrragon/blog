---
title: "Incident Command System"
date: 2026-04-23
description: "說明事故期間的指揮角色、決策邊界與協作方式"
weight: 152
---

Incident command system 的核心概念是「事故期間由明確角色統一決策與分工」。它把指揮、操作、溝通與紀錄拆開，降低多人同時決策造成的混亂。 可先對照 [Incident Severity](/backend/knowledge-cards/incident-severity/)。

## 跟其他概念的關係

指揮系統連接 [incident severity](/backend/knowledge-cards/incident-severity/)、[escalation policy](/backend/knowledge-cards/escalation-policy/) 與 [incident timeline](/backend/knowledge-cards/incident-timeline/)。常見角色包括 incident commander、technical owner、communication owner 與 scribe。

## 可觀察訊號與例子

系統需要指揮系統的訊號是事故期間同時出現多個聊天室與多個口頭指令。若沒有單一指揮窗口，團隊容易同時做出互相衝突的切換與回滾。

## 判斷條件與後果

角色責任沒有指派時，事故期間同時出現多個聊天室與多個口頭指令，團隊可能同時執行互相衝突的切換與回滾，原因是沒有單一指揮窗口收斂決定。決策權限沒有寫清楚時，incident commander 遇到回滾或對外公告這類決定，要先找人確認自己能不能做，處置時間被拉長。交接規則與值班補位流程缺席時，事故拖過一個班次或指揮者離線，角色出現空缺，接手的人不知道哪些決定已經做過。事故結束後拿 [incident decision log](/backend/knowledge-cards/incident-decision-log/) 的時間線回看，找得出這幾項裡哪一項拖慢了這次的處置，角色設計與授權邊界的調整才有依據。
