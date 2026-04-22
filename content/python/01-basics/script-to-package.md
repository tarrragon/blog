---
title: "1.2 從單一 script 到多檔案專案"
date: 2026-04-22
description: "理解 Python 程式如何從單一 .py 檔案長成 module、package 與可測試專案"
weight: 2
---

Python 程式變大的第一個斷點通常不是物件導向或架構分層，而是執行方式與 import 邊界。初學者常從一個 `script.py` 開始，接著拆出 helper module，最後才整理成 package；每一步都會改變程式如何被執行、如何 import，以及測試如何找到程式碼。

> 撰寫提示：本章先保留大綱，詳細內容之後補。補寫時請使用中立範例，例如 `notify.py`、`config.py`、`parser.py`、`service.py`，避免綁定特定專案或 Hook 系統細節。

## 本章目標

學完本章後，你將能夠：

1. 判斷何時保留單一 script
2. 理解一個 `.py` 檔案就是一個 module
3. 分辨「同層多檔案」與「package」的差異
4. 看懂 `python file.py` 與 `python -m package.module` 的差異
5. 判斷何時需要 `__init__.py`、`pyproject.toml` 或 `src/` layout

## 章節大綱

### 1. 單一 script 是合理起點

核心原則：小工具與實驗程式可以先從單一 `.py` 檔案開始。這個階段的重點是讓流程清楚，不是急著拆資料夾。

後續補寫範例：

```text
notify.py
```

應補充重點：

- `if __name__ == "__main__"` 的基本用途。
- 函式先集中在同一檔案，避免過早拆分。
- 當檔案開始同時包含 CLI、設定、解析、業務規則時，再考慮拆檔。

### 2. 拆成同層 module

核心原則：Python 的每個 `.py` 檔案都是 module。同層拆檔可以降低單檔負擔，但 import 會受到目前執行位置與 `sys.path` 影響。

後續補寫範例：

```text
notify/
├── notify.py
├── config.py
├── parser.py
└── service.py
```

應補充重點：

- `import config` 與 `from config import load_config`。
- 從專案根目錄執行與從其他目錄執行的差異。
- 同層 module 適合小型工具，但不一定適合長期擴張。

### 3. 整理成 package

核心原則：package 是一組 module 的命名空間。當多個 module 共同形成一個概念，就可以用資料夾與 `__init__.py` 整理成 package。

後續補寫範例：

```text
notify/
├── notify_app/
│   ├── __init__.py
│   ├── config.py
│   ├── parser.py
│   └── service.py
└── main.py
```

應補充重點：

- `__init__.py` 的角色：初始化、公開 API、package 標記。
- package 內部使用 absolute import 或 relative import 的取捨。
- 不要把所有名稱都重新 export 到 `__init__.py`。

### 4. 執行方式會影響 import

核心原則：Python 的 import 行為和執行方式密切相關。`python main.py`、`python -m package.module`、測試工具與安裝後執行，可能會看到不同的 module search path。

後續補寫範例：

```bash
python main.py
python -m notify_app.cli
python -m pytest
```

應補充重點：

- `__name__` 與 `__package__` 的差異。
- 為什麼 package 內相對 import 在直接執行檔案時容易失敗。
- CLI 入口和 library module 最好分開。

### 5. 測試會推動專案結構

核心原則：當程式需要測試時，專案結構必須讓測試穩定 import 目標程式碼。測試不是最後才加入的附屬品，而是拆分 module 與 package 的重要壓力來源。

後續補寫範例：

```text
notify/
├── notify_app/
│   ├── __init__.py
│   └── service.py
└── tests/
    └── test_service.py
```

應補充重點：

- `tests/` 和 package 的相對位置。
- 為什麼測試常揭露 import 路徑設計不穩。
- 小型專案可以先維持簡單，大型或可發布專案再導入 `pyproject.toml`。

### 6. 何時進入可安裝專案與 `src/` layout

核心原則：`pyproject.toml` 與 `src/` layout 是正式專案管理工具，不是所有初學程式的起點。當專案需要被安裝、發布、由多個工具穩定執行時，再導入這些結構。

後續補寫範例：

```text
notify/
├── pyproject.toml
├── src/
│   └── notify_app/
│       ├── __init__.py
│       └── service.py
└── tests/
    └── test_service.py
```

應補充重點：

- `src/` layout 防止「剛好從目前目錄 import 成功」的假象。
- editable install 的用途。
- 進階打包內容應連到 `python-advanced/07-packaging/`。

## 後續補寫時的比較提示

Python 和 Go 在這個主題上的差異應明確說清楚：

| 主題        | Python                                        | Go                                         |
| ----------- | --------------------------------------------- | ------------------------------------------ |
| 最小單位    | `.py` module                                  | package                                    |
| 單檔起點    | 任意 script                                   | `package main` + `func main()`             |
| 可見性      | `_name` 慣例，runtime 不強制                  | 大小寫由編譯器強制                         |
| import 問題 | 受 `sys.path`、執行方式、安裝方式影響         | 受 `go.mod`、module path、package 邊界影響 |
| 循環依賴    | runtime 才可能爆 partially initialized module | 編譯期拒絕 import cycle                    |
| 正式專案    | `pyproject.toml`、package、`src/` layout      | `go.mod`、package、`cmd/`、`internal/`     |

## 本章不處理

- 不展開 packaging 與發布流程。
- 不深入 dependency management。
- 不討論大型框架專案結構。
- 不把 `src/` layout 當成所有專案的預設起點。

## 小結

Python 程式的成長路線通常是 script、同層 module、package、可安裝專案。這條路線的核心不是目錄變多，而是執行方式、import 邊界與測試方式逐步穩定。
