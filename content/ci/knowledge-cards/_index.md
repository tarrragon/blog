---
title: "Knowledge Cards"
date: 2026-05-06
description: "用原子化卡片整理 CI/CD 章節的核心術語，讓流程文章專注在判讀與決策"
tags: ["CI", "CD", "Knowledge Cards"]
weight: 0
---

CI/CD 知識卡片的核心責任是建立共同語言。流程文章會使用 pipeline、gate、artifact、rollout、rollback、environment protection 等術語；卡片負責定義它們在系統中的位置、可觀察訊號與設計責任。

## 核心術語

| 卡片                                                                    | 核心問題                           | 常見出現位置                                |
| ----------------------------------------------------------------------- | ---------------------------------- | ------------------------------------------- |
| [CI Pipeline](/ci/knowledge-cards/ci-pipeline/)                         | 變更如何在合併前被自動驗證         | lint、test、build、security check           |
| [CD Pipeline](/ci/knowledge-cards/cd-pipeline/)                         | 驗證後產物如何被安全推進到目標環境 | deploy、promotion、release workflow         |
| [Required Checks](/ci/knowledge-cards/required-checks/)                 | PR 合併條件如何由檢查結果定義      | branch protection、status checks            |
| [Artifact](/ci/knowledge-cards/artifact/)                               | 交付產物如何被追溯、保存與發布     | build output、image、app bundle             |
| [Artifact Handoff](/ci/knowledge-cards/artifact-handoff/)               | 測試與發布如何共用同一份產物       | build artifact、package、deploy             |
| [Migration](/ci/knowledge-cards/migration/)                             | 狀態變更如何在相容窗口內受控推進   | schema change、backfill、release            |
| [Branch Protection](/ci/knowledge-cards/branch-protection/)             | 主線合併條件如何由規則強制保護     | required checks、review policy              |
| [Readiness / Health Check](/ci/knowledge-cards/readiness-health-check/) | 部署放行如何區分存活與可接流量訊號 | rollout、probe、traffic switch              |
| [Container Registry](/ci/knowledge-cards/container-registry/)           | image 供應鏈如何被保存與推進       | push、retention、promotion                  |
| [App Signing](/ci/knowledge-cards/app-signing/)                         | 行動與桌面發版能力如何由簽章維持   | certificate、profile、keystore              |
| [Flaky Test](/ci/knowledge-cards/flaky-test/)                           | 非決定性測試如何影響 gate 信任度   | rerun noise、test governance                |
| [Environment Protection](/ci/knowledge-cards/environment-protection/)   | 目標環境如何設置審核與發布保護     | production、staging、review gate            |
| [Preview Environment](/ci/knowledge-cards/preview-environment/)         | PR 變更如何在隔離環境中被提前驗證  | frontend preview URL、review app            |
| [Rollout Strategy](/ci/knowledge-cards/rollout-strategy/)               | 新版本如何分批推進以控制風險       | rolling、canary、phased rollout             |
| [Rollback Strategy](/ci/knowledge-cards/rollback-strategy/)             | 發布異常時如何回到已知可用狀態     | deploy rollback、hotfix、forward fix        |
| [Deployment Dry Run](/ci/knowledge-cards/deployment-dry-run/)           | 發布前如何先驗證流程條件與權限     | preflight check、artifact check、permission |
| [Backfill](/ci/knowledge-cards/backfill/)                               | 歷史資料如何受控補算               | migration、data pipeline、repair            |
| [Checkpoint](/ci/knowledge-cards/checkpoint/)                           | 長時間任務如何保存接續位置         | backfill、stream processor、rerun           |
| [Rerun](/ci/knowledge-cards/rerun/)                                     | 重跑流程如何避免擴大副作用         | flaky test、data repair、pipeline recovery  |
| [Image Digest](/ci/knowledge-cards/image-digest/)                       | container image 如何取得不可變身分 | registry、scan、runtime handoff             |
| [SBOM](/ci/knowledge-cards/sbom/)                                       | artifact 內含元件如何被揭露        | image scan、release evidence、compliance    |
| [Release Channel](/ci/knowledge-cards/release-channel/)                 | 版本如何依使用者範圍分流           | app、desktop、beta、stable                  |
| [Update Feed](/ci/knowledge-cards/update-feed/)                         | 已安裝客戶端如何取得新版本         | desktop auto-update、rollback channel       |
| [Infrastructure Drift](/ci/knowledge-cards/infrastructure-drift/)       | 真實環境與 IaC 宣告如何分叉        | Terraform、Pulumi、manual hotfix            |
| [State Lock](/ci/knowledge-cards/state-lock/)                           | IaC apply 如何避免併發覆寫 state   | Terraform backend、workspace、apply         |
| [Function Alias](/ci/knowledge-cards/function-alias/)                   | serverless 入口如何指向特定版本    | alias rollback、traffic shift               |
| [Event Source](/ci/knowledge-cards/event-source/)                       | 事件來源如何影響 retry 與回復      | queue、topic、HTTP trigger、scheduler       |

卡片與流程文章分工清楚。卡片負責名詞與邊界，流程文章負責情境判讀與操作路由。
