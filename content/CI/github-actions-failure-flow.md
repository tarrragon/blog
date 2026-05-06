---
title: "CI/CD 失敗到修復發布流程"
date: 2026-05-06
description: "說明 CI/CD 測試、建置或發布失敗後如何判讀、重現、修復、重新觸發與恢復發布"
tags: ["CI", "GitHub Actions", "workflow", "發布"]
weight: 1
---

CI/CD 失敗處理的核心責任是把紅燈轉成明確的下一步路由。紅燈本身是驗證或交付層的訊號；工程流程要做的是找出失敗層、重現同一個條件、修正後重新讓 [CI Pipeline](/ci/knowledge-cards/ci-pipeline/) 證明變更可發布。

## 失敗後先看什麼

失敗後第一步是定位 workflow 與 job。CI/CD 系統會把一次 push、pull request、tag 或 release 拆成多個 workflow，每個 workflow 下面又有多個 job；真正的下一步取決於是哪一層失敗。

| 失敗位置      | 常見原因                                                              | 下一步路由                                                        |
| ------------- | --------------------------------------------------------------------- | ----------------------------------------------------------------- |
| Lint / format | 程式碼、文件或設定格式不符                                            | 回本機跑同一條 lint / format 命令                                 |
| Test          | 單元、整合、瀏覽器或裝置測試回歸                                      | 下載 report，回本機用同條件重現                                   |
| Build         | 編譯、bundle、package 或靜態產物失敗                                  | 回本機跑 production build 入口                                    |
| Package       | image、app bundle、[artifact](/ci/knowledge-cards/artifact/) 產生失敗 | 檢查版本、簽章、registry 或路徑                                   |
| Deploy        | hosting、runtime、store 或權限設定                                    | 先確認 build [artifact](/ci/knowledge-cards/artifact/) 是否已成功 |

Lint / format 失敗代表靜態契約沒有通過。常見情境是程式格式、文件格式、型別檢查、schema 或設定規則不符合規範。這類失敗的修復路徑通常很短：讀錯誤訊息、修正來源、必要時跑 formatter，再提交修正。

Test 失敗代表某個行為或契約沒有符合預期。這類失敗要先看 report、screenshot、trace、device log 或 error context，確認是功能真的回歸、測試假設過期，還是測試環境缺少 production-like artifact。直接改測試前，要先確認測試原本守的是哪個使用者或系統行為。

Build 失敗代表 pipeline 尚未產生可部署產物。這類失敗通常來自編譯錯誤、bundle 設定、依賴版本、環境變數、template 或資源路徑。修復時以專案定義的 production build 命令作為最小重現入口。

Deploy 失敗代表發布動作沒有完成。這類失敗需要先區分 artifact 是否存在、發布通道權限是否正確、環境保護是否放行。若測試與 build 已成功，deploy 失敗多半是發布通道問題；若 artifact 沒有產生，應回到 build 或 package 階段。

## 本機重現流程

本機重現的責任是讓修復建立在同一個驗證條件上。CI 是用乾淨環境執行的一組命令；只要能在本機跑出同樣的失敗，修復就能被快速驗證。

```bash
make build
make test
make deploy-dry-run
```

Build 命令驗證 production artifact 是否能產生。這一步應該接近 CI 使用的 build 入口，避免開發模式遮蔽 production 問題。

Test 命令驗證產物或程式行為。前端可能是 browser test，後端可能是 integration / contract test，App 可能是 device test，Docker 可能是 image scan 或 smoke test。

Deploy dry-run 命令驗證發布前條件。高風險部署至少要能檢查 artifact、權限、環境與版本資訊；沒有 dry-run 的專案，也應保留對等的 preflight check。

## 修復與重新觸發

修復流程的核心是用新 commit 讓 CI 重新驗證。一般流程不需要刪掉失敗 commit，也不需要 force push；失敗 commit 留在歷史裡，後續 fix commit 會形成清楚的修復脈絡。

