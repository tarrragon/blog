---
title: "從修改競爭判斷拆檔：何時拆、怎麼拆"
date: 2026-10-19
description: "用 git 歷史統計每個檔案被幾個不相干的需求修改、把結果當成單一職責的間接量測，修改熱點的分類與處理，以及在不改變對外行為的前提下拆分 Python 模組"
weight: 79
tags: ["python", "refactoring", "srp", "git"]
---

一個檔案被幾個不相干的需求修改過，可以從版本歷史數出來，這個數字是判斷它該不該拆的依據。本篇的範圍是這個量測、量出來的熱點怎麼分類，以及拆分 Python 模組時維持對外行為不變的做法。量測的前提是需求與檔案的對應查得到：本篇從 commit 標題裡的需求編號取（commit 訊息帶票號的慣例見 [Commit message vs source code doc](/record/commit-message-vs-source-doc/)），也可以從 issue tracker 取——PR 連到的 issue 加上 PR 改的檔案——那樣下文幾條只讀標題造成的限制都不存在。commit 不帶任何編號時，腳本沒有輸出，改用〈從修改紀錄找出職責邊界〉那樣逐檔讀 commit 標題人工歸類。範例是一支 commit 守衛：多個 AI 代理人各自在自己的工作目錄同時開發時（下文稱並行期間），代理人工具在執行每一條 shell 指令之前把整條指令字串交給它判斷，它擋下把 commit 寫進其他代理人工作目錄的寫法。命令解析、狀態判斷與提示訊息產生三種職責寫在同一個檔案裡。

同一個模組裡，[重構的動機與策略](/python/07-refactoring/refactoring-strategy/)用認知負擔判斷何時該重構、怎麼分階段進行，[程式碼壞味道偵測](/python/07-refactoring/code-smells/)從程式碼本身的寫法辨認問題；本篇的修改競爭量的是另一件事——一個檔案混了幾種改變的理由，它判斷的是拆檔。規則文件、操作手冊這類文字文件的拆分寫在 record 的[依職責拆分文字文件](/record/document-split-by-responsibility/)。

## 修改競爭與單一職責原則

修改競爭指的是處理不相干需求的人或代理人要改同一個檔案。git 只在兩邊改動的行重疊或相鄰時產生合併衝突，所以同一個檔案的修改不一定互相阻擋；會讓它們互相等待的是三種情形：

- **改動落在同一處**：例如兩個需求都在同一份清單或檔尾追加一筆。處理第一個需求的人先改、先合併，處理第二個需求的人拉最新版、解衝突、重跑測試。
- **合併沒有文字衝突，而行為互相影響**：兩邊各改一個函式，合併成功，而 rebase 之後仍要重跑測試，確認兩邊沒有改壞對方。
- **並行的代理人共用同一個工作目錄**：兩方的改動還沒提交就混在同一份檔案裡，一方要等另一方提交或清空改動才能動手。

排好順序與加強溝通能縮短每次等待的時間，而一個檔案承載的職責越多，落在它身上的不相干修改越多，等待的次數跟著增加。只有一個人依序開發時沒有等待成本，量到的不相干修改仍然有意義：它代表一個需求的改動有機會改壞另一個需求在乎的行為，這份隔離是單一職責原則要保護的東西。

單一職責原則（SRP）常被解讀成「一個模組只做一件事」，而「一件事」的範圍很難判斷。Robert C. Martin 給過一個更可操作的表述：

> 一個模組應該只有一個「改變的理由」。

他在 2014 年的說明裡把「理由」對到提出變更的人：一個模組的變更應該只來自一群緊密合作、代表單一業務職能的人。bug 修正與重構不算改變的理由，他的說法是那是程式設計師的責任，不是程式的。這個表述把抽象的「職責」換成了可以觀察的對象——**改變的理由**。版本歷史記下了每一次改變，也記下了它是為了哪一個需求（票、issue、PR）而做，需求數因此可以當成改變理由的間接量測（proxy measure）。

| 現象                                   | 代表什麼                                                         |
| -------------------------------------- | ---------------------------------------------------------------- |
| 同一個需求的多次 commit 都改同一個檔   | 正常。同一主題的演進集中在一處，這是內聚                         |
| 三、四個**不相干的需求**都要改同一個檔 | 這個檔最多有三、四種改變的理由；實際幾種，由逐個 commit 歸類決定 |

