---
title: "Desktop client 簽章、公證與自動更新流程"
date: 2026-05-21
description: "說明 Flutter Desktop、Electron、Tauri 等桌面客戶端 CI/CD 如何處理 installer、code signing、notarization、update feed 與 rollback channel"
tags: ["CI", "CD", "desktop", "signing", "update"]
weight: 1
---

Desktop client 發布流程的核心責任是讓多平台安裝包可信、可更新、可回復。桌面應用和 web 不同，使用者會下載 installer 或 package 到本機；CI/CD 需要處理平台差異、code signing、notarization、auto-update feed、delta package 與多版本共存。

## 流程定位

Desktop client 的風險集中在作業系統信任鏈與更新通道。macOS、Windows、Linux 對簽章、安裝包格式與安全提示的要求不同；同一份 source 通常會產生多個平台 artifact，因此 workflow 要把平台 matrix、簽章 secret 與 [Release Channel](/ci/knowledge-cards/release-channel/) 拆清楚。

| 階段     | 責任                                                                  | 判讀訊號                         |
| -------- | --------------------------------------------------------------------- | -------------------------------- |
| Build    | 產生 `.dmg`、`.pkg`、`.msi`、AppImage 等                              | 平台 matrix 是否完整             |
| Signing  | 建立 OS 信任                                                          | certificate、timestamp、keychain |
| Notarize | 通過 macOS 公證或平台審查                                             | staple、gatekeeper 是否通過      |
| Release  | 發布到 channel 或 download page                                       | stable / beta / internal 分流    |
| Update   | 推送 [Update Feed](/ci/knowledge-cards/update-feed/) 或 delta package | feed 簽章、版本相容、回退策略    |
| Recovery | hotfix、rollback channel、停用更新                                    | 是否能阻止錯誤版本擴散           |

Build 階段負責產生平台專屬 artifact。Flutter Desktop、Electron 與 Tauri 的輸出格式不同，但共同要求是每個 artifact 都能追到 commit、workflow run 與 dependency lock。

Signing 階段負責讓 OS 信任安裝包。Windows code signing certificate、macOS Developer ID、timestamp server 與 Linux package signing key 都是發布能力；secret 應放在受控環境，並限制能觸發 signing job 的分支與 reviewer。

Notarize 階段負責處理 macOS 信任 gate。macOS app 即使完成簽章，也常需要 notarization 與 stapling；CI 要把 notarization log 保存下來，否則使用者看到 Gatekeeper 警告時很難回溯。

Release 階段負責把 artifact 放到正確 [Release Channel](/ci/knowledge-cards/release-channel/)。Internal、beta、stable 與 enterprise channel 的 gate 不同；CI/CD 要避免未審核的 beta artifact 被 stable feed 取用。

Update 階段負責維持升級路徑。[Update Feed](/ci/knowledge-cards/update-feed/)、delta package、signature、minimum supported version 與 rollback channel 要一起設計；更新壞掉時，使用者可能卡在需要人工修復的版本。

Recovery 階段負責止血。桌面客戶端常用方式是撤下 update feed、發布 hotfix、切換 rollback channel、停用 remote feature 或要求最低版本；每種方式都依賴 app 內建相容支援。

## 平台差異判讀

平台差異判讀的責任是讓 CI matrix 對應真實發布風險。桌面發布除了確認「三平台都 build 成功」，還要確認每個平台的安裝、啟動、更新與卸載行為。

| 平台    | 高風險點                                     | 驗證方向                           |
| ------- | -------------------------------------------- | ---------------------------------- |
| macOS   | Developer ID、notarization、universal binary | Gatekeeper、arm64 / x64 啟動       |
| Windows | Authenticode、SmartScreen、installer 權限    | 安裝、更新、卸載、權限提示         |
| Linux   | AppImage、deb、rpm、repository key           | dependency、desktop entry、sandbox |

這張表的用途是避免平台細節被單一「desktop build」欄位抹平。每個 OS 的失敗代價不同，CI 應保留平台專屬 gate。

## Update feed 契約

[Update Feed](/ci/knowledge-cards/update-feed/) 契約的責任是讓已安裝使用者安全升級。Auto-update 需要簽章、版本比較、channel、最低版本與回退策略共同成立，才能讓新版本 URL 進入 feed。

1. Feed 只指向已簽章且已驗證的 artifact。
2. Stable feed 只接收 stable release，beta feed 只接收 beta release。
3. App 啟動時能處理 feed 暫時不可用。
4. Delta update 失敗時能 fallback 到 full installer。
5. 錯誤版本要能從 feed 撤下，並讓未更新使用者停止取得。
6. 已更新使用者要有 hotfix 或 rollback channel。

這些條件讓更新通道具備操作性。若 app 只知道「看到新版就下載」，錯誤 feed 會把事故放大到所有啟動中的使用者。

## 下一步路由

- Desktop 部署總覽：回 [Desktop Client 部署 CI/CD](../)。
- App 發布通用觀念：讀 [App 簽章、商店審核與分批發布流程](../../app-deploy/signing-store-rollout-flow/)。
- 簽章術語：讀 [App Signing](/ci/knowledge-cards/app-signing/)。
