---
title: "模組一：Python 基礎概念"
date: 2026-01-20
description: "Python 語言、script、module、package 與 import 機制的核心概念快速回顧"
weight: 1
---


本模組帶你快速回顧 Python 的核心概念。如果你已經有其他程式語言經驗，這些內容能幫助你理解 Python 的「思考方式」，以及程式如何從單一 script 長成多檔案與 package。

## 章節列表

| 章節 | 主題 | 關鍵收穫 |
|------|------|---------|
| [1.1](philosophy/) | Python 哲學與設計理念 | 理解「Pythonic」的真正含義 |
| [1.2](script-to-package/) | 從單一 script 到多檔案專案 | 理解 `.py` module、package、執行方式與測試結構如何逐步出現 |
| [1.3](modules/) | 模組與套件組織 | 掌握 `__init__.py` 的作用 |
| [1.4](imports/) | 導入機制與路徑管理 | 解決「找不到模組」的困擾 |

## 實際範例來源

本模組的範例主要來自：

- `.claude/lib/__init__.py` - 模組初始化範例
- Hook 腳本的導入結構

> 後續補寫提示：`1.2 從單一 script 到多檔案專案` 應改用中立範例，避免依賴特定 Hook 系統背景。這一章負責補上初學者從單檔到 package 的過渡；`1.3` 和 `1.4` 再處理既有專案中的 module、package 與 import 問題。

## 預備知識

- 基本程式設計概念（變數、函式、迴圈）
- 對任一程式語言有基礎了解

## 學習時間

預計 45-60 分鐘
