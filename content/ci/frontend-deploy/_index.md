---
title: "前端部署 CI/CD"
date: 2026-05-06
description: "整理靜態站、SPA、CDN、preview environment 與前端 artifact 的 CI/CD 注意事項"
tags: ["CI", "CD", "frontend", "deployment"]
weight: 10
---

前端部署 CI/CD 的核心責任是把瀏覽器可執行的靜態產物安全交付到 hosting、CDN 或 [preview environment](/ci/knowledge-cards/preview-environment/)。前端部署常見輸出是 HTML、CSS、JavaScript、圖片與搜尋索引；它的風險集中在 build [artifact](/ci/knowledge-cards/artifact/)、路由、cache、環境變數與使用者可見回歸。

## 場域定位

前端部署和後端部署的差異在於 runtime 責任位置。前端產物通常在 build time 完成大部分工作，發布後由 browser、CDN 或 static hosting 提供服務；後端服務則要在 runtime 處理連線、資料庫、migration、狀態與 rollback。

| 面向                                                        | 前端部署常見責任                      | 判讀訊號                          |
| ----------------------------------------------------------- | ------------------------------------- | --------------------------------- |
| Build                                                       | bundle、static site、asset hashing    | build 是否可重現                  |
| Test                                                        | browser regression、a11y、layout      | Playwright / visual diff 是否通過 |
| [Artifact](/ci/knowledge-cards/artifact/)                   | static files、search index、sourcemap | 測試與發布是否同一份產物          |
| Deploy                                                      | hosting、CDN、Pages、preview URL      | cache invalidation 與路由是否正確 |
| [Rollback Strategy](/ci/knowledge-cards/rollback-strategy/) | 回退前一版 static artifact            | 是否保留可回復版本                |

Build 階段負責產生 browser 實際會執行的內容。真實服務常見訊號是 bundle size、asset hash、base URL、環境變數與 static route 是否穩定；若 build 只能在開發機成功，CI 就要把 Node 版本、package lock、build command 與環境變數收斂成固定入口。

Test 階段負責驗證使用者可見行為。前端常見測試包含 component test、browser regression、accessibility check 與 layout check；測試應盡量靠近 production artifact，讓 dev server 的寬鬆行為不會蓋掉實際部署問題。

[Artifact](/ci/knowledge-cards/artifact/) 階段負責保存可發布產物。靜態檔、搜尋索引與 sourcemap 都可能影響使用者體驗與除錯能力；測試與發布共用同一份 artifact，可以避免「測試通過的是 A，發布出去的是 B」的漂移。

Deploy 階段負責把 artifact 放到 hosting 或 CDN。真實風險通常集中在 HTML cache、asset cache、SPA fallback、preview URL 與 production domain 是否對齊。

[Rollback Strategy](/ci/knowledge-cards/rollback-strategy/) 階段負責讓上一個可用 artifact 能重新服務使用者。前端 rollback 通常比後端快，但若 build time 環境變數、資料 schema 或 CDN cache 已變更，回退仍需要驗證頁面路由與 API 相容性。

## 常見注意事項

- CDN cache 要和 asset hash、HTML cache policy 分開看。
- Preview environment 要能對應 PR，讓 reviewer 看到真實 build。
- 前端測試要跑在 production-like artifact 上，避免 dev server 行為遮蔽問題。
- 環境變數若在 build time 注入，重新發布才會生效。
- SPA route 需要 fallback 設定，靜態站 route 需要檔案路徑與 base URL 對齊。

## 下一步路由

- 本 blog 的靜態站案例：讀 [本 blog 專案部署](../blog-project-deploy/)。
- Gate 原理：讀 [CI gate 與 workflow 邊界](../ci-gate-workflow-boundary/)。
- 失敗處理：讀 [CI 失敗到修復發布流程](../github-actions-failure-flow/)。
