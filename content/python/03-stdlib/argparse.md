---
title: "3.6 argparse - CLI 介面"
description: "命令列參數解析"
weight: 6
---

# argparse - CLI 介面

`argparse` 是 Python 標準庫中用於建立命令列介面（CLI）的模組。它能自動生成幫助訊息、處理各種參數類型，並進行輸入驗證。

## 基本用法

### 最簡單的 CLI

```python
import argparse

parser = argparse.ArgumentParser(description="我的程式")
parser.add_argument("filename", help="要處理的檔案")
args = parser.parse_args()

print(f"處理檔案: {args.filename}")
```

執行：

```bash
$ python script.py myfile.txt
處理檔案: myfile.txt

$ python script.py --help
usage: script.py [-h] filename

我的程式

positional arguments:
  filename    要處理的檔案

options:
  -h, --help  show this help message and exit
```

## 參數類型

### 位置參數（Positional Arguments）

必須提供的參數：

```python
parser.add_argument("filename")
# 使用: python script.py myfile.txt
```

### 可選參數（Optional Arguments）

使用 `-` 或 `--` 開頭：

```python
parser.add_argument("-v", "--verbose", action="store_true")
parser.add_argument("-o", "--output", default="output.txt")
# 使用: python script.py -v -o result.txt
```

### 布林旗標

```python
# store_true：出現時為 True
parser.add_argument("--debug", action="store_true")

# store_false：出現時為 False
parser.add_argument("--no-cache", action="store_false", dest="cache")
```

## 實際範例：Hook 驗證器

來自 `.claude/lib/hook_validator.py`：

```python
def main():
    """命令行介面"""
    parser = argparse.ArgumentParser(
        description="Hook 合規性驗證工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例:
  # 驗證單一 Hook
  python hook_validator.py .claude/hooks/my-hook.py

  # 驗證所有 Hook
  python hook_validator.py --all

  # 輸出 JSON 格式
  python hook_validator.py --all --json

  # 自訂 Hook 目錄
  python hook_validator.py --all --dir .claude/hooks
        """
    )

    parser.add_argument(
        "hook_path",
        nargs="?",
        help="Hook 檔案路徑（相對或絕對）"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="驗證所有 Hook 檔案"
    )
    parser.add_argument(
        "--dir",
        help="自訂 Hook 目錄路徑（預設 .claude/hooks）"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="輸出 JSON 格式"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="嚴格模式：將 warning 視為 error"
    )

    args = parser.parse_args()

    # 根據參數執行不同邏輯
    if args.all:
        results = validate_all_hooks(hooks_dir=args.dir)
    elif args.hook_path:
        results = [validate_hook(args.hook_path)]
    else:
        parser.print_help()
        sys.exit(1)

    # 輸出結果
    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(format_validation_report(results))
```

## 常用參數選項

### nargs - 參數數量

```python
# 單一值（預設）
parser.add_argument("filename")

# 可選（0 或 1）
parser.add_argument("output", nargs="?", default="out.txt")

# 零或多個
parser.add_argument("files", nargs="*")

# 一或多個
parser.add_argument("files", nargs="+")

# 固定數量
parser.add_argument("point", nargs=2, type=int)  # 需要兩個整數
```

### type - 型別轉換

```python
# 整數
parser.add_argument("--count", type=int, default=10)

# 浮點數
parser.add_argument("--ratio", type=float)

# 檔案路徑
from pathlib import Path
parser.add_argument("--config", type=Path)
```

### choices - 限制選項

```python
parser.add_argument(
    "--format",
    choices=["json", "yaml", "text"],
    default="text",
    help="輸出格式"
)
```

### default - 預設值

```python
parser.add_argument("--timeout", type=int, default=30)
parser.add_argument("--verbose", action="store_true")  # 預設 False
```

### required - 強制必填

```python
parser.add_argument("--config", required=True)
```

### dest - 屬性名稱

```python
parser.add_argument("--no-cache", action="store_false", dest="use_cache")
# args.use_cache 而非 args.no_cache
```

## 實際範例：Markdown 連結檢查器

來自 `.claude/lib/markdown_link_checker.py`：

