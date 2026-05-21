---
title: "Image build、scan、registry 與 promotion 流程"
date: 2026-05-21
description: "說明 Docker / container image CI/CD 如何建立可追溯 tag、掃描 gate、registry promotion 與 runtime handoff"
tags: ["CI", "CD", "Docker", "container", "registry"]
weight: 1
---

Image 供應鏈流程的核心責任是讓 container image 從 build 到 runtime 都可追溯。Image 同時包含 application、runtime、OS package 與 dependency；CI/CD 需要把 Dockerfile、base image、tag、scan、registry 與 deployment manifest 串成同一條供應鏈。

## 流程定位

Image deployment 的風險集中在「看似同名、實際不同」的產物漂移。`latest`、mutable tag、重新 build 與跨 registry promotion 都可能讓 staging 測過的 image 不等於 production 跑的 image。嚴謹流程應以 [Image Digest](/ci/knowledge-cards/image-digest/) 或 immutable tag 作為 artifact 身分。

| 階段                                                          | 責任                                                       | 判讀訊號                                 |
| ------------------------------------------------------------- | ---------------------------------------------------------- | ---------------------------------------- |
| Build                                                         | 從 Dockerfile 產生 image                                   | base image、lockfile、build arg 是否固定 |
| Tag                                                           | 建立查詢與推進入口                                         | commit SHA、semver、digest 是否可追      |
| Scan                                                          | 顯性化漏洞、secret、[SBOM](/ci/knowledge-cards/sbom/) 風險 | 阻擋門檻與例外流程是否存在               |
| [Container registry](/ci/knowledge-cards/container-registry/) | 保存 image 並控制 promotion                                | immutable、retention、權限               |
| Runtime handoff                                               | 讓 deployment 使用已驗證 image                             | manifest 是否指向已掃描 digest           |

Build 階段負責封裝 runtime。Multi-stage build、dependency cache、base image pinning 與 build secret 處理會直接影響安全性；CI 應能在乾淨 runner 上重建 image，避免開發機狀態被帶入。

Tag 階段負責支援不同查詢情境。Commit SHA 適合事故追溯，semver 適合 release 溝通，[Image Digest](/ci/knowledge-cards/image-digest/) 適合 runtime 精準鎖定；production 判讀應以 digest 為準，tag 只作為人類入口。

Scan 階段負責把風險分流。Vulnerability scan、secret scan、license scan 與 [SBOM](/ci/knowledge-cards/sbom/) 不應只是報表；流程要定義哪些風險阻擋發布、哪些風險允許例外、例外誰審核、何時重新評估。

[Container registry](/ci/knowledge-cards/container-registry/) 階段負責保存與推進 image。Registry 要處理權限、retention、immutability、promotion 與垃圾回收；若 production 直接從 feature branch push 的 tag 拉 image，供應鏈邊界就失去治理。

Runtime handoff 階段負責把已驗證 image 交給部署平台。Kubernetes、ECS、Compose 或其他 runtime 都應指向已驗證 digest 或 immutable tag，並把 health、readiness、resource limit 與 rollback 連到同一次 release。

## Tag 與 digest 策略

Tag 策略的責任是讓人查得到、機器鎖得住。單一 tag 很難同時滿足可讀性、可追溯與不可變三個需求，因此實務上常搭配多個 tag 與 digest。

| 標識       | 適合用途                   | 風險                                |
| ---------- | -------------------------- | ----------------------------------- |
| Commit SHA | 從 runtime 回查 source     | 對使用者不友善                      |
| Semver     | 對外 release 溝通          | tag 可能被覆寫，需搭配 immutability |
| Branch tag | preview / staging 快速迭代 | 不適合作為 production 依據          |
| Digest     | runtime 精準鎖定           | 人類閱讀成本高                      |

Production deployment 應能從 running pod 或 task 反查 image digest，再反查 registry metadata、scan report、workflow run 與 source commit。這條查詢路徑是 incident response 的基本能力。

## Scan gate 分流

Scan gate 的責任是讓安全訊號變成可操作路由。掃描工具會產生大量結果，沒有分流規則時，團隊會在兩種壞狀態間搖擺：全部阻擋導致發不出去，全部忽略導致掃描失去信任。

| 結果類型                                  | 策略                           | 下一步                            |
| ----------------------------------------- | ------------------------------ | --------------------------------- |
| Critical exploitable                      | 阻擋 production promotion      | 升級 dependency / base image      |
| High with mitigation                      | 需要審核例外與到期日           | 記錄風險、設定重新掃描            |
| Base image aging                          | 排入 base image refresh        | 建立定期更新節奏                  |
| Secret in layer                           | 阻擋並輪替 secret              | 重建 image、撤銷已暴露 credential |
| [SBOM](/ci/knowledge-cards/sbom/) missing | 阻擋高治理環境，低風險環境警告 | 補 provenance / SBOM 產出         |

這個分流讓 scan 成為 gate。例外流程要有 owner 與到期日，讓例外維持可追蹤、可重新評估。

## 常見反模式

反模式的共同問題是讓 image 身分失去穩定錨點。當 image 身分漂移，測試結果、掃描結果與 runtime 狀態會彼此分叉。

| 反模式                           | 風險                        | 替代做法                                                                |
| -------------------------------- | --------------------------- | ----------------------------------------------------------------------- |
| production 使用 `latest`         | running image 缺少精準身分  | 使用 [Image Digest](/ci/knowledge-cards/image-digest/) 或 immutable tag |
| staging 與 production 各自 build | 測試產物與上線產物分叉      | build once，promote same image                                          |
| build secret 留在 layer          | secret 進入 registry 與節點 | 使用 BuildKit secret mount                                              |
| scan 只報告不阻擋                | 高風險漏洞仍進 production   | 定義阻擋門檻與例外流程                                                  |

## 下一步路由

- Image 部署總覽：回 [Docker / Image 部署 CI/CD](../)。
- Registry 術語：讀 [Container Registry](/ci/knowledge-cards/container-registry/)。
- 後端 runtime 部署：讀 [後端部署 CI/CD](../../backend-deploy/)。
