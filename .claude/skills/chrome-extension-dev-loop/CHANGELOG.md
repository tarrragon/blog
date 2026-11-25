# Changelog

**Version**: 1.0.0 — 初版：未封裝擴充功能三個執行位置的改動生效時機（含實驗紀錄與重驗方法）、開發版自動重新載入的設計與通用實作（`scripts/dev-auto-reload.js`）。內容來自一個 MV3 擴充功能專案的實驗：改檔後 popup 重新開啟即為新版，content script 與 service worker（含停掉再喚醒）皆為舊版，全新載入的正對照為新版；自動重新載入在使用者的 Chrome 實測成功（console 戳記與 `onInstalled` 的 `reason: update`）。
