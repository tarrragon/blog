---
title: "Artifact 與可重播性"
date: 2026-05-21
description: "說明 CI/CD 中 artifact 如何支撐測試、發布、回溯與 rollback，並建立 build once、verify once、promote same artifact 的流程"
tags: ["CI", "CD", "artifact", "reproducibility"]
weight: 30
---

Artifact 可重播性的核心責任是讓每次發布都能追到同一份被驗證的產物。CI/CD 不只是在 runner 上跑命令；它要回答「測試通過的是哪份內容」「發布出去的是哪份內容」「事故時如何找回同一份內容」。

## 概念定位

[Artifact](/ci/knowledge-cards/artifact/) 是 CI/CD 流程中的交付單位。前端可能是 `dist/`，後端可能是 binary 或 image，App 可能是 IPA / AAB，資料任務可能是 DAG 或 query package；不同形式的 artifact 都承擔同一個責任：把 source change 轉成可驗證、可保存、可推進的產物。

| 能力                                                      | 責任                              | 判讀訊號                              |
| --------------------------------------------------------- | --------------------------------- | ------------------------------------- |
| Build once                                                | 同一次變更只產生一次正式 artifact | build job 是否保存產物                |
| Verify once                                               | 測試同一份 artifact               | test job 是否 download artifact       |
| [Artifact handoff](/ci/knowledge-cards/artifact-handoff/) | 在 job / workflow 間交接產物      | checksum、digest、version 是否一致    |
| Promote same artifact                                     | staging / production 推進同一份   | production 是否重新 build             |
| Recover artifact                                          | 事故時找回上一份可用產物          | retention、release、registry 是否保留 |

Build once 的責任是降低環境漂移。若 test job 與 deploy job 各自 build，一個 lockfile、環境變數或 base image 差異就能讓兩份產物不同；此時 CI 綠燈不再能證明 production 內容可信。

Verify once 的責任是把測試結果綁到具體產物。測試應輸出 artifact identity，例如 checksum、[Image Digest](/ci/knowledge-cards/image-digest/)、release asset name 或 bundle version，讓 reviewer 能確認紅綠燈對應哪份內容。

[Artifact handoff](/ci/knowledge-cards/artifact-handoff/) 的責任是在 job 邊界保留身分。Upload / download artifact、registry digest、release asset、package registry 與 object storage 都可以做 handoff；重點是交接時沿用既有產物。

Promote same artifact 的責任是讓環境差異集中在設定與流量。Staging 驗證過的 image、package 或 static artifact 應被推進到 production；若 production 重新 build，就需要重新驗證 production 那份產物。

Recover artifact 的責任是讓 rollback 有實體目標。沒有保留 artifact 的 rollback 會變成「從舊 commit 重新 build」，這會受到依賴、base image、registry、toolchain 與時間漂移影響。

## 可重播性檢查

可重播性檢查的責任是確認產物身分與建置條件足夠明確。嚴格 reproducible build 很難在所有專案做到，但 CI/CD 至少要達到「同一次 workflow 的產物可以被查詢、保存、驗證與重新部署」。

| 檢查項      | 判讀問題                  | 常見做法                                                     |
| ----------- | ------------------------- | ------------------------------------------------------------ |
| Source      | artifact 對應哪個 commit  | embed git SHA / release version                              |
| Dependency  | dependency 是否固定       | lockfile、base image digest                                  |
| Environment | build 環境是否固定        | runner image、toolchain version                              |
| Identity    | artifact 是否有不可變身分 | checksum、digest、signature                                  |
| Retention   | artifact 保留多久         | release asset、registry retention                            |
| Provenance  | artifact 如何被產生       | workflow run、[SBOM](/ci/knowledge-cards/sbom/)、attestation |

這張表讓團隊知道自己目前在哪個成熟度。初期可以先做到 source、dependency、identity；高治理場景再補 SBOM、signature 與 provenance。

## 常見反模式

反模式的共同問題是讓「綠燈」失去指向性。當綠燈不知道對應哪份產物，CI/CD 只剩下命令執行紀錄。

| 反模式                        | 風險                       | 替代做法                       |
| ----------------------------- | -------------------------- | ------------------------------ |
| test 與 deploy 各自 build     | 測試與發布內容漂移         | build once，artifact handoff   |
| rollback 重新 build 舊 commit | 舊 commit 可能產出不同內容 | 保留上一份 release artifact    |
| 只用人類可讀 tag              | tag 可被覆寫或語意不精準   | 搭配 checksum / digest         |
| artifact retention 太短       | 事故時找不到可回復版本     | 對 release artifact 設長期保留 |

## 下一步路由

- Artifact 術語：讀 [Artifact](/ci/knowledge-cards/artifact/)。
- Artifact handoff：讀 [Artifact Handoff](/ci/knowledge-cards/artifact-handoff/)。
- Gate 邊界：讀 [CI gate 與 workflow 邊界](../ci-gate-workflow-boundary/)。
