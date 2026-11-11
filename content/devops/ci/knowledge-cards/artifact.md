---
title: "Artifact"
date: 2026-05-06
description: "說明 CI/CD 中可被驗證、保存與發布的交付產物"
tags: ["CI", "artifact", "knowledge-card"]
weight: 4
aliases: ["/ci/knowledge-cards/artifact/"]
---

Artifact 的核心概念是「可被追溯的交付產物」。它是 build 的輸出單位，也是 test 與 deploy 透過 [Artifact Handoff](/devops/ci/knowledge-cards/artifact-handoff/) 共用的依據。

## 跟其他概念的關係

Artifact 位在 build、test、package、deploy 之間，常見形式包含靜態網站檔案、[container image](/devops/ci/knowledge-cards/image-digest/)、app bundle、安裝包與報告檔案。

## 可觀察訊號

- 測試與部署的輸入來源需要一致。
- 發布事故需要從線上版本反查 build run。
- 團隊需要管理產物保留時間與完整性驗證。

## 接近真實服務的例子

前端靜態站會把 `public/` 作為 artifact，上傳後再部署。後端則用 image digest 作為 artifact 識別，推進到不同環境。

## 判斷條件與後果

Artifact 的命名、保留與完整性各自讓一種事後追查做得到。命名與版本追溯讓線上版本反查得到 build run，缺了它，發布事故只能從部署時間推測是哪一次 build；保留策略決定能回頭重播多久以前的發布，保留期短於事故追查期時，要比對的產物已經不在；完整性檢查讓部署前確認產物沒有被替換或損壞，缺了它，測試過的與部署的是否為同一份產物無法證明，審計也拿不到這份證據。
