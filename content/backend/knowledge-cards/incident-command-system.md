---
title: "Incident Command System"
date: 2026-04-23
description: "說明事故期間的指揮角色、決策邊界與協作方式"
weight: 151
---


Incident command system 的核心概念是「事故期間由明確角色統一決策與分工」。它把指揮、操作、溝通與紀錄拆開，降低多人同時決策造成的混亂。 可先對照 [Incident Severity](/backend/knowledge-cards/incident-severity/)。

## 概念位置

指揮系統連接 [incident severity](/backend/knowledge-cards/incident-severity/)、[escalation policy](/backend/knowledge-cards/escalation-policy/) 與 [incident timeline](/backend/knowledge-cards/incident-timeline/)。常見角色包括 incident commander、technical owner、communication owner 與 scribe。

## 可觀察訊號與例子

系統需要指揮系統的訊號是事故期間同時出現多個聊天室與多個口頭指令。若沒有單一指揮窗口，團隊容易同時做出互相衝突的切換與回滾。

## 設計責任

指揮系統要定義角色責任、決策權限、交接規則與值班補位流程。事故結束後應回看決策時間線，調整角色設計與授權邊界。
