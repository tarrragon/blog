---
title: "CI/CD：驗證與發布 gate、artifact、失敗到修復的流程，以及各部署場域的差異"
date: 2026-05-06
slug: "ci"
description: "要設計變更的驗證與發布 gate、判讀 CI 失敗到修復發布的流程、處理 flaky test 與 artifact 的可重播性，或比較前端、後端、App、桌面、容器、Serverless、IaC 與套件發布的部署流程時讀"
tags: ["CI", "CD", "教學", "workflow"]
weight: 3
aliases: ["/ci/"]
---

CI/CD 教學的核心目標是把「變更如何被驗證、建置、交付」寫成可重播流程。[CI Pipeline](/devops/ci/knowledge-cards/ci-pipeline/) 負責驗證變更是否可信，[CD Pipeline](/devops/ci/knowledge-cards/cd-pipeline/) 負責把可信 [artifact](/devops/ci/knowledge-cards/artifact/) 交付到目標環境；兩者共享 gate、artifact、環境與回復路徑，但不同部署場域的細節差異很大。

CI/CD 的責任是提供一致的判讀入口。當 workflow 顯示失敗時，團隊需要能快速判斷是 lint、test、build、package、[Artifact Handoff](/devops/ci/knowledge-cards/artifact-handoff/)、deploy 還是 [Rollback Strategy](/devops/ci/knowledge-cards/rollback-strategy/) 階段出問題，並知道下一步該回到本機重現、修正、重新提交，還是暫停發布。

### [前置知識卡片](/devops/ci/knowledge-cards/)

用原子化卡片整理 [Artifact](/devops/ci/knowledge-cards/artifact/)、[Required Checks](/devops/ci/knowledge-cards/required-checks/)、[Artifact Handoff](/devops/ci/knowledge-cards/artifact-handoff/)、[Environment Protection](/devops/ci/knowledge-cards/environment-protection/)、[Preview Environment](/devops/ci/knowledge-cards/preview-environment/)、[Rollout Strategy](/devops/ci/knowledge-cards/rollout-strategy/)、[Rollback Strategy](/devops/ci/knowledge-cards/rollback-strategy/)、[Migration](/devops/ci/knowledge-cards/migration/)、[Backfill](/devops/ci/knowledge-cards/backfill/)、[Image Digest](/devops/ci/knowledge-cards/image-digest/)、[Release Channel](/devops/ci/knowledge-cards/release-channel/)、[Infrastructure Drift](/devops/ci/knowledge-cards/infrastructure-drift/)、[Function Alias](/devops/ci/knowledge-cards/function-alias/) 與 [Flaky Test](/devops/ci/knowledge-cards/flaky-test/) 等核心術語。流程文章專注情境判讀與決策順序，術語背景交由卡片維持一致。

## 學習路線

| 章節                                                                   | 主題                       | 核心責任                                        |
| ---------------------------------------------------------------------- | -------------------------- | ----------------------------------------------- |
| [CI 失敗到修復發布流程](/devops/ci/github-actions-failure-flow/)       | Failure routing            | 從失敗 workflow 判斷下一步路由                  |
| [CI gate 與 workflow 邊界](/devops/ci/ci-gate-workflow-boundary/)      | Workflow boundary          | 說明 required checks、needs 與 artifact handoff |
| [前端部署 CI/CD](/devops/ci/frontend-deploy/)                          | Frontend deployment        | 靜態站、SPA、CDN 與 preview environment         |
| [後端部署 CI/CD](/devops/ci/backend-deploy/)                           | Backend deployment         | API / worker 的 migration、rollout 與 rollback  |
| [App 部署 CI/CD](/devops/ci/app-deploy/)                               | App deployment             | mobile / desktop app 的簽章、審核與版本發布     |
| [Docker / Image 部署 CI/CD](/devops/ci/docker-deploy/)                 | Image deployment           | image build、scan、tag、registry 與 runtime     |
| [Serverless 部署 CI/CD](/devops/ci/serverless-deploy/)                 | Serverless deployment      | function 版本、權限、事件觸發與 alias rollback  |
| [Data Pipeline 部署 CI/CD](/devops/ci/data-pipeline-deploy/)           | Data pipeline deployment   | schema 相容、backfill、checkpoint 與 rerun      |
| [IaC / Platform 部署 CI/CD](/devops/ci/iac-platform-deploy/)           | IaC deployment             | plan/apply、drift、state 與環境治理             |
| [Desktop Client 部署 CI/CD](/devops/ci/desktop-client-deploy/)         | Desktop client deployment  | 桌面安裝包簽章、公證、更新通道與回退            |
| [Package / Library Release CI/CD](/devops/ci/package-library-release/) | Package release deployment | SDK / NPM / PyPI 的版本、契約與發版供應鏈治理   |
| [本 blog 專案部署](/devops/ci/blog-project-deploy/)                    | Project case               | Hugo、Pagefind、GitHub Pages 與本專案 workflow  |
| [Artifact 與可重播性](/devops/ci/artifact-reproducibility/)            | Artifact reproducibility   | 讓 CI 產物能被測試與發布共用                    |
| [Flaky test 治理](/devops/ci/flaky-test-governance/)                   | Flaky governance           | 把不穩定測試從雜訊變成可處理任務                |

