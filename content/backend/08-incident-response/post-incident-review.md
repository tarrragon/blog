---
title: "8.5 復盤與改進追蹤"
date: 2026-04-23
description: "把 RCA 與 action items 轉成可驗證閉環"
weight: 5
---

## 大綱

- timeline reconstruction
- [rca](/backend/knowledge-cards/rca/) method
- [action item closure](/backend/knowledge-cards/action-item-closure/)
- closure criteria

## 判讀訊號

- timeline 還原靠記憶、不是 log / chat 紀錄
- [RCA](/backend/knowledge-cards/rca/) 停在症狀層、不挖系統性根因
- [action item closure](/backend/knowledge-cards/action-item-closure/) 不清、action items 寫了沒人追、永遠 open
- closure criteria 不清、[post-incident review](/backend/knowledge-cards/post-incident-review/) 變形式檢查
- 同類事故反覆發生、[post-incident review](/backend/knowledge-cards/post-incident-review/) 學習未跨團隊擴散

## 設計責任

復盤要包含影響摘要、時間線、根因、有效措施、無效措施、行動項與驗證期限。行動項需要指定 owner、完成標準與 [action item closure](/backend/knowledge-cards/action-item-closure/) 條件，避免停在會議紀錄。

## 交接路由

- 04.8 訊號治理閉環：偵測缺口回寫成新訊號
- 08.9 事故型態庫：抽象出 pattern
- 08.13 repeated / toil：跨事故 pattern 的工程化處理
- 08.16 runbook lifecycle：事故後 runbook 修訂
- 06.18 reliability metrics：[MTTR](/backend/knowledge-cards/mttr/) 計算的事件來源
- 08.17 security vs operational：證據保全與 [RCA](/backend/knowledge-cards/rca/) 範圍
