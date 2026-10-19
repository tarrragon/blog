---
title: "從修改競爭判斷拆檔：何時拆、怎麼拆"
date: 2026-10-19
description: "用 git 歷史統計每個檔案被幾個不相干的需求修改、把結果當成單一職責的代理量測，修改熱點的分類與處理，以及在不改變對外行為的前提下拆分 Python 模組"
weight: 79
tags: ["python", "refactoring", "srp", "cognitive-load"]
---

這篇整理用版本歷史量測「一個檔案被幾個不相干的需求修改」、據此判斷是否拆檔，以及拆分 Python 模組時維持對外行為不變的做法。範例是一支 commit 守衛：多個 AI 代理人各自在自己的工作目錄同時開發時（下文稱並行期間），它在 git commit 執行之前檢查指令，擋下把 commit 寫進其他代理人工作目錄的寫法，命令解析、狀態判斷與提示訊息產生三種職責寫在同一個檔案裡。量測的前提是 commit 訊息帶有需求編號。

何時該重構、如何把重構分階段進行，在[重構的動機與策略](/python/07-refactoring/refactoring-strategy/)；從程式碼本身的寫法辨認問題，在[程式碼壞味道偵測](/python/07-refactoring/code-smells/)；把重複的程式碼收斂成共用模組，在[DRY 原則與共用程式庫](/python/07-refactoring/dry-principle/)；規則文件、操作手冊這類文字文件的拆分，在[依職責拆分文字文件](/record/document-split-by-responsibility/)。

## 修改競爭與單一職責原則

修改競爭指的是處理不相干需求的人要改同一個檔案。git 只在兩邊改動的行重疊或相鄰時產生合併衝突，所以同一個檔案的修改不一定互相阻擋；會讓它們互相等待的是三種情形：改動落在同一處（例如都在清單或檔尾追加一筆）、合併沒有文字衝突而行為互相影響（rebase 之後仍要重跑測試，確認兩邊沒有改壞對方），以及並行的代理人共用同一個工作目錄。這三種情形發生時，一個需求先改、先合併，下一個需求拉最新版、解衝突、重跑測試；下一週第三個需求要改這個檔，再等一次。排好順序與加強溝通能縮短每次等待的時間，而一個檔案承載的職責越多，落在它身上的不相干修改越多，等待的次數跟著增加。

單一職責原則（SRP）常被解讀成「一個模組只做一件事」，而「一件事」的範圍很難判斷。Robert C. Martin 給過一個更可操作的表述：

> 一個模組應該只有一個「改變的理由」。

他在 2014 年的說明裡把「理由」對到提出變更的人：同一群人（同一個角色）為了同一個目的提出的變更，屬於同一個理由；不同角色提出的變更要分開放。這個定義把抽象的「職責」換成了可以觀察的對象：**改變的理由**。版本歷史記下了每一次改變，也記下了它是為了哪一個需求（票、issue、PR）而做；需求數因此可以當成改變理由的代理量測。

| 現象                                   | 代表什麼                                       |
| -------------------------------------- | ---------------------------------------------- |
| 同一個需求的多次 commit 都改同一個檔   | 正常。同一主題的演進集中在一處，這是內聚       |
| 三、四個**不相干的需求**都要改同一個檔 | 這個檔有三、四種改變的理由，也就是三、四種職責 |

所以一個檔案被幾個不相干的需求修改，可以當成它有幾種改變理由的代理量測。判斷兩個需求是否相干，看它們是不是由不同的人或角色、為了不同的目的提出：同一個角色提出的五張票，在 Martin 的定義下仍是同一個理由。

### 行數與修改競爭的量測對象

常見的拆檔門檻是行數，例如超過 300 行就考慮拆。行數是檔案過大的症狀，而它在兩種檔案上會給出與修改競爭相反的結果：

| 情況                                       | 行數判斷       | 修改競爭判斷 |
| ------------------------------------------ | -------------- | ------------ |
| 200 行的骨架產生器，被 6 個不同需求改過    | 不會觸發       | 會觸發       |
| 900 行的解析器，只屬於同一個需求的連續演進 | 會觸發（誤判） | 不會觸發     |

行數量的是檔案的大小，修改競爭量的是一個檔案混了幾種改變的理由。SRP 在意的是改變的理由有幾種。

## 用 git 歷史量出熱點