需求數是篩選訊號：它決定要不要回頭讀這個檔案的修改紀錄，這個檔案實際有幾種改變的理由，在〈從修改紀錄找出職責邊界〉逐個 commit 歸類時才判定。兩個需求服務不同的業務職能，就是不相干的需求；所有票都由同一位 PM 開的團隊裡，開票的人分不出理由，判斷看的是需求服務哪一項業務職能。bug 修正照 Martin 的說法不另算一個理由，歸類時併進它修的那一類。同一個需求拆成多張票時，要靠下文的父子對照表把它們歸到同一個根需求。

### 行數與修改競爭的量測對象

常見的拆檔門檻是行數，例如超過 300 行就考慮拆。行數是檔案過大的症狀，而它在兩種檔案上會給出與修改競爭相反的結果：

| 情況                                       | 行數判斷       | 修改競爭判斷 |
| ------------------------------------------ | -------------- | ------------ |
| 200 行的骨架產生器，被 6 個不同需求改過    | 不會觸發       | 會觸發       |
| 900 行的解析器，只屬於同一個需求的連續演進 | 會觸發（誤判） | 不會觸發     |

照行數把 900 行的解析器切成三份，同一主題之後的每一次修改都要同時改三個檔。一個需求改多個檔案，Martin Fowler 的《Refactoring》叫它散彈式修改（shotgun surgery，其他中文資料也寫作散彈槍手術）；與它成對的是發散式變更（divergent change）：一個模組因為不同的理由、以不同的方式反覆被修改，這正是本篇用修改紀錄量的那種壞味道（站內的定義與偵測在 [Code Smell 檢查清單](/record/code_smell/)）。修改競爭是發散式變更在並行開發時造成的等待成本。行數量的是檔案的大小，修改競爭量的是一個檔案混了幾種改變的理由，SRP 在意的是改變的理由有幾種。

## 用 git 歷史量出熱點

commit 標題帶有需求編號（票號、issue 號）時，可以直接算出每個檔案被幾個不同需求改過。下文把排行前段、被明顯更多不同需求修改的檔案稱為修改熱點（簡稱熱點），它沒有固定的名次門檻。它與效能分析裡「最常執行的程式路徑」那種熱點是兩件事；git 歷史分析的文獻裡也有 hotspot（Adam Tornhill 用修改頻率乘上程式碼的複雜度），本篇數的是不同需求數，不數 commit 次數，也不乘複雜度。

```python
"""依 commit 標題中的需求編號，統計每個檔案被幾個不同需求修改。"""
import collections
import os
import re
import subprocess

ISSUE_ID = re.compile(r"#(\d+)")  # 依專案的 commit 慣例調整
PR_SUFFIX = re.compile(r"\s*\(#\d+\)\s*$")  # squash merge 在標題結尾附加的 (#PR號)
STRIP_PR_SUFFIX = True  # 只在用 squash merge、標題結尾的 (#N) 是 PR 號時設 True
EXCLUDE = {"uv.lock", "poetry.lock", "package-lock.json"}  # 工具產生的檔案，不列入統計

def collect_changes(since: str, path: str = ".") -> tuple[dict[str, set[str]], int]:
    log = subprocess.run(
        # core.quotePath=false：非 ASCII 檔名照原樣輸出，不轉成跳脫碼
        ["git", "-c", "core.quotePath=false", "log", f"--since={since}", "--no-merges",
         "--name-only", "--format=@@%s", "--", path],
        capture_output=True, text=True, check=True,
    ).stdout

    issues_per_file: dict[str, set[str]] = collections.defaultdict(set)
    current: set[str] = set()
    skipped = 0
    for line in log.splitlines():
        if line.startswith("@@"):
            subject = line[2:]
            if subject.startswith('Revert "'):
                current = set()  # revert 的標題帶著被還原那個 commit 的 PR 號
                continue
            if STRIP_PR_SUFFIX:
                subject = PR_SUFFIX.sub("", subject)
            current = set(ISSUE_ID.findall(subject))
            skipped += not current
            continue
        if line and current and os.path.basename(line) not in EXCLUDE:
            for issue in current:
                issues_per_file[line].add(issue)
    return issues_per_file, skipped

def report(since: str, top: int = 20) -> None:
    changes, skipped = collect_changes(since)
    ranked = sorted(changes.items(), key=lambda kv: -len(kv[1]))
    for path, issues in ranked[:top]:
        print(f"{len(issues):3d} 個需求  {path}  {' '.join(sorted(issues))}")
    print(f"略過 {skipped} 個標題沒有需求編號的 commit")

if __name__ == "__main__":
    report("2 weeks ago")
```

