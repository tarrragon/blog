# Changelog

**Version**: 1.0.0 — 初版：以 `--load-extension` 全新載入建置副本驗證 content script 與 service worker（本機頁注入、標記、CDP 停 service worker 與狀態序列、正對照），以 `file://` 加假 chrome API 渲染 popup 各狀態（API 形狀比照 MV3、握手要回應、連線中用拒絕模擬），以及限制（`chrome.runtime.reload()` 讓 `--load-extension` 載入的擴充功能消失、拿不到登入狀態與真實 DOM）。內容來自一個 MV3 擴充功能專案 popup 改版與開發迴圈實驗。
