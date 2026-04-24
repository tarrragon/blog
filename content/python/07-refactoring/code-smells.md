---
title: "程式碼壞味道偵測"
date: 2026-03-04
description: "從三級分類系統到偵測工具鏈，建立系統化的程式碼品質防線"
weight: 72
---

_上一章：[重構的動機與策略](/python/07-refactoring/refactoring-strategy/)_

「程式碼壞味道」(Code Smell) 是 Martin Fowler 在《Refactoring》中提出的概念：程式碼中暗示深層問題的表面跡象。壞味道不是 Bug，程式仍然能正常執行，但它們預告了維護成本的攀升。上一章介紹了認知負擔指數——重複程式碼和難以理解的結構是指數升高的主要原因。本章把這些讓認知負擔上升的具體模式系統化，稱為「壞味道」。

本章建立一套從「識別」到「行動」的完整流程：先以三級分類理解問題的嚴重程度，再以工具鏈偵測，最後透過 5 Why 分析找到根本原因。

## 壞味道三級分類

不是所有壞味道都一樣嚴重。依照影響範圍和修復成本，分成三個等級：

### 第一級：實作級 -- 單一檔案內的問題

影響範圍最小，通常改一個檔案就能解決。

| Pattern ID | 壞味道             | 典型症狀                      | 風險 |
| ---------- | ------------------ | ----------------------------- | ---- |
| IMP-001    | 重複程式碼散落各處 | 同一個函式在 4 個檔案各寫一次 | 中   |
| IMP-002    | 魔法數字           | `line[9:]` -- 為什麼是 9？    | 低   |

**IMP-001 範例：四份一模一樣的函式**

```python
# hooks/pre_commit.py
def run_git_command(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip()

# hooks/post_merge.py -- 完全相同的程式碼
def run_git_command(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip()

# hooks/branch_check.py -- 又是一模一樣
# hooks/worktree_guardian.py -- 第四份...
```

問題不在於程式碼本身有錯，而在於當你需要加入錯誤處理時，要改四個地方，漏掉一個就是 Bug。

**IMP-002 範例：沒人記得的數字**

```python
def parse_worktree_line(line):
    if line.startswith("worktree "):
        return line[9:]  # 三個月後，你還記得 9 是什麼嗎？
```

### 第二級：架構級 -- 跨模組的結構問題

影響多個檔案的互動方式，需要架構層面的重新設計。

| Pattern ID | 壞味道           | 典型症狀                     | 風險 |
| ---------- | ---------------- | ---------------------------- | ---- |
| ARCH-001   | 配置與程式碼混合 | 800 行的檔案，一半是配置資料 | 高   |

**ARCH-001 範例：被配置淹沒的邏輯**

```python
# 一個 800+ 行的 Hook 檔案
PROTECTED_BRANCHES = ["main", "master", "develop"]
ALLOWED_PATTERNS = ["feat/*", "fix/*", "chore/*"]
ERROR_MESSAGES = {
    "branch_not_allowed": "分支名稱不符合規範",
    "missing_ticket": "缺少 Ticket 引用",
    # ... 數十行配置繼續
}

def check_branch():
    # 真正的邏輯只有幾十行，卻埋在幾百行配置之下
    pass
```

修改一條錯誤訊息就要打開整個程式碼檔案，負責配置的人被迫閱讀程式邏輯，負責邏輯的人被迫捲過數百行配置——兩者都承受了不必要的負擔。

### 第三級：遷移級 -- 重構過程中引入的問題

最危險的一類。它們不是原本就存在的壞味道，而是在修復其他壞味道時「創造」出來的新問題。遷移級問題在 Error Pattern 系統中仍使用 IMP 前綴，因為它們本質上是實作層面的作用域和 Import 問題——只是發生在重構過程中，因此格外危險。

| Pattern ID | 壞味道               | 典型症狀                        | 風險 |
| ---------- | -------------------- | ------------------------------- | ---- |
| IMP-003    | 重構作用域迴歸       | 變數移入函式後，其他函式找不到  | 高   |
| IMP-005    | 模組遷移 Import 斷裂 | 檔案搬家後，Import 路徑沒跟著改 | 高   |

**IMP-003 範例：搬家沒留新地址**

```python
# 修正前：logger 是全域變數，所有函式都看得到
logger = setup_hook_logging("hook-name")

def helper_function():
    logger.info("doing something")  # OK，全域可見

def main():
    result = helper_function()

# 修正後：logger 搬進 main()，但 helper 沒收到通知
def helper_function():
    logger.info("doing something")  # NameError! logger 不見了

def main():
    logger = setup_hook_logging("hook-name")  # 現在是區域變數
    result = helper_function()  # helper 找不到 logger
```

