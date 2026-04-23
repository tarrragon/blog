---
title: "Change Data Capture"
date: 2026-04-23
description: "說明資料變更如何被捕捉並傳送到其他系統"
weight: 79
---

Change Data Capture 的核心概念是「捕捉資料庫變更並把變更傳送給其他系統」。CDC 可以用於同步搜尋索引、資料倉儲、cache、event stream 或新舊系統遷移。

## 概念位置

CDC 是資料同步與事件化的橋樑。它通常從 database log、trigger、polling 或平台工具取得變更，再轉成可消費的事件流。

## 可觀察訊號與例子

系統需要 CDC 的訊號是正式資料更新後，多個衍生系統都需要同步。會員資料變更後，搜尋、推薦、報表與客服系統可能都需要收到更新。

## 設計責任

CDC 設計要處理順序、重複、schema 變更、backfill、lag、重放與資料遮罩。觀測上要看 capture lag、delivery lag、錯誤率與最舊未同步資料時間。
