---
title: "RCA"
date: 2026-04-23
description: "說明根因分析如何區分觸發事件、系統弱點與防線缺口"
weight: 157
---


RCA 的核心概念是「找出事故能發生的系統性原因」。它區分 trigger、contributing factors 與 control gaps，避免把單一操作失誤當成唯一答案。 可先對照 [Post-Incident Review](/backend/knowledge-cards/post-incident-review/)。

## 概念位置

RCA 是 [post-incident-review](/backend/knowledge-cards/post-incident-review/) 的分析骨架，並和 [incident timeline](/backend/knowledge-cards/incident-timeline/) 與 [runbook](/backend/knowledge-cards/runbook/) 改進連動。

## 可觀察訊號與例子

系統需要 RCA 的訊號是事故說明只停在「某人操作錯誤」。更完整的分析通常還包含告警門檻不足、權限設計過寬、回滾流程不清楚等系統層因素。

## 設計責任

RCA 要建立證據鏈、假設邊界與可驗證改進。分析結果應轉成具體行動項，並與後續演練或測試串接。