這個 Bug 在真實專案中影響了 7 個 Hook、41 個函式。更危險的是，例外捕捉機制將錯誤靜默吞掉，直到開發者主動翻查日誌才發現。在事件發生當時，錯誤被靜默吞掉。此問題後來已修復，現在 Hook 失敗會輸出到 stderr 確保開發者可見。

### 三級分類速查表

| 級別   | 影響範圍 | 修復成本 | 偵測難度         | 典型 Pattern     |
| ------ | -------- | -------- | ---------------- | ---------------- |
| 實作級 | 單一檔案 | 低       | 容易             | IMP-001, IMP-002 |
| 架構級 | 跨模組   | 中-高    | 中等             | ARCH-001         |
| 遷移級 | 重構過程 | 高       | 困難（可能靜默） | IMP-003, IMP-005 |

## 偵測工具鏈

識別壞味道不能只靠肉眼。以下工具從簡單到進階，組成完整的偵測鏈。

### 第一層：grep 模式掃描

最快的初步篩檢，幾秒鐘就能掃完整個專案。

```bash
# 偵測 IMP-001：找出重複的函式定義
grep -rh "^def " hooks/*.py | sort | uniq -c | sort -rn | head -10
#  4 def run_git_command(cmd):    <-- 出現 4 次，高度疑似重複
#  2 def parse_output(line):      <-- 出現 2 次，需要確認

# 偵測 IMP-002：找出魔法數字
grep -rn -E "\[[0-9]+:\]" hooks/*.py      # 數字切片 [9:]
grep -rn "sleep([0-9]" hooks/*.py        # 硬編碼的等待時間
grep -rn "range([0-9]" hooks/*.py        # 硬編碼的迴圈次數

# 偵測 ARCH-001：找出超長檔案
find hooks/ -name "*.py" -exec wc -l {} \; | awk '$1 > 500'
# 847 hooks/user_prompt_submit.py    <-- 紅色警報

# 偵測 IMP-005：模組遷移後殘留的舊 Import
grep -rn "from common_functions import" hooks/*.py
# 如果 common_functions.py 已經搬到 lib/，這些都是未更新的引用
```

**grep 的限制**：只做文字比對，無法理解程式碼結構。`line[9:]` 會被抓到，但 `offset = 9; line[offset:]` 就抓不到了。

### 第二層：AST 分析

Python 的 `ast` 模組能解析程式碼結構，做到 grep 做不到的事。

```python
import ast
import sys

def find_scope_references(filename, variable_name):
    """找出所有在非 main 函式中引用特定變數的位置。
    限制：此函式只做名稱比對，無法追蹤賦值或閉包捕獲。"""
    with open(filename) as f:
        tree = ast.parse(f.read())

    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name != "main":
            param_names = {arg.arg for arg in node.args.args}
            if variable_name in param_names:
                continue  # 函式已接收此變數為參數，非問題
            for child in ast.walk(node):
                if isinstance(child, ast.Name) and child.id == variable_name:
                    issues.append(f"  {node.name}() 在第 {child.lineno} 行引用 {variable_name}")
                    break
    return issues

# 使用方式
issues = find_scope_references("hooks/pre_commit.py", "logger")
for issue in issues:
    print(issue)
```

**AST 能做而 grep 做不到的事**：

| 能力                 | grep | AST  |
| -------------------- | ---- | ---- |
| 找出字面上的文字模式 | 可以 | 可以 |
| 區分變數定義和使用   | 不行 | 可以 |
| 分析函式的參數列表   | 不行 | 可以 |
| 偵測作用域問題       | 不行 | 可以 |
| 計算巢狀深度         | 不行 | 可以 |

自己撰寫 AST 腳本適合針對特定問題的精確偵測。但對於更廣泛的靜態分析需求，現成工具能用更低的成本涵蓋更多場景。

### 第三層：靜態分析工具比較

不同工具的偵測能力差異很大，選錯工具會漏掉關鍵問題。

| 偵測能力                  | py_compile | pylint | mypy   |
| ------------------------- | ---------- | ------ | ------ |
| 語法錯誤                  | 可以       | 可以   | 可以   |
| 未使用的變數              | 不行       | 可以   | 不行   |
| 作用域問題 (IMP-003)      | **不行**   | 可以   | 部分   |
| Import 路徑錯誤 (IMP-005) | **不行**   | 可以   | 部分\* |
| 型別錯誤                  | 不行       | 部分   | 可以   |
| 程式碼風格                | 不行       | 可以   | 不行   |
| 執行速度                  | 最快       | 中等   | 較慢   |

\*mypy 偵測 Import 路徑錯誤需正確設定 MYPYPATH 或 mypy.ini，對動態 `sys.path` 無效。

