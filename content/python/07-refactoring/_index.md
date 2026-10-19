---
title: "模組七：重構實戰"
date: 2026-01-20
description: "基於 v0.28.0-v0.31.0 重構經驗的程式碼品質改善指南"
weight: 8
tags: ["python", "refactoring"]
---

本模組基於 v0.28.0-v0.31.0 Hook 系統重構的實際經驗，教你如何識別程式碼問題並進行系統性重構。

## 學習目標

1. 學會識別常見的程式碼壞味道
2. 理解配置與程式碼分離的重要性
3. 掌握 DRY 原則的實踐方法
4. 學會消除魔法數字
5. 能夠進行系統性的程式碼重構
6. 理解變數作用域變更在重構中的風險

## 章節內容

### [重構的動機與策略](/python/07-refactoring/refactoring-strategy/)

量化認知負擔、制定重構策略、掌握階段分解方法。

### [程式碼壞味道偵測](/python/07-refactoring/code-smells/)

學習如何識別程式碼中的問題，包括 Error Patterns 系統介紹和 5 Why 分析方法。

### [DRY 原則與共用程式庫](/python/07-refactoring/dry-principle/)

基於 IMP-001 錯誤模式，學習如何識別重複程式碼並建立共用模組。

### [配置分離與常數管理](/python/07-refactoring/constants-management/)

基於 IMP-002、ARCH-001 錯誤模式，學習三種硬編碼（魔法數字、配置、字串）的系統性消除。

### [大規模統一化重構](/python/07-refactoring/unified-infrastructure/)

基於 W22-W24 統一化重構經驗，學習三階段漸進式重構方法。

### [重構陷阱與防護](/python/07-refactoring/refactoring-pitfalls/)

基於 IMP-003、IMP-005 錯誤模式，學習重構中的常見陷阱和防護措施。

### [完整案例回顧](/python/07-refactoring/case-study/)

完整回顧 v0.28.0-v0.31.0 重構流程，從問題識別到最終成果。

### [作用域迴歸案例研究](/python/07-refactoring/scope-regression/)

基於 IMP-003 錯誤模式，學習 Python 變數作用域在重構中的陷阱。W24 統一 logger 初始化時，7 個 Hook 因作用域變更靜默失敗的真實案例。

### [拆分 Python 模組：pytest 的特徵測試、同名套件與重新匯出、自動登記的分派表、避免循環匯入](/python/07-refactoring/python-module-split/)

職責邊界決定之後，在不改變對外行為的前提下拆分 Python 模組。要不要拆、依什麼切，以及拆分時與語言無關的特徵測試、搬移與修改分開提交、單向依賴，在軟體設計原則模組的[從修改紀錄畫模組邊界](/design-principles/module-boundary-from-change-history/)。

## 重構成效數據

v0.28.0 重構的實際成果：

| 指標           | 數值              |
| -------------- | ----------------- |
| 消除重複程式碼 | ~415 行           |
| Hook 檔案縮減  | 38%-65%           |
| 新增共用模組   | 7 個              |
| 單元測試       | 28 個（全部通過） |

## Backlog

| 項目                                                                                                                                                                                                              | 類型 | 前置條件                  | 規模 |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ------------------------- | ---- |
| 聚焦入口候選：拆成套件之後 monkeypatch 失效，目前埋在〈拆分 Python 模組〉與 monkeypatch 卡的段落裡（rebase 撞到拆檔的衝突已移到 design-principles 的 Backlog；CHANGELOG 合併衝突在 record〈依職責拆分文字文件〉） | 案例 | 有實際事件再寫成 work-log | 小   |
| 目錄頁 description 與 python/_index.md 模組七的簡介「基於 v0.28.0 重構經驗」不涵蓋〈拆分 Python 模組〉（範例是 commit 守衛，不來自那幾個版本）；改寫成本模組實際涵蓋的主題，版本來源移到〈資料來源〉              | 主章 | 無                        | 小   |
| case-study〈W28：一致性審查〉的「開發者說」一句疑為虛構引述，查證來源或改寫成條件句                                                                                                                               | 主章 | 無                        | 小   |

## 資料來源

本模組使用的實際案例來自：

- **Error Patterns**: `.claude/error-patterns/` 目錄下的錯誤模式文件
- **Git 歷史**: Commit `60f1b95`（v0.28.0）、`3cf47d4e`（v0.31.0 W24）及相關重構提交
- **共用程式庫**: `.claude/lib/` 目錄下的模組

## 先修知識

建議先完成以下模組：

- [模組一：Python 基礎概念](/python/01-basics/)
- [模組四：物件導向設計](/python/04-oop/)

---

*文件版本：v0.31.0*
*最後更新：2026-03-04*
