---
title: "作用域迴歸案例研究"
date: 2026-03-04
description: "從 IMP-003 事件學習 Python 變數作用域的陷阱"
weight: 76
---

本章記錄 W24 開發週期中發生的一個真實 bug：在統一 16 個 Hook 的 logger 初始化風格時，7 個 Hook 因為**變數作用域變更**而靜默失敗，影響 41 個函式。

這個案例的價值在於：bug 本身很簡單（`NameError`），但它暴露了重構時一個容易被忽略的系統性風險。

## 背景

W24 的任務是統一所有 Hook 的 logger 初始化風格。原本各 Hook 的 logger 初始化位置不一致：

```python
# 風格 A：模組級初始化（13 個 Hook 使用）
logger = setup_hook_logging("my-hook")  # 在最外層

def helper():
    logger.info("working...")  # OK：logger 是全域變數

def main():
    helper()
    logger.info("done")
    return 0

# 風格 B：main() 內初始化（已有部分 Hook 使用）
def helper(logger):
    logger.info("working...")  # OK：logger 是參數

def main():
    logger = setup_hook_logging("my-hook")  # 在 main() 內
    helper(logger)
    logger.info("done")
    return 0
```

統一目標：全部改為**風格 B**（`main()` 內初始化），理由是：

- logger 不該在模組被 import 時就建立
- `main()` 內初始化更明確，生命週期更可控

## 出了什麼問題

修改時只做了一件事：把 `logger = setup_hook_logging(...)` 從模組級移到 `main()` 內部。

```python
# 修改前
logger = setup_hook_logging("acceptance-gate-hook")

def check_acceptance_criteria(ticket_path):
    logger.info(f"Checking {ticket_path}")  # OK
    # ...

def validate_ticket_format(content):
    logger.info("Validating format")  # OK
    # ...

def main():
    result = check_acceptance_criteria(path)
    # ...

# 修改後（有 bug）
def check_acceptance_criteria(ticket_path):
    logger.info(f"Checking {ticket_path}")  # NameError!
    # ...

def validate_ticket_format(content):
    logger.info("Validating format")  # NameError!
    # ...

def main():
    logger = setup_hook_logging("acceptance-gate-hook")  # 區域變數
    result = check_acceptance_criteria(path)
    # ...
```

`logger` 從全域變數變成了 `main()` 的區域變數。但 `check_acceptance_criteria` 和 `validate_ticket_format` 仍然以全域方式引用 `logger`——它們不知道 `logger` 已經不在全域作用域了。

## Python 作用域規則回顧

Python 的變數查找遵循 **LEGB 規則**：

```
L - Local      : 函式內部
E - Enclosing  : 外層函式（閉包）
G - Global     : 模組級
B - Built-in   : Python 內建
```

```python
# 修改前：logger 在 G（Global）
logger = setup_hook_logging("hook")  # Global scope

def helper():
    logger.info("...")  # L 找不到 → E 找不到 → G 找到了

# 修改後：logger 在 main 的 L（Local）
def helper():
    logger.info("...")  # L 找不到 → E 找不到 → G 找不到 → NameError!

def main():
    logger = setup_hook_logging("hook")  # main 的 Local scope
    helper()  # helper 無法存取 main 的 Local
```

`main()` 的區域變數對 `helper()` 來說是**不可見的**。`helper()` 不是定義在 `main()` 內部（不是閉包），所以 Enclosing scope 也找不到。

## 為什麼沒被立刻發現

這個 bug 最危險的地方是**靜默失敗**。原因是 `run_hook_safely` 的頂層例外處理：

```python
def run_hook_safely(main_func, hook_name):
    logger = setup_hook_logging(hook_name)
    try:
        exit_code = main_func()
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        tb_str = traceback.format_exc()
        _log_exception(logger, hook_name, tb_str)
        return EXIT_ERROR  # 返回錯誤碼，但不會 crash
```

流程是這樣的：

```
1. main() 被 run_hook_safely 呼叫
2. main() 內呼叫 check_acceptance_criteria()
3. check_acceptance_criteria() 引用 logger → NameError
4. NameError 是 Exception 的子類別
5. run_hook_safely 捕獲，寫入日誌檔案
6. 返回 EXIT_ERROR（整數 1）
7. Hook 系統收到非零退出碼 → 顯示 "hook success"（suppressOutput）
8. 用戶看不到任何異常
```

7 個 Hook 就這樣在至少 2 個 session 中靜默失敗。直到有人手動觸發了一個受影響的 Hook 並檢查日誌，才發現問題。

> 這也是為什麼 W25-005 後來在 `_log_exception` 加入了 stderr 輸出。詳見 [5.5 頂層例外處理機制](../../05-error-testing/error-infrastructure/)。

## 正確的修正方式

### Step 1：影響範圍分析

修改變數作用域**之前**，先列出所有引用該變數的函式：

```bash
# 用 AST 分析找出所有引用 logger 的非 main 函式
python3 -c "
import ast, sys

tree = ast.parse(open(sys.argv[1]).read())
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name != 'main':
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and child.id == 'logger':
                print(f'  {node.name}() references logger')
                break
" acceptance-gate-hook.py
```

