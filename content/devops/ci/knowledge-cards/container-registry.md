---
title: "Container Registry"
date: 2026-05-06
description: "說明容器產物儲存、權限與推進流程在 CD 中的責任"
tags: ["CD", "container", "registry", "knowledge-card"]
weight: 13
aliases: ["/ci/knowledge-cards/container-registry/"]
---

Container Registry 的核心概念是「管理可部署 [image](/devops/ci/knowledge-cards/image-digest/) 的供應鏈節點」。它負責保存、授權、保留與推進已驗證影像。

## 跟其他概念的關係

Container Registry 位在 image build、scan、promotion 與 runtime deploy 之間，連接 [CI](/devops/ci/knowledge-cards/ci-pipeline/) 產物與環境發布。

## 可觀察訊號

- 同一 tag 在不同環境對應內容不一致。
- 部署因拉取權限或鏡像不存在失敗。
- 線上 image 缺少來源與掃描紀錄的反查路徑。

## 接近真實服務的例子

團隊以 immutable digest 推進 staging 與 production，並透過 registry policy 控制 retention、pull 權限與 promotion 路徑。

## 判斷條件與後果

Container registry 的命名、權限、保留與來源追溯四項規則，各自決定一種發布失效是否發生。image 用可覆寫的 tag 推進時，同一個 tag 在 staging 驗過之後可以被重新推送，production 拉到的是沒有驗過的內容，原因是 tag 只是指向某個 digest 的名字、可以改指；用 immutable digest 推進時，各環境拉到的內容由 digest 保證相同。權限模型沒有涵蓋部署端的身分時，部署在拉取 image 這一步失敗；權限放得太寬時，能推送的身分都能覆寫 production 正在用的 tag。保留策略只依時間或數量清除時，線上仍在跑的 image 或回滾要用的舊版可能已經被清掉，回滾時才發現拉不到。image 沒有記下來源 commit 與掃描紀錄時，線上出問題的 image 反查不到是哪一次 build 產生的、是否掃過，稽核與事故調查都在這一步中斷。
