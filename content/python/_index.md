---
title: "Python 維護工程師實戰指南"
date: 2026-01-20
description: "以 Hook 系統為範例的 Python 開發教學"
weight: 30
---

# Python 維護工程師實戰指南

本教學文件專為需要維護和擴展 Hook 系統的工程師設計。透過實際專案範例，幫助你快速掌握 Python 開發的核心技能。

## 目標讀者

- 有程式經驗的工程師（非 Python 專家）
- 需要維護和擴展現有 Hook 系統
- 需要理解 Python 設計理念和可用技術

## 學習目標

1. 理解 Python 語言的設計理念
2. 能看懂現有架構和邏輯
3. 知道有哪些技術可以用來實現概念
4. 學習識別程式碼壞味道並進行重構
5. 理解「降低認知負擔」是所有原則的核心目的

## 教學模組

### [模組零：設計哲學（序章）](00-philosophy/)

所有程式碼設計原則的統一視角：降低閱讀者的認知負擔。

- [認知負擔：程式碼設計的核心目的](00-philosophy/cognitive-load/)
- [命名的藝術：讓程式碼說故事](00-philosophy/naming-art/)
- [開放封閉原則與認知負擔](00-philosophy/open-closed-principle/)

### [模組一：Python 基礎概念](01-basics/)

快速回顧 Python 的核心概念，包括語言哲學、模組組織和導入機制。

- [Python 哲學與設計理念](01-basics/philosophy/)
- [模組與套件組織](01-basics/modules/)
- [導入機制與路徑管理](01-basics/imports/)

### [模組二：型別系統](02-type-system/)

現代 Python 的型別系統，讓程式碼更易讀、更易維護。

- [Type Hints 基礎](02-type-system/type-hints/)
- [Optional、Union、泛型](02-type-system/optional-union/)
- [Dataclass 資料結構](02-type-system/dataclass/)
- [Enum 列舉型別](02-type-system/enum/)

### [模組三：標準庫實戰](03-stdlib/)

Python 標準庫的常用模組，這些都是 Hook 系統中實際使用的工具。

- [pathlib - 路徑操作](03-stdlib/pathlib/)
- [json - 序列化](03-stdlib/json/)
- [subprocess - 執行外部命令](03-stdlib/subprocess/)
- [re - 正規表達式](03-stdlib/regex/)
- [logging - 日誌系統](03-stdlib/logging/)
- [argparse - CLI 介面](03-stdlib/argparse/)
- [並行處理 - threading、multiprocessing、concurrent.futures](03-stdlib/concurrency/)
- [效能迷思與優化策略](03-stdlib/performance/)

### [模組四：物件導向設計](04-oop/)

Python 的物件導向設計模式，從類別設計到設計模式。

- [類別設計原則](04-oop/class-design/)
- [抽象基類 ABC](04-oop/abc/)
- [工廠模式](04-oop/factory/)
- [單例與快取模式](04-oop/singleton-cache/)

### [模組五：錯誤處理與測試](05-error-testing/)

穩健程式碼的基石：異常處理和單元測試。

- [異常處理策略](05-error-testing/exception/)
- [返回值設計](05-error-testing/return-values/)
- [unittest 基礎](05-error-testing/unittest/)
- [Mock 與測試隔離](05-error-testing/mock/)

### [模組六：實戰指南](06-practical/)

將所學應用到實際工作中，包含完整的操作流程。

- [如何新增一個 Hook](06-practical/new-hook/)
- [如何擴展共用模組](06-practical/extend-lib/)
- [如何新增語言解析器](06-practical/new-parser/)

### [模組七：重構實戰](07-refactoring/)

基於 v0.28.0 重構經驗，學習識別程式碼問題並進行系統性重構。

- [程式碼壞味道識別](07-refactoring/code-smells/)
- [配置與程式碼分離](07-refactoring/config-separation/)
- [DRY 原則與共用程式庫](07-refactoring/dry-principle/)
- [消除魔法數字](07-refactoring/magic-numbers/)
- [重構案例研究](07-refactoring/case-study/)

## 範例來源

所有範例均來自實際的 Hook 系統程式碼：

```text
.claude/lib/
├── __init__.py           # 模組初始化
├── config_loader.py      # 配置載入
├── git_utils.py          # Git 操作
├── hook_io.py            # 輸入輸出
├── hook_logging.py       # 日誌系統
├── hook_validator.py     # 驗證工具
├── markdown_link_checker.py  # 連結檢查
└── tests/                # 測試檔案
```

## 如何使用本教學

1. **快速查閱**：直接跳到需要的章節
2. **系統學習**：按模組順序閱讀
3. **實戰練習**：配合模組六進行實作

---

*文件版本：v0.32.0*
*最後更新：2026-01-20*
*新增內容：並行處理、效能優化章節*
