---
title: "拆分 Python 模組：pytest 的特徵測試、同名套件與重新匯出、自動登記的分派表、避免循環匯入"
date: 2026-10-19
description: "職責邊界已經從修改紀錄歸類出來之後，用 Python 拆分一個模組而不改變對外行為：用 pytest 寫特徵測試與 monkeypatch 的替換目標、改成同名套件並重新匯出、把巨型分支改成自動登記的分派表，以及拆出模組之間循環匯入在 Python 的症狀與解法"
weight: 79
tags: ["python", "refactoring", "srp", "packaging"]
---

這篇整理在 Python 裡拆分一個模組、而對外行為不變的寫法，範圍從職責邊界已經決定好那一刻開始。是否要拆、依什麼切，以及拆分時與語言無關的三件事——特徵測試鎖住行為、搬移與修改分開提交、拆出模組之間的依賴只朝一個方向——寫在[從修改紀錄畫模組邊界](/design-principles/module-boundary-from-change-history/)：那一篇用 git 歷史統計每個檔案被幾個不同的需求修改，再在〈從修改紀錄找出職責邊界〉逐個 commit 把需求歸到職責。本篇沿用那一篇的範例：一支 commit 守衛 `guard.py`，多個 AI 代理人各自在自己的工作目錄同時開發時，代理人工具在執行每一條 shell 指令之前把整條指令字串交給它判斷，它擋下把 commit 寫進其他代理人工作目錄的寫法。修改紀錄歸類出三種職責：命令解析、狀態判斷、訊息產生。

同在 Python 重構這一章的[重構的動機與策略](/python/07-refactoring/refactoring-strategy/)用認知負擔判斷何時該重構、怎麼分階段進行，[程式碼壞味道偵測](/python/07-refactoring/code-smells/)從程式碼本身的寫法辨認壞味道；本篇處理的是決定拆之後怎麼拆。

## 用 pytest 寫特徵測試鎖住拆分前的行為

特徵測試（[characterization test](/testing/knowledge-cards/characterization-test/)）的預期值取自拆分前程式當下的實際輸出，所以寫測試時先對拆分前的程式跑一次，把輸出填成預期值；測試表要含應該擋下的反例，理由在[從修改紀錄畫模組邊界](/design-principles/module-boundary-from-change-history/)的〈拆分時與語言無關的做法〉。用 pytest 寫成：

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

`is_parallel_period` 的結果取決於執行當下有哪些代理人在工作，所以 [fixture](/python/knowledge-cards/pytest-fixture/) 先把它固定住，測試在任何機器上都得到同一個結果。`evaluate` 每次執行時都在 `guard` 模組的命名空間裡查 `is_parallel_period` 這個名字，fixture 用 [monkeypatch](/python/knowledge-cards/monkeypatch/) 替換的正是那個名字。〈改成同名套件並重新匯出，保留原本的匯入路徑〉會把 `guard.py` 改成同名套件、`evaluate` 留在 `guard/__init__.py`，`evaluate` 查名字的位置仍是 `guard` 這個命名空間，所以拆分前後同一個 fixture 都生效；`evaluate` 之後若搬進 `guard/core.py` 這類子模組，它查名字的位置變成 `guard.core`，`monkeypatch.setattr` 的第一個引數要跟著改成 `guard.core`。

測試表裡的 `git -C /other commit` 是應該擋下的寫法。這個範例只示範結構；實際的 commit 守衛還要處理 `--git-dir`、`--work-tree`、`GIT_DIR` 環境變數與先 `cd` 再 commit 這些同樣會把 commit 寫到別處的寫法。

## 改成同名套件並重新匯出，保留原本的匯入路徑

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

`guard.py` 與 `guard/` 同時存在時，Python 的匯入系統在 `import guard` 時取到的是套件，留下來的 `guard.py` 沒有人載入，之後改它不會有任何效果，所以要刪掉。git 依內容相似度判定改名，改名與搬函式混在同一個 commit 時，`__init__.py` 只剩下原檔的一小部分，git 認不出它是 `guard.py` 改名而來，`git log --follow guard/__init__.py` 就追不到改名之前的歷史。所以刪的方式是把它改名成套件的 `__init__.py`，單獨提交一個只改名的 commit，再往外搬函式：

```bash
mkdir guard                          # git mv 不會自動建立目標目錄
git mv guard.py guard/__init__.py
git commit -m "guard.py 改成套件 guard/（只改名）"
```

這個 commit 只影響 `git log` 的追蹤；等待中的需求的分支 rebase 到拆分之後的版本時，git 的改名偵測比對的是拆分前後的整體差異、不看中間的 commit，所以它不決定哪一份新檔被當成改名目標（衝突的兩種形態見[從修改紀錄畫模組邊界](/design-principles/module-boundary-from-change-history/)的〈拆分的時機與等待中的需求〉）。

