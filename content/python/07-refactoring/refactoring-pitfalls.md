---
title: "重構陷阱與防護"
date: 2026-03-04
description: "三個真實重構事故的共通模式：部分更新問題與系統性防護方法"
weight: 76
---

# 重構陷阱與防護

「只是把變數移個位置」「只是搬個檔案」「只是加個參數」——這些聽起來無害的操作，在我們的專案中分別造成了 7 個 Hook 靜默失敗、5 個 Hook 啟動崩潰、以及使用者看到莫名其妙的 "hook error" 訊息。

本章整合三個真實事故（IMP-003、IMP-005、IMP-006），分析它們的共通模式，並建立一套防護方法。如果你只帶走一句話，請記住：**修改了定義，就必須更新所有引用**。

## 三個陷阱的概覽

| 陷阱 | 重構類型 | 遺漏 | 靜默時間 |
|------|---------|------|---------|
| 作用域迴歸 (IMP-003) | 變數從全域移入函式 | 引用該變數的函式未更新 | 2+ sessions |
| Import 未同步 (IMP-005) | 模組搬遷至子目錄 | 引用該模組的檔案未更新 | 直到下次啟動 |
| 靜默故障 (IMP-006) | 函式簽名變更 | 部分 call site 未更新 | 直到該路徑被執行 |

三者看似不同，但根本原因完全一致：**修改了定義，但沒有更新所有引用**。

---

## 陷阱一：作用域迴歸

> 本節是概要。IMP-003 的完整分析（含 LEGB 規則詳解、AST 修正腳本）請見[作用域迴歸案例研究](../scope-regression/)。

### 事件摘要

W24 的任務是統一 16 個 Hook 的 logger 初始化風格：從模組級初始化（全域變數）改為 `main()` 內初始化（區域變數）。

```python
# 修改前：logger 是全域變數，所有函式可存取
logger = setup_hook_logging("my-hook")

def helper():
    logger.info("working...")  # OK：LEGB 在 Global 層找到

# 修改後：logger 變成 main() 的區域變數
def helper():
    logger.info("working...")  # NameError! helper 看不到 main 的區域變數

def main():
    logger = setup_hook_logging("my-hook")
    helper()
```

### 為什麼危險

兩個因素疊加讓這個 bug 特別難發現：

1. **`py_compile` 抓不到**：`logger.info(...)` 語法完全合法，名稱解析要到執行時才發生
2. **頂層例外處理吞掉了 `NameError`**：`run_hook_safely()` 捕捉所有 `Exception`，Hook 靜默失敗而非 crash（詳見 [5.5 頂層例外處理機制](../../05-error-testing/error-infrastructure/)）

結果：7 個 Hook 在至少 2 個 session 中靜默失敗，41 個函式需要修正，+143/-81 行修改——全部源自一個「只是移動定義位置」的操作。

### 正確做法

修改前用 grep 或 AST 列出所有引用，逐一加入 `logger` 參數，再用 AST 驗證無遺漏。完整的四步修正流程見[作用域迴歸案例研究](../scope-regression/)。

---

## 陷阱二：Import 未同步

### 背景

W22 重構將 `common_functions.py` 從 `.claude/hooks/` 遷移至 `.claude/hooks/lib/`。但只更新了部分 Hook 的 import 路徑。

```python
# 遷移前（模組在同目錄）
sys.path.insert(0, str(Path(__file__).parent))
from common_functions import hook_output  # OK

# 遷移後（模組移到 lib/，但 import 未更新）
sys.path.insert(0, str(Path(__file__).parent))
from common_functions import hook_output  # ModuleNotFoundError!

# 正確的遷移後寫法
from lib.common_functions import hook_output  # OK
```

### 5 Why 分析

1. Hook 啟動時拋出 `ModuleNotFoundError`
2. `from common_functions import ...` 找不到模組
3. `common_functions.py` 已遷移至 `lib/` 子目錄
4. 遷移時只更新了**部分** Hook 的 import 路徑
5. **根本原因**：模組遷移後缺乏「全量引用更新」步驟

5 個 Hook 受影響，涵蓋 SessionStart、PostToolUse、UserPromptSubmit 三種事件類型。

### 第二次發生

同一個模式在後續又發生了一次。W24 統一 `sys.path` 風格時，`task-dispatch-readiness-check.py` 的 `sys.path` 只包含 `.claude/hooks/`，缺少 `.claude/lib/`。

更危險的是，這次的 error 與另一個 Hook 的 error（plugin timeout）同時出現。移除 plugin 後以為問題解決了，實際上只消除了其中一個來源。

**教訓**：多個不同來源的 error 同時存在時，修一個後不能假設全部修好了——必須逐一驗證每一個。

### 正確的遷移步驟

```bash
# Step 1：列出所有引用
grep -r "from common_functions import" .claude/hooks/*.py

# Step 2：列出所有直接 import
grep -r "import common_functions" .claude/hooks/*.py

# Step 3：逐一更新 import 路徑（根據 Step 1-2 的清單）

# Step 4：逐一驗證
for f in .claude/hooks/*.py; do
    echo "Testing $f..."
    echo '{}' | python3 "$f" 2>&1 | head -5
done
```

