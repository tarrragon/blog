---
title: "Handover Protocol"
date: 2026-04-23
description: "說明事故與值班交接時要傳遞哪些資訊、責任與完成條件"
weight: 152
---

Handover protocol 的核心概念是「把事故或值班責任從一個人或一組人，完整、安全地轉到下一個接手者」。它不是單純通知誰接手，而是確認目前狀態、未完成事項、風險與下一步。

## 概念位置

Handover protocol 位在 [on-call](../on-call/)、[incident command system](../incident-command-system/) 與 [escalation policy](../escalation-policy/) 之間。它承接角色切換、班次結束與事故升級時的資訊交接。

## 可觀察訊號與例子

系統需要 handover protocol 的訊號是：事故已經持續一段時間、原本負責的人要下班、或指揮權需要轉給下一位。若沒有明確交接，常見問題是重複排查、遺漏已嘗試過的措施，或對下一步有不同理解。

## 設計責任

Handover protocol 要明確包含當前狀態、已知事實、已嘗試動作、阻塞點、下一個檢查時間、對外溝通狀態與接手確認。交接完成前，責任歸屬應保持單一，不要同時存在多個實際決策者。