`py_compile` 只檢查語法是否合法。`logger` 變數不存在是執行期錯誤，不是語法錯誤。這就是為什麼 IMP-003 能通過 `py_compile` 的檢查，卻在執行時爆炸。

```bash
# py_compile：語法 OK 不代表能跑
python3 -m py_compile hooks/pre_commit.py  # 通過！但 logger 根本找不到

# pylint：能抓到更多問題
pylint hooks/pre_commit.py
# E0602: Undefined variable 'logger' (undefined-variable)

# 實際執行：最可靠的驗證
python3 hooks/pre_commit.py < /dev/null
# NameError: name 'logger' is not defined
```

**建議的偵測策略**：先用 grep 做快速掃描，對疑似問題用 AST 確認，重構後用 pylint 或實際執行做最終驗證。

| 使用場景             | 推薦工具      | 適用理由                              |
| -------------------- | ------------- | ------------------------------------- |
| 快速掃描重複模式     | grep          | 速度最快，適合初篩                    |
| 確認特定函式結構問題 | AST 分析      | 精確到語法層級，無正規表達式偽陽性    |
| 重構後整體品質驗證   | pylint / mypy | 涵蓋面廣，可持續整合                  |
| 作用域和型別問題     | 實際執行      | py_compile 不夠，需 pytest 或直接執行 |

## 5 Why 根因分析

找到壞味道只是起點；若要防止問題再次出現，必須找到根本原因。

### 完整範例：ARCH-001 配置與程式碼混合

```
問題：單一 Hook 檔案超過 800 行，其中約一半是硬編碼的配置資料

Why 1: 為什麼檔案會有 800 行？
--> 因為配置資料（分支規則、錯誤訊息、檔案模式）和程式邏輯
    全部寫在同一個檔案中

Why 2: 為什麼配置和邏輯放在一起？
--> 因為開發時為求快速，直接在程式碼中定義配置常數

Why 3: 為什麼選擇快速做法而非分離？
--> 因為缺乏配置管理策略，沒有標準化的做法可以遵循

Why 4: 為什麼沒有配置管理策略？
--> 因為 Hook 系統初期設計時，只考慮了功能實現，
    沒有考慮到配置會不斷增長

Why 5: 為什麼初期設計沒考慮配置增長？
--> 【根本原因】缺乏明確的架構原則指導配置與程式碼分離
```

**根因指向的行動**：制定架構原則，明確規定什麼放在 YAML、什麼留在程式碼中。

| 資料類型     | 正確位置      | 判斷依據                             |
| ------------ | ------------- | ------------------------------------ |
| 業務規則配置 | YAML 檔案     | 會隨環境改變嗎？非工程師可能修改嗎？ |
| 錯誤訊息     | YAML 或 i18n  | 需要多語言嗎？                       |
| 常數定義     | Python 常數檔 | 與程式邏輯緊密耦合嗎？               |
| 程式邏輯     | Python 檔案   | 是演算法或流程控制嗎？               |

### 5 Why 的技巧

1. **持續追問**：第一個「為什麼」幾乎永遠不是根本原因
2. **客觀描述**：寫「缺乏審查機制」而不是「某人偷懶」
3. **可驗證**：每一層的回答都應該可以被事實確認
4. **可行動**：最終原因必須能轉化成具體的改善措施
5. **停止條件**：當答案指向「流程或規範的缺失」時，通常就是根因

## Error Patterns 經驗傳承系統

個人發現壞味道是一次性的收穫；將其記錄為 Error Pattern，才能讓整個團隊持續受益。

### 目錄結構

```
.claude/error-patterns/
├── README.md              # 系統說明與索引
├── test/                  # 測試相關：TEST-001, TEST-002, ...
├── documentation/         # 文件相關：DOC-001, DOC-002, ...
├── architecture/          # 架構相關：ARCH-001, ARCH-002, ...
└── implementation/        # 實作相關：IMP-001, IMP-002, ...
```

### Pattern 文件模板

```markdown
# [Pattern ID]: [簡短標題]

## 基本資訊

- **Pattern ID**: {CATEGORY}-{NNN}
- **風險等級**: 高/中/低
- **發現日期**: YYYY-MM-DD

## 問題描述

### 症狀

[用程式碼範例展示問題的外在表現]

### 根本原因 (5 Why 分析)

1. Why 1: ...
2. Why 2: ...
3. Why 3: ...
4. Why 4: ...
5. Why 5: (根本原因)

## 解決方案

### 正確做法

[程式碼範例]

### 錯誤做法 (避免)

[程式碼範例]

## 檢測方法

[grep 指令、AST 腳本或工具配置]
```

### 建立流程

1. **識別模式**：確認問題確實重複出現（至少 2 次）
2. **分類歸檔**：選擇 TEST / DOC / ARCH / IMP
3. **5 Why 分析**：找出根本原因
4. **記錄方案**：寫下正確和錯誤做法的對比
5. **加入偵測**：提供 grep 或 AST 的偵測指令

