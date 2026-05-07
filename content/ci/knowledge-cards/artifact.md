---
title: "Artifact"
date: 2026-05-06
description: "說明 CI/CD 中可被驗證、保存與發布的交付產物"
tags: ["CI", "artifact", "knowledge-card"]
weight: 4
---

Artifact 的核心概念是「可被追溯的交付產物」。它是 build 的輸出單位，也是 test 與 deploy 的共同依據。

## 概念位置

Artifact 位在 build、test、package、deploy 之間，常見形式包含靜態網站檔案、container image、app bundle、安裝包與報告檔案。

## 可觀察訊號

- 測試與部署的輸入來源需要一致。
- 發布事故需要從線上版本反查 build run。
- 團隊需要管理產物保留時間與完整性驗證。

## 接近真實服務的例子

前端靜態站會把 `public/` 作為 artifact，上傳後再部署。後端則用 image digest 作為 artifact 識別，推進到不同環境。

## 設計責任

Artifact 要定義命名、版本追溯、保留策略與完整性檢查，讓發布結果可重播、可比對、可審計。