學習路線先從失敗處理與 gate 邊界開始，因為 CI/CD 的價值會在紅燈時最清楚。當讀者能判讀失敗位置與下一步路由，再依部署場域進入前端、後端、App、Docker 或本 blog 專案案例。

## 與其他教學的分工

CI/CD 教學負責日常工作流程與部署場域差異，Backend 可靠性模組負責系統層可靠性判斷。讀者想知道 workflow 失敗後怎麼修、發布 gate 怎麼切、前端與後端部署流程差在哪裡，讀本系列；想知道 CI 在 release gate、SLO、load test 與可靠性治理中的位置，回到 [模組六：可靠性驗證流程](/backend/06-reliability/)。

Go、Python 或其他語言教材只需要保留測試寫法與本機命令。當內容開始涉及 workflow event、required checks、preview deployment、container registry、mobile signing、artifact、cache 或 branch protection，就應該移到本系列，讓不同語言共用同一套 CI/CD 操作語意。

## 判讀訊號

- GitHub Actions 紅燈後，不知道該看哪個 job。
- 本機測試通過，但 CI 失敗。
- 測試失敗後仍有部署 workflow 啟動。
- deploy 失敗時，團隊分不清 build artifact、部署權限與測試 gate 的責任。
- 前端、後端、App 與 Docker 使用同一套發布說明，導致場域細節混在一起。
- workflow 只有命令清單，沒有說明失敗後的處理路由與部署場域邊界。

## 下一步路由

- 想處理 GitHub Actions 紅燈：讀 [CI 失敗到修復發布流程](/devops/ci/github-actions-failure-flow/)。
- 想理解 CI gate 原理：讀 [CI gate 與 workflow 邊界](/devops/ci/ci-gate-workflow-boundary/)。
- 想理解前端部署：讀 [前端部署 CI/CD](/devops/ci/frontend-deploy/)。
- 想理解後端部署：讀 [後端部署 CI/CD](/devops/ci/backend-deploy/)。
- 想理解 App 發布：讀 [App 部署 CI/CD](/devops/ci/app-deploy/)。
- 想理解 Docker / image 流程：讀 [Docker / Image 部署 CI/CD](/devops/ci/docker-deploy/)。
- 想理解 Serverless 發布：讀 [Serverless 部署 CI/CD](/devops/ci/serverless-deploy/)。
- 想理解資料處理任務發布：讀 [Data Pipeline 部署 CI/CD](/devops/ci/data-pipeline-deploy/)。
- 想理解 IaC / 平台變更發布：讀 [IaC / Platform 部署 CI/CD](/devops/ci/iac-platform-deploy/)。
- 想理解 Flutter/Electron/Tauri 類客戶端發布：讀 [Desktop Client 部署 CI/CD](/devops/ci/desktop-client-deploy/)。
- 想理解 SDK / NPM / PyPI 發版：讀 [Package / Library Release CI/CD](/devops/ci/package-library-release/)。
- 想維護本 blog 的 workflow：讀 [本 blog 專案部署](/devops/ci/blog-project-deploy/)。
- 想讓測試與發布共用同一份產物：讀 [Artifact 與可重播性](/devops/ci/artifact-reproducibility/)。
- 想治理不穩定測試：讀 [Flaky test 治理](/devops/ci/flaky-test-governance/)。
- 想理解可靠性層的 CI 分層：讀 [6.1 CI pipeline](/backend/06-reliability/ci-pipeline/)。
- 想理解發布 gate：讀 [6.8 Release Gate 與變更節奏](/backend/06-reliability/release-gate/)。
- 想理解 infra 變更的 plan / apply 流程怎麼走 CI：讀 [Infra 走 PR 流程與自動化護欄](/devops/infra/07-infra-as-pr/)。
