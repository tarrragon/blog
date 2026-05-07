---
title: "Desktop Client 部署 CI/CD"
date: 2026-05-06
description: "整理桌面客戶端（Flutter / Electron / Tauri）的打包、簽章、公證、更新與回退流程"
tags: ["CI", "CD", "desktop", "client"]
weight: 17
---

Desktop Client 部署 CI/CD 的核心責任是把可安裝客戶端安全交付到使用者裝置，並維持可更新與可回退能力。它和 web 發布不同，重點在安裝包簽章、公證、更新通道與多平台相容。

## 場域定位

Desktop client 常見於 Flutter Desktop、Electron、Tauri。部署流程通常要分平台建置（macOS、Windows、Linux），並處理安裝體驗、更新節奏與版本共存。

| 面向     | Desktop client 部署常見責任           | 判讀訊號             |
| -------- | ------------------------------------- | -------------------- |
| Build    | platform-specific bundle / installer  | 各平台產物是否可重現 |
| Signing  | code signing、notarization、timestamp | 安裝與啟動是否受信任 |
| Release  | channel、staged rollout、notes        | 更新節奏是否可控     |
| Update   | auto-update feed、delta package       | 升級是否穩定可回復   |
| Recovery | hotfix package、rollback channel      | 失敗時是否可快速回退 |

## 常見注意事項

- 不同 OS 的簽章與公證流程需分開治理。
- Auto-update 要有版本相容策略與 fallback feed。
- 崩潰回報與更新成功率應列為發布後 gate。
- 若與 Flutter App 共用程式碼，要明確區分 mobile 與 desktop 的發布管線。

## 下一步路由

- 行動與客戶端通用觀念：讀 [App 部署 CI/CD](../app-deploy/)。
- 簽章治理：讀 [App Signing](/ci/knowledge-cards/app-signing/) 與 [Secret Management](/backend/knowledge-cards/secret-management/)。
- 失敗處理：讀 [CI 失敗到修復發布流程](../github-actions-failure-flow/)。