commit 訊息帶有需求編號（票號、issue 號）時，可以直接算出每個檔案被幾個不同需求改過。下文把排行前面、被最多不同需求修改的檔案稱為修改熱點（簡稱熱點）；它與效能分析裡「最常執行的程式路徑」那種熱點是兩件事。

```python
"""依 commit 訊息中的需求編號，統計每個檔案被幾個不同需求修改。"""
import collections
import re
import subprocess

ISSUE_ID = re.compile(r"#(\d+)")  # 依專案的 commit 慣例調整

def collect_changes(since: str, path: str = ".") -> dict[str, set[str]]:
    log = subprocess.run(
        # core.quotePath=false：非 ASCII 檔名照原樣輸出，不轉成跳脫碼
        ["git", "-c", "core.quotePath=false", "log", f"--since={since}", "--no-merges",
         "--name-only", "--format=@@%s", "--", path],
        capture_output=True, text=True, check=True,
    ).stdout

    issues_per_file: dict[str, set[str]] = collections.defaultdict(set)
    current: set[str] = set()
    for line in log.splitlines():
        if line.startswith("@@"):
            current = set(ISSUE_ID.findall(line[2:]))
            continue
        if line and current:
            for issue in current:
                issues_per_file[line].add(issue)
    return issues_per_file

def report(since: str, top: int = 20) -> None:
    changes = collect_changes(since)
    ranked = sorted(changes.items(), key=lambda kv: -len(kv[1]))
    for path, issues in ranked[:top]:
        print(f"{len(issues):3d} 個需求  {path}")

if __name__ == "__main__":
    report("2 weeks ago")
```

腳本裡影響計數的設計：

- **統計的時間範圍**：`report()` 的引數是 `git log --since` 接受的時間字串（`"2 weeks ago"`、`"2026-01-01"`）。範圍要涵蓋幾輪需求，才看得出同一個檔案被不同需求反覆修改；範例的兩週適合需求密集的專案，修改頻率低的專案要拉長。被幾個需求修改算多，門檻跟著時間範圍變，所以比較排行的相對位置比看絕對數字穩定。腳本在 repo 的根目錄執行。
- **`--no-merges`**：`git log` 預設不列出 merge commit 改了哪些檔案，所以目前這個選項不影響結果；改用 `--first-parent` 或 `-m` 讓 merge commit 也列出檔案時，merge 會把整條分支的改動再算一次，`--no-merges` 先把它排除。
- **PR 號**：GitHub 的 squash merge 會在 commit 標題附上 `(#PR號)`，同一個需求會被算成需求號與 PR 號兩個；用這種慣例的專案要讓 `ISSUE_ID` 只比對需求編號的格式。
- **一則 commit 帶多個編號**：`ISSUE_ID.findall` 取出訊息裡的全部編號。一個 commit 同時處理多個需求時，它改過的每個檔都會記到每個需求名下。
- **把子需求歸到同一個主題**：點號格式的子需求（例如 `#120.3`），`#(\d+)` 只取第一段數字，本來就會算進根需求 120。子需求若有獨立編號（例如父需求 `#120`、子需求 `#135`），則要另備一份父子對照表，把子需求歸到根需求再計數；不歸併的話，同一主題的連續修改會被誤算成多個改變理由。

## 熱點的分類與處理方式

排行榜上名列前茅的檔案有些該拆、有些不該拆，依熱點類型分開處理：

| 熱點類型                                | 例子                                                       | 處理                                           |
| --------------------------------------- | ---------------------------------------------------------- | ---------------------------------------------- |
| 一般程式碼，被 3 個以上不相干的需求修改 | 一支同時負責「解析命令」「判斷狀態」「產生提示訊息」的模組 | **拆分評估**                                   |
| 同一主題的連續演進                      | 一個佇列模組，被同一個「排隊機制」需求的 5 張子票陸續修改  | 不拆，這是內聚                                 |
| 聚合檔：設定、註冊表、CHANGELOG、索引   | `settings.json`、外掛註冊清單                              | 不以職責拆分，改用「一項一檔」或「只追加」格式 |
| 只有測試檔是熱點                        | 一個大測試檔被多個需求加測項                               | 先看它測的產品檔；測試通常隨產品檔一起拆       |

