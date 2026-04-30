---
title: "Artifact Provenance"
tags: ["供應鏈", "Provenance"]
date: 2026-04-30
description: "說明交付物的來源、完整性與簽章關聯如何建立信任"
weight: 258
---

Artifact provenance 的核心概念是「證明交付物來源、建置路徑與完整性，讓部署決策有可驗證信任基礎」。它把供應鏈信任從假設改成證據。

## 概念位置

Artifact provenance 位在 [CI Pipeline](/backend/knowledge-cards/ci-pipeline/)、[Credential](/backend/knowledge-cards/credential/) 與 [Release Gate](/backend/knowledge-cards/release-gate/) 之間。它連接建置流程、簽章機制與正式放行決策。

## 可觀察訊號

系統需要 artifact provenance 的訊號是：

- 需要確認 artifact 來源是否來自受信建置流程
- 部署前需要驗證簽章、摘要與版本關聯
- 供應鏈事件後需要快速判讀受影響範圍
- 團隊需要可追溯證據支援稽核與復盤

## 接近真實網路服務的例子

團隊在發佈前驗證 artifact 簽章與 digest，並比對建置紀錄與 commit 來源；若 provenance 證據缺口出現，release gate 直接阻擋放行並觸發治理流程。

## 設計責任

Artifact provenance 要定義來源證據欄位、簽章驗證流程、失敗處理路徑與證據保留策略，並把驗證結果寫入 release governance 與 incident workflow。