### 與陷阱一的對比

| 維度 | 陷阱一（作用域） | 陷阱二（Import） |
|------|----------------|-----------------|
| 修改了什麼 | 變數定義的位置 | 模組檔案的位置 |
| 遺漏了什麼 | 引用該變數的函式 | 引用該模組的檔案 |
| py_compile 能偵測？ | 否 | 否 |
| grep 能找出？ | 是 | 是 |

根本結構完全相同：**移動了定義，沒有追蹤引用**。

---

## 陷阱三：靜默故障

IMP-006 收錄了四個 Hook 隱性故障案例。這裡選取三個，分別代表不同的「部分更新」變體。

### 案例 A：函式參數遺漏

`save_check_log()` 需要 5 個參數，但某個 call site 只傳了 4 個：

```python
# 第 471 行（正確）
save_check_log(prompt, result, is_dev, count, logger)

# 第 453 行（早期返回路徑，遺漏 logger）
save_check_log(prompt, None, False, 0)  # TypeError: missing argument
```

同一個函式在同一個檔案中呼叫了兩次。第二次是在早期返回（early return）路徑上，開發者 copy-paste 後漏掉了最後一個參數。

這跟陷阱一本質相同——函式簽名變更後（加入 `logger` 參數），沒有更新**所有** call site。

### 案例 B：語義分類錯誤

`command-entrance-gate-hook.py` 將「分析、調查、研究」等關鍵字歸入 `DEVELOPMENT_KEYWORDS`，導致分析命令被當作開發命令處理，被要求先建立 Ticket 才能執行。

但根據決策樹，分析類命令走「問題處理流程」，不需要 Ticket。

```python
# 錯誤：ANALYSIS_KEYWORDS 被放進 DEVELOPMENT_KEYWORDS
DEVELOPMENT_KEYWORDS = [
    "implement", "create", "fix",
    "analyze", "investigate", "research",  # 這些不是開發命令！
]

# 正確：分析類關鍵字應在白名單中
exploration_patterns = ["analyze", "investigate", "research", "trace"]
```

這不是典型的「引用未更新」，但仍屬於**部分更新**問題：Hook 的語義分類與決策樹的語義定義不同步。修改了決策樹的行為分類，但沒有同步更新 Hook 的關鍵字分類。

### 案例 C：多路徑覆蓋不完整

`agent-ticket-validation-hook.py` 有兩條錯誤路徑：

```python
# 路徑 1：未預期異常（已有 stderr 輸出）
except Exception:
    print(f"[Error] {traceback.format_exc()}", file=sys.stderr)

# 路徑 2：有意阻止（遺漏 stderr 輸出）
if not valid:
    return 2  # exit code 2，但沒有 stderr 告訴使用者為什麼
```

開發者只覆蓋了第一條路徑。第二條路徑（業務邏輯拒絕）執行時，使用者只看到 "hook error" 和 "No stderr output"，無法得知被拒絕的原因。

**教訓**：一個函式的所有非成功路徑都需要相同等級的錯誤報告，不能只覆蓋 exception 路徑。

---

## 共通模式：部分更新

三個陷阱的根本結構完全相同：

```
          修改了 A
              |
    A 有 N 個引用/依賴
              |
     只更新了其中 M 個
              |
       N - M 個壞掉了
              |
         靜默失敗
```

不管 A 是變數定義（陷阱一）、模組路徑（陷阱二）、還是函式簽名（陷阱三），模式一致：

1. 修改了某個「被依賴的東西」
2. 沒有找出**所有**依賴它的地方
3. 遺漏的部分在**執行時**才爆炸
4. 由於例外處理或 UI 限制，爆炸被吞掉

### 防護公式

```
安全的重構 = 修改定義 + 列出全部引用 + 逐一更新 + 逐一驗證
```

四步少一步都會出事：

- 少了「列出全部引用」 -- 你不知道影響範圍（三個陷阱的共通原因）
- 少了「逐一更新」 -- 知道但沒做完（陷阱二的第二次發生）
- 少了「逐一驗證」 -- 做了但不確定對不對（陷阱一用 py_compile 驗證的盲點）

### grep：防護公式的第一步

「列出全部引用」聽起來很簡單，但容易被跳過。以下是每種重構類型對應的 grep 命令：

```bash
# 變數作用域變更：找出所有引用某變數的位置
grep -rn "logger" hooks/*.py | grep -v "def.*logger" | grep -v "^#"

# 模組遷移：找出所有 import 語句
grep -rn "from common_functions import" .claude/hooks/*.py
grep -rn "import common_functions" .claude/hooks/*.py

# 函式簽名變更：找出所有呼叫端
grep -rn "save_check_log(" .claude/hooks/*.py
```

重點不是 grep 語法有多精確，而是**養成習慣**：修改定義之前，先跑一次搜尋，看看這個名稱出現在哪些地方。這一步花不到 30 秒，但能避免幾小時的除錯。