聚合檔的處置跟一般程式碼相反。註冊表的職責是集中列出所有項目，每加一個功能就要登記一次，所以修改它的需求數會隨功能數一起增加。把它依職責拆成三份註冊表，每次登記仍然要改其中一份，衝突只是換到另一個檔案。這類檔案的解法是降低每次修改的衝突面，例如每個項目一個片段檔、由載入端合併。

## 從修改紀錄找出職責邊界

決定要拆之後，切檔之前先回頭讀那些修改：把近期改過這個檔案的每個需求列出來，寫下它改的是哪一種職責。

```text
需求 A：修正命令解析遇到引號時的錯誤        → 命令解析
需求 B：新增「並行期間」的判斷條件           → 狀態判斷
需求 C：提示訊息改成指引使用者改寫命令       → 訊息產生
需求 D：解析器支援 -C 參數                   → 命令解析
需求 E：並行期間改依工作位置過濾             → 狀態判斷
```

歸類之後，每一類職責是一個候選模組。這個例子分出命令解析、狀態判斷與訊息產生。

歸類後只剩一類時，這個檔案被多個需求修改的原因是同一主題的連續演進（內聚），或它是聚合檔，回到〈熱點的分類與處理方式〉的表重新判斷。

## 拆分 Python 模組的做法

### 用測試鎖住拆分前的行為

拆分是結構調整，對外行為要維持不變，所以動手之前先確認對外行為都有測試覆蓋，特別是**邊界與反例**：

```python
import pytest

import guard
from guard import evaluate  # 拆分前後都從這裡匯入

@pytest.fixture(autouse=True)
def fixed_parallel_state(monkeypatch):
    # 固定並行狀態：只有 /other 是其他代理人正在使用的工作目錄
    monkeypatch.setattr(guard, "is_parallel_period", lambda target_dir: target_dir == "/other")

@pytest.mark.parametrize("command, expected", [
    ("git commit -m 'msg'", "allow"),
    ("git -C /other commit -m 'msg'", "block"),   # 應擋：-C 把 commit 指到別的工作目錄
    ("echo 'git commit'", "allow"),               # 字串中出現的 git
])
def test_evaluate_behavior_is_unchanged(command, expected):
    assert evaluate(command) == expected
```

測試表裡的 `git -C /other commit` 是應該擋下的寫法。`is_parallel_period` 取決於執行當下有哪些代理人在工作，所以 fixture 先把它固定住，測試在任何機器上都得到同一個結果；`evaluate` 在模組層級查找這個名字，拆分前後同一個 `monkeypatch` 都替換得到。測試只驗證正常情況會放行時，拆分不小心改壞了擋下的判斷，測試依然全綠，拆分前後的差別不會出現在任何一項測試結果裡。

### 依職責萃取模組並保留原本的匯入路徑

把每一類職責的函式移到新模組，原模組改成套件：`guard/__init__.py` 從新模組匯入對外名稱，再以套件的名義重新匯出（re-export）：

```text
guard.py              ← 原本 1200 行，三種職責混在一起

guard/
├── __init__.py       ← 保留 evaluate 等對外名稱，呼叫端不用改
├── command_parse.py  ← 命令解析
├── state.py          ← 狀態判斷
└── messages.py       ← 訊息產生
```

```python
# guard/__init__.py
from .command_parse import parse_command
from .messages import build_block_message
from .state import is_parallel_period

def evaluate(command: str) -> str:
    parsed = parse_command(command)
    if parsed.is_commit and is_parallel_period(parsed.target_dir):
        print(build_block_message(parsed))
        return "block"
    return "allow"
```

原本寫 `from guard import evaluate` 的呼叫端不用改。等所有呼叫端都改用新路徑之後，再決定是否拿掉重新匯出。

### 把重複的判斷收斂到共用模組

拆分時常會發現同一種判斷在好幾個檔案各寫了一份，例如三支守衛各自實作「從命令中取出 commit 的目標工作目錄」。規則一改，三份都要跟著改：一個需求改多個檔案，業界叫散彈式修改（shotgun surgery），方向與修改競爭相反。

把它收斂成共用模組裡的單一函式，各處改為呼叫它，規則再改時只產生一次修改。遷移的步驟與遷移時的陷阱在[DRY 原則與共用程式庫](/python/07-refactoring/dry-principle/)。

### 把巨型分支改成分派表

