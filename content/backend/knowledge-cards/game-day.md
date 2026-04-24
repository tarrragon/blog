---
title: "Game Day"
date: 2026-04-23
description: "說明事故演練如何驗證流程、工具與團隊協作"
weight: 163
---

Game day 的核心概念是「在受控環境模擬故障並演練處置流程」。它用實際操作驗證告警、分級、指揮、回滾與通訊是否真的可用。

## 概念位置

Game day 是 [on-call](/backend/knowledge-cards/on-call/)、[incident timeline](/backend/knowledge-cards/incident-timeline/) 與 [post-incident-review](/backend/knowledge-cards/post-incident-review/) 的訓練場景。它把文件假設轉成可觀察行為與量化結果。

## 可觀察訊號與例子

系統需要 game day 的訊號是流程文件完整但實戰仍常卡住。團隊可在預備環境模擬 broker 中斷、database 延遲或憑證失效，觀察 MTTR 與升級節奏是否符合預期。

## 設計責任

Game day 要定義演練範圍、安全邊界、成功標準、紀錄方式與復盤輸出。演練設計應避免只測單一團隊，並包含跨角色溝通與決策節點。