1. 讀失敗 job 的 log 或 artifact。
2. 在本機跑對應命令重現。
3. 修改最小必要範圍。
4. 跑同一條本機命令確認修復。
5. commit 並 push。
6. 等 GitHub Actions 重新跑。

這個流程的好處是保留可追溯性。日後再看到同類失敗，可以從 commit history 與 CI log 找到當時的判讀方式。

## 發布 gate 路由

發布 gate 的責任是把「是否進入下一階段」變成明確條件。這一頁只處理失敗後的操作路由；[required checks](/ci/knowledge-cards/required-checks/)、job `needs`、[environment protection](/ci/knowledge-cards/environment-protection/) 與 [artifact handoff](/ci/knowledge-cards/artifact-handoff/) 的設計原理，獨立放在 [CI gate 與 workflow 邊界](../ci-gate-workflow-boundary/)。

## 常見處理情境

CI 失敗但本機通過時，優先檢查環境差異。常見差異包括語言版本、套件管理器版本、缺少子模組、缺少 build artifact、測試依賴未安裝、時區或檔案大小寫差異。這類問題要把版本與建置前置條件寫進 workflow、Makefile 或 script，讓重現條件成為專案的一部分。

測試不穩定時，優先把 [Flaky Test](/ci/knowledge-cards/flaky-test/) 狀態標出來並建立 owner。短期可以隔離或重跑，長期要找到不穩定來源，例如等待條件錯誤、外部網路依賴、時間假設、測試資料不穩或動畫 transition 尚未完成。測試不穩定會降低 gate 信任度，因此它本身就是需要治理的 CI 問題。

Deploy 失敗但測試通過時，優先看 artifact 與權限。若 build output 存在且可下載，問題通常在部署通道、token permission 或 [environment protection](/ci/knowledge-cards/environment-protection/)；若 artifact 缺失，就回到 build job。

## 反模式與替代做法

| 反模式                     | 風險                     | 替代做法                           |
| -------------------------- | ------------------------ | ---------------------------------- |
| 看到紅燈直接重跑           | 掩蓋 flaky 或環境問題    | 先看失敗 log，再決定是否重跑       |
| 用 `--no-verify` 或跳過 CI | 把局部問題帶進主線       | 修掉 gate 或明確記錄例外           |
| CI 與本機命令不同          | 本機通過但 CI 失敗       | 把命令收斂到 Makefile / npm script |
| 測試直接打外部服務         | 網路與第三方狀態污染判斷 | 使用 fixture、mock 或可控環境      |

反模式的共同問題是讓 CI 失去判讀價值。CI 的目標是讓綠燈代表「這次變更在定義好的條件下可發布」。

## 最小可用流程

最小可用流程是讓每次變更都有同一條路徑。對小型靜態網站或個人 blog，先做到以下四件事，就能形成穩定發布節奏。

1. `push` 或 PR 觸發 lint / test / build。
2. production build 有單一入口。
3. 測試失敗時保留 artifact 或 report。
4. deploy 只接受測試與 build 通過後的產物。

這套流程建立後，CI 紅燈就會成為清楚的路由訊號：哪一層壞、用哪個命令重現、修完後用哪個 gate 放行。

若變更涉及後端服務，可再對照 backend 知識卡的 [Runbook](/backend/knowledge-cards/runbook/)、[Rollback Strategy](/backend/knowledge-cards/rollback-strategy/) 與 [Release Gate](/backend/knowledge-cards/release-gate/) 進一步細化故障處理順序與放行條件。

## 下一步路由

- 需要理解 CI 在可靠性模組的位置：讀 [6.1 CI pipeline](/backend/06-reliability/ci-pipeline/)。
- 需要看靜態站部署案例：讀 [本 blog 專案部署](../blog-project-deploy/)。
- 需要理解 CI gate 設計：讀 [CI gate 與 workflow 邊界](../ci-gate-workflow-boundary/)。
- 需要理解發布阻擋策略：讀 [6.8 Release Gate 與變更節奏](/backend/06-reliability/release-gate/)。