```bash
# 存成 hotspots.py 之後，在 repo 的根目錄執行
python3 hotspots.py
```

腳本裡影響計數的設計：

- **統計的時間範圍**：`report()` 的引數是 `git log --since` 接受的時間字串（`"2 weeks ago"`、`"2026-01-01"`）。範圍要涵蓋幾輪需求，才看得出同一個檔案被不同需求反覆修改；範例的兩週適合需求密集的專案，修改頻率低的專案要拉長。被幾個需求修改算多的那個數字跟著時間範圍變，所以看排行裡的相對位置比看絕對數字穩定。
- **統計的目錄**：`collect_changes` 的 `path` 預設是 `"."`，指的是執行腳本時所在的目錄；從子目錄執行，只會統計那個子目錄底下的檔案。
- **只讀 commit 標題**：`--format=@@%s` 取的是標題。把需求編號寫在內文或 trailer（`Refs: #160`）的專案，這些 commit 會被靜默略過；改用 `%B` 取完整訊息時，內文的行會和檔名混在一起，分隔方式與解析都要跟著改。
- **PR 號**：GitHub 的 issue 與 PR 共用同一組 `#N` 編號，squash merge 又會在標題結尾附上 `(#PR號)`，只改 `ISSUE_ID` 分不開兩者；`STRIP_PR_SUFFIX` 為 `True` 時，腳本先去掉標題結尾的 `(#N)` 再比對。這一行只適用用 squash merge 的 repo，而且需求編號要寫在 PR 標題裡；習慣在標題結尾寫 `(#45)` 引用 issue 的專案，要把它設成 `False`，否則那個 issue 號會被刪掉。需求編號與 PR 編號格式不同的專案（例如需求用 `PROJ-123`），改 `ISSUE_ID` 就分得開。revert 的標題會把被還原那個 commit 的 PR 號帶進引號裡，腳本略過 `Revert "` 開頭的標題。
- **工具產生的檔案**：lock 檔、每個 PR 都跟著升號的版號檔、產生的程式碼，每個需求都會改到，排行會被它們佔滿，而它們沒有任何人帶著意圖去編輯；把檔名加進 `EXCLUDE`。
- **改名與橫切的需求**：`--name-only` 不跟改名，大量重新命名之後，舊路徑與新路徑各自計數。相依套件升級、全域改名、格式化這類橫切的需求會讓大量檔案各加一，排行前段若出現一整批一起出現的檔案，先看是不是同一個橫切需求造成的，再把那個需求的編號排除。
- **沒有編號的 commit**：腳本最後印出略過的 commit 數。這個數字接近全部 commit 時，統計沒有意義，改用人工歸類。
- **`--no-merges`**：`git log` 預設不列出 merge commit 改了哪些檔案，所以目前這個選項不影響結果；改用 `--first-parent` 或 `-m` 讓 merge commit 也列出檔案時，merge 會把整條分支的改動再算一次，加了 `--no-merges` 的 `git log` 不輸出 merge commit。
- **一則 commit 帶多個編號**：`ISSUE_ID.findall` 取出標題裡的全部編號。一個 commit 同時處理多個需求時，它改過的每個檔都會記到每個需求名下。
- **把子需求歸到同一個主題**：點號格式的子需求（例如 `#120.3`），正規式 `#(\d+)` 只比對到第一段數字，本來就會算進根需求 120。子需求若有獨立編號（例如父需求 `#120`、子需求 `#135`），要另備一份父子對照表，把子需求歸到根需求再計數；不歸併的話，同一主題的連續修改會被誤算成多個改變理由。

## 熱點的分類與處理方式

排行前段的檔案有些該拆、有些不該拆，依熱點類型分開處理：

| 熱點類型                                         | 例子                                                       | 處理                                 |
| ------------------------------------------------ | ---------------------------------------------------------- | ------------------------------------ |
| 一般程式碼，排在前段、被多個不相干的需求修改     | 一支同時負責「解析命令」「判斷狀態」「產生提示訊息」的模組 | **拆分評估**                         |
| 同一主題的連續演進                               | 一個佇列模組，被同一個「排隊機制」需求的 5 張子票陸續修改  | 不拆，這是內聚                       |
| 集中登記檔：每加一個功能就要在這裡登記一筆的檔案 | URL 路由表、外掛註冊表、`settings.json`                    | 不以職責拆分，改成每個項目一個片段檔 |
| 只有測試檔是熱點                                 | 一個大測試檔被多個需求加測項                               | 見表下說明                           |
| 工具產生或衍生的檔案                             | `uv.lock`、每個 PR 都升號的 `version.py`、產生的程式碼     | 不拆，從統計排除；衝突靠重新產生解   |

