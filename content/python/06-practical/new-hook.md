---
title: "6.1 如何新增一個 Hook"
date: 2026-01-20
description: "完整的 Hook 開發流程"
weight: 1
---

# 如何新增一個 Hook

本章介紹如何從零開始建立一個 Claude Code Hook 腳本。這是一個實戰指南，整合了前面學到的所有概念。

## 前置知識

建議先閱讀：
- [3.2 json 序列化](../../03-stdlib/json/)
- [3.5 logging 日誌系統](../../03-stdlib/logging/)
- [4.1 類別設計原則](../../04-oop/class-design/)
- [5.1 異常處理策略](../../05-error-testing/exception/)

## Hook 系統概述

Claude Code Hook 是在特定事件發生時執行的腳本，例如：
- `SessionStart` - 會話開始
- `Stop` - Claude 主動結束
- `PreToolUse` - 工具使用前
- `PostToolUse` - 工具使用後

## 步驟 1：建立基本結構

### 使用 UV 單檔模式

推薦使用 `uv` 的單檔腳本模式：

```python
#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
My Custom Hook - 簡短描述

Hook Event: SessionStart

這裡寫詳細說明。
"""

import sys
from pathlib import Path

# 添加 lib 目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from hook_logging import setup_hook_logging

def main():
    """Hook 主函式"""
    logger = setup_hook_logging("my_custom_hook")
    logger.info("Hook 開始執行")

    # 你的邏輯在這裡

    logger.info("Hook 執行完成")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### 路徑設定

Hook 腳本需要能找到共用模組：

```python
import sys
from pathlib import Path

# 添加 lib 目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

# 現在可以導入共用模組
from git_utils import get_current_branch
from hook_logging import setup_hook_logging
from hook_io import read_hook_input, write_hook_output
```

## 步驟 2：處理輸入輸出

### SessionStart Hook 範例

SessionStart Hook 不需要讀取輸入，直接輸出即可：

```python
#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Branch Status Reminder - 分支狀態提醒

Hook Event: SessionStart
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from git_utils import (
    get_current_branch,
    get_project_root,
    is_protected_branch,
)


def main():
    print("=" * 60)
    print("Branch Status Reminder")
    print("=" * 60)

    current_branch = get_current_branch()
    if not current_branch:
        print("警告: 無法獲取分支資訊")
        return 0

    is_protected = is_protected_branch(current_branch)
    branch_status = "保護分支" if is_protected else "開發分支"

    print(f"當前分支: {current_branch} ({branch_status})")
    print(f"工作目錄: {get_project_root()}")

    if is_protected:
        print()
        print("警告: 當前在保護分支上")
        print("建議: 建立 feature 分支後再進行開發")

    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### PreToolUse/PostToolUse Hook 範例

這類 Hook 需要讀取 stdin 並輸出 JSON：

```python
#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Tool Usage Logger - 記錄工具使用情況

Hook Event: PostToolUse
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from hook_io import read_hook_input, write_hook_output
from hook_logging import setup_hook_logging


def main():
    logger = setup_hook_logging("tool_usage_logger")

    try:
        # 讀取 Hook 輸入
        hook_input = read_hook_input()

        if hook_input is None:
            write_hook_output(continue_execution=True)
            return 0

        # 取得工具資訊
        tool_name = hook_input.get("tool_name", "unknown")
        tool_input = hook_input.get("tool_input", {})

        # 記錄使用情況
        logger.info(f"工具使用: {tool_name}")
        logger.debug(f"輸入參數: {tool_input}")

        # 輸出結果（不阻擋執行）
        write_hook_output(continue_execution=True)

    except Exception as e:
        logger.error(f"Hook 執行錯誤: {e}")
        write_hook_output(continue_execution=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## 步驟 3：使用共用模組

### Git 工具

```python
from git_utils import (
    run_git_command,
    get_current_branch,
    get_project_root,
    is_protected_branch,
    is_allowed_branch,
)

# 取得當前分支
branch = get_current_branch()

# 檢查是否為保護分支
if is_protected_branch(branch):
    print("警告：你在保護分支上")

# 執行 git 命令
success, output = run_git_command(["status", "--short"])
if success:
    print(output)
```

### 日誌系統

```python
from hook_logging import setup_hook_logging

# 設定日誌
logger = setup_hook_logging("my_hook")

# 使用日誌
logger.debug("詳細資訊")
logger.info("一般資訊")
logger.warning("警告訊息")
logger.error("錯誤訊息")
```

### 輸入輸出

```python
from hook_io import (
    read_hook_input,
    write_hook_output,
    create_pretooluse_output,
    create_posttooluse_output,
)

# 讀取輸入
hook_input = read_hook_input()

# 允許繼續執行
write_hook_output(continue_execution=True)

# 阻擋執行並附帶訊息
write_hook_output(
    continue_execution=False,
    decision="block",
    reason="不允許此操作"
)

