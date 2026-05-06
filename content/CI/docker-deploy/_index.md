---
title: "Docker / Image 部署 CI/CD"
date: 2026-05-06
description: "整理 container image 的 build、tag、scan、registry、promotion 與 runtime 部署注意事項"
tags: ["CI", "CD", "Docker", "container"]
weight: 13
---

Docker / image 部署 CI/CD 的核心責任是把可執行環境封裝成可追溯的 image。Image 同時承載 application、runtime、OS package、dependency 與安全掃描結果，因此它是可以被推進、掃描與回溯的部署產物；而 [Container Registry](/ci/knowledge-cards/container-registry/) 提供保存與推進的供應鏈節點。

## 場域定位

Image 部署常出現在後端、worker、batch job 與自架服務。它把「在哪個環境跑」前移到 build 階段，但也引入 registry、tag、base image、vulnerability scan 與 promotion 流程（platform 概念可對照 [Container](/backend/knowledge-cards/container/)）。

| 面向     | Image 部署常見責任              | 判讀訊號                             |
| -------- | ------------------------------- | ------------------------------------ |
| Build    | Dockerfile、multi-stage build   | image 是否可重現、layer 是否合理     |
| Tag      | semver、commit SHA、release tag | tag 是否能追到 source                |
| Scan     | vulnerability、secret、SBOM     | 是否有阻擋門檻與例外流程             |
| Registry | push、retention、promotion      | prod image 是否來自已驗證 artifact   |
| Runtime  | Kubernetes、Compose、ECS 等     | health、readiness、rollback 是否存在 |

Build 階段負責把 application 與 runtime 封裝成 image。Multi-stage build、dependency cache、base image 與 layer 順序會影響速度、安全性與可重現性；CI 應能從 Dockerfile 與 lockfile 重建同一類產物。

Tag 階段負責讓 image 可追溯。Commit SHA、release tag 與 semver 各自服務不同查詢情境；production 需要能從 running image 反查 source、workflow run 與掃描結果。

Scan 階段負責讓 image 風險可見。Vulnerability scan、secret scan 與 SBOM 能把 base image、OS package 與 dependency 風險顯性化；阻擋門檻要和例外流程一起定義，讓掃描結果能被分流處理。

Registry 階段負責保存與推進 image。真實流程通常需要 retention、immutability、promotion 與權限控管；production image 應來自已驗證 [artifact handoff](/ci/knowledge-cards/artifact-handoff/)，讓各環境推進同一份產物（供應鏈治理可對照 [Artifact Provenance](/backend/knowledge-cards/artifact-provenance/)）。

Runtime 階段負責把 image 轉成可運行服務。Kubernetes、Compose、ECS 或其他平台都需要 [health check](/backend/knowledge-cards/health-check/)、[readiness](/backend/knowledge-cards/readiness/)、[resource limit](/backend/knowledge-cards/resource-limit/)、secret injection（可對照 [Secret Management](/backend/knowledge-cards/secret-management/)）與 rollback 設計，否則 image 成功不等於服務可用。

## 常見注意事項

- `latest` 不適合當 production 追溯依據。
- Base image 要有更新節奏，否則掃描結果會持續惡化。
- Build secret 不應留在 image layer。
- Scan gate 要區分阻擋門檻與可接受例外。
- Promotion 應推進同一份 image，讓 staging 與 production 的差異集中在設定與流量。

## 下一步路由

- 後端部署：讀 [後端部署 CI/CD](../backend-deploy/)。
- Gate 原理：讀 [CI gate 與 workflow 邊界](../ci-gate-workflow-boundary/)。
- Backend deployment platform：讀 [模組五：部署平台與網路入口](/backend/05-deployment-platform/)。