一個函式的主體是一長串 `if/elif`、每個分支處理一種事件類型時，每新增一種事件類型都要改這個函式。改成分派表之後，新增一種事件類型只需要加一個處理函式並登記：

```python
# 改之前：每個新需求都要改這個函式
def handle(event):
    if event.kind == "commit":
        ...
    elif event.kind == "merge":
        ...
    elif event.kind == "rebase":
        ...

# 改之後：新增事件類型只需要加一個處理函式並登記
HANDLERS = {}

def register(kind):
    def decorator(func):
        HANDLERS[kind] = func
        return func
    return decorator

@register("commit")
def handle_commit(event): ...

@register("merge")
def handle_merge(event): ...

@register("rebase")
def handle_rebase(event): ...

def handle(event):
    handler = HANDLERS.get(event.kind)
    if handler is None:
        return None  # 與改之前相同：未知的事件類型不處理
    return handler(event)
```

分派表要讓檔案離開熱點排行，處理函式還得放進各自的模組：處理函式都寫在同一個檔案裡時，每個新需求仍然改這個檔，而且都在檔尾追加，兩個同時進行的需求照樣衝突。處理函式各放一個模組之後，負責 import 它們、讓裝飾器執行登記的那份清單又是一份聚合檔，登記改用片段式的機制——例如自動匯入某個目錄底下的所有模組，或用套件的 entry points——對應〈熱點的分類與處理方式〉裡聚合檔的處理。

### 讓拆出來的模組單向依賴

拆出來的模組只依賴比它底層的模組，循環匯入就不會出現。`state.py` 和 `messages.py` 需要互相呼叫時，先確認兩個方向的呼叫是否都必要，有時拿掉其中一邊就夠了；兩邊都必要時，常見的原因是兩者之間還有一塊共用的定義沒有抽出來，把它再往下抽一層（例如 `models.py`），讓兩者都依賴它。

### 搬移與修改分開提交

純搬移的 commit 不同時修改行為：搬移和修改混在同一個 commit 裡，測試一紅，就分不出是搬錯了還是改錯了。先提交一個只搬移、測試全綠的版本，行為的修改放在之後的 commit。

## 拆分的時機與等待中的需求

拆分要排在正在等待的需求**之前**。拆分合併之後，等待中的需求改以新版本為基準，各自只改自己職責所在的新檔：

```text
拆分前：命令解析、狀態判斷、訊息產生各有一個需求在等，三個都要改 guard.py → 一個接一個
拆分後：命令解析的需求改 command_parse.py、狀態判斷的改 state.py、訊息產生的改 messages.py → 可以同時進行
```

這是拆分換到的結果：原本要一個接一個做的三個需求，拆分之後可以平行處理。已經開工、在拆分之前就改了 `guard.py` 的分支，rebase 時會遇到 modify/delete 衝突（`guard.py` 在主線已經刪除），要手動把改動移到對應的新檔，所以拆分要在這些需求開工之前合併。

過一段時間後再跑一次熱點統計，確認這個檔案與拆出來的新檔，被不同需求修改的次數確實下降。某個新檔很快又成為熱點時，先檢查當初的職責分類是否切錯了位置；也可能是出現了一種新的職責，或那個新檔本身是聚合檔。

## 思考題：熱點排行與直覺、註冊表的衝突、新檔再成熱點

1. 專案裡最常讓兩個人同時想修改的是哪個檔案？用本篇的腳本跑一次，結果和原本的直覺一致嗎？
2. 一個註冊表檔案被 10 個需求修改過。為什麼拆成兩個註冊表無法解決問題？要怎麼降低它的衝突？
3. 拆分後，拆出來的其中一個新檔很快又變成熱點，這代表什麼？

## 實作練習：父子需求對照、職責歸類、反例測試

1. 子需求使用獨立編號時，為腳本加入父子對照表（例如從 issue tracker 匯出），把子需求歸到根需求後再計數。
2. 挑一個專案中被 3 個以上不相干需求修改過的模組，依〈從修改紀錄找出職責邊界〉一節列出每次修改的職責，寫出會拆成哪幾個模組（不必實際動手拆）。
3. 為該模組補一組行為測試，至少包含一筆「應被擋下或應回報錯誤」的反例，再思考：拆分時如果拆錯了，這組測試抓得到嗎？

---

上一章：[作用域迴歸案例研究](/python/07-refactoring/scope-regression/)