# PreToolUse 專用輸出
output = create_pretooluse_output(
    decision="allow",  # 或 "block", "modify"
    reason="操作允許"
)
print(json.dumps(output))
```

## 步驟 4：註冊 Hook

在 `.claude/settings.json` 中註冊：

```json
{
  "hooks": {
    "SessionStart": [
      {
        "type": "command",
        "command": "python .claude/hooks/branch-status-reminder.py",
        "event": "SessionStart"
      }
    ],
    "PreToolUse": [
      {
        "type": "command",
        "command": "python .claude/hooks/tool-guard.py",
        "event": "PreToolUse"
      }
    ]
  }
}
```

## 步驟 5：撰寫測試

```python
# tests/test_my_hook.py
"""
My Hook 測試
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# 添加 hooks 目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent / ".claude" / "hooks"))


class TestMyHook(unittest.TestCase):
    """測試 My Hook"""

    @patch("my_hook.get_current_branch")
    def test_protected_branch_warning(self, mock_branch):
        """測試保護分支警告"""
        mock_branch.return_value = "main"

        # 導入並測試
        from my_hook import check_branch_status

        result = check_branch_status()
        self.assertTrue(result["is_protected"])

    @patch("my_hook.read_hook_input")
    def test_empty_input_handling(self, mock_input):
        """測試空輸入處理"""
        mock_input.return_value = None

        from my_hook import main

        # 應該正常退出，不拋出異常
        result = main()
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
```

## 完整範例：檔案類型檢查 Hook

```python
#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
File Type Permission Hook - 檔案類型權限檢查

阻止對特定類型檔案的危險操作。

Hook Event: PreToolUse
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from hook_io import read_hook_input, create_pretooluse_output
from hook_logging import setup_hook_logging
import json


# 配置：受保護的檔案模式
PROTECTED_PATTERNS = [
    "*.env",
    "*.pem",
    "*.key",
    "*credentials*",
]

# 需要檢查的工具
MONITORED_TOOLS = ["Write", "Edit", "Bash"]


def main():
    logger = setup_hook_logging("file_type_permission")

    try:
        hook_input = read_hook_input()

        if hook_input is None:
            print(json.dumps(create_pretooluse_output("allow")))
            return 0

        tool_name = hook_input.get("tool_name", "")
        tool_input = hook_input.get("tool_input", {})

        # 只檢查特定工具
        if tool_name not in MONITORED_TOOLS:
            print(json.dumps(create_pretooluse_output("allow")))
            return 0

        # 取得檔案路徑
        file_path = tool_input.get("file_path") or tool_input.get("command", "")

        # 檢查是否為受保護的檔案
        if is_protected_file(file_path):
            logger.warning(f"阻擋對受保護檔案的操作: {file_path}")
            output = create_pretooluse_output(
                decision="block",
                reason=f"此檔案受保護，不允許直接操作: {file_path}"
            )
        else:
            output = create_pretooluse_output("allow")

        print(json.dumps(output))

    except Exception as e:
        logger.error(f"Hook 錯誤: {e}")
        print(json.dumps(create_pretooluse_output("allow")))

    return 0


def is_protected_file(file_path: str) -> bool:
    """檢查檔案是否受保護"""
    if not file_path:
        return False

    path = Path(file_path)

    for pattern in PROTECTED_PATTERNS:
        if path.match(pattern):
            return True

    return False


if __name__ == "__main__":
    sys.exit(main())
```

## 開發檢查清單

新增 Hook 時的檢查項目：

- [ ] 使用 UV 單檔模式（`#!/usr/bin/env -S uv run --quiet --script`）
- [ ] 正確設定 `sys.path` 以導入共用模組
- [ ] 使用 `setup_hook_logging()` 設定日誌
- [ ] 使用 `read_hook_input()` / `write_hook_output()` 處理 I/O
- [ ] 妥善處理異常（不讓 Hook 崩潰影響系統）
- [ ] 在 `settings.json` 中註冊
- [ ] 撰寫單元測試
- [ ] 更新文件

## 常見問題

### Q: Hook 執行失敗會影響 Claude 嗎？

Hook 應該優雅地處理錯誤，不要讓異常傳播出去：

```python
def main():
    try:
        # 你的邏輯
        pass
    except Exception as e:
        logger.error(f"Error: {e}")
        # 允許繼續執行，不阻擋系統
        write_hook_output(continue_execution=True)

    return 0  # 總是返回 0
```

### Q: 如何調試 Hook？

1. 使用日誌：

```python
logger = setup_hook_logging("my_hook", level=logging.DEBUG)
logger.debug(f"輸入資料: {hook_input}")
```

2. 查看日誌檔案：

```bash
tail -f .claude/hook-logs/my_hook.log
```

### Q: Hook 執行順序是什麼？

同一事件的多個 Hook 按照 `settings.json` 中定義的順序執行。

## 思考題

1. 為什麼要將 Hook 邏輯封裝在 `main()` 函式中？
2. 什麼時候應該使用 `block`，什麼時候使用 `allow`？
3. 如何設計 Hook 以便於測試？

---

*下一章：[如何擴展共用模組](../extend-lib/)*
*回到首頁：[Python 維護工程師實戰指南](../../)*
