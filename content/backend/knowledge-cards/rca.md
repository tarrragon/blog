---
title: "RCA"
date: 2026-04-23
description: "說明根因分析如何區分觸發事件、系統弱點與防線缺口"
weight: 158
---

RCA 的核心概念是「找出事故能發生的系統性原因」。它區分 trigger、contributing factors 與 control gaps，避免把單一操作失誤當成唯一答案。 可先對照 [Post-Incident Review](/backend/knowledge-cards/post-incident-review/)。

## 跟其他概念的關係

RCA 是 [post-incident-review](/backend/knowledge-cards/post-incident-review/) 的分析骨架，並和 [incident timeline](/backend/knowledge-cards/incident-timeline/) 與 [runbook](/backend/knowledge-cards/runbook/) 改進連動。

## 可觀察訊號與例子

系統需要 RCA 的訊號是事故說明只停在「某人操作錯誤」。更完整的分析通常還包含告警門檻不足、權限設計過寬、回滾流程不清楚等系統層因素。

## 判斷條件與後果

RCA 的結論停在單一操作失誤時，同樣的事故仍會發生，原因是告警門檻、權限範圍、回滾流程這類讓失誤演變成事故的系統層因素沒有被改動。分析有證據鏈（每一個因果判斷對得到 [incident timeline](/backend/knowledge-cards/incident-timeline/) 上的紀錄）時，後來的人能檢查結論；假設的邊界寫明時，讀者知道哪些因素還沒被排除。改進項目寫成可驗證的行動項並接到後續的演練或測試時，才確認得了 control gap 已經補上；沒有驗證的改進項目，在下一次事故之前看不出是否有效。
