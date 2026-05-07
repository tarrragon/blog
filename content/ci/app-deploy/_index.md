---
title: "App 部署 CI/CD"
date: 2026-05-06
description: "整理 mobile / desktop app 的簽章、版本、審核、分批發布與回退限制"
tags: ["CI", "CD", "app", "deployment"]
weight: 12
---

App 部署 CI/CD 的核心責任是把可安裝的 client [artifact](/ci/knowledge-cards/artifact/) 安全送到發行通道。App 發布和 web 部署最大的差異是使用者裝置會保留舊版，app store 審核、[App Signing](/ci/knowledge-cards/app-signing/)、版本號與分批發布會直接影響交付節奏。

## 場域定位

App 部署的風險集中在 artifact 不可變、簽章憑證、store review 與版本分佈。後端可以快速 rollback，前端靜態站可以重新部署，但已安裝的 App 需要靠更新、[feature flag](/backend/knowledge-cards/feature-flag/) 或服務端相容性管理。

| 面向                                                        | App 部署常見責任                   | 判讀訊號                        |
| ----------------------------------------------------------- | ---------------------------------- | ------------------------------- |
| Build                                                       | IPA、APK、AAB、desktop package     | build number / version 是否遞增 |
| Signing                                                     | certificate、profile、keystore     | secret 是否安全、是否可輪替     |
| Test                                                        | unit、UI、device matrix            | 是否覆蓋目標 OS 與裝置          |
| Release                                                     | store review、phased rollout       | 審核狀態與 rollout 百分比       |
| [Rollback Strategy](/ci/knowledge-cards/rollback-strategy/) | hotfix、remote config、kill switch | 是否能處理已安裝舊版            |

Build 階段負責產生可安裝 artifact。Mobile 常見產物是 IPA、APK 或 AAB，desktop 則可能是 installer 或 signed package；版本號、build number 與 commit 對應關係會決定後續除錯與回報能否追溯。

Signing 階段負責證明 artifact 由可信來源發布。憑證、profile、keystore 與 signing secret 都屬於發布能力；它們需要輪替、權限控管與備援流程，避免單一憑證問題中斷發布（安全治理延伸見 [Secret Management](/backend/knowledge-cards/secret-management/)）。

Test 階段負責驗證不同裝置與作業系統組合。App 測試常見風險是 emulator 通過但真機失敗、特定 OS 權限模型不同、背景執行限制不同；device matrix 要依使用者分佈與高風險功能選擇。

Release 階段負責把 artifact 送進發行通道。Store review、phased rollout、internal testing、beta track 與 production track 都是 gate；發布節奏要把審核時間與分批比例納入 [rollout strategy](/ci/knowledge-cards/rollout-strategy/) 的風險控制（backend 延伸見 [Config Rollout](/backend/knowledge-cards/config-rollout/)）。

[Rollback Strategy](/ci/knowledge-cards/rollback-strategy/) 階段負責處理已安裝版本。App 發布後會長期存在多個使用者版本，因此 hotfix、remote config、kill switch 與後端相容性要一起設計（相容治理延伸見 [API Contract](/backend/knowledge-cards/api-contract/)）。

## 常見注意事項

- 簽章憑證是發布能力的一部分，要用 [Secret Management](/backend/knowledge-cards/secret-management/) 管理。
- 版本號與 build number 要可追溯到 commit 與 artifact。
- Store review 會讓 rollback 和 hotfix 變慢，風險要提前用 [feature flag](/backend/knowledge-cards/feature-flag/) 控制。
- Client / server contract 要支援多版本共存。
- Crash reporting 與 phased rollout 是發布後 gate 的一部分。

## 下一步路由

- Gate 原理：讀 [CI gate 與 workflow 邊界](../ci-gate-workflow-boundary/)。
- 失敗處理：讀 [CI 失敗到修復發布流程](../github-actions-failure-flow/)。
