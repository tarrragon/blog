---
title: "Artifact Handoff"
date: 2026-05-06
description: "說明測試與部署如何共用同一份可追溯產物"
tags: ["CI", "artifact", "knowledge-card"]
weight: 4
---

Artifact Handoff 的核心概念是「測試與發布共用同一份產物」。它把可重現性從口頭約定變成流程保證。

## 概念位置

Artifact Handoff 位在 build、test、deploy 之間，透過 upload / download artifact 串接驗證與發布。

## 可觀察訊號

- 測試通過但部署後行為與測試結果不一致。
- 多環境重新 build 造成版本漂移。
- 事故追查時無法從部署版本反查 build run。

## 接近真實服務的例子

CI build 產生靜態網站 artifact，browser test 驗證該 artifact，deploy job 再發布同一份產物。容器場域則可把 image digest 當成 handoff 物件。

## 設計責任

Artifact Handoff 要定義產物格式、保留策略、完整性驗證與追溯欄位，讓測試結果可直接映射到發布結果。
