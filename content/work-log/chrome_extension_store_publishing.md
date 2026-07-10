---
title: "Chrome Extension 從開發到上架的完整記錄"
date: 2026-05-21
draft: true
description: "記錄一個 Chrome extension 從開發環境、Manifest V3 設定到上架 Chrome Web Store 的完整流程：開發者帳號類型、Store listing、權限與隱私聲明、審核與駁回處理、版本更新，以及過程中踩到的雷。"
tags: ["chrome-extension", "chrome-web-store", "manifest-v3", "publishing", "tooling"]
---

<!-- 待填：這次開發並上架的是什麼套件、解什麼問題、給誰用（自用 / 給團隊 / 公開）。一句話交代 context，後面章節才知道判讀的前提。 -->

---

## 開發環境與專案結構

<!-- 待填：用什麼開發（純 JS / TypeScript / 有沒有 build 工具如 Vite）、目錄怎麼擺、有沒有用 framework。 -->

---

## 擴充元件架構

<!-- 待填：用到哪些元件、各自的責任 — background service worker、content script、popup、options page、side panel 等。記下元件之間怎麼溝通（message passing / storage）。 -->

---

## 開發者帳號與費用

Chrome Web Store 開發者帳號的一次性註冊費是 USD $5。

註冊後要選帳號類型：營利用途，或個人開發工具的非營利用途。營利帳戶需要上傳個人文件或公司證明，加上大約一個月的審核，所以這次先選非營利帳戶。（**待驗證**：兩種類型之後能不能互相切換，目前只有 AI 的說法、沒有實際切換過，也還沒查到官方文件的明確條文。）

判定營利的範圍比直覺寬：訂閱、一次性付費、甚至贊助連結都算營利行為。比較特別的是最常見的 Google Ads 反而禁止放進 extension 裡（見 [Chrome Web Store 廣告政策](https://developer.chrome.com/docs/webstore/program-policies/ads)）。

<!-- 待填：付款方式、註冊流程實際走完的步驟與等待時間。 -->

---

## 上架前準備

### manifest.json 檢查

<!-- 待填：manifest 版本（v3）、`manifest_version` / `name` / `version` / `description` 欄位、`permissions` 與 `host_permissions` 的範圍、上架前需要收斂掉的開發用設定。記下實際填的值與當下不確定的地方。 -->

### 視覺資產

<!-- 待填：icon 尺寸需求、商店截圖規格與數量、宣傳圖（small / marquee tile）的尺寸與是否必填。記下實際做出來的尺寸與工具。 -->

---

## 打包與上傳

<!-- 待填：打包成 zip 的方式（手動 / 腳本）、要排除哪些檔案、在 Developer Dashboard 上傳的步驟。 -->

---

## Store listing 填寫

<!-- 待填：商店頁面要填的欄位 — 詳細描述、分類、語言、單一用途聲明（single purpose）。哪些欄位事後難改、哪些影響搜尋曝光。 -->

---

## 權限與隱私聲明

<!-- 待填：每個 permission 的使用理由（justification）、資料用途聲明（data usage）、隱私權政策連結。這段通常最容易卡審核，記下實際填法。 -->

---

## 提交審核與等待

<!-- 待填：提交後的審核狀態流轉、實際等待時間、審核期間能不能改東西。 -->

---

## 駁回與修正紀錄

<!-- 待填：被駁回的話 — 駁回理由原文、對應的修正、重新提交後的結果。沒被駁回也記一句「一次過」。 -->

---

## 發布設定

<!-- 待填：可見性選項（公開 / 不公開 unlisted / 私人）、發布範圍、發布後多久生效。 -->

---

## 版本更新流程

<!-- 待填：改版後重新打包、version 號規則、更新是否需要重新審核、使用者端多久收到更新。 -->

---

## 踩雷與心得總結

<!-- 待填：整個流程中非預期的點、下次會怎麼做、給之後上架的人的判讀訊號與操作判準。 -->
