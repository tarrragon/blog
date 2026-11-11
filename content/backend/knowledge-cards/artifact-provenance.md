---
title: "Artifact Provenance"
tags: ["供應鏈", "Provenance"]
date: 2026-04-30
description: "說明交付物的來源、完整性與簽章關聯如何建立信任"
weight: 259
---

Artifact provenance 的核心概念是「證明交付物來源、建置路徑與完整性，讓部署決策有可驗證信任基礎」。它把供應鏈信任從假設改成證據。 可先對照 [CI Pipeline](/backend/knowledge-cards/ci-pipeline/)。

## 跟其他概念的關係

Artifact provenance 位在 [CI Pipeline](/backend/knowledge-cards/ci-pipeline/)、[Credential](/backend/knowledge-cards/credential/) 與 [Release Gate](/backend/knowledge-cards/release-gate/) 之間。它連接建置流程、簽章機制與正式放行決策。

## 可觀察訊號

系統需要 artifact provenance 的訊號是：

- 需要確認 artifact 來源是否來自受信建置流程
- 部署前需要驗證簽章、摘要與版本關聯
- 供應鏈事件後需要快速判讀受影響範圍
- 團隊需要可追溯證據支援稽核與復盤

## 接近真實網路服務的例子

團隊在發佈前驗證 artifact 簽章與 digest，並比對建置紀錄與 commit 來源；若 provenance 證據缺口出現，release gate 直接阻擋放行並觸發治理流程。

## 判斷條件與後果

Artifact provenance 的哪一環缺席，部署決策在那一環就回到假設。沒有來源證據欄位（建置紀錄、commit、digest）時，供應鏈事件發生後查不出哪些 artifact 出自受影響的建置流程，影響範圍只能整批假設；有簽章而部署前不驗證時，被替換的 artifact 照樣上線；驗證失敗而沒有處理路徑時，是否放行由當下值班的人臨場決定；證據保留的期間短於稽核與復盤要查的期間時，事後查不回當時的依據。驗證結果沒有寫進 release governance 時，release gate 讀不到它，證據缺口擋不下放行；沒有寫進 incident workflow 時，事故調查要另外重建同一份證據。
