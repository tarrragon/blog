---
title: "重構案例研究"
description: "完整回顧 v0.28.0 Hook 系統重構流程"
weight: 75
---

# 重構案例研究

本章完整回顧 v0.28.0 版本的 Hook 系統重構流程，從問題識別到最終成果，展示如何進行系統性的大規模重構。

## 重構背景

### 問題發現

在日常開發中，逐漸發現 Hook 系統存在多個問題：

| 問題 | 症狀 | 影響 |
|------|------|------|
| 重複程式碼 | 相同函式在 4+ 檔案中重複 | 修改需改多處 |
| 配置混雜 | 單一檔案 800+ 行，一半是配置 | 難以維護 |
| 魔法數字 | `line[9:]` 等難懂的切片 | 可讀性差 |
| 缺乏測試 | 沒有單元測試 | 改動風險高 |

### 決策：系統性重構

而非零散修補，決定進行一次完整的重構：

**目標**：
1. 建立共用程式庫
2. 分離配置與邏輯
3. 消除魔法數字
4. 建立測試覆蓋

**原則**：Linux Good Taste - 追求簡潔、優雅、可維護的程式碼

## 重構規劃

### Wave 架構

將重構分為四個 Wave，確保每個階段都能獨立驗證：

```
Wave 1: 建立共用程式庫
   ↓
Wave 2: 配置分離
   ↓
Wave 3: Hook 重構
   ↓
Wave 4: 驗證與文件
```

### Wave 1: 建立共用程式庫

**目標**：建立 `.claude/lib/` 目錄，抽取共用功能

**新建模組**：

```
.claude/lib/
├── __init__.py           # 模組初始化和公開介面
├── git_utils.py          # Git 操作工具
├── hook_io.py            # Hook 輸入輸出處理
├── hook_logging.py       # 日誌系統
└── config_loader.py      # YAML 配置載入器
```

**抽取的函式**：

| 函式 | 來源 | 說明 |
|------|------|------|
| `run_git_command()` | 4 個 Hook | 執行 Git 命令 |
| `get_current_branch()` | 3 個 Hook | 取得當前分支 |
| `get_repo_root()` | 2 個 Hook | 取得儲存庫根目錄 |
| `parse_worktree_output()` | 2 個 Hook | 解析 worktree 輸出 |
| `load_json()` | 2 個 Hook | 載入 JSON 檔案 |
| `save_json()` | 2 個 Hook | 儲存 JSON 檔案 |

**程式碼範例**：

```python
# lib/git_utils.py
"""Git 操作工具模組。"""

import subprocess
from pathlib import Path
from typing import List, Optional

def run_git_command(
    cmd: List[str],
    cwd: Optional[Path] = None,
    check: bool = False
) -> str:
    """執行 Git 命令並返回輸出。

    Args:
        cmd: Git 命令列表
        cwd: 工作目錄
        check: 是否在失敗時拋出異常

    Returns:
        命令輸出（已去除首尾空白）
    """
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
        check=check
    )
    return result.stdout.strip()
```

### Wave 2: 配置分離

**目標**：將硬編碼配置抽取到 YAML 檔案

**新建配置檔**：

```
.claude/config/
├── agents.yaml           # 代理人配置（323 行）
└── quality_rules.yaml    # 品質規則配置（108 行）
```

**agents.yaml 範例**：

```yaml
# 代理人角色定義
agents:
  rosemary-project-manager:
    role: "dispatcher"
    description: "專案經理，負責任務分派"
    allowed_actions:
      - dispatch
      - review

  parsley-flutter-developer:
    role: "executor"
    description: "Flutter 開發者，負責程式碼實作"
    allowed_actions:
      - implementation

# 任務類型對應
task_types:
  Implementation:
    allowed_executors:
      - parsley-flutter-developer
      - pepper-test-implementer
    forbidden_executors:
      - rosemary-project-manager
```

**配置載入器**：

