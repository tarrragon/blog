---
title: "從修改競爭判斷拆檔：何時拆、怎麼拆"
date: 2026-10-19
description: "不同主題的修改反覆落在同一個檔案，是單一職責超標的可觀測訊號。學習用 git 歷史量出熱點、判斷何時該拆，以及在不改變行為的前提下拆分 Python 模組"
weight: 79
tags: ["python", "refactoring", "srp", "cognitive-load"]
---

這篇整理用版本歷史量測「一個檔案被幾個不相干的需求修改」、據此判斷是否拆檔，以及拆分 Python 模組時維持對外行為不變的做法。範例是一支 commit 守衛模組，命令解析、狀態判斷與提示訊息產生三種職責寫在同一個檔案裡；量測的前提是 commit 訊息帶有需求編號。

## 修改競爭與單一職責原則

修改競爭指的是處理不相干需求的人要改同一個檔案，於是只能排隊：一個需求先改、先合併，下一個需求拉最新版、解衝突、重跑測試。兩個開發者或兩個 AI 代理人並行工作時，下一週又有第三個需求要改這個檔，排隊再來一次。排好順序與加強溝通能縮短每次排隊的時間，而排隊的次數由這個檔案承載了幾種職責決定。

單一職責原則（SRP）常被解讀成「一個模組只做一件事」，而「一件事」的範圍很難判斷。Robert C. Martin 給過一個更可操作的定義：

> 一個模組應該只有一個「改變的理由」。

這個定義把抽象的「職責」換成了可以觀察的對象：**改變的理由**。改變的理由記錄在版本歷史裡——每一次 commit 是一次改變，每一個需求（票、issue、PR）是一個理由。

| 現象                                   | 代表什麼                                       |
| -------------------------------------- | ---------------------------------------------- |
| 同一個需求的多次 commit 都改同一個檔   | 正常。同一主題的演進集中在一處，這是內聚       |
| 三、四個**不相干的需求**都要改同一個檔 | 這個檔有三、四種改變的理由，也就是三、四種職責 |

所以一個檔案被幾個不相干的需求修改，可以直接當成 SRP 定義的量測值。

### 行數與修改競爭的量測對象

常見的拆檔門檻是行數，例如超過 300 行就考慮拆。行數是有用的症狀，而它在兩種檔案上會給出與修改競爭相反的結果：

| 情況                                       | 行數判斷       | 修改競爭判斷 |
| ------------------------------------------ | -------------- | ------------ |
| 200 行的骨架產生器，被 6 個不同需求改過    | 不會觸發       | 會觸發       |
| 900 行的解析器，只屬於同一個需求的連續演進 | 會觸發（誤判） | 不會觸發     |

行數量的是檔案的大小，修改競爭量的是一個檔案混了幾種改變的理由。SRP 在意的是改變的理由有幾種。

## 用 git 歷史量出熱點

commit 訊息帶有需求編號（票號、issue 號）時，可以直接算出每個檔案被幾個不同需求改過：

```python
"""依 commit 訊息中的需求編號，統計每個檔案被幾個不同需求修改。"""
import collections
import re
import subprocess

ISSUE_ID = re.compile(r"#(\d+)")  # 依專案的 commit 慣例調整

def collect_changes(since: str, path: str = ".") -> dict[str, set[str]]:
    log = subprocess.run(
        ["git", "log", f"--since={since}", "--no-merges",
         "--name-only", "--format=@@%s", "--", path],
        capture_output=True, text=True, check=True,
    ).stdout

    issues_per_file: dict[str, set[str]] = collections.defaultdict(set)
    current = None
    for line in log.splitlines():
        if line.startswith("@@"):
            match = ISSUE_ID.search(line)
            current = match.group(1) if match else None
            continue
        if line and current:
            issues_per_file[line].add(current)
    return issues_per_file

def report(since: str, top: int = 20) -> None:
    changes = collect_changes(since)
    ranked = sorted(changes.items(), key=lambda kv: -len(kv[1]))
    for path, issues in ranked[:top]:
        print(f"{len(issues):3d} 個需求  {path}")

if __name__ == "__main__":
    report("2 weeks ago")
```

腳本有兩處設計會影響計數：

- **`--no-merges`**：merge commit 會把整條分支的改動列進來，不排除就會重複計數。
- **把子需求歸到同一個主題**：需求有父子關係時（例如 `#120` 底下的 `#120.3`），要以根需求計數，否則同一主題的連續修改會被誤算成多個理由。

## 熱點的分類與處理方式

排行榜上名列前茅的檔案有些該拆、有些不該拆，依熱點類型分開處理：

| 熱點類型                                | 例子                                                       | 處理                                           |
| --------------------------------------- | ---------------------------------------------------------- | ---------------------------------------------- |
| 一般程式碼，被 3 個以上不相干的需求修改 | 一支同時負責「解析命令」「判斷狀態」「產生提示訊息」的模組 | **拆分評估**                                   |
| 同一主題的連續演進                      | 一個佇列模組，被同一個「排隊機制」需求的 5 張子票陸續修改  | 不拆，這是內聚                                 |
| 聚合檔：設定、註冊表、CHANGELOG、索引   | `settings.json`、外掛註冊清單                              | 不以職責拆分，改用「一項一檔」或「只追加」格式 |
| 只有測試檔在競爭                        | 一個大測試檔被多個需求加測項                               | 先看它測的產品檔；測試通常隨產品檔一起拆       |

聚合檔的處置跟一般程式碼相反。註冊表的職責是集中列出所有項目，每加一個功能就要登記一次，所以修改它的需求數會隨功能數一起增加。把它依職責拆成三份註冊表，每次登記仍然要改其中一份，競爭只是換到另一個檔案。這類檔案的解法是降低每次修改的衝突面，例如每個項目一個片段檔、由載入端合併。

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

