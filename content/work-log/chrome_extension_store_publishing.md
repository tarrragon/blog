---
title: "Chrome 套件上架 Chrome Web Store 心得記錄"
date: 2026-05-21
draft: true
description: "記錄把 Chrome extension 上架到 Chrome Web Store 的完整流程：開發者帳號、上架前準備、Store listing 填寫、權限與隱私聲明、審核與駁回處理、版本更新，以及過程中踩到的雷。"
tags: ["chrome-extension", "chrome-web-store", "publishing", "tooling"]
---

_待填：這次上架的是什麼套件、做什麼用、為什麼要上架（自用 / 給團隊 / 公開）。一句話交代 context，後面章節才知道判讀的前提。_

---

## 開發者帳號與費用

_待填：註冊 Chrome Web Store 開發者帳號的流程、一次性費用、付款方式、帳號類型（個人 / 公司）的選擇與差異。_

---

## 上架前準備

### manifest.json 檢查

_待填：manifest 版本（v3）、`name` / `version` / `description` 欄位、`permissions` 與 `host_permissions` 的範圍、上架前需要收斂掉的開發用設定。_

### 視覺資產

_待填：icon 尺寸需求、商店截圖規格與數量、宣傳圖（small / marquee tile）的尺寸與是否必填。記下實際做出來的尺寸與工具。_

---

## 打包與上傳

_待填：打包成 zip 的方式（手動 / 腳本）、要排除哪些檔案、在 Developer Dashboard 上傳的步驟。_

---

## Store listing 填寫

_待填：商店頁面要填的欄位 — 詳細描述、分類、語言、單一用途聲明（single purpose）。哪些欄位事後難改、哪些影響搜尋曝光。_

---

## 權限與隱私聲明

_待填：每個 permission 的使用理由（justification）、資料用途聲明（data usage）、隱私權政策連結。這段通常最容易卡審核，記下實際填法。_

---

## 提交審核與等待

_待填：提交後的審核狀態流轉、實際等待時間、審核期間能不能改東西。_

---

## 駁回與修正紀錄

_待填：被駁回的話 — 駁回理由原文、對應的修正、重新提交後的結果。沒被駁回也記一句「一次過」。_

---

## 發布設定

_待填：可見性選項（公開 / 不公開 unlisted / 私人）、發布範圍、發布後多久生效。_

---

## 版本更新流程

_待填：改版後重新打包、version 號規則、更新是否需要重新審核、使用者端多久收到更新。_

---

## 踩雷與心得總結

_待填：整個流程中非預期的點、下次會怎麼做、給之後上架的人的判讀訊號與操作判準。_
