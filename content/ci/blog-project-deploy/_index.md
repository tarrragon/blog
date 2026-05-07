---
title: "本 blog 專案部署"
date: 2026-05-06
description: "記錄本 blog 專案的 Hugo、Pagefind、GitHub Pages 與 GitHub Actions 部署流程，作為專案維護參考"
tags: ["CI", "CD", "GitHub Actions", "blog維護"]
weight: 20
---

本 blog 專案部署是前端靜態站部署的一個具體案例。這個資料夾只記錄本專案實際使用的 Hugo、Pagefind、Playwright、GitHub Pages 與 Claude workflow，不把這些細節當成所有 CI/CD 場域的通用規則。

## 專案定位

本專案的部署產物是靜態網站。Hugo 負責產生 HTML，Pagefind 負責產生搜尋索引，GitHub Pages 負責 hosting，Playwright 負責驗證搜尋與版面行為。

| 文件                                                 | 責任                                       |
| ---------------------------------------------------- | ------------------------------------------ |
| [GitHub Actions workflow](github-actions-workflows/) | 記錄本專案 `.github/workflows/` 的實際設定 |

## 與通用 CI/CD 的關係

本資料夾是實例層。通用 gate 原理、不同部署場域差異與失敗處理流程放在上層文章；本資料夾只回答「這個 blog 專案現在怎麼部署、失敗時要看哪裡」。術語定義統一回連 [CI 知識卡片](/ci/knowledge-cards/)。

## 下一步路由

- 本專案 workflow：讀 [GitHub Actions workflow](github-actions-workflows/)。
- 前端部署通用注意事項：讀 [前端部署 CI/CD](../frontend-deploy/)。
- CI gate 原理：讀 [CI gate 與 workflow 邊界](../ci-gate-workflow-boundary/)。
- Markdown CI 規則：讀 [Blog Markdown 寫作規範與 mdtools 檢查](/posts/markdown-writing-spec/)。
