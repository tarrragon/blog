---
title: "Expand / Contract"
date: 2026-04-24
description: "說明先擴充相容面、再收斂舊路徑的遷移做法"
weight: 139
---

Expand / Contract 的核心概念是「先把新結構或新路徑加進去，確認相容後，再移除舊結構或舊路徑」。

## 概念位置

Expand / Contract 位在 schema migration、online migration、deployment 與 release gate 之間。它是降低變更風險的遷移順序，不是單一工具。

## 可觀察訊號

系統需要 expand / contract 的訊號是：

- 舊版本與新版本會同時存在
- 新功能需要先讓舊程式不壞掉
- 移除舊欄位或舊路徑前，必須先讓新版本穩定接上
- migration 不能一次做完

## 接近真實網路服務的例子

新增欄位時先擴表、補預設值、讓新舊版本都能讀寫，再等舊版本完全退出後移除舊欄位；換搜尋索引時先讓新寫入同步到兩邊，等驗證完成後再收斂舊索引。這些都屬於 expand / contract。

## 設計責任

Expand / Contract 要定義擴張階段、相容條件、收斂條件、驗證方式與回復方式。它的重點是讓每一步都保有回頭路。