工具產生的檔案沒有人帶著意圖編輯，不屬於任何一種職責：lock 檔的衝突靠重新產生解決，版號改由發版時的 tag 衍生，就不必每個 PR 都改它。

集中登記檔的處置跟一般程式碼相反。註冊表的職責是集中列出所有項目，每加一個功能就要登記一次，所以修改它的需求數會隨功能數一起增加。把它依職責拆成三份註冊表，每次登記仍然要改其中一份，衝突只是換到另一個檔案；兩個需求都在同一份清單的尾端追加，照樣是相鄰的改動。這類檔案的解法是讓每次登記不碰同一個檔案：每個項目一個片段檔，由載入端掃描目錄合併。

只有測試檔是熱點時，先看它測的產品檔。產品檔也是熱點，測試隨產品檔一起拆；產品檔不是熱點，或已經拆成幾個模組，代表這個測試檔一次測了好幾個產品模組，依它測的模組拆成對應的測試檔。

## 從修改紀錄找出職責邊界

職責的邊界記在修改紀錄裡：每個需求改的是哪一種職責，讀它的 commit 就知道。`report()` 在每個檔案後面印出了改過它的需求編號，要看每個需求做了什麼，列出這個檔案的 commit 標題：

```bash
# 時間範圍用與熱點統計相同的範圍，路徑換成要拆的那個檔案
git log --no-merges --since="2 weeks ago" --format='%h %s' -- guard.py
```

把每個需求歸到它改的職責：

```text
需求 A：修正命令解析遇到引號時的錯誤        → 命令解析
需求 B：新增「並行期間」的判斷條件           → 狀態判斷
需求 C：提示訊息改成指引使用者改寫命令       → 訊息產生
需求 D：解析器支援 -C 參數                   → 命令解析
需求 E：並行期間改依工作位置過濾             → 狀態判斷
```

歸類的單位是每個 commit 改到的程式，不是需求本身：`git show <hash>` 看得到那個 commit 改了哪些函式。一個需求或一個長期計畫改到幾類，就逐個 commit 歸到幾類，計畫本身不構成一個模組。多數需求都同時改到某兩類時，這兩類對需求而言是同一個改變的理由，不要分開——依它們切開，每個需求都要同時改兩個新檔，就是散彈式修改。

歸類之後，每一類職責是一個候選模組，這個例子分出命令解析、狀態判斷與訊息產生。歸類後只剩一類時，這個檔案被多個需求修改的原因是同一主題的連續演進（內聚），或這個檔案是集中登記檔，回到〈熱點的分類與處理方式〉的表重新判斷。

## 拆分 Python 模組的做法

### 用測試鎖住拆分前的行為

拆分前後跑同一組測試、結果相同，才證明拆分沒有改到對外行為。這種測試叫特徵測試（[characterization test](/testing/knowledge-cards/characterization-test/)）：預期值取自拆分前程式當下的實際輸出，不是規格上應該如何，所以它能抓到拆分造成的任何行為差異，包括原本就存在的錯誤被「順手修好」。這組測試要涵蓋**邊界與反例**：

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
    ("git -C /other commit -m 'msg'", "block"),   # 拆分前的輸出是 block：-C 把 commit 指到別的工作目錄
    ("echo 'git commit'", "allow"),               # 字串中出現的 git
])
def test_evaluate_behavior_is_unchanged(command, expected):
    assert evaluate(command) == expected
```

`is_parallel_period` 的結果取決於執行當下有哪些代理人在工作，所以 fixture 先把它固定住，測試在任何機器上都得到同一個結果。`evaluate` 每次執行時都在 `guard` 模組的命名空間裡查 `is_parallel_period` 這個名字，fixture 替換的正是那個名字，所以拆分前（`guard.py`）與拆分後（`guard/__init__.py`）同一個 fixture 都生效；`evaluate` 之後若搬進 `guard/core.py` 這類子模組，替換的目標要跟著改成 `guard.core`。

測試表裡的 `git -C /other commit` 是應該擋下的寫法。測試表若只驗證正常情況會放行，拆分不小心改壞了擋下的判斷，測試依然全綠，拆分前後的差別不會出現在任何一項測試結果裡。這個範例只示範結構；實際的 commit 守衛還要處理 `--git-dir`、`--work-tree`、`GIT_DIR` 環境變數與先 `cd` 再 commit 這些同樣會把 commit 寫到別處的寫法。

### 依職責萃取模組並保留原本的匯入路徑

呼叫端寫的是 `from guard import evaluate`，所以拆分之後 `guard` 這個名字要繼續提供 `evaluate`。做法是刪掉 `guard.py`，改成同名的套件目錄 `guard/`，把每一類職責的函式移到套件裡的新模組，`guard/__init__.py` 從新模組匯入對外名稱，再以套件的名義重新匯出（re-export）：

```text
guard.py              ← 原本 1200 行，三種職責混在一起；拆分時刪除

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

