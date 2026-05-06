---
title: "CI gate 與 workflow 邊界"
date: 2026-05-06
description: "說明 required checks、job needs、environment protection 與 artifact handoff 的責任邊界，避免測試與發布流程互相錯位"
tags: ["CI", "workflow", "release gate", "artifact"]
weight: 3
---

CI gate 的核心責任是把「是否進入下一階段」變成明確條件。測試、建置、發布與人工審核可以分成不同 workflow 或 job，但只要它們共同決定同一次發布，就需要有清楚的 gate 關係。

## Gate 形式

Gate 形式要依控制範圍選擇。PR 合併、job 執行順序、production 發布與 artifact 傳遞是四種不同責任，混在一起會讓紅燈的意義變模糊。

| Gate 形式                                                             | 責任                                      | 判讀方式                                |
| --------------------------------------------------------------------- | ----------------------------------------- | --------------------------------------- |
| [Required checks](/ci/knowledge-cards/required-checks/)               | 阻止未通過測試的 commit 合併              | PR 或 branch protection 顯示必須通過    |
| Job `needs`                                                           | 讓 deploy 等 test / build                 | 同一 workflow 內 deploy 依賴前置 job    |
| [Environment protection](/ci/knowledge-cards/environment-protection/) | 控制 production / target environment 發布 | 部署環境需要審核或 required reviewers   |
| [Artifact handoff](/ci/knowledge-cards/artifact-handoff/)             | 確保測試與發布使用同一份產物              | test job 產生 artifact，deploy job 使用 |

[Required checks](/ci/knowledge-cards/required-checks/) 適合保護主線。它讓測試結果成為合併條件，避免紅燈變更進入 `main` 或 release branch（backend 延伸見 [CI Pipeline](/backend/knowledge-cards/ci-pipeline/)）。

Job `needs` 適合同一條 workflow 內的發布管線。它讓 `deploy` 必須等 `test`、`build` 或 `package` 成功後才執行，避免 deploy job 先於驗證結果流動（platform 延伸見 [Deployment Contract](/backend/knowledge-cards/deployment-contract/)）。

[Environment protection](/ci/knowledge-cards/environment-protection/) 適合正式環境。即使 build 與測試通過，production 或其他目標環境仍可要求人工審核、特定分支或特定 reviewer 才能部署（治理延伸見 [Release Gate](/backend/knowledge-cards/release-gate/)）。

[Artifact handoff](/ci/knowledge-cards/artifact-handoff/) 適合避免「測試一份、發布另一份」的漂移。較嚴謹的流程會讓 build job 產生 artifact，test job 驗證這份 artifact，deploy job 發布同一份 artifact（供應鏈延伸見 [Artifact Provenance](/backend/knowledge-cards/artifact-provenance/)）。

## Workflow 邊界

Workflow 邊界的責任是決定哪些步驟共享同一條執行圖。放在同一條 workflow 裡的 job 可以用 `needs` 建立顯式依賴；分散在不同 workflow 裡的流程，通常要靠 branch protection 或 environment protection 建立跨 workflow gate。

| 結構                 | 適合情境                       | 常見風險                            |
| -------------------- | ------------------------------ | ----------------------------------- |
| 單一 workflow 多 job | test / build / deploy 緊密相依 | YAML 變長，但依賴關係清楚           |
| 多 workflow          | 不同觸發條件或責任完全不同     | 跨 workflow gate 要靠 repo 設定     |
| PR workflow + deploy | PR 驗證、main 發布分離         | main push 若缺 required checks 會漏 |
| Artifact pipeline    | 同一份產物要被測試再發布       | artifact 版本與權限要治理           |

多 workflow 的關鍵風險是順序假設。GitHub Actions 的 workflow 彼此獨立；跨 workflow 順序需要靠 repository 設定或 API 顯式串接。

## 發布阻擋判讀

發布阻擋要同時看 YAML 與 GitHub repository 設定。YAML 說明 workflow 或 job 如何執行；跨 workflow 的「測試通過才發布」通常要靠 [Branch Protection](/ci/knowledge-cards/branch-protection/)、required status checks 或 environment protection。

| 問題                              | 只看 YAML 能判斷嗎 | 應檢查的位置                                                                                                          |
| --------------------------------- | ------------------ | --------------------------------------------------------------------------------------------------------------------- |
| deploy 是否等 build               | 可以               | 同 workflow 的 `needs`                                                                                                |
| deploy 是否等另一條 test workflow | 通常要查設定       | [Branch Protection](/ci/knowledge-cards/branch-protection/) / [Required Checks](/ci/knowledge-cards/required-checks/) |
| PR 是否必須通過測試才能合併       | 需要查 repo 設定   | [Branch Protection](/ci/knowledge-cards/branch-protection/)                                                           |
| 目標環境是否需要人工審核          | 需要查環境設定     | Environment protection                                                                                                |
| 測試與發布是否同一份 artifact     | 可以部分判斷       | workflow artifact upload / download                                                                                   |

這個判讀順序能避免錯修。若測試紅燈但目標環境仍發布，問題通常在 deploy gate 尚未把測試狀態納入發布條件。

## 常見反模式

反模式的共同問題是讓 CI 綠燈與發布安全之間失去因果關係。CI 的目標是讓綠燈代表「這次變更在定義好的條件下可進下一階段」。

| 反模式                     | 風險                   | 替代做法                           |
| -------------------------- | ---------------------- | ---------------------------------- |
| deploy workflow 不等 test  | 測試紅燈仍可能發布     | 用 required checks 或 `needs`      |
| CI 與本機命令不同          | 本機通過但 CI 失敗     | 把命令收斂到 Makefile / npm script |
| 測試與發布各自 build       | 測試產物與發布產物漂移 | 用 artifact handoff                |
| 看到紅燈直接重跑           | 掩蓋 flaky 或環境問題  | 先看失敗 log，再決定是否重跑       |
| 用 `--no-verify` 或跳過 CI | 把局部問題帶進主線     | 修掉 gate 或明確記錄例外           |

## Tripwire

Tripwire 的責任是提示什麼時候 workflow 結構需要重切，讓團隊從局部 patch 回到 gate 設計。

- 測試紅燈仍發布：把 deploy gate 顯式化，使用 required checks 或同 workflow `needs`。
- 本機常常重現不出 CI：把命令收斂到 `Makefile` 或 `npm scripts`，減少 workflow 專屬命令。
- 測試常因 artifact 缺失失敗：建立 artifact handoff，讓測試與發布使用同一份產物。
- workflow 說明與實作分叉：同步更新 workflow 文件與 YAML，讓維護入口保持可信。

## 下一步路由

- CI 紅燈處理流程：讀 [CI 失敗到修復發布流程](../github-actions-failure-flow/)。
- 靜態站部署案例：讀 [本 blog 專案部署](../blog-project-deploy/)。
- 可靠性層的 release gate：讀 [6.8 Release Gate 與變更節奏](/backend/06-reliability/release-gate/)。