原本寫 `from guard import evaluate` 的呼叫端不用改。`__init__.py` 從新模組匯入的 `parse_command`、`build_block_message`、`is_parallel_period` 三個名字都被 `evaluate` 用到，所以要留著；`is_parallel_period` 另外還是〈用 pytest 寫特徵測試鎖住拆分前的行為〉那個 fixture 替換的名字。舊的呼叫端若也直接寫 `from guard import parse_command`，`parse_command` 這個名字同時負責相容，等那些呼叫端改成從 `guard.command_parse` 匯入之後，相容的用途才結束。`__init__.py` 在套件匯入時扮演的角色與 `from package import name` 的解析方式，見 Python 官方教學的 [Packages](https://docs.python.org/3/tutorial/modules.html#packages) 一節。

拆分時常會發現同一種判斷在好幾個檔案各寫了一份，例如 commit 守衛和另外兩支擋 push、擋 rebase 的守衛，各自實作「從命令中取出 commit 的目標工作目錄」。三份跟著同一條規則改，是同一份知識（判斷依據見 [DRY](/design-principles/knowledge-cards/dry-principle/) 卡片），規則一改三份都要改，這是[散彈式修改（Shotgun Surgery）](/design-principles/knowledge-cards/shotgun-surgery/)；收斂成共用模組的做法與遷移時的陷阱在[DRY 原則與共用程式庫](/python/07-refactoring/dry-principle/)。

## 把巨型分支改成自動登記的分派表

一個函式的主體是一長串 `if/elif`、每個分支處理一種事件類型時，每新增一種事件類型都要在這個函式加一個分支。這個函式是寫成程式碼的集中登記檔（每加一個功能就要在這裡登記一筆的檔案），它所在的檔案一直被不同的需求修改，留在熱點排行（依被幾個不同需求修改排序的檔案清單）的前段；兩個詞的完整說明在[從修改紀錄畫模組邊界](/design-principles/module-boundary-from-change-history/)的〈用 git 歷史量出熱點〉與〈熱點的分類與處理方式〉。改成分派表（dispatch table）之後，新增一種事件類型只需要加一個處理函式並登記，這是把「新增事件類型」這一類變更做成擴充點，對應的原則是 [Open-Closed Principle（開放封閉原則）](/design-principles/knowledge-cards/open-closed-principle/)：

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

分派表要讓檔案離開熱點排行，處理函式還得放進各自的模組：處理函式都寫在同一個檔案裡時，每個新需求仍然改這個檔，而且都在檔尾追加，兩個同時進行的需求照樣衝突。處理函式各放一個模組之後，手動列出 import 的那份清單（一個模組加一行 import）又是一份集中登記檔，所以登記改成由載入端掃描目錄。`HANDLERS` 與 `register` 放進獨立的 `registry.py`，處理函式的模組從那裡匯入：若把它們寫在 `handlers/__init__.py` 的掃描迴圈之後，處理函式的模組在掃描時被匯入，去 `handlers` 套件找 `register`，而那時 `handlers` 套件還沒執行到定義 `register` 的那一行，匯入就失敗。`handle` 留在原本的模組，不放進 `registry.py`，否則 `registry.py` 為了觸發登記去 `import handlers`，處理函式又回頭匯入 `registry.py`，形成循環匯入。三個位置的配置是：

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

新增一種事件類型只需要在 `handlers/` 底下加一個檔案；`handle` 所在的模組要先 `import handlers`，登記才會發生。處理函式分散在不同套件時，改用套件的 entry points：每個套件在自己的 `pyproject.toml` 宣告登記點，安裝之後由 `importlib.metadata.entry_points()` 列舉出來。這兩種自動登記的共同代價（靜態分析看不到登記關係、半成品檔也會被登記）見[從修改紀錄畫模組邊界](/design-principles/module-boundary-from-change-history/)的〈熱點的分類與處理方式〉。登記式的外掛（plugin）架構在[插件系統設計](/python-advanced/03-design-patterns/plugin-system/)，用 metaclass 與裝飾器自動註冊的寫法在[案例：自動註冊機制](/python-advanced/02-metaprogramming/case-studies/auto-registration/)。

## 拆出模組之間的循環匯入：Python 的症狀與解法

拆出來的模組之間依賴要只朝一個方向，判斷上下層的方法與互相呼叫時是否併回同一個模組，寫在[從修改紀錄畫模組邊界](/design-principles/module-boundary-from-change-history/)的〈拆分時與語言無關的做法〉。Python 違反這一條時的症狀是匯入失敗：`state.py` 與 `messages.py` 互相 `from .state import ...`、`from .messages import ...`，先被匯入的那一個執行到 import 那一行時，另一個還沒執行完，要取的名字還不存在，Python 拋出 `ImportError: cannot import name '...' from partially initialized module '...' (most likely due to a circular import)`。

這個例子裡 `command_parse.py` 只把指令字串解析成結構，在最下層；`state.py` 與 `messages.py` 使用解析結果；`__init__.py` 組合三者，在最上層。兩個模組都用到的定義（例如 `state.py` 與 `messages.py` 都用到的「並行狀態」資料型別）往下抽成一個 `models.py`，兩者都從 `models.py` 匯入、彼此不互相匯入，循環就斷開。`models.py` 之後被每個需求都改到時的判讀，在[從修改紀錄畫模組邊界](/design-principles/module-boundary-from-change-history/)的〈拆分之後重跑熱點統計〉。

拆分要排在等待中的需求開工之前合併，rebase 時的兩種衝突形態與處置在[從修改紀錄畫模組邊界](/design-principles/module-boundary-from-change-history/)的〈拆分的時機與等待中的需求〉；搬移與修改分開提交、用 `git diff --color-moved` 確認只有搬移，在同一篇的〈拆分時與語言無關的做法〉。

## 實作練習：反例測試

為一個要拆的模組補一組特徵測試，至少包含一筆「應被擋下或應回報錯誤」的反例，再思考：拆分時如果拆錯了——例如把 `-C` 參數的解析搬進 `command_parse.py` 時漏掉一個分支——這組測試抓得到嗎？

---

是否要拆、依什麼切：[從修改紀錄畫模組邊界](/design-principles/module-boundary-from-change-history/)（用 git 歷史量出被多個需求修改的檔案，逐個 commit 歸類職責）。

上一章：[作用域迴歸案例研究](/python/07-refactoring/scope-regression/)