`guard.py` 與 `guard/` 同時存在時，`import guard` 取到的是套件，留下來的 `guard.py` 沒有人載入，之後改它不會有任何效果，所以要刪掉（先用 `git mv guard.py guard/__init__.py` 單獨提交一個只改名的 commit，再往外搬函式，`git log --follow` 才追得到改名之前的歷史）。原本寫 `from guard import evaluate` 的呼叫端不用改。`parse_command` 這類只為了相容舊的呼叫端而重新匯出的名字，等呼叫端都改成從 `guard.command_parse` 匯入之後可以拿掉；`evaluate` 自己用到的 `is_parallel_period` 要留著，上一節的 fixture 也替換這個名字。套件、`__init__.py` 與公開 API 的基礎在[從單一 script 到多檔案專案](/python/01-basics/script-to-package/)。

拆分時常會發現同一種判斷在好幾個檔案各寫了一份，例如 commit 守衛和另外兩支擋 push、擋 rebase 的守衛，各自實作「從命令中取出 commit 的目標工作目錄」。規則一改三份都要跟著改，這是散彈式修改；收斂成共用模組的做法與遷移時的陷阱在[DRY 原則與共用程式庫](/python/07-refactoring/dry-principle/)。

### 把巨型分支改成分派表

一個函式的主體是一長串 `if/elif`、每個分支處理一種事件類型時，每新增一種事件類型都要改這個函式，它所在的檔案就留在熱點排行上。改成分派表之後，新增一種事件類型只需要加一個處理函式並登記：

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

分派表要讓檔案離開熱點排行，處理函式還得放進各自的模組：處理函式都寫在同一個檔案裡時，每個新需求仍然改這個檔，而且都在檔尾追加，兩個同時進行的需求照樣衝突。處理函式各放一個模組之後，負責 import 這些模組、讓裝飾器執行登記的那份清單又是一份集中登記檔，所以登記改成由載入端掃描目錄。`HANDLERS` 與 `register` 這時要搬到獨立的 `registry.py`，處理函式的模組從那裡匯入；放在 `handlers/__init__.py` 的掃描迴圈之後，處理函式匯入時會遇到還沒初始化完的模組而失敗：

```python
# handlers/__init__.py：匯入同目錄底下的每一個模組，模組裡的 @register 在匯入時執行登記
import importlib
import pkgutil

for module in pkgutil.iter_modules(__path__):
    importlib.import_module(f"{__name__}.{module.name}")
```

新增一種事件類型只需要在 `handlers/` 底下加一個檔案；`handle` 所在的模組要先 `import handlers`，登記才會發生。處理函式分散在不同套件時，改用套件的 entry points：每個套件在自己的 `pyproject.toml` 宣告登記點，安裝之後由 `importlib.metadata.entry_points()` 列舉出來。片段式登記的代價是靜態分析看不到登記關係，放進目錄的半成品檔也會被自動登記。登記式的插件架構在[插件系統設計](/python-advanced/03-design-patterns/plugin-system/)，用 metaclass 與裝飾器自動註冊的寫法在[案例：自動註冊機制](/python-advanced/02-metaprogramming/case-studies/auto-registration/)。

### 讓拆出來的模組單向依賴

拆出來的模組之間，依賴只朝一個方向，循環匯入就不會出現。判斷上下層的依據是誰需要知道誰：被較多模組使用、自己不需要知道其他拆出模組的那一個在下層。這個例子裡 `command_parse.py` 只把指令字串解析成結構，在最下層；`state.py` 與 `messages.py` 使用解析結果；`__init__.py` 組合三者，在最上層。