## 從識別到行動的決策流程

找到壞味道之後，不是每個都要立刻修。用這個流程判斷優先級：

```
發現壞味道
    |
    v
影響正確性嗎？（會導致 Bug）
    |
    +-- 是 --> 立即修復，建立 Ticket
    |
    +-- 否 --> 影響多個檔案嗎？
                |
                +-- 是 --> 記錄 Error Pattern + 建立 Ticket
                |
                +-- 否 --> 認知負擔高嗎？（函式超長、巢狀太深）
                            |
                            +-- 是 --> 排入下次重構
                            |
                            +-- 否 --> 記錄，暫不處理
```

**關鍵原則**：遷移級壞味道（IMP-003、IMP-005）幾乎都會影響正確性，必須立即處理。實作級壞味道（IMP-001、IMP-002）通常不影響正確性，可以排入重構計畫。

## 實作練習

### 練習 1：分類壞味道

以下程式碼有哪些壞味道？各屬於哪一級？

```python
BRANCH_RULES = {
    "protected": ["main", "master"],
    "max_length": 50,
    "patterns": ["feat/*", "fix/*", "chore/*"],
}

def check(data):
    res = []
    for i in range(len(data)):
        if data[i]["type"] == "A":
            if data[i]["status"] == 1:
                if data[i]["value"] > 100:
                    res.append(data[i]["name"][5:])
    return res
```

<details>
<summary>參考答案</summary>

**實作級壞味道**：

1. **重複程式碼散落各處** (IMP-001) -- `data[i]` 在迴圈中重複出現 5 次，應提取為區域變數
2. **魔法數字** (IMP-002) -- `1`、`100`、`[5:]` 含義不明
3. **巢狀過深** -- 三層 if 應該用 Guard Clause 攤平
4. **使用 range(len())** -- 應該直接迭代集合

**架構級壞味道**：5. **配置與程式碼混合** (ARCH-001) -- `BRANCH_RULES` 字典直接寫在程式碼中

</details>

### 練習 2：設計偵測指令

針對以下壞味道，各寫一條 grep 指令來偵測：

1. 在 `src/` 目錄下找出所有超過 3 層巢狀的 if 語句
2. 找出可能的重複函式定義
3. 找出所有引用已遷移模組 `old_utils` 的檔案

<details>
<summary>參考答案</summary>

```bash
# 1. 找出深層巢狀（透過縮排層級近似偵測，偵測第 4 層起始）
grep -rn "^                if " src/*.py  # 16 個空格 = 第四層（超過 3 層）
# 這個方法假設每層縮排使用 4 個空格。如果專案使用 2 格縮排，對應數字應改為 8。
# 更可靠的做法是使用 AST 分析計算實際巢狀深度。

# 2. 找出重複的函式定義
grep -rh "^def " src/*.py | sort | uniq -c | sort -rn | head -10

# 3. 找出未更新的舊 import
grep -rn "from old_utils import" src/*.py
grep -rn "import old_utils" src/*.py
```

</details>

### 練習 3：5 Why 分析

對以下問題進行 5 Why 分析：「重構時把 `logger` 從全域移到 `main()` 內部，導致 7 個 Hook 靜默失敗」。

<details>
<summary>參考答案</summary>

```
Why 1: 為什麼 7 個 Hook 會失敗？
--> 因為 helper 函式引用了 logger，但 logger 已不在全域作用域

Why 2: 為什麼 logger 不在全域了？
--> 因為重構要求統一 logger 初始化風格為「main() 內部」

Why 3: 為什麼只移動了 logger，沒有更新引用？
--> 因為執行重構時沒有先列出所有引用 logger 的函式

Why 4: 為什麼沒有做引用分析？
--> 因為缺乏「作用域變更檢查清單」的標準步驟

Why 5: 為什麼沒有這個檢查清單？
--> 【根本原因】重構流程缺乏「影響範圍分析」的強制步驟
```

**行動**：在每次變更變數作用域前，強制執行 grep 或 AST 分析列出所有引用。

</details>

## 小結

- 壞味道分三級：實作級影響單一檔案，架構級需跨模組重新設計，遷移級最危險——它是重構過程中創造出來的新問題
- 偵測工具鏈由淺入深：grep 快速掃描、AST 結構分析、pylint/mypy 靜態檢查
- `py_compile` 只檢查語法，無法偵測作用域問題和 Import 錯誤
- 5 Why 分析追問到「流程或規範的缺失」才是根因
- Error Patterns 把個人經驗變成團隊資產

_下一章：[DRY 原則與共用程式庫](/python/07-refactoring/dry-principle/)_