```python
# lib/config_loader.py
from pathlib import Path
from typing import Any, Dict
import yaml

_config_cache: Dict[str, Any] = {}

def load_config(filename: str) -> Dict[str, Any]:
    """載入 YAML 配置檔案（帶快取）。"""
    if filename in _config_cache:
        return _config_cache[filename]

    config_path = get_config_dir() / filename
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    _config_cache[filename] = config
    return config
```

### Wave 3: Hook 重構

**目標**：使用共用模組和配置重構現有 Hook

**重構成果**：

| Hook 檔案 | 重構前 | 重構後 | 縮減比例 |
|-----------|--------|--------|----------|
| task-dispatch-readiness-check.py | 858 行 | 296 行 | -65% |
| branch-verify-hook.py | 238 行 | 109 行 | -54% |
| branch-status-reminder.py | 167 行 | 103 行 | -38% |

**重構範例** (branch-verify-hook.py)：

重構前：
```python
# 238 行，包含重複程式碼和硬編碼
import subprocess
import os

PROTECTED_BRANCHES = ["main", "master", "develop"]

def run_git_command(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip()

def get_current_branch():
    return run_git_command(["git", "branch", "--show-current"])

# ... 更多重複程式碼 ...
```

重構後：
```python
# 109 行，使用共用模組
from lib.git_utils import get_current_branch, get_repo_root
from lib.config_loader import load_config
from lib.hook_logging import info, error

def main():
    config = load_config("branch_rules.yaml")
    current_branch = get_current_branch()

    if current_branch in config["protected_branches"]:
        error(f"不允許直接在 {current_branch} 分支開發")
        return False

    info(f"分支檢查通過: {current_branch}")
    return True
```

### Wave 4: 驗證與文件

**單元測試**：

```python
# lib/tests/test_git_utils.py
import unittest
from unittest.mock import patch
from lib.git_utils import get_current_branch

class TestGetCurrentBranch(unittest.TestCase):
    @patch("lib.git_utils.run_git_command")
    def test_returns_branch_name(self, mock_run):
        mock_run.return_value = "main"
        result = get_current_branch()
        self.assertEqual(result, "main")
```

**測試執行結果**：

```
$ python -m pytest .claude/lib/tests/ -v

test_config_loader.py::test_load_config PASSED
test_config_loader.py::test_config_caching PASSED
test_config_loader.py::test_missing_config PASSED
test_git_utils.py::test_run_git_command PASSED
test_git_utils.py::test_get_current_branch PASSED
test_git_utils.py::test_get_repo_root PASSED
test_hook_io.py::test_load_json PASSED
test_hook_io.py::test_save_json PASSED
...

28 passed in 2.31s
```

## 最終成果

### 量化指標

| 指標 | 數值 |
|------|------|
| 消除重複程式碼 | ~415 行 |
| 新增共用模組 | 7 個 |
| 新增配置檔 | 2 個 |
| 新增單元測試 | 28 個 |
| Hook 檔案縮減 | 38%-65% |

### 檔案變更統計

```
16 files changed, 1883 insertions(+), 1047 deletions(-)
```

淨增加 836 行，但：
- 新增 766 行共用程式庫（可重用）
- 新增 431 行配置檔（易於維護）
- 新增 356 行測試（提升品質）
- Hook 邏輯從 1260 行減少到 607 行

### Git Commit

```
commit 60f1b95f3922b4b97069b1c9d3d09ffd9c6c551a
Author: tarragonstop
Date:   Mon Jan 19 14:24:14 2026 +0800

    refactor(v0.28.0): Hook 系統共用程式庫重構 - Linux Good Taste 原則

    ## WHAT
    建立 .claude/lib/ 共用程式庫，抽取配置到 .claude/config/，
    重構 5 個 Hook 檔案使用共用模組

    ## WHY
    - 消除 ~415 行重複程式碼
    - 分離配置與邏輯
    - 修復魔法數字
    - 建立可測試的模組架構
```

## 經驗教訓

### 成功因素

