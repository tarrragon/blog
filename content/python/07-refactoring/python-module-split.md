---
title: "拆分 Python 模組：用特徵測試鎖住行為、保留匯入路徑、分派表與單向依賴"
date: 2026-10-19
description: "職責邊界已經從修改紀錄歸類出來之後，用 Python 拆分一個模組而不改變對外行為：特徵測試與 monkeypatch 的替換目標、改成同名套件並重新匯出、把巨型分支改成自動登記的分派表、拆出模組之間的單向依賴，以及搬移與修改分開提交"
weight: 79
tags: ["python", "refactoring", "srp", "packaging"]
---

這篇整理在 Python 裡拆分一個模組、而對外行為不變的做法，範圍從職責邊界已經決定好那一刻開始。是否要拆、依什麼切，是從版本歷史判斷的，與語言無關，寫在[從修改紀錄畫模組邊界](/design-principles/module-boundary-from-change-history/)：那一篇用 git 歷史統計每個檔案被幾個不同的需求修改，再逐個 commit 把需求歸到職責。本篇沿用那一篇的範例：一支 commit 守衛 `guard.py`，多個 AI 代理人各自在自己的工作目錄同時開發時，代理人工具在執行每一條 shell 指令之前把整條指令字串交給它判斷，它擋下把 commit 寫進其他代理人工作目錄的寫法。修改紀錄歸類出三種職責：命令解析、狀態判斷、訊息產生。

同在 Python 重構這一章的[重構的動機與策略](/python/07-refactoring/refactoring-strategy/)用認知負擔判斷何時該重構、怎麼分階段進行，[程式碼壞味道偵測](/python/07-refactoring/code-smells/)從程式碼本身的寫法辨認壞味道；本篇處理的是決定拆之後怎麼拆。


## 用測試鎖住拆分前的行為

拆分前後跑同一組測試、結果相同，才證明拆分沒有改到對外行為。這種測試叫特徵測試（[characterization test](/testing/knowledge-cards/characterization-test/)）：預期值取自拆分前程式當下的實際輸出，不是規格上應該如何——寫測試時先對拆分前的程式跑一次，把輸出填成預期值。它抓得到拆分在測到的輸入與斷言的輸出上造成的任何差異，包括原本就存在的錯誤被「順手修好」；沒有斷言的輸出，它抓不到。這組測試要涵蓋**邊界與反例**：

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

def test_block_message_is_unchanged(capsys):
    # 訊息產生也是要拆的一類，所以印出的內容也要斷言；
    # 把 <拆分前印出的訊息> 換成拆分前的程式實際印出的那一行
    evaluate("git -C /other commit -m 'msg'")
    assert capsys.readouterr().out == "<拆分前印出的訊息>\n"
