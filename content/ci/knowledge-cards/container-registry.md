---
title: "Container Registry"
date: 2026-05-06
description: "說明容器產物儲存、權限與推進流程在 CD 中的責任"
tags: ["CD", "container", "registry", "knowledge-card"]
weight: 13
---

Container Registry 的核心概念是「管理可部署 image 的供應鏈節點」。它負責保存、授權、保留與推進已驗證影像。

## 概念位置

Container Registry 位在 image build、scan、promotion 與 runtime deploy 之間，連接 CI 產物與環境發布。

## 可觀察訊號

- 同一 tag 在不同環境對應內容不一致。
- 部署因拉取權限或鏡像不存在失敗。
- 無法從線上 image 反查來源與掃描紀錄。

## 接近真實服務的例子

團隊以 immutable digest 推進 staging 與 production，並透過 registry policy 控制 retention、pull 權限與 promotion 路徑。

## 設計責任

Container Registry 要定義命名策略、權限模型、保留策略與來源追溯，讓 image 發布具備可審計性。
