---
title: "前端 artifact 與 preview deployment 流程"
date: 2026-05-21
description: "說明前端 CI/CD 如何用同一份靜態 artifact 串起 build、browser test、preview environment、CDN 發布與 rollback"
tags: ["CI", "CD", "frontend", "artifact", "preview"]
weight: 1
---

前端 artifact 流程的核心責任是讓測試、預覽與正式發布使用同一份靜態產物。前端部署常見輸出是 HTML、CSS、JavaScript、圖片、sourcemap 與搜尋索引；這些產物一旦被重新 build，就可能受到環境變數、依賴版本、base URL 或 framework 設定影響，因此 CI/CD 需要把「產生一次、驗證一次、推進同一份」當成主線。

## 流程定位

前端部署的風險集中在 build time。後端服務可以在 runtime 讀取設定、檢查資料庫與逐步接流量；前端靜態產物多半在 build 階段就把 route、asset path、環境變數與 feature flag 預先寫入 bundle。CI/CD 的判讀重點因此是「被部署的 artifact 是否就是已驗證的那一份」。

| 階段                                                            | 責任                                 | 判讀訊號                               |
| --------------------------------------------------------------- | ------------------------------------ | -------------------------------------- |
| Build                                                           | 產生 production-like static artifact | lockfile、Node 版本、base URL 是否固定 |
| Browser test                                                    | 驗證使用者可見行為                   | 測試是否跑在 build 後 artifact         |
| [Preview environment](/ci/knowledge-cards/preview-environment/) | 讓 PR 變更可被 reviewer 實際操作     | preview URL 是否對應 commit / PR       |
| Deploy                                                          | 推進到 hosting、Pages 或 CDN         | HTML cache、asset cache、SPA fallback  |
| [Rollback strategy](/ci/knowledge-cards/rollback-strategy/)     | 重新服務上一份已知可用 artifact      | 舊 artifact、cache purge 與 API 相容性 |

Build 階段負責建立可驗證產物。真實服務裡，`npm run dev` 成功不代表 production build 能成功；CI 應固定 Node 版本、package manager、lockfile、build command 與必要環境變數，讓 artifact 可以從乾淨環境重建。

Browser test 階段負責驗證使用者實際會看到的頁面。Playwright、visual diff、a11y check 或 smoke test 應盡量對 build 後的靜態站執行，避免 dev server 的 fallback、熱更新或寬鬆路由遮蔽 production 問題。

[Preview environment](/ci/knowledge-cards/preview-environment/) 階段負責把 PR 變成可操作畫面。Preview URL 要能追到 PR、commit 與 workflow run，reviewer 才能把畫面問題回報到正確版本；preview 也要隔離 production 資料與 credential，避免預覽環境變成未受控入口。

Deploy 階段負責把 artifact 放到 hosting 或 CDN。前端部署失敗常出現在 cache policy、SPA fallback、base URL、static route 與 sourcemap 權限；deploy 成功只代表檔案上傳完成，仍需要檢查入口頁、核心路由與 asset 是否能從公開網址載入。

[Rollback strategy](/ci/knowledge-cards/rollback-strategy/) 階段負責恢復上一份可用靜態產物。前端 rollback 表面上只是切回舊檔案，但若 API schema、build time config 或 CDN cache 已經變動，舊頁面仍可能呼叫不相容的後端，因此 rollback 要搭配 smoke test 與 cache purge。

## 常見失敗路由

前端 CI 紅燈要先判斷失敗在 build、browser test、preview 還是 production deploy。不同層的修復入口不同；把所有紅燈都當成「重跑 workflow」會掩蓋 artifact 漂移與 cache 問題。

| 訊號                         | 判讀                                   | 下一步                                       |
| ---------------------------- | -------------------------------------- | -------------------------------------------- |
| 本機 dev 正常、CI build 失敗 | production build 條件與本機不同        | 回本機跑 CI 同一條 build command             |
| 測試通過、上線後空白頁       | 測試沒有覆蓋 production artifact / URL | 對已部署 artifact 跑 smoke test              |
| Preview URL 顯示舊畫面       | preview cache 或 commit 對應錯位       | 檢查 preview artifact 與 workflow run        |
| 只有深層路由 404             | SPA fallback 或 static route 設定錯誤  | 檢查 hosting rewrite / base URL              |
| rollback 後仍看到新版        | CDN / browser cache 尚未失效           | 檢查 cache invalidation 與 HTML cache policy |

這張表的用途是縮短定位時間。前端部署問題常被誤判成「CDN 壞掉」或「瀏覽器快取」，但更常見的根因是 build artifact、route 與 cache policy 的契約沒有明確寫進 pipeline。

## 最小 workflow 骨架

前端 workflow 應把 build、test、preview 與 deploy 的資料流顯性化。下面是概念骨架，重點在 artifact handoff 的方向，特定平台語法是次要的。

```yaml
jobs:
  build:
    steps:
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-artifact
        with:
          name: web-dist
          path: dist

  test:
    needs: build
    steps:
      - uses: actions/download-artifact
        with:
          name: web-dist
      - run: npm run test:e2e:static

  preview:
    needs: test
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/download-artifact
        with:
          name: web-dist
      - run: npm run deploy:preview

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/download-artifact
        with:
          name: web-dist
      - run: npm run deploy:production
```

這個骨架讓 deploy 依賴 test，也讓 test 與 deploy 使用 build job 產生的同一份產物。若專案需要在不同環境注入設定，要明確區分 build time config 與 runtime config，避免同一份 artifact 被重新 build 成另一份內容。

## Tripwire

Tripwire 的責任是提醒前端 workflow 需要重切。當同一類問題反覆出現，局部補命令通常只能暫時遮住資料流錯位。

- Preview 常和 production 不一致：把 preview 改成部署 build artifact，讓 preview job 沿用同一份產物。
- E2E 測試通過但 production 壞：把 E2E 改到 static artifact 或 production-like server 上執行。
- rollback 依賴人工找舊 commit：保留 release artifact 與版本索引，讓回退指向明確產物。
- CDN cache 問題反覆出現：把 HTML cache、asset cache 與 purge 策略寫進 deploy checklist。

## 下一步路由

- 前端部署總覽：回 [前端部署 CI/CD](../)。
- Gate 原理：讀 [CI gate 與 workflow 邊界](../../ci-gate-workflow-boundary/)。
- 本 blog 靜態站案例：讀 [本 blog 專案部署](../../blog-project-deploy/)。