```

`is_parallel_period` 的結果取決於執行當下有哪些代理人在工作，所以 [fixture](/python/knowledge-cards/pytest-fixture/) 先把它固定住，測試在任何機器上都得到同一個結果。`evaluate` 每次執行時都在 `guard` 模組的命名空間裡查 `is_parallel_period` 這個名字，fixture 用 [monkeypatch](/python/knowledge-cards/monkeypatch/) 替換的正是那個名字，所以拆分前（`guard.py`）與拆分後（`guard/__init__.py`）同一個 fixture 都生效；`evaluate` 之後若搬進 `guard/core.py` 這類子模組，替換的目標要跟著改成 `guard.core`。

測試表裡的 `git -C /other commit` 是應該擋下的寫法。測試表若只驗證正常情況會放行，拆分不小心改壞了擋下的判斷，測試依然全綠，拆分前後的差別不會出現在任何一項測試結果裡。這個範例只示範結構；實際的 commit 守衛還要處理 `--git-dir`、`--work-tree`、`GIT_DIR` 環境變數與先 `cd` 再 commit 這些同樣會把 commit 寫到別處的寫法。

## 依職責萃取模組並保留原本的匯入路徑

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

`guard.py` 與 `guard/` 同時存在時，`import guard` 取到的是套件，留下來的 `guard.py` 沒有人載入，之後改它不會有任何效果，所以要刪掉。刪的方式是把它改名成套件的 `__init__.py`，單獨提交一個只改名的 commit，再往外搬函式：

```bash
mkdir guard                          # git mv 不會自動建立目標目錄
git mv guard.py guard/__init__.py
git commit -m "guard.py 改成套件 guard/（只改名）"
```

只改名的 commit 讓 `git log --follow guard/__init__.py` 追得到改名之前的歷史；改名與搬函式混在同一個 commit 時，`__init__.py` 只剩下原檔的一小部分，git 不會把它當成 `guard.py` 改名而來。這個 commit 只影響 `git log` 的追蹤，rebase 時的改名偵測比對的是拆分前後的整體差異，不看中間的 commit。原本寫 `from guard import evaluate` 的呼叫端不用改。`__init__.py` 匯入的三個名字 `evaluate` 都要用，所以要留著；`is_parallel_period` 另外還是〈用測試鎖住拆分前的行為〉那個 fixture 替換的名字。舊的呼叫端若也直接寫 `from guard import parse_command`，這個名字同時負責相容，等那些呼叫端改成從 `guard.command_parse` 匯入之後，相容的用途才結束。`__init__.py` 在套件匯入時扮演的角色與 `from package import name` 的解析方式，見 Python 官方教學的 [Packages](https://docs.python.org/3/tutorial/modules.html#packages) 一節。

拆分時常會發現同一種判斷在好幾個檔案各寫了一份，例如 commit 守衛和另外兩支擋 push、擋 rebase 的守衛，各自實作「從命令中取出 commit 的目標工作目錄」。三份跟著同一條規則改，是同一份知識（判斷依據見 [DRY](/design-principles/knowledge-cards/dry-principle/) 卡片），規則一改三份都要改，這是[散彈式修改（Shotgun Surgery）](/design-principles/knowledge-cards/shotgun-surgery/)；收斂成共用模組的做法與遷移時的陷阱在[DRY 原則與共用程式庫](/python/07-refactoring/dry-principle/)。

## 把巨型分支改成分派表

一個函式的主體是一長串 `if/elif`、每個分支處理一種事件類型時，每新增一種事件類型都要在這個函式加一個分支。這個函式是寫成程式碼的集中登記檔，它所在的檔案一直被不同的需求修改，留在熱點排行上（熱點與集中登記檔的定義在[從修改紀錄畫模組邊界](/design-principles/module-boundary-from-change-history/)的〈用 git 歷史量出熱點〉與〈熱點的分類與處理方式〉）。改成分派表（dispatch table）之後，新增一種事件類型只需要加一個處理函式並登記，這是把「新增事件類型」這一類變更做成擴充點，對應的原則是 [Open-Closed Principle（開放封閉原則）](/design-principles/knowledge-cards/open-closed-principle/)：

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

分派表要讓檔案離開熱點排行，處理函式還得放進各自的模組：處理函式都寫在同一個檔案裡時，每個新需求仍然改這個檔，而且都在檔尾追加，兩個同時進行的需求照樣衝突。處理函式各放一個模組之後，手動列出 import 的那份清單（一個模組加一行 import）又是一份集中登記檔，所以登記改成由載入端掃描目錄。`HANDLERS` 與 `register` 搬到獨立的 `registry.py` 最不容易出錯，處理函式的模組從那裡匯入；若把它們寫在 `handlers/__init__.py` 的掃描迴圈之後，處理函式匯入時會遇到還沒初始化完的模組而失敗。`handle` 留在原本的模組，不放進 `registry.py`，否則 `registry.py` 為了觸發登記去 `import handlers`，又會繞回自己形成循環匯入。三個位置的配置是：

```text
registry.py           ← HANDLERS 與 register，不匯入任何處理函式
handlers/
├── __init__.py       ← 掃描同目錄，逐一匯入（見下一個區塊）
├── commit.py         ← from registry import register；@register("commit") def handle_commit
└── merge.py          ← 同上，一種事件類型一個檔
dispatch.py           ← handle() 原本所在的模組：import handlers 觸發登記，handle() 用 HANDLERS.get 分派
```

```python
# handlers/__init__.py：匯入同目錄底下的每一個模組，模組裡的 @register 在匯入時執行登記
import importlib
import pkgutil