```python
def main():
    """命令行介面"""
    parser = argparse.ArgumentParser(
        description="Markdown 連結檢查工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例:
  # 檢查單一文件
  python markdown_link_checker.py docs/README.md

  # 檢查整個目錄
  python markdown_link_checker.py --dir .claude/methodologies/

  # JSON 輸出
  python markdown_link_checker.py --dir docs/ --json

  # 只檢查當前目錄（不遞迴）
  python markdown_link_checker.py --dir docs/ --no-recursive
        """
    )

    parser.add_argument(
        "file_path",
        nargs="?",
        help="Markdown 檔案路徑"
    )
    parser.add_argument(
        "--dir",
        help="要檢查的目錄路徑"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="輸出 JSON 格式"
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="不遞迴檢查子目錄"
    )

    args = parser.parse_args()

    # 決定工作模式
    if args.dir:
        results = checker.check_directory(
            args.dir,
            recursive=not args.no_recursive
        )
    elif args.file_path:
        results = [checker.check_file(args.file_path)]
    else:
        parser.print_help()
        sys.exit(1)
```

## 進階技巧

### 參數群組

```python
parser = argparse.ArgumentParser()

# 必要參數群組
required = parser.add_argument_group("required arguments")
required.add_argument("--config", required=True)

# 可選參數群組
optional = parser.add_argument_group("optional arguments")
optional.add_argument("--verbose", action="store_true")
```

### 互斥參數

```python
group = parser.add_mutually_exclusive_group()
group.add_argument("--json", action="store_true")
group.add_argument("--yaml", action="store_true")
# 只能選擇其中一個
```

### 子命令

```python
parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(dest="command")

# add 子命令
add_parser = subparsers.add_parser("add", help="新增項目")
add_parser.add_argument("name")

# list 子命令
list_parser = subparsers.add_parser("list", help="列出項目")
list_parser.add_argument("--all", action="store_true")

args = parser.parse_args()
if args.command == "add":
    # 處理 add
    pass
elif args.command == "list":
    # 處理 list
    pass
```

## 完整範例模板

```python
#!/usr/bin/env python3
"""
我的 CLI 工具

使用方式:
    python my_tool.py input.txt -o output.txt --verbose
"""

import argparse
import sys


def create_parser() -> argparse.ArgumentParser:
    """建立參數解析器"""
    parser = argparse.ArgumentParser(
        description="我的 CLI 工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="範例: python my_tool.py input.txt -o output.txt"
    )

    parser.add_argument(
        "input",
        help="輸入檔案"
    )
    parser.add_argument(
        "-o", "--output",
        default="output.txt",
        help="輸出檔案 (預設: output.txt)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="詳細輸出"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0"
    )

    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    if args.verbose:
        print(f"Input: {args.input}")
        print(f"Output: {args.output}")

    # 主要邏輯
    process(args.input, args.output)


if __name__ == "__main__":
    main()
```

## 最佳實踐

### 1. 提供有意義的 help 訊息

```python
parser.add_argument(
    "--timeout",
    type=int,
    default=30,
    help="超時時間（秒），預設 30"  # 說明用途和預設值
)
```

### 2. 使用 epilog 提供使用範例

```python
parser = argparse.ArgumentParser(
    epilog="""
範例:
  %(prog)s file.txt                    # 處理單一檔案
  %(prog)s -d ./data --recursive       # 遞迴處理目錄
    """
)
```

### 3. 合理的 exit code

```python
if not results:
    sys.exit(0)  # 成功
else:
    sys.exit(1)  # 失敗
```

## 思考題

1. `nargs="?"` 和 `nargs="*"` 有什麼區別？
2. 為什麼 `--no-recursive` 使用 `action="store_true"` 而不是 `store_false`？
3. 如何實作一個同時支援 `--verbose` 和 `-v` 的參數？

## 實作練習

1. 為現有的 Python 腳本添加 CLI 介面
2. 實作一個支援子命令的 CLI 工具
3. 建立一個參數驗證函式，檢查檔案是否存在

---

*上一章：[logging - 日誌系統](../logging/)*
*下一模組：[物件導向設計](../../04-oop/)*