歸類後只剩一類時，競爭來自同一主題的連續演進，或這個檔案是聚合檔，回到〈熱點的分類與處理方式〉的表重新判斷。

## 拆分 Python 模組的做法

### 用測試鎖住拆分前的行為

拆分是結構調整，對外行為要維持不變，所以動手之前先確認對外行為都有測試覆蓋，特別是**邊界與反例**：

```python
import pytest

from guard import evaluate  # 拆分前後都從這裡匯入

@pytest.mark.parametrize("command, expected", [
    ("git commit -m 'msg'", "allow"),
    ("git -C /other commit -m 'msg'", "block"),   # 應擋的寫法
    ("echo 'git commit'", "allow"),               # 字串中出現的 git
])
def test_evaluate_behavior_is_unchanged(command, expected):
    assert evaluate(command) == expected
```

測試表裡的 `git -C /other commit` 是應該擋下的寫法。測試只驗證正常情況會放行時，拆分不小心改壞了擋下的判斷，測試依然全綠，拆分前後的差別不會出現在任何一項測試結果裡。

### 依職責萃取模組並保留原本的匯入路徑

把每一類職責的函式移到新模組，原模組改成套件，從新模組匯入（re-export）對外名稱：

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

原本寫 `from guard import evaluate` 的呼叫端不用改。等所有呼叫端都改用新路徑之後，再決定是否拿掉 re-export。

### 把重複的判斷收斂到共用模組

拆分時常會發現同一種判斷在好幾個檔案各寫了一份，例如三支守衛各自實作「從命令中取出 ID」。三份各自的實作，就是這三個檔案被同一個需求一起修改的原因：規則一改，三份都要跟著改。

把它收斂成共用模組裡的單一函式，各處改為呼叫它。之後規則再改，只需要改一個地方，也只產生一次修改，三個檔案不再為同一條規則競爭。

### 把巨型分支改成分派表

一個函式的主體是一長串 `if/elif`、每個分支處理一種情況時，每新增一種情況都要改這個函式，它會一直留在熱點排行上。改成分派表之後，新增情況只需要加一個處理函式並登記：

```python
# 改之前：每個新需求都要改這個函式
def handle(event):
    if event.kind == "commit":
        ...
    elif event.kind == "merge":
        ...
    elif event.kind == "rebase":
        ...

# 改之後：新增情況只需要加一個處理函式並登記
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

def handle(event):
    handler = HANDLERS.get(event.kind)
    if handler is None:
        raise ValueError(f"未知的事件類型：{event.kind}")
    return handler(event)
```

### 讓拆出來的模組單向依賴

拆出來的模組只依賴比它底層的模組，循環匯入就不會出現。`state.py` 和 `messages.py` 需要互相呼叫時，代表兩者之間還有一塊共用的定義沒有抽出來，把它再往下抽一層（例如 `types.py`），讓兩者都依賴它。

### 搬移與修改分開提交

純搬移的 commit 不同時修改行為：搬移和修改混在同一個 commit 裡，測試一紅，就分不出是搬錯了還是改錯了。先提交一個只搬移、測試全綠的版本，行為的修改放在之後的 commit。

## 拆分的時機與等待中的需求

拆分要排在正在等待的需求**之前**。拆分合併之後，等待中的需求改以新版本為基準，各自只改自己職責所在的新檔：

```text
拆分前：需求 A、B、C 都要改 guard.py → 只能排隊，一個接一個
拆分後：A 改 command_parse.py、B 改 state.py、C 改 messages.py → 可以同時進行
```

拆分的回報就在這裡：原本只能排隊做的三個需求，拆分之後可以平行處理。

過一段時間後再跑一次熱點統計，確認這個檔案與拆出來的新檔，被不同需求修改的次數確實下降。某個新檔很快又成為熱點時，代表當初的職責分類切錯了位置。

## 文字文件的拆分

這套方法也適用於文字文件。規則文件、操作手冊、範本被不同主題反覆修改，同樣代表一份文件承載了太多種職責。文字文件的拆法：

| 原則               | 做法                                                     |
| ------------------ | -------------------------------------------------------- |
| 依職責切，不依長度 | 每份新文件只處理一種內容（何時做、怎麼做、為什麼這樣做） |
| 原檔保留路由       | 原檔留一張索引表，指向各個新文件                         |
| 一條規則只定義一次 | 其他文件引用它，不複製內容，避免拆完變成兩份各自修改     |
| 更新所有引用       | 用 `grep -rl` 找出所有引用原檔或舊標題的地方，逐一更新   |

## 思考題

1. 專案裡最常讓兩個人同時想修改的是哪個檔案？用本篇的腳本跑一次，結果和原本的直覺一致嗎？
2. 一個註冊表檔案被 10 個需求修改過。為什麼拆成兩個註冊表無法解決問題？要怎麼降低它的衝突？
3. 拆分後，拆出來的其中一個新檔很快又變成熱點，這代表什麼？

## 實作練習

1. 修改本篇的熱點統計腳本，讓它把有父子關係的需求（例如 `#120` 與 `#120.3`）歸到同一個根需求計數。
2. 挑一個專案中被 3 個以上不相干需求修改過的模組，依〈從修改紀錄找出職責邊界〉一節列出每次修改的職責，寫出會拆成哪幾個模組（不必實際動手拆）。
3. 為該模組補一組行為測試，至少包含一筆「應被擋下或應回報錯誤」的反例，再思考：拆分時如果拆錯了，這組測試抓得到嗎？