for module in pkgutil.iter_modules(__path__):
    importlib.import_module(f"{__name__}.{module.name}")
```

新增一種事件類型只需要在 `handlers/` 底下加一個檔案；`handle` 所在的模組要先 `import handlers`，登記才會發生。處理函式分散在不同套件時，改用套件的 entry points：每個套件在自己的 `pyproject.toml` 宣告登記點，安裝之後由 `importlib.metadata.entry_points()` 列舉出來。每個項目一個片段檔的登記方式，代價是靜態分析看不到登記關係，放進目錄的半成品檔也會被自動登記。登記式的外掛（plugin）架構在[插件系統設計](/python-advanced/03-design-patterns/plugin-system/)，用 metaclass 與裝飾器自動註冊的寫法在[案例：自動註冊機制](/python-advanced/02-metaprogramming/case-studies/auto-registration/)。

## 讓拆出來的模組單向依賴

拆出來的模組之間，依賴只朝一個方向，循環匯入就不會出現。判斷上下層的依據是誰需要知道誰：被較多模組使用、而且自己不需要知道其他拆出模組的那一個在下層，兩個條件都成立。這個例子裡 `command_parse.py` 只把指令字串解析成結構，在最下層；`state.py` 與 `messages.py` 使用解析結果；`__init__.py` 組合三者，在最上層。

兩邊都要呼叫對方時，先看兩邊過去的修改：幾乎每次都一起發生，代表它們是同一類職責，歸類時切錯了，併回同一個模組（判斷見[從修改紀錄畫模組邊界](/design-principles/module-boundary-from-change-history/)的〈從修改紀錄找出職責邊界〉與 [Coupling（耦合）](/design-principles/knowledge-cards/coupling/) 卡片）。修改各自發生時，互相呼叫多半代表中間有一塊共用的定義沒有抽出來，例如 `state.py` 與 `messages.py` 都用到的「並行狀態」資料型別。先確認兩個方向的呼叫是否都必要，有時拿掉其中一邊就夠了；兩邊都必要時，把那塊共用定義再往下抽一層（例如 `models.py`），讓兩者都依賴它。拆分之後 `models.py` 被每個需求都改到時，常見的原因是共用定義抽得太大，裡面混了只有某一個模組用的型別，把那些型別搬回使用它的模組。

## 搬移與修改分開提交

搬移和修改混在同一個 commit 裡，測試一紅，就分不出是搬錯了還是改錯了，所以純搬移的 commit 不同時修改行為，行為的修改放在之後的 commit。`git diff --color-moved` 會把搬移過的行與新寫的行用不同顏色標出，用來確認一個 commit 裡只有搬移。

## 拆分合併的時機

拆分要排在等待中的需求開工之前合併。拆分在某個需求開工之後才合併時，那個需求的分支改的是舊的 `guard.py`，rebase 時會遇到 modify/delete 衝突，或在保留原檔過半內容的那份新檔裡遇到內容衝突（git 的改名偵測把那份新檔當成 `guard.py` 改名而來）；兩種形態的處置與 rebase 沒有衝突時也要做的檢查，寫在[從修改紀錄畫模組邊界](/design-principles/module-boundary-from-change-history/)的〈拆分的時機與等待中的需求〉。

## 實作練習：反例測試

為一個要拆的模組補一組特徵測試，至少包含一筆「應被擋下或應回報錯誤」的反例，再思考：拆分時如果拆錯了——例如把 `-C` 參數的解析搬進 `state.py` 時漏掉一個分支——這組測試抓得到嗎？

---

上一章：[作用域迴歸案例研究](/python/07-refactoring/scope-regression/)
