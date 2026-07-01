---
title: "Chrome Extension 上架記錄"
date: 2026-05-21
draft: true
description: "記錄 Chrome extension 上架 Chrome Web Store 的過程"
tags: ["chrome-extension", "chrome-web-store", "manifest-v3", "publishing", "tooling"]
---

_待填：這次開發的是什麼套件、解什麼問題、給誰用（自用 / 團隊 / 公開）。一句話交代 context，後面章節才知道判讀前提。_

---

## 開發環境與專案結構

_待填：用什麼開發（純 JS / TypeScript / 有沒有 build 工具如 Vite）、目錄怎麼擺、有沒有用 framework。_

---

## Manifest V3 基礎

_待填：`manifest.json` 的核心欄位 — `manifest_version` / `name` / `version` / `description` / `permissions` / `host_permissions`。記下實際填的值與當下不確定的地方。_

---

## 擴充元件架構

_待填：用到哪些元件、各自的責任 — background service worker、content script、popup、options page、side panel 等。記下元件之間怎麼溝通（message passing / storage）。_

---



---

## 打包

_待填：打包成 zip 的方式（手動 / 腳本）、要排除哪些檔案、version 號規則。_

---

## 上架 Chrome Web Store

### 開發者帳號與費用



Chrome Web Store 開發者帳號：一次性註冊費 USD $5
但是註冊後會讓你確認你是營利用的帳戶還是個人開發工具用的非營利用途，問AI是說之後可以再切換，因為如果選營利用帳戶需要上傳個人文件或者公司證明，加上大約一個月的審核，我是先選擇非營利的帳戶。

所有可以獲利的行為都算是營利帳戶，無論是訂閱，一次性付費，甚至是贊助連結，都算是營利，比較特別的是，最常見的 google ads 是禁止放在 extension 裡面的
[developer.chrome.com](https://developer.chrome.com/docs/webstore/program-policies/ads)

### Store listing 填寫

_待填：商店頁面要填的欄位 — 詳細描述、分類、語言、視覺資產（icon / 截圖 / 宣傳圖）的尺寸需求、單一用途聲明。哪些欄位事後難改。_

### 權限與隱私聲明

_待填：每個 permission 的使用理由（justification）、資料用途聲明、隱私權政策連結。這段通常最容易卡審核，記下實際填法。_

### 審核與駁回處理

_待填：提交後的審核狀態流轉、實際等待時間。被駁回的話記駁回理由原文 + 對應修正 + 重新提交結果。_

### 發布設定

_待填：可見性選項（公開 / 不公開 unlisted / 私人）、發布範圍、發布後多久生效。_

---

## 版本更新流程

_待填：改版後重新打包、更新是否需要重新審核、使用者端多久收到更新。_