1. **Wave 架構**：分階段執行，每階段可獨立驗證
2. **先寫測試**：確保重構不改變行為
3. **漸進式重構**：一個檔案一個檔案處理
4. **完整文件**：記錄決策和設計

### 遇到的挑戰

1. **循環依賴**：lib 模組之間的依賴需要仔細設計
2. **介面設計**：公開介面要穩定，避免後續頻繁修改
3. **配置格式**：YAML 結構需要前期規劃好

### 建議做法

| 情境 | 建議 |
|------|------|
| 小型重構 | 可以直接進行 |
| 中型重構 | 建立 Ticket 追蹤 |
| 大型重構 | 使用 Wave 架構分階段 |

## Error Patterns 記錄

重構過程中發現的模式已記錄到 Error Patterns 系統：

- **ARCH-001**: 配置與程式碼混合
- **IMP-001**: 重複程式碼散落各處
- **IMP-002**: 魔法數字

這些記錄將幫助團隊避免未來重蹈覆轍。

## 後續發展

v0.28.0 重構完成後，後續版本基於此架構持續擴展：

| 版本 | 新增功能 |
|------|---------|
| v0.29.0 | hook_validator.py - Hook 合規性驗證工具 |
| v0.30.0 | markdown_link_checker.py - 連結檢查工具 |

新功能直接使用共用模組，開發效率大幅提升。

## 實作練習

### 練習 1：規劃重構

假設你發現以下問題：

```python
# file1.py
def send_email(to, subject, body):
    # 50 行的郵件發送邏輯

# file2.py
def send_email(to, subject, body):
    # 相同的 50 行邏輯

# file3.py
def send_notification(user):
    # 包含類似的郵件發送邏輯
```

請規劃重構步驟。

<details>
<summary>參考答案</summary>

**Wave 1: 建立共用模組**
```python
# lib/email_utils.py
def send_email(to: str, subject: str, body: str) -> bool:
    """發送郵件的統一介面。"""
    # 50 行邏輯
```

**Wave 2: 撰寫測試**
```python
# tests/test_email_utils.py
def test_send_email():
    # 測試郵件發送
```

**Wave 3: 替換使用處**
```python
# file1.py, file2.py
from lib.email_utils import send_email

# file3.py
from lib.email_utils import send_email

def send_notification(user):
    send_email(user.email, "通知", "...")
```

**Wave 4: 驗證**
- 執行測試確認功能正常
- 確認所有使用處都已更新

</details>

### 練習 2：評估重構效益

對於以下情境，評估是否值得重構：

1. 一個 100 行的函式，只有一處使用
2. 三個檔案各有 20 行相同的程式碼
3. 一個 500 行的檔案，其中 400 行是配置

<details>
<summary>參考答案</summary>

1. **100 行函式，單一使用**
   - 不急著重構
   - 可以先拆分成小函式提高可讀性
   - 等到需要第二處使用時再抽取

2. **三個檔案各 20 行重複**
   - 建議重構
   - 總共 60 行重複，抽取後可以減少到 20 行
   - 修改時只需要改一處

3. **500 行檔案，400 行配置**
   - 強烈建議重構
   - 分離配置到 YAML 檔案
   - 邏輯檔案會縮減到 100 行左右
   - 配置可以由非工程師修改

</details>

## 小結

- 大型重構使用 Wave 架構分階段執行
- 先建立測試再進行重構
- 將發現的問題記錄到 Error Patterns
- 重構不只是刪減程式碼，更是改善架構
- 好的重構為未來開發打下基礎

## 完成模組七

恭喜你完成了重構實戰模組！你現在具備了：

- 識別程式碼壞味道的能力
- 分離配置和程式碼的技巧
- 消除重複程式碼的方法
- 處理魔法數字的經驗
- 進行系統性重構的流程

將這些知識應用到實際專案中，持續改善程式碼品質。

---

*文件版本：v0.30.0*
*建立日期：2026-01-20*