兩邊都要呼叫對方，多半代表中間有一塊共用的定義沒有抽出來，例如 `state.py` 與 `messages.py` 都用到的「並行狀態」資料型別。先確認兩個方向的呼叫是否都必要，有時拿掉其中一邊就夠了；兩邊都必要時，把那塊共用定義再往下抽一層（例如 `models.py`），讓兩者都依賴它。

### 搬移與修改分開提交

搬移和修改混在同一個 commit 裡，測試一紅，就分不出是搬錯了還是改錯了，所以純搬移的 commit 不同時修改行為，行為的修改放在之後的 commit。`git diff --color-moved` 會把搬移過的行與新寫的行用不同顏色標出，用來確認一個 commit 裡只有搬移。

## 拆分的時機與等待中的需求

拆分合併的時間點，決定等待中的需求以哪一版為基準。拆分先合併，等待中的需求以新版本為基準，各自只改自己職責所在的新檔：

```text
拆分前：命令解析、狀態判斷、訊息產生各有一個需求在等，三個都要改 guard.py → 一個接一個
拆分後：處理命令解析需求的人改 command_parse.py，狀態判斷的改 state.py，訊息產生的改 messages.py → 可以同時進行
```

原本要一個接一個做的三個需求，拆分之後可以平行處理。拆分若在某個需求開工之後才合併，那個需求的分支改的是舊的 `guard.py`，rebase 時遇到的衝突有兩種形態：

- **沒有一份新檔保留原檔過半的內容**：git 判定 `guard.py` 被刪除，出現 modify/delete 衝突。
- **有一份新檔保留了原檔過半的內容**：git 的改名偵測把它當成 `guard.py` 改名而來，衝突以一般的內容衝突出現在那份新檔，衝突區塊裡是已經搬到其他模組的舊函式。照一般衝突處理接受這一段，會把搬走的函式重新塞回那份新檔，改動落在不會被呼叫的副本裡，測試仍然全綠。

兩種形態的處置相同：把這個分支的改動移到那一職責所在的新檔，不接受衝突區塊裡整段的舊程式碼。rebase 沒有衝突也要檢查一次：分支在被當成改名目標的那份新檔裡新增的函式會乾淨合併，即使它屬於另一類職責。用 `git diff main --stat` 與 `git diff main` 看分支新增的每個函式落在哪個檔。拆分前就有的測試在這些情形下仍然全綠，這個分支替自己的改動補的測試才會紅。這也是拆分要排在等待中的需求開工之前合併的原因。

過一段時間後再跑一次熱點統計，`report()` 的引數設成拆分合併的那一天，比較 `guard/` 底下各檔被幾個需求修改，並看每個需求是不是只改了一個新檔——多數需求同時改到兩個新檔，代表當初把同一個改變的理由切成了兩類。某個新檔很快又成為熱點時，把它的修改再歸類一次：修改落在拆分時已有的幾類而混在一起，是當初的職責分類切錯了位置；出現拆分時沒有的一類，是多了一種新的職責；每次修改都是登記一筆，代表它本身是集中登記檔。同一類收到很多不相干的需求、而它們都屬於這一類時，代表這一類的粒度還太粗，可以在裡面再找一次職責邊界；也可能它本來就是最常變動的那一處，拆分已經把變動集中在那裡。抽出來的 `models.py` 被每個需求都改到時，常見的原因是共用定義抽得太大，裡面混了只有某一個模組用的型別，把那些型別搬回使用它的模組。

## 思考題：熱點排行與直覺、註冊表的衝突、新檔再成熱點

1. 專案裡最常讓兩個人同時想修改的是哪個檔案？用本篇的腳本跑一次，結果和原本的直覺一致嗎？
2. 一個註冊表檔案被 10 個需求修改過。為什麼拆成兩個註冊表無法解決問題？要怎麼降低它的衝突？
3. 拆分後，拆出來的其中一個新檔很快又變成熱點，這代表什麼？

## 實作練習：父子需求對照、職責歸類、反例測試

1. 子需求使用獨立編號時，為腳本加入父子對照表（例如從 issue tracker 匯出），把子需求歸到根需求後再計數。
2. 挑一個在熱點排行前段、被多個不相干需求修改過的模組，依〈從修改紀錄找出職責邊界〉一節列出每次修改的職責，寫出會拆成哪幾個模組（不必實際動手拆）。
3. 為該模組補一組行為測試，至少包含一筆「應被擋下或應回報錯誤」的反例，再思考：拆分時如果拆錯了，這組測試抓得到嗎？

---

上一章：[作用域迴歸案例研究](/python/07-refactoring/scope-regression/)