輸出：

```
  check_acceptance_criteria() references logger
  validate_ticket_format() references logger
  check_worklog_sections() references logger
  ... (共 11 個函式)
```

### Step 2：修改函式簽名

每個引用 `logger` 的函式都必須接收 `logger` 作為參數：

```python
def check_acceptance_criteria(ticket_path, logger):  # 加入 logger 參數
    logger.info(f"Checking {ticket_path}")
    # ...

def validate_ticket_format(content, logger):  # 加入 logger 參數
    logger.info("Validating format")
    # ...
```

### Step 3：更新所有呼叫端

```python
def main():
    logger = setup_hook_logging("acceptance-gate-hook")
    result = check_acceptance_criteria(path, logger)  # 傳遞 logger
    validate_ticket_format(content, logger)            # 傳遞 logger
    return 0
```

### Step 4：驗證

```bash
# AST 驗證：確認沒有函式在引用全域 logger
python3 -c "
import ast, sys

tree = ast.parse(open(sys.argv[1]).read())
issues = []
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name != 'main':
        params = {arg.arg for arg in node.args.args}
        if 'logger' not in params:
            for child in ast.walk(node):
                if isinstance(child, ast.Name) and child.id == 'logger':
                    issues.append(node.name)
                    break
if issues:
    print(f'FAIL: {issues} still reference global logger')
else:
    print('PASS: all functions receive logger as parameter')
" acceptance-gate-hook.py
```

## 修正規模

| 指標             | 數值              |
| ---------------- | ----------------- |
| 受影響 Hook      | 7 個              |
| 受影響函式       | 41 個             |
| 修正行數         | +143 / -81        |
| 靜默失敗持續時間 | 至少 2 個 session |

## 為什麼 py_compile 抓不到這個 bug

你可能會想：修改後跑一下語法檢查不就好了？

```bash
python3 -m py_compile acceptance-gate-hook.py
# 通過！沒有任何錯誤
```

`py_compile` 只檢查**語法**（syntax），不檢查**作用域**（scope）。`logger.info("...")` 在語法上完全正確——它是一個合法的「存取名稱 logger 的 info 屬性並呼叫」。只有在**執行時**，Python 才會查找 `logger` 這個名稱，發現找不到，拋出 `NameError`。

### 驗證工具的能力比較

| 工具         | 能否偵測此 bug | 原因                        |
| ------------ | -------------- | --------------------------- |
| `py_compile` | 否             | 只檢查語法                  |
| `mypy`       | 可能           | 型別檢查會分析名稱可見性    |
| AST 分析     | 是             | 可以追蹤名稱引用和定義      |
| 實際執行     | 是             | 直接觸發 `NameError`        |
| `pylint`     | 是             | 會警告 `undefined-variable` |

## 教訓：作用域變更的強制檢查清單

任何涉及**變數作用域變更**的重構（全域 → 區域、模組級 → 函式內、類別屬性 → 方法參數），都必須執行：

| 步驟 | 動作                                     | 驗證方式                                  |
| ---- | ---------------------------------------- | ----------------------------------------- |
| 1    | 列出所有引用該變數的函式                 | `grep` 或 AST 分析                        |
| 2    | 每個函式確認：透過參數接收還是依賴全域？ | 逐一檢查函式簽名                          |
| 3    | 依賴全域的函式必須新增參數               | 修改函式簽名                              |
| 4    | 所有呼叫端必須傳遞新參數                 | 修改所有 call site                        |
| 5    | 驗證                                     | AST 分析或實際執行（不要只用 py_compile） |

## 更廣泛的啟示

這個案例不只適用於 `logger`。任何「移動變數定義位置」的重構都有同樣的風險：

```python
# 範例：將資料庫連線從全域移入函式
# 修改前
db = connect_database()

def get_user(user_id):
    return db.query(f"SELECT * FROM users WHERE id = {user_id}")

# 修改後（有 bug）
def get_user(user_id):
    return db.query(...)  # NameError: db 不再是全域

def main():
    db = connect_database()
    user = get_user(123)
```

同樣的模式，同樣的陷阱。解決方式也一樣：分析引用 → 修改簽名 → 傳遞參數 → 驗證。

## 思考題

1. 如果使用 `global logger` 宣告，能否解決這個問題？為什麼不推薦這種做法？
2. 閉包（closure）能否解決這個問題？把 `helper` 定義在 `main()` 內部會怎樣？
3. 這個 bug 在什麼條件下才會被發現？（提示：考慮測試覆蓋率和 Hook 觸發時機）

## 實作練習

1. 找一段使用全域變數的程式碼，嘗試將變數移入函式內部，並用 AST 分析驗證所有引用
2. 寫一個腳本，掃描指定的 Python 檔案，找出所有「函式內引用但未定義、也不在參數中」的名稱
3. 設計一個 pre-commit hook，在 `git diff` 中偵測「變數定義位置改變」的情況

---

_上一章：[重構案例研究](../case-study/)_
_相關：[5.5 頂層例外處理機制](../../05-error-testing/error-infrastructure/) — 本案例中 bug 被靜默吞掉的機制分析_