---

## 防護工具箱

不同的驗證工具能偵測不同層級的問題。沒有銀彈，但可以根據重構類型選擇正確的工具組合。

### 工具能力對照表

| 工具 | 語法錯誤 | 作用域問題 | Import 問題 | 參數數量 | 語義正確性 |
|------|---------|-----------|------------|---------|-----------|
| `py_compile` | 是 | **否** | **否** | **否** | **否** |
| `grep` / 文字搜尋 | -- | 找出引用 | 找出引用 | 找出 call site | -- |
| AST 分析 | 是 | **是** | 部分 | **是** | **否** |
| `pylint` | 是 | **是** | **是** | **是** | **否** |
| `mypy` | 是 | **是** | **是** | **是** | **否** |
| 實際執行 | 是 | **是** | **是** | **是** | **是** |

### 關鍵發現

**py_compile 是必要但不充分的**。它能確認「Python 能讀懂這個檔案」，但不能確認「這個檔案能正確執行」。三個陷阱中沒有一個能被 py_compile 偵測到。

**grep 是最可靠的第一步**。不管是變數引用、import 路徑還是函式呼叫，文字搜尋都能找出所有使用處。它不聰明，但不會遺漏。

**實際執行是唯一能驗證語義的工具**。案例 B 的語義分類錯誤，靜態工具全部無法偵測——因為程式碼邏輯上沒錯，錯的是**業務語義**。

### 按重構類型選擇工具

| 重構類型 | 最低要求 | 建議 |
|---------|---------|------|
| 移動變數定義 | grep + AST 分析 | + 實際執行覆蓋所有路徑 |
| 移動模組檔案 | grep + 逐一 import 驗證 | + `echo '{}' \| python3 file.py` |
| 修改函式簽名 | grep + AST 參數檢查 | + pylint + 測試覆蓋 |
| 修改關鍵字/分類 | 與設計文件交叉比對 | + 手動場景測試 |
| 統一風格（批量） | 先 grep 建立完整清單 | + 逐一驗證，不依賴數量判斷 |

### 批量重構的特殊風險

統一化重構（如「把 16 個 Hook 的 logger 風格統一」）比單一檔案的修改危險得多，因為：

1. **數量產生虛假信心**：改了 13 個成功了，容易假設剩下 3 個也沒問題
2. **機械性動作降低警覺**：重複相同操作 16 次，注意力會下降
3. **驗證疲勞**：逐一驗證 16 個檔案很煩，容易偷懶跳過

對策：建立完整清單，逐一打勾，用腳本自動化驗證。

---

## 建立自己的重構檢查清單

根據本章三個陷阱的經驗，任何涉及「移動或修改被引用物件」的重構，都應該執行以下清單：

### 修改前（強制）

- [ ] 用 `grep` 列出所有引用/使用處，建立完整清單
- [ ] 評估每個引用是否需要同步更新
- [ ] 確認驗證方法（不能只用 py_compile）

### 修改中

- [ ] 按清單逐一更新每個引用
- [ ] 每更新一個就在清單打勾，不跳過

### 修改後（強制）

- [ ] 用 AST 分析或 pylint 驗證作用域和參數
- [ ] 實際執行（或測試）覆蓋所有修改過的檔案
- [ ] 如果是批量修改，逐一驗證每個檔案，不依賴數量判斷

---

## 思考題

1. 為什麼動態語言（Python、JavaScript）比靜態語言（Java、Dart）更容易出現這類問題？靜態語言的什麼機制能在編譯期偵測到陷阱一和陷阱二？

2. 陷阱三案例 B（語義分類錯誤）無法被任何靜態工具偵測。你會如何設計一個測試來防護這類問題？

3. 「頂層例外處理吞掉錯誤」既是安全機制（防止 crash），也是風險（隱藏 bug）。如何在這兩個需求之間取得平衡？（可參考 [5.5 頂層例外處理機制](../../05-error-testing/error-infrastructure/) 的設計方案）

## 實作練習

1. 選擇一個使用全域變數的 Python 專案，嘗試將一個全域變數移入函式內部。在修改前後分別用 py_compile、AST 分析、pylint 驗證，比較各工具的偵測能力。

2. 寫一個 Python 腳本，接受一個 Python 檔案和一個變數名稱作為輸入，輸出「所有引用該變數但沒有在參數中接收它的函式」清單。

3. 設計一個模組遷移的自動化腳本：接受舊路徑和新路徑，自動搜尋所有 `import` 語句並更新，最後逐一驗證每個修改過的檔案是否能成功 import。

---

*上一章：[大規模統一化重構](../unified-infrastructure/)*
*下一章：[非程式碼的重構](../non-code-refactoring/)*
*相關：[作用域迴歸案例研究](../scope-regression/) -- 陷阱一的完整深入分析*
*相關：[5.5 頂層例外處理機制](../../05-error-testing/error-infrastructure/) -- 例外處理如何隱藏 bug 的機制分析*
