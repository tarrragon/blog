---
title: "Artifact Handoff"
date: 2026-05-06
description: "說明測試與部署如何共用同一份可追溯產物"
tags: ["CI", "artifact", "knowledge-card"]
weight: 4
aliases: ["/ci/knowledge-cards/artifact-handoff/"]
---

Artifact Handoff 的核心概念是「測試與發布共用同一份[產物](/devops/ci/knowledge-cards/artifact/)」。它把可重現性從口頭約定變成流程保證。

## 跟其他概念的關係

Artifact Handoff 位在 build、test、deploy 之間，透過 upload / download [artifact](/devops/ci/knowledge-cards/artifact/) 串接驗證與發布。

## 可觀察訊號

- 測試通過但部署後行為與測試結果不一致。
- 多環境重新 build 造成版本漂移。
- 事故追查時缺少從部署版本反查 build run 的路徑。

## 接近真實服務的例子

CI build 產生靜態網站 artifact，browser test 驗證該 artifact，deploy job 再發布同一份產物。容器場域則可把 image digest 當成 handoff 物件。

## 判斷條件與後果

Artifact Handoff 的保證是測試與部署拿到同一份產物，每一個欄位缺席時，這個保證斷在不同位置。產物格式沒有固定時，下游 job 各自重新打包，打包的差異讓測試結果對不上發布內容；保留期短於事故追查需要的時間時，事故發生後原始 artifact 已被刪除，無法重跑測試比對；沒有完整性驗證（checksum 或 image digest）時，傳遞途中被替換或損壞的產物照樣被部署；沒有追溯欄位時，從線上版本反查不到 build run。
