---
title: "App 簽章、商店審核與分批發布流程"
date: 2026-05-21
description: "說明 mobile / desktop app CI/CD 如何處理 signing secret、store review、phased rollout、hotfix 與多版本共存"
tags: ["CI", "CD", "app", "signing", "rollout"]
weight: 1
---

App 發布流程的核心責任是把可安裝 artifact 送進受控發行通道。App 與 web 最大差異是使用者裝置會長期保留舊版本；CI/CD 需要把 build number、簽章、審核、分批發布與服務端相容性一起管理。

## 流程定位

App 部署的風險集中在不可變 artifact 與外部 gate。IPA、APK、AAB 或桌面安裝包一旦被使用者安裝，團隊需要靠 hotfix、remote config、kill switch 或服務端相容性止血；store review、簽章憑證與 phased rollout 會決定錯誤版本能否快速收斂。

| 階段                                                      | 責任                               | 判讀訊號                          |
| --------------------------------------------------------- | ---------------------------------- | --------------------------------- |
| Version                                                   | 管理 version 與 build number       | 每次上傳是否可唯一追溯            |
| [App signing](/ci/knowledge-cards/app-signing/)           | 產生可信 artifact                  | certificate / keystore 是否安全   |
| Test                                                      | 驗證裝置與 OS matrix               | 高風險裝置、權限與離線情境        |
| Store review                                              | 通過商店或企業發行 gate            | 審核時間、拒審理由、metadata      |
| [Rollout strategy](/ci/knowledge-cards/rollout-strategy/) | 控制使用者取得比例                 | crash-free rate、conversion、回報 |
| Recovery                                                  | hotfix、remote config、kill switch | 是否能處理已安裝版本              |

Version 階段負責讓 artifact 可追溯。App crash report、客服回報與 store console 都依賴 version / build number；版本號對應 commit 與 workflow run 時，事故定位可以直接回到發布紀錄。

[App signing](/ci/knowledge-cards/app-signing/) 階段負責維持發布信任鏈。簽章憑證、provisioning profile、keystore 與 notarization credential 都是發布能力；它們要用 secret 管理、權限隔離、輪替與備援流程保護。

Test 階段負責覆蓋目標裝置條件。App 測試要依實際使用者分佈選擇 OS、裝置、權限狀態、網路條件與升級路徑；只跑 emulator smoke test，通常抓不到真機權限、背景限制或升級資料遷移問題。

Store review 階段負責處理外部 gate。審核可能因 metadata、隱私揭露、權限使用、付款政策或 crash 被拒；CI/CD 文件要記錄誰能處理審核回覆、哪些變更需要重新提交。

[Rollout strategy](/ci/knowledge-cards/rollout-strategy/) 階段負責控制新版本擴散速度。分批發布的觀察指標包含 crash rate、登入、購買、同步、推播與核心流程完成率；達到停損條件時應暫停 rollout，先讓已受影響範圍維持可控。

Recovery 階段負責處理已安裝版本。App 常見止血工具是 remote config、feature flag、kill switch、server-side compatibility、hotfix build 與要求使用者升級；每個工具都要在事故前實作，事故時才有路可走。

## 多版本共存契約

多版本共存是 App 發布的基本前提。後端 API、資料格式、推播 payload 與 remote config 都要支援一段時間的新舊 client，因為使用者更新節奏不受團隊完全控制。

| 契約           | 判讀問題                          | 常見風險                     |
| -------------- | --------------------------------- | ---------------------------- |
| API response   | 舊 app 看到新增欄位是否能正常處理 | 刪欄位或改語意造成舊版 crash |
| Auth / session | 更新前後 token 是否仍可使用       | 強制登出或登入狀態破壞       |
| Local storage  | app upgrade 是否能遷移本機資料    | 新版寫入後舊版讀取契約失效   |
| Push payload   | 舊版是否能忽略未知 action         | 推播點擊進入不存在頁面       |
| Remote config  | config key 是否有預設值與版本條件 | 未支援版本收到新功能開關     |

這些契約要在 CI 或 release checklist 裡被驗證。若只靠後端「盡量相容」，App 發布失敗會在使用者更新後才暴露，回復成本會比 web 或後端高。

## Release checklist

Release checklist 的責任是把外部 gate 與內部 gate 接起來。App 發布牽涉商店、憑證、客服、行銷與後端相容，因此 checklist 應該是流程契約，不只是提醒清單。

1. 確認 version、build number、commit 與 artifact 對應。
2. 確認 signing secret、profile 或 keystore 仍有效。
3. 跑 unit、UI、device matrix 與 upgrade test。
4. 檢查 API / remote config / push payload 多版本相容。
5. 上傳 internal / beta track，跑 smoke test。
6. 提交 store review，記錄審核狀態。
7. 用 phased rollout 推進，觀察 crash-free rate 與核心指標。
8. 觸發停損條件時暫停 rollout、關閉功能或準備 hotfix。

這個順序讓 App 發布從「把包丟上去」變成可觀測流程。每一步都對應一個失敗路由，事故時能知道下一個可執行動作。

## 下一步路由

- App 部署總覽：回 [App 部署 CI/CD](../)。
- 簽章概念：讀 [App Signing](/ci/knowledge-cards/app-signing/)。
- Gate 原理：讀 [CI gate 與 workflow 邊界](../../ci-gate-workflow-boundary/)。
