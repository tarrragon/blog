---
title: "只讀檢查腳本 host-check.py 的原始碼與逐段說明：選項的切分與各工具的白名單規則、清單的載入與驗證、指令的執行、各項檢查、路徑與時間的量測、結果檔與命令列，以及這一版的已知限制"
date: 2026-10-26
slug: "host-check-script-source"
description: "要讀主機維護清單的只讀檢查腳本實際怎麼切分各工具的選項、怎麼驗證清單、怎麼判定 PASS、WARN 與 MANUAL、怎麼寫結果檔，或要照它的做法寫自己的檢查腳本時，查完整的 Python 原始碼與每一段這樣寫的理由"
weight: 2
tags: ["operations", "maintenance", "python", "toml", "systemd", "hands-on"]
---

> **事件說明**：2026-10-26，把作者私有專案裡的檢查腳本 `host-check.py` 在這一天的版本（commit `3fc41c0`）整理成這篇。這一版的單元測試在一台 Apple Silicon 的 macOS 開發機上，用 uv 分別起 Python 3.12 與 Python 3.15 各執行一次；這一版在 Oracle Linux 10 的容器裡執行過；一台 Oracle Linux 10.2 的雲端主機上執行過的，是修正「權限擋下的目錄被判成路徑不存在」之前的版本。

這篇是主機維護清單的只讀檢查腳本 `host-check.py` 的完整原始碼，依腳本自己的結構分節。每一個 `##` 節先寫這一段程式負責什麼、它滿足的是清單或執行環境的哪一項需求，接著是這一段的原始碼，之後說明從程式碼不容易看出來的地方：為什麼這樣判斷、換成另一種寫法會讓哪一種寫入或誤判通過、哪一項單元測試鎖住這個行為。各節依序是：檔頭的說明與共用常數；照 `getopt_long` 語法切分選項的函式；`systemctl`、`journalctl`、`firewall-cmd`、`ss`、`find`、`sqlite3`、`openssl`、`sshd`、`needs-restarting`、`dnf`、`rpm`、`ausearch` 各自的選項規則，以及不另外比對選項的工具；判定一條指令是否只讀的 `readonly_violation` 與腳本自己組出來的指令；清單的載入與驗證；執行指令的 `Runner` 與時鐘；`Checker` 對入口與接聽中的連接埠、log、會累積的資料、檔案系統、自動更新、暫停與恢復步驟的檢查；路徑的展開與大小的量測；時間字串的解析與組輸出用的小函式；結果檔的讀寫與跟前一次的差異；命令列與 exit code；最後是這一版的已知限制與重現方式，依清單的驗證、指令的執行與 exit code、各項檢查、結果檔分組。

各節的 `python` 程式碼區塊照順序接起來就是完整的腳本。區塊內的空行照原檔保留；兩個區塊之間夾著說明的位置，原檔是空行，接的時候補回去：下一個區塊以縮排開頭（`Checker` 類別裡的方法）時補一個空行，其餘補兩個空行。區塊之間補幾個空行只影響跟原檔逐字比對的結果，不影響執行。照這條規則接出來的檔案是 1442 行，sha256 是 `22228d77ee7bc0d126401d04fc3a73b37e0a5768566abefa2b2b9dce69a0761d`；這是本篇版本（拿掉 `# i18n-exempt` 標記、換掉兩處票號之後）的值，不是私有專案裡原檔的值。跟原檔相比改了兩處：行尾給私有專案的翻譯檢查工具用的 `# i18n-exempt` 標記拿掉了；檔頭說明裡兩處專案內部的工作票號，換成不帶票號的寫法。腳本只用 Python 標準函式庫，需要 Python 3.11 以上（解析 [TOML](/infra/knowledge-cards/toml/) 的 `tomllib` 在 3.11 加入）。單元測試的檔案沒有收進這篇，說明裡提到的測試以測試函式的名字指稱，並寫出它斷言的行為；每一個 `##` 節第一次提到時寫成「單元測試 `test_…`（本篇沒有收錄）」。74 項單元測試在 Python 3.12 與 3.15 都通過；以 root 執行時，`test_glob_in_unlistable_dir_is_unreadable`、`test_unreadable_glob_with_missing_ok_does_not_pass`、`test_literal_path_under_unreadable_parent_is_unreadable` 這三項會失敗：它們靠目錄權限擋住讀取，而 root 不受目錄權限限制，測試裡的前提檢查寫明以 root 執行時這幾項失敗、不跳過（讀碼）。

文中的行為標兩種來源。「實跑」是實際執行過的結果：沒有另外註明環境的，是在一台 Apple Silicon 的 macOS 26.5 開發機上，以 Python 3.15.0 執行這一版的腳本，把它載入成模組、直接呼叫函式或方法，或從命令列跑整支腳本（Python 的版本差異另外用 uv 起 3.10.18、3.11.13、3.12.11）；在別的環境跑的，就地寫出環境。「讀碼」是從程式碼推得、沒有執行過的行為。

清單的格式與欄位、白名單要擋下哪些寫法與理由、輸出與 exit code 的讀法、結果檔，以及 systemd 沙箱各屬性實跑的效果，寫在 [主機維護清單寫成 TOML：JSON、YAML、TOML 的取捨、TOML 1.0 與 1.1 的版本差異、清單的欄位設計與只讀檢查腳本](/operations/09-host-lifecycle/host-manifest-in-toml/)，這篇不重寫那些理由，各節連到對應的段落。把這支腳本與每台的清單部署到多台主機、以 sudo 與 `systemd-run` 執行它的步驟與輸出，在 [多台主機維護清單的實作紀錄：在容器上安裝 ansible-core 與 Terraform、由 Terraform 產生 inventory、用 Ansible 的範本部署每台的清單、以 sudo 與 systemd-run 執行檢查腳本，以及清理](/operations/09-host-lifecycle/hands-on/multi-host-manifest-walkthrough/)。

接起來的腳本要一份清單才跑得起來：它預設讀腳本所在目錄的 `host.toml`，沒有清單或清單格式錯時以 exit 2 結束、一項檢查都不執行。最小的清單從 [多台主機維護清單的實作紀錄：在容器上安裝 ansible-core 與 Terraform、由 Terraform 產生 inventory、用 Ansible 的範本部署每台的清單、以 sudo 與 systemd-run 執行檢查腳本，以及清理](/operations/09-host-lifecycle/hands-on/multi-host-manifest-walkthrough/)〈變數檔與範本：檢查腳本實際要求的欄位、兼任兩種角色的主機〉的 `host.toml.j2` 取得：把裡面的 `{{ }}` 換成這台主機實際的值，就是一份這支腳本載入得過的清單；哪些段落必填、哪些可以不寫，在本篇〈清單的載入與驗證：Probe、_Validator、load_manifest 與 validate〉。

## 檔頭的說明、匯入的模組與共用常數

檔頭的 docstring 是寫給維護的人讀的使用說明：用法、輸出的格式、結果檔、systemd 沙箱要加的屬性、exit code 與只讀的保證；這些行為的理由與實跑結果在 [主機維護清單寫成 TOML：JSON、YAML、TOML 的取捨、TOML 1.0 與 1.1 的版本差異、清單的欄位設計與只讀檢查腳本](/operations/09-host-lifecycle/host-manifest-in-toml/)〈只讀檢查腳本的白名單、輸出、exit code 與結果檔〉。docstring 之後是匯入的模組與整支腳本共用的常數。

```python
#!/usr/bin/env python3
"""web-demo 主機的只讀維護檢查。

在主機上讀同目錄的 host.toml，逐項執行 where = "host" 的只讀檢查，主機外
（OCI Console、Cloudflare dashboard、開發機）的項目印成 MANUAL。

用法（在主機上，以 root 執行；firewalld 查詢、sshd -T、collector 的資料庫、nginx 的 log 目錄、
audit.log 與 journal 一般帳號讀不到，專用帳號的實測見 README〈以專用帳號執行〉）：

    sudo python3 host-check.py                       # 例行維護：入口、log、累積的資料、更新
    sudo python3 host-check.py --phase suspend       # 暫停上線前要做的步驟
    sudo python3 host-check.py --phase resume        # 恢復上線後要做的步驟
    sudo python3 host-check.py --manifest other.toml --set repo_dir=/opt/monitor
    sudo python3 host-check.py --state-file PATH     # 結果檔換路徑（預設 /var/lib/host-check/last.json）
    sudo python3 host-check.py --no-state            # 不讀也不寫結果檔

輸出：每項一行 `PASS` / `WARN` / `MANUAL`、項目名與理由；接著是與前一次的差（`since:` 開頭，
其後每個差一行：`CHANGED` 狀態改變、`DELTA` 值改變、`NEW` 新出現、`GONE` 消失）；結尾一行
`summary: N PASS, M WARN, K MANUAL`；沒有印出 summary 代表腳本中途中止。

結果檔：每次執行結束把這次的計數與量到的值（探針值、累積的 bytes、可用 bytes）寫進結果檔
（JSON，每個 phase 一段，只替換本次的 phase），下一次拿它算差。目錄不存在時以 0700 建立，檔案
0600，用同目錄暫存檔加 os.replace 寫入。目錄已存在時不改它的權限：由 systemd 的 StateDirectory=
建立的目錄，權限照 StateDirectoryMode=（預設 0755，每次啟動都會把既有目錄改回這個值），沙箱裡
執行時要設 StateDirectoryMode=0700。讀不到、壞掉或寫不進去只在 stderr 印 `note:`，不改變
exit code；清單本身只描述要檢查什麼，不存放結果。

systemd 沙箱（在 Oracle Linux 10 容器裡實測）：ProtectSystem=strict 下要加 ReadWritePaths=/var/log /var/cache/dnf
（dnf needs-restarting 要寫 dnf.log 與 metadata lock），StateDirectory=host-check 加 StateDirectoryMode=0700；
NoNewPrivileges、PrivateTmp、IPAddressDeny=any 不影響檢查；不開 PrivateNetwork（ss 看不到主機的 socket，
入口與 listen-audit 的檢查都會失準）。完整設定見 README〈在 systemd 沙箱裡執行〉。

exit code：
    0  全部 PASS，或只有 PASS 與 MANUAL
    1  至少一項 WARN
    2  清單格式錯（缺必填欄位、型別錯、要執行的指令不在只讀白名單裡），一項都沒有執行

只讀的保證：
    - 指令不經過 shell（shlex 切詞後直接 exec），沒有管線、轉向與命令替換。
    - 要執行的每一條指令在執行任何一條之前先比對白名單（READONLY_RULES）；
      不在白名單裡、或帶了會改變狀態的參數（find -delete、
      firewall-cmd --add-*、sqlite3 沒有同時帶 -init /dev/null、-readonly 與 -safe 這類）時，整份清單判成格式錯。
    - systemctl、dnf、rpm、journalctl、ss、find 的選項是列允許：依各工具自己的選項語法（getopt_long，
      吃值的選項會吃掉下一個字，值可黏在選項後）切分，表外的選項一律拒絕，所以工具日後新增的
      寫入選項預設就是拒絕（例：rpm --pipe/--eval/-D、systemctl -H/-M、dnf -x、journalctl --cursor-file）。
    - sshd 只接受單獨的 -T；指令的路徑只接受裸名或 /usr/bin、/usr/sbin、/bin、/sbin 下的檔案。
    - command 一律會被執行（且必須通過白名單）；manual_command、purge_command 是要人執行的動作，
      一律只印出來。只印的位置（[[log]]、[[suspend]] / [[resume]]、主機外的 [[entrypoint.verify]]）
      寫舊名 command 判成格式錯。
    - 寫結果檔之外不改動任何受檢狀態；結果檔是腳本自己唯一會寫的檔案。例外：collector 停止後
      資料庫的 -shm、-wal 已被收掉，此時 sqlite3 -readonly 會自己建出這兩個檔（擁有者同資料庫）；
      在唯讀檔案系統（ProtectSystem=strict）上建不出來，sqlite3 exit 14，該項印成 WARN。
    - 檔案大小與時間用 Python 的 os.lstat 量，不執行 du。

只用標準函式庫，需要 Python 3.11 以上（tomllib）。
"""

from __future__ import annotations

import argparse
import configparser
import datetime as dt
import glob
import json
import os
import re
import shlex
import stat
import subprocess
import sys
import tempfile
import time
import tomllib
from dataclasses import dataclass, field
from typing import Any, Callable

WHERE_VALUES = ("host", "external", "console")
EXPOSURE_VALUES = ("public", "cdn-only", "admin-only", "loopback")
PROTOCOL_VALUES = ("tcp", "udp")
BILLED_VALUES = ("yes", "no", "unknown", "n/a")
MEASURE_VALUES = ("lines", "value", "age_days")
PHASES = ("maintain", "suspend", "resume")
COMMAND_TIMEOUT_S = 30
DEFAULT_STATE_FILE = "/var/lib/host-check/last.json"
STATE_FORMAT = 1

VAR_RE = re.compile(r"\{\{([A-Za-z_][A-Za-z0-9_]*)\}\}")
```

docstring 裡的 README〈以專用帳號執行〉與 README〈在 systemd 沙箱裡執行〉是私有專案的 README，沒有公開；改用專用帳號執行時哪些檢查讀得到、哪些讀不到，以及沙箱每一個屬性的實跑效果，寫在清單寫成 TOML 的那篇概念文章的〈只讀檢查腳本的白名單、輸出、exit code 與結果檔〉。docstring 裡的 `web-demo` 是示範清單所描述的那台主機上跑的服務，collector 是那台主機上寫 SQLite 資料庫的程式。

docstring 裡有幾句跟程式實際的行為不一致，程式碼照原檔保留，實際行為以後面的節為準：

- **「systemctl、dnf、rpm、journalctl、ss、find 的選項是列允許：依各工具自己的選項語法（getopt_long，……）切分」**：「列允許」成立，`find` 也是列允許；而 `find` 不照 `getopt_long` 語法切分，它的規則自己逐個參數比對，寫在〈find 的運算式〉。照 `getopt_long` 語法切分的是 `systemctl`、`journalctl`、`ss`、`needs-restarting`、`dnf`、`rpm` 這六支，寫在〈選項的切分：OptionSpec 與 getopt_long 語法〉。
- **exit code 2 的「清單格式錯（……），一項都沒有執行」**：清單格式錯時成立。exit 2 另有一個出口：清單通過載入時的比對、執行時 `Runner` 的白名單又拒絕了一條指令，這時在它之前的指令已經執行過，寫在〈命令列與 exit code：main〉。
- **exit code 1 的「至少一項 WARN」**：檢查中途丟出沒有接住的例外時，Python 也以 exit 1 結束，這時 stdout 沒有 `summary:` 那一行，寫在〈host-check.py（3fc41c0）的已知限制與重現方式〉的〈指令的執行與 exit code：沒有接住的例外〉。
- **結果檔的「目錄不存在時以 0700 建立」**：0700 只套在 `os.makedirs` 這次新建的最後一層目錄，中間各層用預設的權限，寫在〈結果檔的讀寫與跟前一次的差異〉。
- **只讀保證的「檔案大小與時間用 Python 的 os.lstat 量」**：會累積的資料用 `os.lstat`；`check_logs` 確認檔案型的 log 時用 `os.stat`（會跟隨符號連結），檔案系統的剩餘空間用 `os.statvfs`，寫在〈定期讀的 log〉與〈檔案系統的剩餘空間〉。

`WHERE_VALUES` 到 `PHASES` 是清單欄位允許的值，下面的 `validate` 拿它們比對每個欄位，`PHASES` 同時是命令列 `--phase` 的選項。這幾個常數只是允許值的清單：加一個值之後，`validate` 就放行它，而用到那個值的分支沒有跟著改時，新的值在執行時出錯或被當成別的值處理。每個常數要一起改的位置：

- **`WHERE_VALUES`**：`_manual_text` 用 `{"console": "主控台", "external": "主機外"}` 查表，新的值在印 `MANUAL` 時丟出 `KeyError`（實跑：`_manual_text("bastion", …)` 丟出 `KeyError: 'bastion'`）；`validate` 與 `Checker` 都只分 `where == "host"` 與其餘，其餘的值一律走主機外的路徑（讀碼）。
- **`MEASURE_VALUES`**：`Checker.measure` 只分 `lines` 與 `value`，其餘一律當成時間解析；新的量法沒有在 `measure` 加分支時，被當成 `age_days` 算出天數（實跑：`measure("bytes", "x=2026-10-26T00:00:00Z")` 回傳了一個天數）。
- **`PHASES`**：`Checker.run` 把 `maintain` 以外的值都交給 `check_phase`、讀 `self.m[phase]`，而 `validate` 只為 `for phase in ("suspend", "resume")` 這兩個建段落；新的階段要同時改這個迴圈，否則執行時丟出 `KeyError`（實跑：`Checker({}).run("drain")` 丟出 `KeyError: 'drain'`）。
- **`PROTOCOL_VALUES`**（讀碼）：`LISTEN_COMMAND` 只帶 `-t -u`，`listening_sockets` 只收這兩種協定，`audit_listening` 的提示用協定的第一個字母組 `ss -lnp{p[0]}`；新的協定要同時改這三處，以及 `ss` 規則允許的選項。
- **`EXPOSURE_VALUES`、`BILLED_VALUES`**（讀碼）：只在 `validate` 比對、在理由裡原樣印出，加值不必改其他位置。`COMMAND_TIMEOUT_S` 是 `Runner` 等一條指令結束的上限，超過時那一項記成 exit 124 並印成 `WARN`：一條卡住的指令（等網路、等鎖）只讓那一項失敗，其餘檢查照常跑完。`DEFAULT_STATE_FILE` 與 `STATE_FORMAT` 是結果檔的預設路徑與格式版本。`VAR_RE` 比對清單字串裡的 `{{名稱}}`，名稱只收 ASCII 的英文字母、數字與底線，第一個字元不能是數字；Python 的識別字另外收非 ASCII 的字母，`{{主機}}` 這種名稱在這裡對不上，原樣留在字串裡。

```python
class ManifestError(Exception):
    """清單格式錯；errors 是逐條的原因。"""

    def __init__(self, errors: list[str]):
        super().__init__("\n".join(errors))
        self.errors = errors
```

`ManifestError` 帶著逐條的錯誤原因。驗證清單的程式把整份清單的錯誤都收齊之後才丟一次這個例外，命令列再逐行印出 `manifest error:`，所以改清單的人一次看到全部的錯誤，不必改一條、跑一次。用 Ansible 部署時，`template` 任務的 `validate` 在受管主機上載入這支腳本、呼叫 `load_manifest` 驗證剛產生的清單，清單格式錯時這個例外讓那個任務失敗，格式錯的清單不會寫到正式的位置，做法在 [多台主機維護清單的實作紀錄：在容器上安裝 ansible-core 與 Terraform、由 Terraform 產生 inventory、用 Ansible 的範本部署每台的清單、以 sudo 與 systemd-run 執行檢查腳本，以及清理](/operations/09-host-lifecycle/hands-on/multi-host-manifest-walkthrough/)〈部署清單：建目錄、copy 與 template、validate 改用檢查腳本的載入函式、--check 的預覽〉。

## 選項的切分：OptionSpec 與 getopt_long 語法

白名單要比對一條指令的選項，得先分出一串參數裡哪些是選項、哪些是選項的值、哪些是位置參數。這一段照 `getopt_long`（GNU C 函式庫解析命令列選項的函式，多數 Linux 工具照它的規則解析參數）的語法切分，`systemctl`、`journalctl`、`ss`、`needs-restarting`、`dnf`、`rpm` 的規則共用它。這六支裡，`systemctl`、`journalctl`、`ss` 用 `getopt_long` 解析參數，`rpm` 用 popt，`dnf` 與 `needs-restarting` 用 Python 的 argparse；popt 與 argparse 在短選項合併、值黏在選項後面、`--名稱=值` 與 `--` 這幾點，切法跟 `getopt_long` 相同，所以共用同一套切分；為什麼要照工具自己的語法切、沒照語法切時放行了哪些寫法，在 [主機維護清單寫成 TOML：JSON、YAML、TOML 的取捨、TOML 1.0 與 1.1 的版本差異、清單的欄位設計與只讀檢查腳本](/operations/09-host-lifecycle/host-manifest-in-toml/)〈只讀檢查腳本的白名單、輸出、exit code 與結果檔〉。

```python
# ── 只讀白名單 ──────────────────────────────────────────────
# 每條規則收 argv（argv[0] 已是 basename），回傳 None 代表放行，字串代表拒絕的理由。


# 一支工具允許的選項（列允許，表外一律拒絕）；選項名連同開頭的 - 一起寫。
@dataclass(frozen=True)
class OptionSpec:
    flags: frozenset[str] = frozenset()  # 不吃值的旗標
    values: frozenset[str] = frozenset()  # 一定吃值的選項
    optional: frozenset[str] = frozenset()  # 選填值：只吃黏在一起的值，或下一個字是整數時


def _spec(flags: str = "", values: str = "", optional: str = "") -> OptionSpec:
    return OptionSpec(frozenset(flags.split()), frozenset(values.split()), frozenset(optional.split()))


def _parse_options(args: list[str], spec: OptionSpec, stop_at_first: bool = False) -> tuple[list[str], set[str], str | None]:
    # 依 getopt_long 的語法把 args 切成（位置參數, 出現過的選項, 拒絕理由）：
    # 短選項可合併（-qa），吃值的短選項值黏在後面或在下一個字；長選項 --name[=value]；-- 之後全是位置參數。
    # stop_at_first 時，第一個位置參數起的全部字都放進位置參數（不再解析選項）。
    positionals: list[str] = []
    seen: set[str] = set()
    i = 0
    while i < len(args):
        tok = args[i]
        i += 1
        if tok == "--":
            positionals.extend(args[i:])
            break
        if not tok.startswith("-") or tok == "-":
            positionals.append(tok)
            if stop_at_first:
                positionals.extend(args[i:])
                break
            continue
        if tok.startswith("--"):
            name, eq, _ = tok.partition("=")
            consumed = _long_option(name, bool(eq), spec, args, i)
            if isinstance(consumed, str):
                return positionals, seen, consumed
            seen.add(name)
            i += consumed
            continue
        for pos in range(1, len(tok)):
            name = "-" + tok[pos]
            if name in spec.flags:
                seen.add(name)
                continue
            consumed = _value_option(name, pos + 1 < len(tok), spec, args, i)
            if isinstance(consumed, str):
                return positionals, seen, consumed
            seen.add(name)
            i += consumed
            break
    return positionals, seen, None


def _long_option(name: str, has_value: bool, spec: OptionSpec, args: list[str], i: int) -> int | str:
    # 回傳這個長選項多吃掉幾個後續字；拒絕時回傳理由。
    if name in spec.flags:
        return f"選項 {name} 不吃值" if has_value else 0
    return _value_option(name, has_value, spec, args, i)


def _value_option(name: str, has_glued_value: bool, spec: OptionSpec, args: list[str], i: int) -> int | str:
    if name not in spec.values and name not in spec.optional:
        return f"選項 {name} 不在允許清單"
    if has_glued_value:
        return 0
    nxt = args[i] if i < len(args) else None
    if name in spec.optional:
        return 1 if nxt is not None and nxt.isdigit() else 0
    return 1 if nxt is not None else f"選項 {name} 缺少值"
```

`OptionSpec` 把一支工具允許的選項分成三組，分組決定切分時這個選項是否吃掉下一個參數：`flags` 不吃值；`values` 一定吃值，值黏在選項後面（`-pX`）時吃黏著的那一段，否則吃下一個參數；`optional` 是值可帶可不帶的選項，值黏在選項後面時吃黏著的那一段，沒有黏著的值時，下一個參數全是數字才吃它，否則不吃。`journalctl` 的 `-n` 放在 `optional`，所以 `journalctl -n 20 -u sshd` 的 `20` 被當成 `-n` 的值，`journalctl -n -u sshd` 的 `-u` 照樣被當成選項比對。「全是數字」用 `str.isdigit()` 判斷：`-5`、`+5` 帶著正負號，不算數字，不會被當成值；`²`、`٣` 這類 Unicode 的數字字元，`isdigit()` 回 `True`，會被當成值（這幾個字串都在 Python 裡實跑過）。把一個吃值的選項錯放進 `flags`，它的值會被當成下一個位置參數，子命令的判定就跟工具實際執行的不同。

短選項的那個迴圈從第二個字元起逐字查：查到旗標就看下一個字元（`-qa` 是 `-q` 與 `-a`）；查到吃值的選項，這個字元後面還有字時（`-ppid`）把剩下的當成值，沒有時吃下一個參數，然後離開這個參數。單獨一個 `-` 算位置參數：照 `getopt` 的慣例，它是一個運算元（多半代表標準輸入），不是選項。長選項用 `partition("=")` 分出名稱與值，旗標帶了 `=值` 時拒絕（`--no-pager=1`）。名稱一律整字比對，`getopt_long` 接受的前綴縮寫（`--cursor-fi` 當成 `--cursor-file`）不在表上，所以被拒絕。表外的選項回傳拒絕理由、不往下切，三組都不在表上的選項就是被拒絕的那一類，這是列允許的寫法在程式裡的樣子。

`stop_at_first` 給 `dnf` 用：切到第一個位置參數（子命令）就停，子命令之後的參數交給那個子命令自己的規則。單元測試 `test_allowed`（本篇沒有收錄）放行 `systemctl --no-pager -ppid status nginx`；`test_rejected` 拒絕 `systemctl -p show stop nginx`（`-p` 吃掉 `show`，子命令是 `stop`）、`systemctl -pshow stop nginx` 與 `systemctl --no-pager=1 status nginx`。

## 各工具的選項規則：systemctl、journalctl、firewall-cmd、ss、find、sqlite3、openssl、sshd、needs-restarting、dnf、rpm、ausearch

每支有選項規則的工具一個函式，收切好的參數串列（第一個元素已經換成檔名），放行時回傳 `None`，拒絕時回傳理由的字串。每支工具允許與排除了哪些選項、排除的理由，在 [主機維護清單寫成 TOML：JSON、YAML、TOML 的取捨、TOML 1.0 與 1.1 的版本差異、清單的欄位設計與只讀檢查腳本](/operations/09-host-lifecycle/host-manifest-in-toml/)〈只讀檢查腳本的白名單、輸出、exit code 與結果檔〉的各工具清單；這一節寫程式怎麼實現那些規則，以及每一支的語法跟〈選項的切分：OptionSpec 與 getopt_long 語法〉的切分有哪裡不同。

### systemctl 的子命令與選項

```python
SYSTEMCTL_READ = {"is-active", "is-enabled", "is-failed", "show", "status", "cat", "list-timers", "list-units", "list-unit-files"}
SYSTEMCTL_OPTIONS = _spec(
    flags="--no-pager --no-legend --plain --value -a --all -l --full -q --quiet --failed",
    values="-p --property -P -t --type --state -n --lines -o --output --timestamp",
)


def _rule_systemctl(argv: list[str]) -> str | None:
    # -p、-t 這類選項會吃掉下一個字，所以子命令要先依選項語法切出來，不能取第一個不以 - 開頭的字。
    # -H/--host 與 -M/--machine 會把操作送到別台主機或容器（-H 以 root 的 SSH 身分連出去），不在允許清單。
    positionals, _, err = _parse_options(argv[1:], SYSTEMCTL_OPTIONS)
    if err:
        return f"systemctl {err}"
    if not positionals or positionals[0] not in SYSTEMCTL_READ:
        return f"systemctl 只允許 {sorted(SYSTEMCTL_READ)}"
    return None
```

子命令取切分之後的第一個位置參數，查 `SYSTEMCTL_READ`。只寫 `systemctl` 而沒有子命令時，`positionals` 是空的，同樣拒絕：systemctl 沒有子命令時執行的是 `list-units`，規則要求清單把子命令寫出來，判定才不依賴工具的預設值。`-H` 與 `-M` 不在 `SYSTEMCTL_OPTIONS` 裡，所以黏在一起的 `-Ha@b`、長選項的 `--host=a@b` 與分開寫的 `--host a@b` 都在切分時被拒絕，單元測試 `test_rejected`（本篇沒有收錄）逐一列了這幾種寫法。

### journalctl 的選項與 match 條件

```python
# --cursor-file 與 --vacuum-*、--rotate、--flush、-f 都會寫檔或改變 journal，不在允許清單。
JOURNALCTL_OPTIONS = _spec(
    flags="-q --quiet --no-pager -r --reverse --utc --no-hostname -k --dmesg -a --all --disk-usage --list-boots",
    values="-u --unit --since --until -o --output -g --grep -p --priority -t --identifier",
    optional="-n --lines",
)


def _rule_journalctl(argv: list[str]) -> str | None:
    _, _, err = _parse_options(argv[1:], JOURNALCTL_OPTIONS)
    return f"journalctl {err}" if err else None
```

`journalctl` 的位置參數是篩選紀錄的 match 條件（`_SYSTEMD_UNIT=x.service`），只用來讀，所以規則只比對選項、不看位置參數。`-n` 放在 `optional`，`test_rejected` 的 `journalctl -n --vacuum-size=1G` 因此被拒絕：`-n` 不吃以 `-` 開頭的下一個參數，`--vacuum-size` 照樣被當成選項比對，而它不在表上。`-f`（持續讀新的紀錄、不會結束）也不在表上，它會讓指令一直跑到 `COMMAND_TIMEOUT_S` 的上限。

### firewall-cmd 的參數樣式

```python
FIREWALL_READ = re.compile(r"^--(permanent|zone=\S+|state|query-\S+|list-\S+|get-\S+|info-\S+)$")


def _rule_firewall_cmd(argv: list[str]) -> str | None:
    for a in argv[1:]:
        if not FIREWALL_READ.match(a):
            return f"firewall-cmd 只允許 --query-*、--list-*、--get-*、--info-*、--state、--permanent、--zone=，不允許 {a}"
    return None
```

`firewall-cmd` 的查詢都寫成一個 `--名稱` 或 `--名稱=值` 的參數，所以規則逐個參數比對樣式，不切分。每個參數都要對上樣式，位置參數因此一個都不允許：分開寫的 `--zone public` 裡，`public` 對不上任何樣式而被拒絕，值要用 `=` 黏在選項上。改動設定的選項（`--add-port=`、`--remove-*`、`--reload`）對不上 `query-`、`list-`、`get-`、`info-` 這幾個前綴，`test_rejected` 列了 `firewall-cmd --add-port=8765/tcp` 與 `firewall-cmd --reload`。

### ss 的選項與過濾式

```python
# -K（kill）、-D（寫檔）、-N（換 netns）、-F（讀過濾檔）、-r（反查 DNS，對外連線）、-E 都不在允許清單。
# 位置參數是過濾式（state listening、sport = :443 這類），ss 只讀它。
SS_OPTIONS = _spec(
    flags=(
        "-H --no-header -l --listening -n --numeric -t --tcp -u --udp -a --all -p --processes -4 --ipv4 -6 --ipv6 "
        "-x --unix -w --raw -e --extended -i --info -m --memory -s --summary -o --options"
    ),
    values="-f --family -A --query",
)


def _rule_ss(argv: list[str]) -> str | None:
    _, _, err = _parse_options(argv[1:], SS_OPTIONS)
    return f"ss {err}" if err else None
```

`ss` 的位置參數是過濾式，跟 `journalctl` 一樣只比對選項。合併的短選項逐字查，所以 `ss -tlnK` 在查到 `K` 時被拒絕，`-K` 不必單獨出現；`-f` 一定吃值，單獨的 `ss -f` 以「缺少值」拒絕。`-E`（持續印出 socket 的事件、不會結束）不在表上，理由跟 `journalctl -f` 相同。

### find 的運算式

```python
# find 不是 getopt 語法，所以自己走一遍：選項只認下面兩張表（-delete、-exec*、-ok*、-fprint*、-fls、
# -D、-files0-from 都不在裡面）；值只吃下一個字；不以 - 開頭的字是路徑或運算子的括號、驚嘆號。
FIND_LEADING = frozenset({"-H", "-L", "-P"})
FIND_OPERATORS = frozenset({"(", ")", "!", ",", "-not", "-and", "-or", "-a", "-o"})
FIND_FLAGS = frozenset(
    "-print -print0 -prune -empty -xdev -mount -true -false -readable -writable -executable".split()
)
FIND_VALUES = frozenset(
    (
        "-name -iname -path -ipath -regex -iregex -type -xtype -mtime -mmin -atime -amin -ctime -cmin "
        "-newer -size -user -group -uid -gid -perm -links -inum -maxdepth -mindepth -printf"
    ).split()
)


def _rule_find(argv: list[str]) -> str | None:
    args = argv[1:]
    i = 0
    while i < len(args) and args[i] in FIND_LEADING:
        i += 1
    while i < len(args):
        tok = args[i]
        i += 1
        if tok in FIND_FLAGS or tok in FIND_OPERATORS:
            continue
        if tok in FIND_VALUES:
            if i >= len(args):
                return f"find 的選項 {tok} 缺少值"
            i += 1
            continue
        if tok.startswith("-") and tok != "-":
            return f"find 的選項 {tok} 不在允許清單"
    return None
```

`find` 的參數是起點路徑加一串運算式，運算式的元素是單一連字號的整字（`-name`、`-mtime`），不能照 `getopt_long` 合併或拆字，所以規則自己逐個參數比對。`-H`、`-L`、`-P` 只在最前面接受，跟 `find` 自己的語法一致；放在中間的 `-L` 對不上任何一張表而被拒絕。以 `-` 開頭而不在表上的參數一律拒絕，`-delete`、`-exec`、`-fprint` 這類動作因此不必逐一列出來擋；`-newerXY` 這種帶後綴的寫法也不在表上，`test_rejected` 列了它。`-printf` 在允許的表上，因為它把格式化的結果印到標準輸出；同類的 `-fprintf` 寫進檔案，不在表上。

### sqlite3 的必帶選項與 dot-command

```python
# sqlite3 的長選項是單破折號整字（--x 等同 -x），不是 getopt 語法，所以自己走一遍：先把開頭的 -- 正規化成 -，再整字比對。
SQLITE_FLAGS = frozenset(
    "-readonly -safe -bail -batch -header -noheader -csv -json -line -list -box -table -markdown -column -quote -tabs -nofollow".split()
)
SQLITE_VALUES = frozenset("-separator -newline -nullvalue".split())
SQLITE_REQUIRED = frozenset({"-readonly", "-safe", "-init"})


def _rule_sqlite3(argv: list[str]) -> str | None:
    # -readonly 只讓資料庫檔唯讀；SQL 函式 writefile()、edit() 與 ATTACH 仍能寫檔案系統。
    # -safe 擋下這些函式與會寫檔的 dot-command（OL10 的 3.46.1 實測支援）。
    # -init 檔與 ~/.sqliterc 在 safe mode 生效前就執行（.shell 照跑，實測會建檔），HOME 擋不住
    # （sqlite3 用 getpwuid 找家目錄）；唯一的擋法是 -init /dev/null 取代 ~/.sqliterc。三個都要帶。
    args = argv[1:]
    seen: set[str] = set()
    positionals: list[str] = []
    i = 0
    while i < len(args):
        tok = args[i]
        i += 1
        if not tok.startswith("-"):
            positionals.append(tok)
            continue
        name = tok[1:] if tok.startswith("--") else tok
        if name in SQLITE_FLAGS:
            seen.add(name)
        elif name == "-init":
            if i >= len(args) or args[i] != "/dev/null":
                return "sqlite3 的 -init 的值必須是 /dev/null"
            seen.add(name)
            i += 1
        elif name in SQLITE_VALUES:
            if i >= len(args):
                return f"sqlite3 的選項 {tok} 缺少值"
            i += 1
        else:
            return f"sqlite3 的選項 {tok} 不在允許清單"
    if not SQLITE_REQUIRED <= seen:
        return "sqlite3 要同時帶 -init /dev/null、-readonly 與 -safe（~/.sqliterc 與 writefile() 都會寫檔）"
    for sql in positionals[1:]:
        if any(line.lstrip().startswith(".") for line in sql.splitlines()):
            return "sqlite3 的 dot-command（.backup、.output、.shell 這類）不允許"
    return None
```

`sqlite3` 的選項是單一連字號的整字，雙連字號的寫法（`--readonly`）跟單一連字號的意思相同，所以規則先把開頭的 `--` 換成 `-` 再比對，`test_sqlite_requires_init_devnull` 放行 `sqlite3 --init /dev/null --readonly --safe -json …`。三個必帶的選項用集合的子集比對（`SQLITE_REQUIRED <= seen`），少任何一個都拒絕；`-init` 的值只接受 `/dev/null`，`-init -readonly -safe` 這種把下一個選項當成值的寫法也被拒絕，因為 `-readonly` 不等於 `/dev/null`。為什麼三個都要帶，在清單寫成 TOML 的那篇概念文章的〈只讀檢查腳本的白名單、輸出、exit code 與結果檔〉講 `sqlite3` 執行 shell 與寫檔途徑的那一段。

位置參數裡，第一個是資料庫檔，之後的每一個是要執行的 SQL。規則把每段 SQL 逐行看，去掉行首空白之後以 `.` 開頭的行就是 dot-command，一律拒絕，不只靠 `-safe` 擋。在 SQL 參數之外塞 dot-command 的 `-cmd` 選項不在表上；`-A`（操作 SQLite 封存檔）、`-interactive`、`-echo`、`-vfs` 也不在表上，`test_sqlite_requires_init_devnull` 逐一列了它們。程式碼註解裡的「OL10 的 3.46.1」指 Oracle Linux 10 上的 sqlite 3.46.1。

### openssl 與 sshd 的固定寫法

```python
OPENSSL_X509_OPTS = {"-noout", "-in", "-checkend", "-enddate", "-startdate", "-dates", "-subject", "-issuer", "-serial", "-fingerprint", "-sha256", "-ext"}


def _rule_openssl(argv: list[str]) -> str | None:
    if len(argv) < 2 or argv[1] != "x509" or "-noout" not in argv:
        return "openssl 只允許 x509 -noout"
    for a in argv[2:]:
        if a.startswith("-") and a not in OPENSSL_X509_OPTS:
            return f"openssl x509 不允許 {a}"
    return None
```

`openssl` 只允許 `x509` 子命令，而且一定要帶 `-noout`（不印出憑證本身的編碼內容）；其餘以 `-` 開頭的參數要在 `OPENSSL_X509_OPTS` 裡。不以 `-` 開頭的參數是選項的值（`-in` 的憑證路徑、`-checkend` 的秒數），放行。寫出檔案的 `-out` 不在表上，`test_rejected` 列了 `openssl x509 -noout -in a -out b`。

```python
def _rule_sshd(argv: list[str]) -> str | None:
    # -E 與 -f 會寫檔或換設定，所以只接受單獨的 -T。
    return None if argv[1:] == ["-T"] else "sshd 只允許單獨的 -T（印出生效中的設定）"
```

`sshd` 的規則把參數串列跟 `["-T"]` 整串比對：檢查要的只有「印出生效中的設定」這一種用法，整串比對比列出允許的選項更窄，`-T -E <檔案>` 與 `-E <檔案> -T` 兩種順序都被拒絕。

### needs-restarting 與 dnf 的子命令

```python
NEEDS_RESTARTING_OPTIONS = _spec(flags="-r -s --reboothint --services")


def _rule_needs_restarting(argv: list[str]) -> str | None:
    positionals, _, err = _parse_options(argv[1:], NEEDS_RESTARTING_OPTIONS)
    if err or positionals:
        return "needs-restarting 只允許 -r、-s、--reboothint、--services"
    return None


DNF_OPTIONS = _spec(flags="-q --quiet -C --cacheonly")
NO_OPTIONS = _spec()


def _rule_dnf(argv: list[str]) -> str | None:
    # -x、--setopt、-c、--installroot 這類吃值的選項不在允許清單；只允許子命令前的 -q、-C。
    rest, _, err = _parse_options(argv[1:], DNF_OPTIONS, stop_at_first=True)
    if err:
        return f"dnf {err}"
    if rest[:1] == ["needs-restarting"]:
        return _rule_needs_restarting(rest)
    if rest[:2] in (["history", "list"], ["history", "info"]):
        _, _, err = _parse_options(rest[2:], NO_OPTIONS)
        return f"dnf {err}" if err else None
    return "dnf 只允許 needs-restarting 與 history list/info"
```

`dnf` 的規則分兩段切：子命令之前用 `DNF_OPTIONS` 切，切到第一個位置參數就停（`stop_at_first`）；剩下的參數以子命令開頭，交給子命令的規則。`needs-restarting` 這個子命令跟單獨呼叫的 `needs-restarting` 共用同一個規則函式，`rest` 的第一個元素正好是 `needs-restarting`，跟單獨呼叫時的參數串列形狀相同。`history list` 與 `history info` 之後用沒有任何允許選項的 `NO_OPTIONS` 切：位置參數（`dnf history info 12` 的交易編號）放行，任何選項都拒絕，`test_rejected` 的 `dnf history list -y` 就是這一種。`dnf -x history -x list install foo` 在子命令之前那一段就被拒絕，`-x` 不在 `DNF_OPTIONS` 裡。

### rpm 的查詢模式

```python
# --eval、-E、-D/--define 展開巨集，%(...) 會經 shell 執行；--pipe 直接執行指令；
# --macros、--rcfile、--dbpath、--root、-p 換設定或資料來源。都不在允許清單。
RPM_OPTIONS = _spec(
    flags=(
        "-q -a -f -i -l -c -d -s -R --query --all --file --info --list --configfiles --docfiles "
        "--state --requires --provides --changelog --last --whatprovides --whatrequires"
    ),
    values="--qf --queryformat",
)


def _rule_rpm(argv: list[str]) -> str | None:
    # 第一個選項必須是查詢模式（-q、-qa、-qi 這類或 --query），不讓 -i、-U 這類模式排在前面。
    if len(argv) < 2 or not (argv[1].startswith("-q") or argv[1] == "--query"):
        return "rpm 只允許查詢（第一個選項要是 -q 開頭或 --query）"
    _, seen, err = _parse_options(argv[1:], RPM_OPTIONS)
    if err:
        return f"rpm {err}"
    if not ({"-q", "--query"} & seen):
        return "rpm 只允許查詢（要帶 -q）"
    return None
```

`rpm` 的 `-i` 在查詢模式裡是「印出套件資訊」，排在最前面時是「安裝套件」，同一個字母的意思由模式決定。規則因此先要求第一個參數是查詢模式（`-q` 開頭或 `--query`），再照選項表切分：`RPM_OPTIONS` 裡的 `-i`、`-f` 只在查詢模式之後才出現得了，`test_rpm_first_option_is_query` 拒絕的 `rpm -i tree.rpm -q`、`rpm -iq`、`rpm -U x.rpm -q` 都在查第一個參數時被拒絕。切分之後再確認出現過的選項裡有 `-q` 或 `--query`：以現在的寫法，通過第一個參數檢查的輸入，切分之後一定帶著 `-q` 或 `--query`，這一道擋不下任何多出來的輸入（讀碼）；它是冗餘的防護，日後有人放寬第一個參數的比對時，查詢模式的要求不會跟著消失。`-qp`（查詢一個 `.rpm` 檔而不是已安裝的套件）的 `-p` 不在表上，`test_rejected` 列了 `rpm -qp /tmp/a.rpm`。

### ausearch 的篩選選項與時間

```python
# ausearch 是單破折號多字母選項，整字比對。--checkpoint、-if/--input 這類寫檔或換輸入來源的選項不在允許清單。
AUSEARCH_FLAGS = frozenset("-i --interpret -r --raw --just-one".split())
AUSEARCH_VALUES = frozenset(
    "-m --message -k --key -c --comm -p --pid -ui --uid -x --executable -sc --syscall -sv --success --format".split()
)
AUSEARCH_TIME = frozenset("-ts --start -te --end".split())
AUSEARCH_CLOCK = re.compile(r"^\d{1,2}:\d{2}(:\d{2})?$")


def _rule_ausearch(argv: list[str]) -> str | None:
    args = argv[1:]
    i = 0
    while i < len(args):
        tok = args[i]
        i += 1
        name, eq, _ = tok.partition("=") if tok.startswith("--") else (tok, "", "")
        if name in AUSEARCH_FLAGS and not eq:
            continue
        if name in AUSEARCH_VALUES or name in AUSEARCH_TIME:
            if not eq:
                if i >= len(args):
                    return f"ausearch 的選項 {tok} 缺少值"
                i += 1
                # -ts 後面是日期時，再下一個字可能是時間（-ts 10/26/2026 10:30）
                if name in AUSEARCH_TIME and i < len(args) and AUSEARCH_CLOCK.match(args[i]):
                    i += 1
            continue
        return f"ausearch 的選項 {tok} 不在允許清單"
    return None
```

`ausearch` 的短選項有多個字母（`-ui`、`-sc`），不能照 `getopt_long` 拆字，所以整字比對；只有雙連字號的長選項接受 `=值`，單一連字號的 `-i=1` 整串對不上表而被拒絕。`-ts`、`-te` 的值可以是一個詞（`today`、`recent`），也可以是日期加時間兩個參數，所以吃掉值之後，下一個參數長得像時刻（`10:30` 或 `10:30:00`）時再吃一個。`test_ausearch_allow_list` 放行 `ausearch -ts 10/26/2026 10:30:00 -te 11:00`，拒絕 `-m` 沒有值、`--checkpoint`、`--input` 與 `-if`。

### 不另外比對選項的工具與規則表

```python
def _allow(argv: list[str]) -> str | None:
    return None


READONLY_RULES: dict[str, Callable[[list[str]], str | None]] = {
    "ss": _rule_ss,
    "systemctl": _rule_systemctl,
    "journalctl": _rule_journalctl,
    "firewall-cmd": _rule_firewall_cmd,
    "find": _rule_find,
    "sqlite3": _rule_sqlite3,
    "openssl": _rule_openssl,
    "sshd": _rule_sshd,
    "needs-restarting": _rule_needs_restarting,
    "dnf": _rule_dnf,
    "rpm": _rule_rpm,
    "ausearch": _rule_ausearch,
    "grep": _allow,
    "wc": _allow,
    "stat": _allow,
    "du": _allow,
    "df": _allow,
    "test": _allow,
    "id": _allow,
    "uname": _allow,
    "getenforce": _allow,
    "sestatus": _allow,
    "getsebool": _allow,
}
```

`READONLY_RULES` 是白名單本身：鍵是執行檔的檔名，值是那支工具的規則函式；不在這張表上的工具在 `readonly_violation` 裡被拒絕。其餘對到 `_allow` 的工具，任何參數都放行，因為它們沒有寫檔或執行其他程式的選項，判斷的依據在清單寫成 TOML 的那篇概念文章的〈只讀檢查腳本的白名單、輸出、exit code 與結果檔〉白名單三層比對（執行檔的路徑、工具、工具的選項）裡的「工具」那一層。白名單要加一支工具時，在這張表加一列；那支工具有會寫檔或執行其他程式的選項時，同時寫一個規則函式，對到 `_allow` 等於宣告它的每一個選項都只讀。

## 指令的只讀判定：readonly_violation 與 Checker 自己組的指令

`readonly_violation` 把一條指令字串判定成放行或拒絕：先用 `shlex` 切詞，再依序做白名單的三層比對。執行檔的路徑那一層在這個函式裡比對；工具那一層依檔名查 `READONLY_RULES`，查不到就拒絕；工具的選項那一層交給查到的規則函式，寫在〈各工具的選項規則：systemctl、journalctl、firewall-cmd、ss、find、sqlite3、openssl、sshd、needs-restarting、dnf、rpm、ausearch〉。程式碼裡排在 `readonly_violation` 之前的，是腳本自己用清單的值組出來的指令（`LISTEN_COMMAND`、`timer_command`、`journal_command`），載入清單時與執行時用的是同一批函式，比對過的字串就是執行的字串。三層比對的理由，以及裸工具名依 `PATH` 找檔案而要經由 sudo 或 systemd 執行的條件，在 [主機維護清單寫成 TOML：JSON、YAML、TOML 的取捨、TOML 1.0 與 1.1 的版本差異、清單的欄位設計與只讀檢查腳本](/operations/09-host-lifecycle/host-manifest-in-toml/)〈只讀檢查腳本的白名單、輸出、exit code 與結果檔〉。

```python
# Checker 實際會拼出來的指令；validate 載入時用同一批函式先比對白名單，兩邊不會不一致。
LISTEN_COMMAND = "ss -H -l -n -t -u"
UPDATE_TIMER_VERBS = (("is-enabled", "enabled"), ("is-active", "active"))
# needs-restarting -r 判定要重開機時印的句子（dnf 4 與 dnf 5 相同，Runner 以 LC_ALL=C 執行）。
# exit 1 也是 dnf 自己出錯時的 exit（ProtectSystem=strict 下寫不了 /var/log/dnf.log），只看 exit 分不開。
REBOOT_REQUIRED_TEXT = "Reboot is required"


def timer_command(verb: str, timer: str) -> str:
    return f"systemctl {verb} {shlex.quote(timer)}"


def journal_command(unit: str) -> str:
    return f"journalctl -u {shlex.quote(unit)} -n 1 -q --no-pager -o short-iso"


TRUSTED_BIN_DIRS = frozenset({"/usr/bin", "/usr/sbin", "/bin", "/sbin"})


def readonly_violation(command: str) -> str | None:
    """command 不在只讀白名單時回傳理由。"""
    try:
        argv = shlex.split(command)
    except ValueError as e:
        return f"指令切詞失敗：{e}"
    if not argv:
        return "指令是空的"
    if "/" in argv[0] and os.path.dirname(argv[0]) not in TRUSTED_BIN_DIRS:
        return f"{argv[0]} 的路徑不在 {', '.join(sorted(TRUSTED_BIN_DIRS))} 之下（只接受裸名或系統目錄）"
    name = os.path.basename(argv[0])
    rule = READONLY_RULES.get(name)
    if rule is None:
        return f"{name} 不在只讀白名單（{', '.join(sorted(READONLY_RULES))}）"
    return rule([name] + argv[1:])
```

`timer_command` 與 `journal_command` 把清單裡的 [systemd timer](/linux/dotfile/knowledge-cards/systemd-timer/) 名稱與 unit 名稱嵌進指令。`shlex.quote` 讓名稱裡的空白與引號在切詞之後仍是一個參數，名稱塞不進第二個參數；而名稱本身寫成選項的樣子時，`shlex.quote` 不改它，要靠白名單擋。單元測試 `test_evil_timer_rejected_at_load`（本篇沒有收錄）把清單的 timer 寫成 `--host=evil`，組出來的 `systemctl is-enabled --host=evil` 在載入時被 `systemctl` 的規則拒絕，腳本以 exit 2 結束，假的執行器一條指令都沒有收到。`REBOOT_REQUIRED_TEXT` 給自動更新那一項判斷要不要重開機，它跟 exit code 一起用的理由寫在註解裡，判定的程式在下面〈自動更新的排程、設定與重開機〉。註解寫這一句「dnf 4 與 dnf 5 相同」，原始碼與測試裡沒有 dnf 5 的輸出可以對照：單元測試用的是 dnf 4 格式的輸出，dnf 5 印的句子這次未實跑。

執行檔路徑那一層比對的是字串：`os.path.dirname` 取出的目錄要逐字等於四個系統目錄之一，沒有先正規化路徑。`./grep` 的目錄是 `.`、`/usr/local/bin/grep` 的目錄是 `/usr/local/bin`，都不在表上；`/usr/bin/../../tmp/grep` 的目錄是 `/usr/bin/../../tmp`，同樣不等於 `/usr/bin`，`..` 因此繞不過這一層。規則函式收到的第一個元素換成了檔名，`/usr/bin/grep` 與 `grep` 走同一個規則。`shlex.split` 遇到沒有收尾的引號時丟出 `ValueError`，這一條指令判成拒絕，不讓整支腳本中止。

白名單是擋得住「請 PID 1 這類別的程序代做」這種改動的那一層。systemd 沙箱的檔案系統與網路限制管的是腳本自己的程序，而 `systemctl stop` 經由 D-Bus 請 systemd（PID 1）去停服務，停服務的是不受這些限制的 systemd。在 Ubuntu 24.04（systemd 255）上實跑：`systemd-run --wait --pipe -p ProtectSystem=strict -p IPAddressDeny=any systemctl stop <unit>` 回 rc=0，unit 被停掉，加上 `PrivateNetwork=yes` 也一樣停得掉；只有用 `RestrictAddressFamilies="AF_INET AF_INET6"` 拿掉 AF_UNIX 時，回 rc=1（`Failed to connect to bus: Address family not supported by protocol`）。所以 `systemctl` 的規則只放行查詢的子命令；白名單與沙箱怎麼分工，在清單寫成 TOML 的那篇概念文章的〈只讀檢查腳本的白名單、輸出、exit code 與結果檔〉。

## 清單的載入與驗證：Probe、_Validator、load_manifest 與 validate

這一段把 TOML 讀成 Python 的 dict 之後逐段驗證並正規化：每個欄位查存在、型別與允許值，字串裡的 `{{名稱}}` 換成 `[vars]` 的值，要執行的指令比對白名單；整份清單的錯誤收齊之後一次丟出 `ManifestError`，這時一條指令都還沒有執行。欄位怎麼依檢查腳本與人的需要設計，在 [主機維護清單寫成 TOML：JSON、YAML、TOML 的取捨、TOML 1.0 與 1.1 的版本差異、清單的欄位設計與只讀檢查腳本](/operations/09-host-lifecycle/host-manifest-in-toml/)〈清單欄位的設計：檢查腳本要讀的與人要讀的〉；照這段驗證實際要求的欄位寫成範本，在 [多台主機維護清單的實作紀錄：在容器上安裝 ansible-core 與 Terraform、由 Terraform 產生 inventory、用 Ansible 的範本部署每台的清單、以 sudo 與 systemd-run 執行檢查腳本，以及清理](/operations/09-host-lifecycle/hands-on/multi-host-manifest-walkthrough/)〈變數檔與範本：檢查腳本實際要求的欄位、兼任兩種角色的主機〉。

```python
# ── 清單解析與驗證 ─────────────────────────────────────────


@dataclass
class Probe:
    command: str
    expect_exit: int | None = None
    ok_exit: list[int] = field(default_factory=lambda: [0])
    expect_stdout: str | None = None
    expect_contains: str | None = None
    expect_not_contains: str | None = None
    measure: str | None = None
    warn_above: float | None = None


class _Validator:
    def __init__(self, variables: dict[str, str]):
        self.errors: list[str] = []
        self.vars = variables

    def err(self, where: str, msg: str) -> None:
        self.errors.append(f"{where}: {msg}")

    def subst(self, where: str, value: str) -> str:
        def repl(m: re.Match[str]) -> str:
            name = m.group(1)
            if name not in self.vars:
                self.err(where, f"{{{{{name}}}}} 沒有定義在 [vars]")
                return m.group(0)
            return self.vars[name]

        return VAR_RE.sub(repl, value)

    def get(self, tbl: dict[str, Any], key: str, typ: type | tuple[type, ...], where: str, required: bool = True, enum: tuple[str, ...] | None = None) -> Any:
        if key not in tbl:
            if required:
                self.err(where, f"缺少必填欄位 {key}")
            return None
        v = tbl[key]
        # bool 是 int 的子類別，數字欄位不收 true/false。
        if not isinstance(v, typ) or (isinstance(v, bool) and bool not in (typ if isinstance(typ, tuple) else (typ,))):
            self.err(where, f"{key} 的型別要是 {_typename(typ)}，實際是 {type(v).__name__}")
            return None
        if enum is not None and v not in enum:
            self.err(where, f"{key} 要是 {list(enum)} 之一，實際是 {v!r}")
            return None
        if isinstance(v, str):
            return self.subst(f"{where}.{key}", v)
        return v

    def reject_old_command_name(self, tbl: dict[str, Any], where: str) -> None:
        # command 一律會被執行；只印不執行的欄位叫 manual_command，舊名出現在只印的位置判成格式錯。
        if "command" in tbl:
            self.err(where, "只印不執行的指令改用 manual_command（command 一律會被執行並過白名單）")

    def str_list(self, tbl: dict[str, Any], key: str, where: str, required: bool = True) -> list[str] | None:
        v = self.get(tbl, key, list, where, required)
        if v is None:
            return None
        if not all(isinstance(x, str) for x in v):
            self.err(where, f"{key} 的每一項都要是字串")
            return None
        return [self.subst(f"{where}.{key}", x) for x in v]

    def table_list(self, data: dict[str, Any], key: str, required: bool = True) -> list[dict[str, Any]]:
        v = data.get(key)
        if v is None:
            if required:
                self.err(key, f"缺少 [[{key}]]")
            return []
        if not isinstance(v, list) or not all(isinstance(x, dict) for x in v):
            self.err(key, f"{key} 要是 [[{key}]] 表格陣列")
            return []
        return v

    def probe(self, tbl: dict[str, Any], where: str, allow_measure: bool = False) -> Probe | None:
        command = self.get(tbl, "command", str, where)
        if command is None:
            return None
        reason = readonly_violation(command)
        if reason:
            self.err(where, f"command 不是只讀指令：{reason}（{command}）")
        p = Probe(command=command)
        p.expect_exit = self.get(tbl, "expect_exit", int, where, required=False)
        ok_exit = tbl.get("ok_exit", [0])
        if not isinstance(ok_exit, list) or not all(isinstance(x, int) and not isinstance(x, bool) for x in ok_exit):
            self.err(where, "ok_exit 要是整數陣列")
        else:
            p.ok_exit = ok_exit
        p.expect_stdout = self.get(tbl, "expect_stdout", str, where, required=False)
        p.expect_contains = self.get(tbl, "expect_contains", str, where, required=False)
        p.expect_not_contains = self.get(tbl, "expect_not_contains", str, where, required=False)
        if allow_measure:
            p.measure = self.get(tbl, "measure", str, where, required=False, enum=MEASURE_VALUES)
            p.warn_above = self.get(tbl, "warn_above", (int, float), where, required=p.measure is not None)
        has_expect = any(x is not None for x in (p.expect_exit, p.expect_stdout, p.expect_contains, p.expect_not_contains, p.measure))
        if not has_expect and "ok_exit" not in tbl:
            self.err(where, "探針至少要有一個預期值（expect_exit、ok_exit、expect_stdout、expect_contains、expect_not_contains 或 measure）")
        return p


def _typename(typ: type | tuple[type, ...]) -> str:
    if isinstance(typ, tuple):
        return " 或 ".join(t.__name__ for t in typ)
    return typ.__name__
```

`Probe` 是一個探針：要執行的一條指令，加上怎樣算正常的預期值。`_Validator` 把驗證時共用的動作收在一起，每個方法查到錯誤時記一條、回傳 `None` 或空的結果（`table_list` 回空串列），不丟例外，所以一個欄位錯了之後，其他欄位照樣往下驗。

`get` 的型別比對多了一個布林的判斷：Python 的 `bool` 是 `int` 的子類別，只用 `isinstance(v, int)` 的話，`port = true` 會被當成整數 1 收下。`get` 先比對型別與允許值，再換掉字串裡的 `{{名稱}}`：有允許值的欄位（`exposure`、`where`、`protocol` 這類）寫成 `{{名稱}}` 時，比對的是 `{{名稱}}` 這串字本身，判成格式錯，所以這些欄位不能用 `[vars]` 填。之後比對白名單的是換過的字串，所以命令列 `--set` 傳進來的值跟清單裡寫死的值走同一道白名單。`[vars]` 沒有的名稱記一條錯誤，原文的 `{{名稱}}` 留在字串裡。

`reject_old_command_name` 管的是欄位名稱的意思：清單裡的 `command` 一律會被執行，只印給人看的指令寫在 `manual_command`。只印的位置（`[[log]]`、暫停與恢復的步驟、主機外的確認）出現 `command` 時判成格式錯，讀清單的人看到 `command` 就知道那一條會被執行，單元測試 `test_log_old_name_rejected`、`test_resume_old_name_rejected` 與 `test_external_verify_old_name_rejected`（本篇沒有收錄）各測一個位置。

`probe` 要求探針至少寫出一個預期值，或明寫 `ok_exit`：`ok_exit` 的預設 `[0]` 不算宣告，清單的讀者要看得到這一項怎樣算正常。`measure` 與 `warn_above` 只在 `allow_measure` 為真時讀，也就是 log 的計數門檻（`[[log.alert]]`）；寫了 `measure` 就一定要有 `warn_above`，量到的值才有門檻可比。

```python
def load_manifest(path: str, overrides: dict[str, str] | None = None) -> dict[str, Any]:
    """讀取並驗證清單，回傳正規化後的結構；格式錯時丟 ManifestError。"""
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except OSError as e:
        raise ManifestError([f"讀不到清單 {path}：{e}"]) from e
    except tomllib.TOMLDecodeError as e:
        raise ManifestError([f"{path} 不是合法的 TOML 1.0：{e}"]) from e
    return validate(data, overrides or {})


def validate(data: dict[str, Any], overrides: dict[str, str]) -> dict[str, Any]:
    raw_vars = data.get("vars", {})
    errors: list[str] = []
    if not isinstance(raw_vars, dict) or not all(isinstance(v, str) for v in raw_vars.values()):
        errors.append("vars: [vars] 的每個值都要是字串")
        raw_vars = {}
    variables = dict(raw_vars)
    for k in overrides:
        if k not in variables:
            errors.append(f"--set {k}: [vars] 沒有這個名稱")
    variables.update(overrides)
    v = _Validator(variables)
    v.errors.extend(errors)
    out: dict[str, Any] = {"vars": variables}

    host = data.get("host")
    if not isinstance(host, dict):
        v.err("host", "缺少 [host]")
        host = {}
    out["host"] = {k: v.get(host, k, str, "host") for k in ("name", "provider", "region", "role")}

    la = data.get("listen_audit", {"protocols": ["tcp"], "allow": []})
    if not isinstance(la, dict):
        v.err("listen_audit", "要是表格")
        la = {}
    protocols = v.str_list(la, "protocols", "listen_audit") or []
    for p in protocols:
        if p not in PROTOCOL_VALUES:
            v.err("listen_audit", f"protocols 只能是 {list(PROTOCOL_VALUES)}，實際有 {p!r}")
    allow_out = []
    allow = la.get("allow", [])
    if not isinstance(allow, list):
        v.err("listen_audit", "allow 要是陣列")
        allow = []
    for i, a in enumerate(allow):
        w = f"listen_audit.allow[{i}]"
        if not isinstance(a, dict):
            v.err(w, "要是 { port = ..., protocol = ..., reason = ... }")
            continue
        allow_out.append({"port": v.get(a, "port", int, w), "protocol": v.get(a, "protocol", str, w, enum=PROTOCOL_VALUES), "reason": v.get(a, "reason", str, w)})
    out["listen_audit"] = {"protocols": protocols, "allow": allow_out}

    eps = []
    for i, ep in enumerate(v.table_list(data, "entrypoint")):
        w = f"entrypoint[{i}]"
        name = v.get(ep, "name", str, w)
        w = f"entrypoint[{name or i}]"
        e = {
            "name": name,
            "port": v.get(ep, "port", int, w),
            "protocol": v.get(ep, "protocol", str, w, enum=PROTOCOL_VALUES),
            "exposure": v.get(ep, "exposure", str, w, enum=EXPOSURE_VALUES),
            "where": v.get(ep, "where", str, w, enum=WHERE_VALUES),
            "enforced_by": v.str_list(ep, "enforced_by", w) or [],
            "verify": [],
        }
        verifies = ep.get("verify", [])
        if not isinstance(verifies, list) or not all(isinstance(x, dict) for x in verifies):
            v.err(w, "verify 要是 [[entrypoint.verify]] 表格陣列")
            verifies = []
        layers_seen = set()
        for j, vf in enumerate(verifies):
            vw = f"{w}.verify[{j}]"
            layer = v.get(vf, "layer", str, vw)
            where = v.get(vf, "where", str, vw, enum=WHERE_VALUES)
            layers_seen.add(layer)
            item: dict[str, Any] = {"layer": layer, "where": where}
            if where == "host":
                item["probe"] = v.probe(vf, vw)
            elif where is not None:
                item["console_path"] = v.get(vf, "console_path", str, vw, required=False)
                v.reject_old_command_name(vf, vw)
                item["manual_command"] = v.get(vf, "manual_command", str, vw, required=False)
                if item["console_path"] is None and item["manual_command"] is None:
                    v.err(vw, "主機外的確認要有 console_path 或 manual_command")
                item["expect"] = v.get(vf, "expect", str, vw)
            e["verify"].append(item)
        for layer in e["enforced_by"]:
            if layer not in layers_seen:
                v.err(w, f"enforced_by 的 {layer!r} 沒有對應的 [[entrypoint.verify]]（layer = {layer!r}）")
        for layer in layers_seen - set(e["enforced_by"]) - {None}:
            v.err(w, f"[[entrypoint.verify]] 的 layer {layer!r} 不在 enforced_by 裡")
        eps.append(e)
    out["entrypoint"] = eps

    logs = []
    for i, lg in enumerate(v.table_list(data, "log")):
        name = v.get(lg, "name", str, f"log[{i}]")
        w = f"log[{name or i}]"
        v.reject_old_command_name(lg, w)
        source = v.get(lg, "source", str, w)
        if source is not None and not re.match(r"^(file|journal):.+", source):
            v.err(w, f"source 要寫成 file:<路徑> 或 journal:<unit>，實際是 {source!r}")
        item = {
            "name": name,
            "source": source,
            "look_for": v.get(lg, "look_for", str, w),
            "interval_days": v.get(lg, "interval_days", int, w),
            "manual_command": v.get(lg, "manual_command", str, w),
            "alerts": [],
        }
        alerts = lg.get("alert", [])
        if not isinstance(alerts, list) or not all(isinstance(x, dict) for x in alerts):
            v.err(w, "alert 要是 [[log.alert]] 表格陣列")
            alerts = []
        for j, al in enumerate(alerts):
            aw = f"{w}.alert[{j}]"
            aname = v.get(al, "name", str, aw)
            item["alerts"].append({"name": aname, "probe": v.probe(al, f"{w}.alert[{aname or j}]", allow_measure=True)})
        logs.append(item)
    out["log"] = logs

    accs = []
    for i, ac in enumerate(v.table_list(data, "accumulation")):
        name = v.get(ac, "name", str, f"accumulation[{i}]")
        w = f"accumulation[{name or i}]"
        paths = ac.get("path")
        if isinstance(paths, str):
            paths = [paths]
            ac = dict(ac, path=paths)
        item = {
            "name": name,
            "paths": v.str_list(ac, "path", w) or [],
            "missing_ok": v.get(ac, "missing_ok", bool, w, required=False) or False,
            "limit_bytes": v.get(ac, "limit_bytes", int, w, required=False),
            "retention_days": v.get(ac, "retention_days", int, w, required=False),
            "purge_command": v.get(ac, "purge_command", str, w),
            "oldest_command": None,
        }
        if item["limit_bytes"] is None and item["retention_days"] is None:
            v.err(w, "limit_bytes 與 retention_days 至少要有一個")
        oc = v.get(ac, "oldest_command", str, w, required=False)
        if oc is not None:
            if item["retention_days"] is None:
                v.err(w, "有 oldest_command 時要有 retention_days")
            reason = readonly_violation(oc)
            if reason:
                v.err(w, f"oldest_command 不是只讀指令：{reason}（{oc}）")
            item["oldest_command"] = oc
        accs.append(item)
    out["accumulation"] = accs

    fss = []
    for i, fs in enumerate(v.table_list(data, "filesystem", required=False)):
        name = v.get(fs, "name", str, f"filesystem[{i}]")
        w = f"filesystem[{name or i}]"
        fss.append({"name": name, "mount": v.get(fs, "mount", str, w), "min_free_bytes": v.get(fs, "min_free_bytes", int, w)})
    out["filesystem"] = fss

    up = data.get("updates")
    if not isinstance(up, dict):
        v.err("updates", "缺少 [updates]")
        up = {}
    expect = up.get("expect", {})
    if not isinstance(expect, dict) or not all(isinstance(x, str) for x in expect.values()):
        v.err("updates", "expect 要是值為字串的 inline table")
        expect = {}
    reboot = v.get(up, "reboot_check", str, "updates", required=False)
    if reboot is not None:
        reason = readonly_violation(reboot)
        if reason:
            v.err("updates", f"reboot_check 不是只讀指令：{reason}")
    out["updates"] = {
        "mode": v.get(up, "mode", str, "updates"),
        "timer": v.get(up, "timer", str, "updates"),
        "config_files": v.str_list(up, "config_files", "updates", required=False) or [],
        "expect": expect,
        "reboot_check": reboot,
    }

    for phase in ("suspend", "resume"):
        steps = []
        for i, st in enumerate(v.table_list(data, phase)):
            w = f"{phase}[{i}]"
            item = {
                "step": v.get(st, "step", int, w),
                "resource": v.get(st, "resource", str, w),
                "billed_when_stopped": v.get(st, "billed_when_stopped", str, w, enum=BILLED_VALUES),
                "billed_when_stopped_beyond_free": v.get(st, "billed_when_stopped_beyond_free", str, w, enum=BILLED_VALUES),
                "billing_basis": v.get(st, "billing_basis", str, w),
                "where": v.get(st, "where", str, w, enum=WHERE_VALUES),
                "manual_command": v.get(st, "manual_command", str, w, required=False),
                "console_path": v.get(st, "console_path", str, w, required=False),
                "verify": None,
            }
            v.reject_old_command_name(st, w)
            if item["manual_command"] is None and item["console_path"] is None:
                v.err(w, "manual_command 或 console_path 至少要有一個")
            vf = st.get("verify")
            if item["where"] == "host":
                if not isinstance(vf, dict):
                    v.err(w, "where = \"host\" 的 verify 要是只讀探針的 inline table")
                else:
                    item["verify"] = v.probe(vf, f"{w}.verify")
            elif item["where"] is not None:
                if not isinstance(vf, str):
                    v.err(w, "主機外的 verify 要是一句要看到的結果（字串）")
                else:
                    item["verify"] = v.subst(f"{w}.verify", vf)
            steps.append(item)
        nums = [s["step"] for s in steps if s["step"] is not None]
        if len(nums) != len(set(nums)):
            v.err(phase, "step 有重複的編號")
        out[phase] = sorted(steps, key=lambda s: s["step"] or 0)

    _check_builtin_commands(v, out)
    if v.errors:
        raise ManifestError(v.errors)
    return out


def _check_builtin_commands(v: "_Validator", out: dict[str, Any]) -> None:
    # Checker 自己拼的指令也含清單的值（timer 名稱、journal unit），載入時一併比對白名單，不合就判成格式錯。
    cmds = [("listen_audit", LISTEN_COMMAND)]
    timer = out["updates"]["timer"]
    if isinstance(timer, str):
        cmds += [("updates.timer", timer_command(verb, timer)) for verb, _ in UPDATE_TIMER_VERBS]
    for lg in out["log"]:
        source = lg["source"]
        if isinstance(source, str) and source.startswith("journal:"):
            cmds.append((f"log[{lg['name']}].source", journal_command(source.partition(":")[2])))
    for where, cmd in cmds:
        reason = readonly_violation(cmd)
        if reason:
            v.err(where, f"自動執行的指令不是只讀指令：{reason}（{cmd}）")
```

`load_manifest` 把兩種讀不進來的情形（檔案打不開、內容不是合法的 TOML）都轉成 `ManifestError`，跟欄位錯走同一個 exit 2。錯誤訊息寫「不是合法的 TOML 1.0」，因為示範清單描述的那台 Oracle Linux 10 主機上，Python 3.12 的 `tomllib` 只認 TOML 1.0：在開發機上用較新的 Python 驗證過的清單，到了只有 3.12 的主機上，1.1 才有的語法會在這裡失敗；兩個版本的差異與解析器的版本在清單寫成 TOML 的那篇概念文章的〈TOML 1.0 與 1.1 的差異與解析器的版本〉。

`validate` 先處理 `[vars]` 與 `--set`：`--set` 給的名稱要已經寫在 `[vars]` 裡，打錯字的名稱算格式錯（`test_unknown_set_name_is_format_error`），不會被當成一個新的變數收下、而清單裡想覆寫的那個值照舊不變。同一份清單套到多台主機時，每台不同的值在執行時用 `--set` 覆寫、還是在部署時就寫進每台的清單，以及依角色過濾項目的取捨，在 [多台主機的維護清單：值的分層與合併的位置、用 Ansible 的 inventory 與範本產生每台的清單、由 Terraform 的輸出產生 inventory、跨主機執行的 exit code，以及單台清單的適用範圍](/operations/09-host-lifecycle/multi-host-manifest/)。之後依清單的段落逐段驗：

- **必填與選填的段落**：`[host]`、`[updates]`、`[[entrypoint]]`、`[[log]]`、`[[accumulation]]`、`[[suspend]]`、`[[resume]]` 缺了都算格式錯；`[[filesystem]]`（`table_list` 的 `required=False`）、`[vars]`（預設是空表格）與 `[listen_audit]`（預設寫在 `[listen_audit]` 那一項）可以不寫。所以一份只想檢查入口的清單，其他段落也要寫出來；這是這支腳本的規格，換成自己的腳本時依需要放寬。
- **`[listen_audit]`**：整段沒寫時，預設檢查 TCP、沒有額外允許的連接埠，沒寫這一段的清單照樣檢查有沒有多開的 TCP 連接埠；寫了這一段就要寫出 `protocols`，寫成空陣列等於關掉這項檢查。
- **錯誤的位置**：入口、log、會累積的資料有名稱時，錯誤的位置寫成 `entrypoint[https]` 這種帶名稱的寫法，名稱缺了才退回索引，改清單的人照名稱找得到那一段。
- **入口的 `enforced_by` 與 `[[entrypoint.verify]]`**：`enforced_by` 的每一層至少要有一筆 `[[entrypoint.verify]]`，每一筆 `verify` 的 `layer` 都要在 `enforced_by` 裡；比對用的是集合，同一層寫兩筆 `verify` 是允許的。宣告由某一層擋、卻沒寫那一層怎麼確認，或寫了確認方式、卻沒宣告由那一層擋，兩種都是格式錯（`test_enforced_layer_without_verify` 測宣告了卻沒有確認的那一種）。理由是清單宣告的防護層，每一層都要有一個確認的動作，欄位這樣設計的推導在清單寫成 TOML 的那篇概念文章的〈清單欄位的設計：檢查腳本要讀的與人要讀的〉。
- **會累積的資料**：`path` 可以寫一個字串或一個陣列，先統一成陣列；`limit_bytes` 與 `retention_days` 至少要有一個，沒有門檻的累積項目只能印出大小、判定不了 `WARN`；`oldest_command` 用來從資料庫查最舊一筆的時間，它跟保留天數一起才有意義，也要過白名單。
- **暫停與恢復的步驟**：`verify` 的型別依 `where` 而定，在主機上確認的是一個只讀探針，寫成寫在同一行的表格（inline table），在主機外確認的是一句人要看到的結果；步驟編號重複時判成格式錯，之後依編號排序，清單裡的寫出順序不影響執行順序。

最後 `_check_builtin_commands` 把腳本自己會組的指令（接聽連接埠的查詢、timer 的兩個查詢、journal 的查詢；journal 是 [journald（systemd-journald）](/linux/dotfile/knowledge-cards/journald/) 收下的紀錄）用清單的值組出來比對白名單，載入時就擋下 `--host=evil` 這種 timer 名稱。全部驗完才看 `v.errors`，有任何一條就丟出 `ManifestError`。

## 執行指令的 Runner 與時鐘

腳本執行外部程式都經過 `Runner.run`：執行之前再比對一次白名單，以固定的環境變數與逾時執行，找不到指令與逾時都轉成一個結果、不丟例外。單元測試把它換成假的執行器，記錄每一次被呼叫的指令並回傳預先寫好的結果，所以測試不碰主機的狀態；取現在時間的 `now_utc` 也可以替換，讓跟時間有關的判定在測試裡有固定的答案。

```python
# ── 執行環境（測試時替換）─────────────────────────────────


@dataclass
class Result:
    exit: int
    stdout: str
    stderr: str


class Runner:
    """執行只讀指令。測試以假的 Runner 替換，記錄被呼叫的指令。"""

    def run(self, command: str) -> Result:
        # 執行前再比對一次白名單：validate 之後到執行之間沒有別的路徑能塞進指令，這是第二道。
        reason = readonly_violation(command)
        if reason:
            raise RuntimeError(f"拒絕執行非只讀指令：{reason}")
        argv = shlex.split(command)
        env = dict(os.environ, LC_ALL="C", LANG="C", SYSTEMD_PAGER="", PAGER="cat")
        try:
            p = subprocess.run(argv, capture_output=True, text=True, timeout=COMMAND_TIMEOUT_S, env=env, stdin=subprocess.DEVNULL)
        except FileNotFoundError:
            return Result(127, "", f"找不到指令 {argv[0]}")
        except subprocess.TimeoutExpired:
            return Result(124, "", f"超過 {COMMAND_TIMEOUT_S} 秒沒有結束")
        return Result(p.returncode, p.stdout, p.stderr)


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)
```

執行前那一次比對不通過時，`Runner` 丟出 `RuntimeError`，命令列把它當成格式錯以 exit 2 結束（單元測試 `test_runner_refuses_non_readonly` 與 `test_runtime_error_becomes_exit_2`，本篇沒有收錄）。正常情形下載入清單時已經擋下，這一道防的是之後有人加了一條不經過 `validate` 就執行指令的程式路徑。

`subprocess.run` 收的是切好的參數串列，不帶 `shell=True`，指令不經過 shell。`shlex.split` 只切詞，不做 shell 會做的展開：`*` 這類 glob、`~`、`$VAR` 都原樣傳給工具。清單寫 `du -s /var/log/x/*` 時，`du` 收到的是字面的 `/var/log/x/*`（實跑：`du` 以 exit 1 結束，錯誤是 `No such file`）；要量多個檔案的大小，寫在 `[[accumulation]]` 的 `path`，那裡的 glob 由 `expand_path` 展開。環境變數從呼叫者的環境複製一份再蓋掉四個：`LC_ALL=C` 與 `LANG=C` 讓工具印英文，`REBOOT_REQUIRED_TEXT` 與 `enabled`、`active` 這類比對字串才對得上；`SYSTEMD_PAGER` 設成空字串、`PAGER=cat`，`systemctl` 與 `journalctl` 就不會開分頁程式等人按鍵；`stdin` 接 `/dev/null`，要讀輸入的工具立刻讀到結尾。`PATH` 沿用呼叫者的：裸工具名依 `PATH` 找檔案，`PATH` 前面的目錄放了一個同名的檔案時，執行的是那一個、不是系統目錄裡的那一支，白名單的執行檔路徑那一層只看指令字串，擋不住這一種。所以腳本要經由 sudo（它的 `secure_path` 會重設 `PATH`）或 systemd 的 unit 執行：systemd 啟動 unit 的程序時不繼承下指令那個 shell 的環境變數，`PATH` 用 systemd 自己的預設值（systemd.exec(5) 的環境變數一節；本篇未實跑），條件寫在 [主機維護清單寫成 TOML：JSON、YAML、TOML 的取捨、TOML 1.0 與 1.1 的版本差異、清單的欄位設計與只讀檢查腳本](/operations/09-host-lifecycle/host-manifest-in-toml/)〈只讀檢查腳本的白名單、輸出、exit code 與結果檔〉白名單三層比對裡的「執行檔的路徑」那一層。

找不到指令時回 127、逾時回 124，跟 shell 與 GNU `timeout` 用的 exit code 相同，錯誤訊息放在 `stderr`。工具自己也可能以 127 或 124 結束，所以 `Checker` 的 `run_probe` 同時看 exit code 與 `stderr` 是否以 `找不到指令` 或 `超過` 開頭，分辨這是 `Runner` 造出來的結果、還是工具自己的 exit code。

## Checker 的各項檢查

`Checker` 依清單逐項執行檢查，每一項產生一行報告：狀態（`PASS`、`WARN`、`MANUAL`）、項目名稱、理由，有量到數字的項目另外帶著那個數字給結果檔用。維護時跑入口、log、會累積的資料、檔案系統與自動更新五類，暫停與恢復時只跑那個階段的步驟。各類檢查要量什麼、門檻怎麼定，在 [長期上線主機的維護項目：會累積的資料、定期讀的 log、對外入口的盤點、安全更新、會到期的設定與檢查間隔的推算](/operations/09-host-lifecycle/long-running-host-maintenance/)；輸出與 exit code 的讀法在 [主機維護清單寫成 TOML：JSON、YAML、TOML 的取捨、TOML 1.0 與 1.1 的版本差異、清單的欄位設計與只讀檢查腳本](/operations/09-host-lifecycle/host-manifest-in-toml/)〈只讀檢查腳本的白名單、輸出、exit code 與結果檔〉。

### 報告的一行與探針的判定

```python
# ── 檢查 ───────────────────────────────────────────────────


@dataclass
class Line:
    status: str  # PASS / WARN / MANUAL
    item: str
    reason: str
    value: float | None = None  # 量到的數字（探針值、累積的 bytes、可用 bytes）；結果檔拿它算與前一次的差
```

`Line` 的 `item` 是結果檔比對前後兩次的鍵（例如 `entrypoint/https:443/tcp`、`accumulation/journald`），由清單的名稱與欄位組出來；清單裡改了一個名稱，下一次的差異就印成舊名稱 `GONE`、新名稱 `NEW`。

```python
class Checker:
    def __init__(self, manifest: dict[str, Any], runner: Runner | None = None, clock: Callable[[], dt.datetime] = now_utc):
        self.m = manifest
        self.runner = runner or Runner()
        self.clock = clock
        self.lines: list[Line] = []

    def emit(self, status: str, item: str, reason: str, value: float | None = None) -> None:
        self.lines.append(Line(status, item, reason, value))

    # 探針：回傳 (ok, 理由, 量到的值)
    def run_probe(self, p: Probe) -> tuple[bool, str, float | None]:
        r = self.runner.run(p.command)
        out = r.stdout.strip()
        if r.exit in (124, 127) and r.stderr.startswith(("找不到指令", "超過")):
            return False, r.stderr, None
        if p.expect_exit is not None:
            if r.exit != p.expect_exit:
                return False, f"exit {r.exit}（預期 {p.expect_exit}）{_brief(r.stderr or out)}", None
        elif r.exit not in p.ok_exit:
            return False, f"exit {r.exit}（可接受 {p.ok_exit}）{_brief(r.stderr or out)}", None
        if p.expect_stdout is not None and out != p.expect_stdout.strip():
            return False, f"輸出 {_brief(out) or '（空）'}（預期 {p.expect_stdout!r}）", None
        if p.expect_contains is not None and p.expect_contains not in r.stdout:
            return False, f"輸出沒有 {p.expect_contains!r}：{_brief(out)}", None
        if p.expect_not_contains is not None and p.expect_not_contains in r.stdout:
            return False, f"輸出含 {p.expect_not_contains!r}：{_brief(out)}", None
        if p.measure is None:
            return True, _brief(out) or f"輸出為空，exit {r.exit}", None
        try:
            value = self.measure(p.measure, r.stdout)
        except ValueError as e:
            return False, str(e), None
        unit = "天" if p.measure == "age_days" else ""
        shown = f"{value:.1f}{unit}" if p.measure == "age_days" else f"{value:g}"
        if p.warn_above is not None and value > p.warn_above:
            return False, f"量到 {shown}，超過門檻 {p.warn_above:g}{unit}", value
        return True, f"量到 {shown}（門檻 {p.warn_above:g}{unit}）", value

    def measure(self, kind: str, stdout: str) -> float:
        if kind == "lines":
            return float(sum(1 for ln in stdout.splitlines() if ln.strip()))
        text = stdout.strip()
        if "=" in text:
            text = text.rsplit("=", 1)[1].strip()
        if kind == "value":
            try:
                return float(text)
            except ValueError:
                raise ValueError(f"輸出不是數字：{_brief(stdout)}") from None
        if text in ("", "n/a"):
            # systemctl show 的時間屬性沒有值時印空值或 n/a（timer 從未觸發就是這樣）。
            raise ValueError(f"沒有時間值（{_brief(stdout) or '空的輸出'}；timer 從未觸發過時就是這樣）")
        ts = parse_time(text)
        if ts is None:
            raise ValueError(f"輸出不是時間值：{_brief(stdout) or '（空）'}")
        return (self.clock() - ts).total_seconds() / 86400
```

`run_probe` 依固定的順序判定一個探針，第一個不符的條件決定那一項的理由：`Runner` 造出來的找不到指令或逾時；exit code（寫了 `expect_exit` 就只比它，否則比 `ok_exit`）；`expect_stdout` 比對去掉前後空白的整段輸出；`expect_contains` 與 `expect_not_contains` 在原始輸出裡找子字串；最後才量數字。exit code 不符時，理由附上 `stderr`（沒有時附輸出）的開頭，`WARN` 那一行就帶著工具自己的錯誤訊息。

`measure` 有三種量法。`lines` 數非空白的行，用在列出符合條件的紀錄、每筆一行的指令；`value` 與 `age_days` 先取最後一個 `=` 之後的字串，因為 `systemctl show -p NRestarts` 這類指令印的是 `NRestarts=0`。`age_days` 遇到空值或 `n/a` 時的理由是「沒有時間值」，跟解析失敗的「輸出不是時間值」分開：「沒有時間值」代表 timer 從來沒有觸發過，是主機的狀態；「輸出不是時間值」代表腳本讀不懂這個格式，是腳本要修的地方。單獨的 `0` 不在「沒有時間值」的條件裡，`measure("age_days", "LastTriggerUSec=0")` 得到「輸出不是時間值」（實跑）。單元測試 `test_alert_age_days_never_triggered`（本篇沒有收錄）斷言 timer 從未觸發時的理由裡有「沒有時間值」。門檻的比較是「大於才 `WARN`」，量到的值等於門檻時是 `PASS`（`test_alert_value_at_threshold_passes`），清單裡的 `warn_above = 0` 因此讀成「出現任何一筆就 `WARN`」。只有量了數字的探針回傳那個值，其餘回傳 `None`。

### 入口與接聽中的連接埠

```python
    def check_entrypoints(self) -> None:
        listening = None
        if any(e["where"] == "host" for e in self.m["entrypoint"]) or self.m["listen_audit"]["protocols"]:
            listening = self.listening_sockets()
        for e in self.m["entrypoint"]:
            item = f"entrypoint/{e['name']}:{e['port']}/{e['protocol']}"
            if e["where"] == "host":
                if listening is None:
                    self.emit("WARN", item, "讀不到監聽中的 socket（ss 失敗）")
                else:
                    addrs = sorted({a for (proto, a, port) in listening if proto == e["protocol"] and port == e["port"]})
                    if addrs:
                        self.emit("PASS", item, f"有程序在聽（{', '.join(addrs)}），exposure={e['exposure']}")
                    else:
                        self.emit("WARN", item, f"沒有程序在聽這個連接埠，exposure={e['exposure']}")
            else:
                self.emit("MANUAL", item, f"主機外的入口，exposure={e['exposure']}，逐層確認見下方")
            for vf in e["verify"]:
                vitem = f"{item}/{vf['layer']}"
                if vf["where"] == "host":
                    ok, reason, value = self.run_probe(vf["probe"])
                    self.emit("PASS" if ok else "WARN", vitem, reason, value)
                else:
                    self.emit("MANUAL", vitem, _manual_text(vf["where"], vf.get("console_path"), vf.get("manual_command"), vf["expect"]))
        if listening is not None:
            self.audit_listening(listening)

    def listening_sockets(self) -> set[tuple[str, str, int]] | None:
        r = self.runner.run(LISTEN_COMMAND)
        if r.exit != 0:
            return None
        socks = set()
        for line in r.stdout.splitlines():
            parts = line.split()
            if len(parts) < 5:
                continue
            proto = parts[0]
            local = parts[4]
            addr, _, port = local.rpartition(":")
            if not port.isdigit() or proto not in PROTOCOL_VALUES:
                continue
            socks.add((proto, addr, int(port)))
        return socks

    def audit_listening(self, listening: set[tuple[str, str, int]]) -> None:
        la = self.m["listen_audit"]
        if not la["protocols"]:
            return
        known = {(e["protocol"], e["port"]) for e in self.m["entrypoint"] if e["where"] == "host"}
        known |= {(a["protocol"], a["port"]) for a in la["allow"]}
        if not any(p in la["protocols"] for (p, _, _) in listening):
            # ss 成功卻一個都沒列出：多半是看不到主機的網路（PrivateNetwork=yes 的沙箱），跟「沒有多開」分不開。
            self.emit("WARN", "listen-audit", f"ss 沒有列出任何 {', '.join(la['protocols'])} 的監聽 socket，判斷不了有沒有多開的連接埠（在 PrivateNetwork=yes 這類隔離網路的環境裡執行時就是這樣）")
            return
        extra = sorted({(p, a, port) for (p, a, port) in listening if p in la["protocols"] and not _is_loopback(a) and (p, port) not in known})
        if not extra:
            self.emit("PASS", "listen-audit", f"loopback 以外只有清單列出的連接埠在聽（{', '.join(la['protocols'])}）")
        for p, a, port in extra:
            self.emit("WARN", f"listen-audit/{port}/{p}", f"{a}:{port} 在聽，但不在 [[entrypoint]] 或 [listen_audit].allow；用 ss -lnp{p[0]} 查是哪個程序")
```

`ss` 在一次維護檢查裡只執行一次，入口的判定與多開連接埠的稽核共用它的結果。`listening_sockets` 讀 `ss -H -l -n -t -u` 的每一行：第一欄是協定（`tcp`、`udp`），第五欄是本機的位址加連接埠；用 `rpartition(":")` 從右邊切，`[::]:22` 與 `*:8765` 這種含冒號或萬用字元的位址也切得出連接埠。`ss` 的 exit code 不是 0 時回傳 `None`，主機上的每個入口都印成「讀不到」的 `WARN`，不判成沒有程式在接聽。

主機上的入口只要有任何一個位址在接聽那個協定與連接埠，就印 `PASS`，理由裡列出接聽的位址與清單寫的 `exposure`。腳本不拿位址去比對 `exposure`：一個 `cdn-only` 的入口接聽在 `0.0.0.0`，對外的範圍由防火牆與雲端規則決定，那幾層的確認寫在 `[[entrypoint.verify]]`，在主機上的逐層跑探針，在主機外的印成 `MANUAL`。

`audit_listening` 找清單沒有列出的連接埠：清單已經列出的連接埠是主機上的入口加 `[listen_audit].allow`，loopback 位址上的接聽不算多開，其餘每個接聽的位址加連接埠各印一行 `WARN`，項目名是 `listen-audit/<連接埠>/<協定>`，理由附上查出是哪個程式的 `ss` 指令。同一個連接埠同時接聽 `0.0.0.0` 與 `[::]` 時印兩行，兩行的項目名相同，結果檔只留後一行（〈host-check.py（3fc41c0）的已知限制與重現方式〉）。`ss` 成功而一個要稽核的協定的 socket 都沒有時印 `WARN`：在 `PrivateNetwork=yes` 的沙箱裡，`ss` 看不到主機的網路，只看結果分不出「沒有多開」與「什麼都看不到」，實跑的結果在清單寫成 TOML 的那篇概念文章的〈只讀檢查腳本的白名單、輸出、exit code 與結果檔〉systemd 屬性表的 `PrivateNetwork=yes` 那一列。`test_extra_port_warns_and_missing_listener_warns` 給一份含 `0.0.0.0:3306` 與 `127.0.0.1:631` 的輸出，斷言 3306 印成 `WARN`、631 不出現，沒有程式接聽的 22 印成 `WARN`；`test_no_socket_listed_warns` 給空的輸出，斷言稽核那一行是 `WARN`。

### 定期讀的 log

```python
    def check_logs(self) -> None:
        for lg in self.m["log"]:
            item = f"log/{lg['name']}"
            kind, _, target = lg["source"].partition(":")
            hint = f"每 {lg['interval_days']} 天讀一次：{lg['manual_command']}"
            if kind == "file":
                try:
                    st = os.stat(target)
                    with open(target, "rb"):
                        pass
                except FileNotFoundError:
                    self.emit("WARN", item, f"{target} 不存在；{hint}")
                    continue
                except PermissionError:
                    self.emit("WARN", item, f"{target} 讀不到（權限，用 sudo 執行）；{hint}")
                    continue
                self.emit("PASS", item, f"{target} {_human(st.st_size)}；{hint}")
            else:
                r = self.runner.run(journal_command(target))
                if r.exit == 127:
                    self.emit("WARN", item, f"{r.stderr}；{hint}")
                elif not r.stdout.strip():
                    self.emit("WARN", item, f"journal 裡沒有 {target} 的紀錄（unit 沒跑過，或沒有權限讀 journal）；{hint}")
                else:
                    self.emit("PASS", item, f"最新一筆：{_brief(r.stdout.strip(), 90)}；{hint}")
            for al in lg["alerts"]:
                ok, reason, value = self.run_probe(al["probe"])
                self.emit("PASS" if ok else "WARN", f"{item}/{al['name']}", reason, value)
```

讀 log 的內容是人的工作，腳本只確認 log 在那裡、讀得到，並在每一行的理由後面附上清單寫的讀取間隔與讀的指令，維護的人照那一行去讀。檔案型的 log 除了 `os.stat`，還實際開一次檔案：`stat` 只要求能進入上層目錄，檔案本身的讀取權限要開檔才知道。journal 型的 log 讀最新的一筆；輸出是空的有兩種成因（那個 unit 沒有跑過、執行者沒有讀 journal 的權限），腳本分不開，理由裡兩種都寫出來。這條路徑除了 127 不看 exit code：逾時（124）或 `journalctl` 以非零結束而沒有輸出時，印的也是同一句理由。log 底下的計數門檻（`[[log.alert]]`）各自是一個探針，照上面的 `run_probe` 判定。`test_missing_file_log_warns` 斷言檔案不存在的 log 印成 `WARN`。

### 會累積的資料

這一段檢查清單的 `[[accumulation]]`，每一筆的欄位是 `name`、`path`（一個或多個路徑，可以是 glob 樣式）、`missing_ok`、`limit_bytes`、`retention_days`、`oldest_command`、`purge_command`。

```python
    def check_accumulations(self) -> None:
        for ac in self.m["accumulation"]:
            item = f"accumulation/{ac['name']}"
            files: list[str] = []
            denied: list[str] = []
            for pat in ac["paths"]:
                found, blocked = expand_path(pat)
                files.extend(found)
                if blocked and blocked not in denied:
                    denied.append(blocked)
            if not files and denied:
                # 讀不到不等於不存在：missing_ok 只管真的不存在的路徑。
                self.emit("WARN", item, f"讀不到 {', '.join(denied)}（權限，用 sudo 執行），量不到 {', '.join(ac['paths'])}")
                continue
            if not files:
                if ac["missing_ok"]:
                    self.emit("PASS", item, f"路徑不存在，算 0 bytes（{', '.join(ac['paths'])}）")
                else:
                    self.emit("WARN", item, f"路徑不存在：{', '.join(ac['paths'])}")
                continue
            total, oldest, unreadable = measure_paths(sorted(set(files)))
            problems = []
            facts = [f"{_human(total)}"]
            if ac["limit_bytes"] is not None:
                facts[0] += f"／上限 {_human(ac['limit_bytes'])}"
                if total > ac["limit_bytes"]:
                    problems.append(f"大小 {_human(total)} 超過上限 {_human(ac['limit_bytes'])}")
            if ac["retention_days"] is not None:
                if ac["oldest_command"]:
                    r = self.runner.run(ac["oldest_command"])
                    ts = parse_time(r.stdout.strip()) if r.exit == 0 else None
                    if r.exit != 0:
                        problems.append(f"oldest_command exit {r.exit}：{_brief(r.stderr)}")
                    elif ts is None and r.stdout.strip():
                        problems.append(f"oldest_command 的輸出不是時間值：{_brief(r.stdout)}")
                    oldest_ts = ts
                    label = "最舊一筆"
                else:
                    oldest_ts = dt.datetime.fromtimestamp(oldest, dt.timezone.utc) if oldest is not None else None
                    label = "最舊的檔案"
                if oldest_ts is not None:
                    age = (self.clock() - oldest_ts).total_seconds() / 86400
                    facts.append(f"{label} {age:.1f} 天前／保留 {ac['retention_days']} 天")
                    if age > ac["retention_days"]:
                        problems.append(f"{label}是 {age:.1f} 天前，超過保留期 {ac['retention_days']} 天")
                else:
                    facts.append(f"{label}：沒有資料")
            if unreadable:
                problems.append(f"{unreadable} 個路徑讀不到（權限，用 sudo 執行）")
            if denied:
                problems.append(f"讀不到 {', '.join(denied)}（權限，用 sudo 執行），那些路徑沒有算進大小")
            if problems:
                self.emit("WARN", item, "；".join(problems) + f"。清理做法（不會自動執行）：{ac['purge_command']}", total)
            else:
                self.emit("PASS", item, "，".join(facts), total)
```

一個累積項目的路徑可能是幾個 glob 樣式，每個樣式交給下面〈路徑的展開與大小的量測：expand_path 與 measure_paths〉的 `expand_path` 展開；展開時被權限擋下的目錄另外記在 `denied`。判定先分三種情形：一個檔案都沒找到而有目錄讀不到，印「讀不到」的 `WARN`；一個檔案都沒找到、也沒有目錄讀不到，才是路徑不存在，這時才看 `missing_ok`；找到檔案，量大小與時間。`missing_ok` 只管沒有被權限擋下的路徑（上層目錄列得出內容，或路徑根本不存在），讀不到的目錄即使設了 `missing_ok` 也印 `WARN`（`test_unreadable_glob_with_missing_ok_does_not_pass`）：資料可能就在那個讀不到的目錄裡，判成「不存在、算 0」會讓一個寫滿磁碟的目錄印成 `PASS`。

保留天數有兩種量法：寫了 `oldest_command` 時，執行它查資料最舊一筆的時間（例如 SQLite 裡某個時間欄位的最小值），沒有寫時取找到的檔案裡最舊的修改時間。`oldest_command` 成功而輸出是空的（資料表沒有資料）時，理由寫「沒有資料」，不算問題；輸出是 `n/a` 或 `0` 時，`parse_time` 回 `None` 而輸出不是空的，記成「oldest_command 的輸出不是時間值」的問題、那一項印 `WARN`（實跑）。超過上限、超過保留期、讀不到的路徑各記一條問題，任何一條都讓這一項印成 `WARN`，理由後面附上清單的 `purge_command`；`purge_command` 只印不執行，`test_accumulation_over_limit_warns` 斷言 `WARN` 那一行印出了清理指令，而要被清理的檔案仍然存在。這一項的 `value` 是總位元組，下一次執行時印成 `DELTA`。

### 檔案系統的剩餘空間

```python
    def check_filesystems(self) -> None:
        for fs in self.m["filesystem"]:
            item = f"filesystem/{fs['name']}"
            try:
                st = os.statvfs(fs["mount"])
            except OSError as e:
                self.emit("WARN", item, f"讀不到 {fs['mount']}：{e}")
                continue
            free = st.f_bavail * st.f_frsize
            size = st.f_blocks * st.f_frsize
            text = f"{fs['mount']} 剩 {_human(free)}／共 {_human(size)}（下限 {_human(fs['min_free_bytes'])}）"
            self.emit("PASS" if free >= fs["min_free_bytes"] else "WARN", item, text, free)
```

`os.statvfs` 讀檔案系統的區塊計數，不執行 `df`。剩餘空間取 `f_bavail`（一般帳號可用的區塊數），不取 `f_bfree`（全部空閒的區塊數）：ext4 這類檔案系統預留給 root 的區塊算在 `f_bfree` 裡，而服務多半以一般帳號寫資料，`f_bavail` 用完時那些服務就寫不進去。區塊數乘上 `f_frsize`（區塊的大小）得到位元組。這一項的 `value` 是可用位元組（傳給 `emit` 的最後一個參數 `free`），兩次之間少了多少，差異段印得出來。可用空間幾乎每一次執行都不同，所以這一項幾乎每次都印 `DELTA`，要讀的是括號裡的差值。`test_filesystem_value_is_free_bytes` 只斷言結果檔裡這一項的值是數字、而且大於 0。

### 自動更新的排程、設定與重開機

```python
    def check_updates(self) -> None:
        up = self.m["updates"]
        for verb, want in UPDATE_TIMER_VERBS:
            r = self.runner.run(timer_command(verb, up["timer"]))
            got = r.stdout.strip() or _brief(r.stderr) or f"exit {r.exit}"
            self.emit("PASS" if got == want else "WARN", f"updates/{up['timer']}/{verb}", f"{got}（預期 {want}）")
        merged: dict[str, str] = {}
        read_files = []
        for pat in up["config_files"]:
            for path in sorted(glob.glob(pat)) if glob.has_magic(pat) else [pat]:
                if not os.path.isfile(path):
                    continue
                cp = configparser.ConfigParser(interpolation=None)
                try:
                    cp.read(path, encoding="utf-8")
                except (configparser.Error, OSError, UnicodeDecodeError) as e:
                    self.emit("WARN", "updates/config", f"{path} 讀不到或格式錯：{e}")
                    continue
                read_files.append(path)
                if cp.has_section("commands"):
                    merged.update({k: v.strip() for k, v in cp.items("commands")})
        if not read_files:
            self.emit("WARN", "updates/config", f"找不到 dnf-automatic 的設定檔（{', '.join(up['config_files'])}）")
        else:
            wrong = {k: merged.get(k) for k, v in up["expect"].items() if merged.get(k) != v}
            item = "updates/config"
            if wrong:
                self.emit("WARN", item, "；".join(f"[commands] {k} = {g!r}（預期 {up['expect'][k]!r}）" for k, g in wrong.items()) + f"，讀了 {', '.join(read_files)}")
            else:
                self.emit("PASS", item, ", ".join(f"{k} = {v}" for k, v in up["expect"].items()) + f"（mode {up['mode']}，讀了 {', '.join(read_files)}）")
        if up["reboot_check"]:
            r = self.runner.run(up["reboot_check"])
            item = "updates/reboot"
            if r.exit == 0:
                self.emit("PASS", item, "不需要重開機")
            elif r.exit == 1 and REBOOT_REQUIRED_TEXT in r.stdout + r.stderr:
                self.emit("WARN", item, f"更新之後需要重開機（{up['reboot_check']}）：{_brief(r.stdout.strip(), 120)}；deploy.sh 不自動重開，排時間 sudo systemctl reboot")
            elif r.exit == 1:
                self.emit("WARN", item, f"{up['reboot_check']} exit 1，但輸出沒有 {REBOOT_REQUIRED_TEXT!r}，判斷不了要不要重開機：{_brief(r.stderr or r.stdout) or '（沒有輸出）'}")
            else:
                self.emit("WARN", item, f"{up['reboot_check']} exit {r.exit}：{_brief(r.stderr or r.stdout)}")
```

自動更新分三項檢查。清單的 `[updates].mode` 不在其中：它只出現在 `updates/config` 那一行 `PASS` 的理由裡（`mode {up['mode']}`），腳本不拿它比對任何設定或輸出。timer 的兩個查詢比對 `systemctl` 印的整個字串：`is-enabled` 要印 `enabled`、`is-active` 要印 `active`，輸出是空的時，理由改用 `stderr` 或 exit code，`WARN` 那一行看得到 `systemctl` 回了什麼。

設定檔可以寫成 glob 樣式（主設定檔，加上放在附加目錄裡、依檔名順序蓋過主設定的片段檔，也就是 drop-in；這是 dnf 自己的設定目錄，不改主設定檔、用片段蓋過其中的值這個做法，跟 [systemd drop-in（不改原檔的設定疊加）](/linux/dotfile/knowledge-cards/systemd-drop-in/) 相同），展開之後依檔名排序、依序讀，`[commands]` 段的值後讀到的蓋過先讀到的。`ConfigParser` 關掉 interpolation：預設的寫法會把值裡的 `%` 當成變數替換的語法，設定值含一個不成語法的 `%` 時，`cp.items` 取值就丟出例外，而取值的那一行 `merged.update({k: v.strip() for k, v in cp.items("commands")})` 不在 `try` 裡（`try` 只包住 `cp.read`），整支腳本會中止。清單的 `expect` 只列要確認的鍵，設定檔裡其他的鍵不比對；理由裡列出讀了哪些檔案，比對錯了的時候，維護的人知道值是從哪一份讀來的。

`reboot_check` 的 exit 1 有兩種成因：dnf 判定要重開機，以及 dnf 自己出錯（在唯讀的檔案系統上寫不了 log）。腳本因此同時看輸出裡有沒有 `Reboot is required`，有才印「需要重開機」，沒有時印「判斷不了」並附上 dnf 的錯誤訊息；兩種成因的實跑結果與沙箱的設定在清單寫成 TOML 的那篇概念文章的〈只讀檢查腳本的白名單、輸出、exit code 與結果檔〉。`test_reboot_required_message_warns_reboot`、`test_reboot_exit1_without_message_is_not_reboot` 與 `test_reboot_exit0_passes` 各給一種輸出，斷言三種理由。理由裡的 `deploy.sh` 是私有專案部署那台主機的腳本，它裝好自動更新、不自動重開機。

### 暫停與恢復的步驟，以及依 phase 選檢查

```python
    def check_phase(self, phase: str) -> None:
        for st in self.m[phase]:
            item = f"{phase}/{st['step']}/{st['resource']}"
            billing = f"停機計費：額度內 {st['billed_when_stopped']}，超出額度 {st['billed_when_stopped_beyond_free']}（{st['billing_basis']}）"
            action = st["manual_command"] or st["console_path"]
            if st["where"] == "host":
                self.emit("MANUAL", item, f"在主機上做（腳本不執行）：{action}；{billing}")
                ok, reason, value = self.run_probe(st["verify"])
                self.emit("PASS" if ok else "WARN", f"{item}/verify", reason, value)
            else:
                self.emit("MANUAL", item, _manual_text(st["where"], st["console_path"], st["manual_command"], st["verify"]) + f"；{billing}")

    def run(self, phase: str = "maintain") -> list[Line]:
        if phase == "maintain":
            self.check_entrypoints()
            self.check_logs()
            self.check_accumulations()
            self.check_filesystems()
            self.check_updates()
        else:
            self.check_phase(phase)
        return self.lines
```

暫停與恢復的每一步都印成 `MANUAL`，理由寫出要做的動作與那項資源停機時的計費；動作由人執行，腳本不執行 `manual_command`。在主機上的步驟另外執行 `verify` 的只讀探針，多印一行 `PASS` 或 `WARN`：維護的人做完那一步再跑一次腳本，`verify` 那一行確認那一步是否做成。`test_host_step_runs_only_verify` 斷言假的執行器只收到 `verify` 的指令，沒有收到 `manual_command`。各步驟要做什麼、停機時哪些資源還在計費，在 [服務暫停與恢復上線：只停服務、停止主機、終止主機到全部刪除各自保留的資源，暫停期間仍計費與仍被指向的資源，恢復前要查的漂移與恢復的順序](/operations/09-host-lifecycle/suspend-and-resume-service/)。

`run` 依 `--phase` 選要跑的檢查。維護時五類檢查依固定順序執行，順序只決定報告裡各行的先後；結果檔以項目名稱比對前後兩次，不依賴行的順序。

## 路徑的展開與大小的量測：expand_path 與 measure_paths

這一段給會累積的資料用：把清單的路徑樣式展開成實際的檔案，分出「不存在」與「讀不到」，再用 `os.lstat` 量總大小與最舊的修改時間，不執行 `du`：白名單裡的 `du` 是給清單的探針用的，腳本自己量大小時不呼叫它。分出讀不到的路徑，是為了讓一般帳號執行時讀不到的目錄印成 `WARN`，而不是被當成路徑不存在，改用專用帳號實跑時讀不到哪些目錄，在 [主機維護清單寫成 TOML：JSON、YAML、TOML 的取捨、TOML 1.0 與 1.1 的版本差異、清單的欄位設計與只讀檢查腳本](/operations/09-host-lifecycle/host-manifest-in-toml/)〈只讀檢查腳本的白名單、輸出、exit code 與結果檔〉。

```python
# ── 小工具 ─────────────────────────────────────────────────


def expand_path(pat: str) -> tuple[list[str], str | None]:
    """展開 [[accumulation]] 的一個路徑，回傳 (找到的路徑, 擋住讀取的目錄)。

    glob 與 os.path.lexists 遇到沒有權限的目錄都安靜地當成沒有（非 root 讀 0711 的 /var/log/nginx、
    0750 的 /var/lib/monitor-collector、0700 的家目錄底下），所以找不到時再查一次：
    glob 查萬用字元之前那一層目錄列不列得出來，一般路徑查 lstat 是不是被權限擋下。
    萬用字元出現在中間一層、而更深一層的目錄讀不到時，這裡查不出來，仍然算成不存在。
    """
    if glob.has_magic(pat):
        found = glob.glob(pat)
        if found:
            return found, None
        parts = pat.split(os.sep)
        i = next(i for i, part in enumerate(parts) if glob.has_magic(part))
        base = os.sep.join(parts[:i]) or (os.sep if pat.startswith(os.sep) else os.curdir)
        try:
            os.listdir(base)
        except PermissionError:
            return [], base
        except OSError:
            pass
        return [], None
    try:
        os.lstat(pat)
    except PermissionError:
        return [], pat
    except OSError:
        return [], None
    return [pat], None


def measure_paths(paths: list[str]) -> tuple[int, float | None, int]:
    """回傳 (總 bytes, 最舊的 mtime, 讀不到的路徑數)；不跟隨 symlink，同一個 inode 只算一次。"""
    total = 0
    oldest: float | None = None
    unreadable = 0
    seen: set[tuple[int, int]] = set()

    def visit(p: str) -> None:
        nonlocal total, oldest, unreadable
        try:
            st = os.lstat(p)
        except OSError:
            unreadable += 1
            return
        key = (st.st_dev, st.st_ino)
        if key in seen:
            return
        seen.add(key)
        if stat.S_ISREG(st.st_mode):
            total += st.st_blocks * 512 if st.st_blocks else st.st_size
            oldest = st.st_mtime if oldest is None else min(oldest, st.st_mtime)
        elif stat.S_ISDIR(st.st_mode):
            try:
                entries = os.listdir(p)
            except OSError:
                unreadable += 1
                return
            for name in entries:
                visit(os.path.join(p, name))

    for p in paths:
        visit(p)
    return total, oldest, unreadable
```

`glob.glob` 遇到列不出內容的目錄時回傳空串列，不丟例外，結果跟「沒有符合的檔案」一樣。`expand_path` 因此在 glob 找不到時，取樣式裡第一個含萬用字元的那一層之前的目錄，試著列一次內容：被權限擋下就回傳那個目錄，讓呼叫的程式印「讀不到」；列得出來（目錄在、只是沒有符合的檔案）或目錄不存在，才算不存在。不含萬用字元的路徑用 `os.lstat` 查，上層目錄不讓進入時 `lstat` 丟出 `PermissionError`。docstring 寫了這個做法查不出的情形：萬用字元在中間一層、更深一層讀不到時，仍然算成不存在。單元測試 `test_glob_in_unlistable_dir_is_unreadable`（本篇沒有收錄）用權限 0311（擁有者可以進入、不能列出內容）的目錄重現一般帳號看 0711 的 `/var/log/nginx`，斷言理由是「讀不到」，同一個目錄擋住兩個樣式時只列一次；`test_literal_path_under_unreadable_parent_is_unreadable` 用權限 0000 的上層目錄測不含萬用字元的路徑。這幾項測試要以一般帳號執行，以 root 執行時權限擋不住讀取，測試會失敗。

`measure_paths` 遞迴走過每個路徑，用 `lstat` 而不用 `stat`：符號連結本身不算進大小，也不會被跟進去，一個指向 `/` 的連結不會讓腳本量整個檔案系統。每個檔案以（裝置編號、inode 編號）為鍵只算一次，inode 是檔案系統裡代表一個檔案的節點，硬連結共用同一個 inode，兩個樣式找到同一個檔案時也只算一次。大小取 `st_blocks * 512`，也就是檔案實際佔用的磁碟區塊（`st_blocks` 以 512 位元組為單位），跟 `du` 量的是同一種值：稀疏檔案的長度可能遠大於它佔用的空間，而上限要比的是磁碟用量。量的過程中讀不到的路徑只計數，不中斷，呼叫的程式把計數寫進 `WARN` 的理由。

`st_blocks` 是 0 時的退路，跟「上限要比的是磁碟用量」互相衝突。程式在 `st_blocks` 是 0 時改用檔案的長度 `st_size`；這個退路是為哪一種情形，原始碼與加入它的 commit 都沒有寫。而整個檔案都是空洞的稀疏檔案，`st_blocks` 正好是 0，會被算成它的長度，寫在〈host-check.py（3fc41c0）的已知限制與重現方式〉的〈各項檢查：ss 失敗、重複的項目名、loopback、特殊檔案、稀疏檔案與時間值〉。

## 時間字串的解析與組輸出用的小函式

`parse_time` 把 log 計數門檻的探針（`[[log.alert]]` 裡 `measure = "age_days"` 的那些）與 `[[accumulation]]` 的 `oldest_command` 印出的時間字串轉成帶時區的時間，接受 systemd 的格式、Unix 時間戳與 ISO 8601；之後是判斷 loopback 位址、把位元組換成 KiB 與 MiB、把輸出壓成一行、組 `MANUAL` 理由的小函式。腳本第一次在雲端主機上執行時讀不懂 systemd 印的時間格式，那一次的結果與修正在 [主機維護清單寫成 TOML：JSON、YAML、TOML 的取捨、TOML 1.0 與 1.1 的版本差異、清單的欄位設計與只讀檢查腳本](/operations/09-host-lifecycle/host-manifest-in-toml/)〈只讀檢查腳本的白名單、輸出、exit code 與結果檔〉裡記錄雲端主機第一次執行結果的那幾段。

```python
# systemd 的時間格式：systemctl show 印時間屬性（LastTriggerUSec 這類）時用它，不理
# --timestamp=unix。例：'Mon 2026-10-26 07:07:43 GMT'、'Mon 2026-10-26 15:07:43.250000 CST'。
# 時區是縮寫：UTC、GMT 直接認；其他縮寫要等於這台主機目前時區的縮寫（time.tzname）才當成本地
# 時間，認不得的不猜（回傳 None）。
SYSTEMD_TIME_RE = re.compile(r"^(?:[A-Z][a-z]{2} )?(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d{1,6})?) ([A-Za-z]{2,6}|[+-]\d{2}:?\d{2})$")


def _parse_systemd_time(text: str) -> dt.datetime | None:
    m = SYSTEMD_TIME_RE.match(text)
    if not m:
        return None
    clock, zone = m.groups()
    naive = dt.datetime.fromisoformat(clock)
    if zone in ("UTC", "GMT", "UCT", "Z"):
        return naive.replace(tzinfo=dt.timezone.utc)
    if zone[0] in "+-":
        return dt.datetime.fromisoformat(f"{clock}{zone[:3]}:{zone[-2:]}")
    if zone in time.tzname:
        # 本地時區：naive 的 astimezone() 依這個程序的時區規則換算（含夏令時間）。
        return naive.astimezone()
    return None


def parse_time(text: str) -> dt.datetime | None:
    text = text.strip()
    if not text or text in ("n/a", "0"):
        return None
    if re.fullmatch(r"@?\d+(\.\d+)?", text):
        return dt.datetime.fromtimestamp(float(text.lstrip("@")), dt.timezone.utc)
    systemd = _parse_systemd_time(text)
    if systemd is not None:
        return systemd
    # 小數秒超過 6 位（Go 的 RFC3339Nano）時截到微秒，fromisoformat 才吃得下。
    t = re.sub(r"(\.\d{6})\d+", r"\1", text.replace(" ", "T", 1))
    t = re.sub(r"Z$", "+00:00", t)
    try:
        ts = dt.datetime.fromisoformat(t)
    except ValueError:
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=dt.timezone.utc)
```

systemd 的時間格式以時區縮寫結尾，而縮寫不唯一對應一個時區：`CST` 在 `Asia/Taipei` 是台灣的標準時間，在美國中部是另一個時區。`_parse_systemd_time` 因此只認 UTC 這一類縮寫，以及等於這台主機目前時區縮寫的那一個（`time.tzname`），也認 `+0800`、`+08:00` 這種數字的時區偏移，其餘回傳 `None`，讓那一項印成「輸出不是時間值」，不猜一個時區而算出差了幾小時的天數。單元測試 `test_alert_age_days_systemd_local_zone`（本篇沒有收錄）把時區設成 `Asia/Taipei`，斷言 `CST` 換算正確、不認得的 `XYZT` 判成不是時間值；`test_alert_age_days_systemd_format` 測 `GMT`、`UTC` 與帶小數秒的寫法。

`parse_time` 接受三種格式：可以有 `@` 前綴的 Unix 時間戳（epoch 秒數）、systemd 的格式、ISO 8601。systemd 的格式要另外處理，因為 `systemctl show` 印時間屬性（`LastTriggerUSec` 這類）時不理 `--timestamp=unix`，印的是 systemd 自己的格式；程式碼註解記了這一點，`test_alert_age_days_systemd_format` 用的就是那種輸出。

單獨的 `0` 與 `n/a`，`parse_time` 回 `None`，`@0` 照樣當成 1970-01-01（實跑）。回 `None` 之後怎麼判由呼叫端決定，兩個呼叫端的判法不同：`measure` 在呼叫 `parse_time` 之前，先把空的輸出與 `n/a` 判成「沒有時間值」，`0` 不在其中，結果是「輸出不是時間值」；`check_accumulations` 只把空的輸出當成沒有資料，`oldest_command` 印 `n/a` 或 `0` 時印 `WARN`「輸出不是時間值」（兩者都實跑）。`measure` 與 `check_accumulations` 各自的結果寫在〈host-check.py（3fc41c0）的已知限制與重現方式〉的〈各項檢查：ss 失敗、重複的項目名、loopback、特殊檔案、稀疏檔案與時間值〉。

ISO 8601 的字串截掉超過微秒的小數秒，程式碼註解寫的理由是 `datetime.fromisoformat` 吃不下 Go 的 RFC3339Nano 印出的奈秒，那是 Python 3.10 以前的行為：實跑 Python 3.10.18 的 `fromisoformat` 對九位小數丟出 `ValueError: Invalid isoformat string`，3.11.13、3.12.11、3.15.0 都接受九位小數、自己截到微秒。腳本要求 3.11 以上，所以在它支援的版本上，這一行截斷是冗餘的，結果跟不截斷相同。

沒有時區的 ISO 時間當成 UTC：字串本身沒有時區，腳本沒有別的資訊可以判斷。資料來源寫進去的是不帶時區的本地時間時，算出的天數會差一個時區偏移（台北是 8 小時，約 0.33 天），保留期的判定在門檻附近會早或晚 8 小時翻轉成 `WARN`。

```python
def _is_loopback(addr: str) -> bool:
    a = addr.strip("[]").split("%", 1)[0]
    return a.startswith("127.") or a == "::1"


def _human(n: int | float) -> str:
    for unit in ("B", "KiB", "MiB", "GiB"):
        if abs(n) < 1024 or unit == "GiB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GiB"


def _brief(text: str, limit: int = 160) -> str:
    one = " ".join(text.split())
    return one if len(one) <= limit else one[: limit - 1] + "…"


def _manual_text(where: str, console_path: str | None, command: str | None, expect: str) -> str:
    place = {"console": "主控台", "external": "主機外"}[where]
    how = console_path if console_path else f"執行 {command}"
    return f"[{place}] {how} → 預期：{expect}"
```

`_is_loopback` 先去掉 IPv6 位址外面的方括號與 `%` 之後的介面名稱（`ss` 印 `[::1]:631` 或 `127.0.0.53%lo:53` 這種寫法），再比對 `127.` 開頭或 `::1`。`_human` 的單位是 1024 進位的 KiB、MiB、GiB，跟 `du -h`、`df -h` 的換算方式相同，報告裡的大小拿去跟這兩支工具的輸出對照時不必換算。`_brief` 把多行的輸出壓成一行並截到 160 個字元，報告每一項維持一行，用 `grep` 篩報告時一項就是一行。

## 結果檔的讀寫與跟前一次的差異

結果檔讓每一次的報告能跟同一個階段的前一次比對（階段就是 `--phase` 的 `maintain`、`suspend`、`resume`）：讀前一次的紀錄、算出差異、印在報告裡，最後把這一次的紀錄寫回去。寫回的做法是同一個目錄裡的暫存檔、`fsync`、`os.replace`，再 `fsync` 目錄，保證中斷時舊的紀錄仍然完整，說明在程式碼之後。結果檔的格式、印出的差異與預設路徑放在 `/var/lib` 的理由，在 [主機維護清單寫成 TOML：JSON、YAML、TOML 的取捨、TOML 1.0 與 1.1 的版本差異、清單的欄位設計與只讀檢查腳本](/operations/09-host-lifecycle/host-manifest-in-toml/)〈只讀檢查腳本的白名單、輸出、exit code 與結果檔〉。

```python
# ── 結果檔（與前一次的差）──────────────────────────────────
# 腳本自己的結果檔，不是清單的一部分：清單只描述要檢查什麼，量到的值存在這裡。
# 唯一會寫的檔案，而且只寫這一個（同目錄暫存檔 + os.replace，結束時目錄裡只有它）。


def load_state(path: str) -> tuple[dict[str, Any], str | None]:
    # 讀結果檔，回傳 (內容, 要印的 note)。不存在回空內容且不印 note；壞掉或格式不認得當成沒有。
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}, None
    except (OSError, ValueError) as e:  # JSONDecodeError、UnicodeDecodeError 都是 ValueError
        return {}, f"結果檔 {path} 讀不到或壞掉（{e}），當成沒有前一次，這次會覆寫"
    if not isinstance(data, dict) or data.get("format") != STATE_FORMAT or not isinstance(data.get("phases"), dict):
        return {}, f"結果檔 {path} 的格式不認得，當成沒有前一次，這次會覆寫"
    return data, None


def previous_phase(state: dict[str, Any], phase: str) -> dict[str, Any] | None:
    prev = state.get("phases", {}).get(phase)
    if isinstance(prev, dict) and isinstance(prev.get("finished_at"), str) and isinstance(prev.get("items"), dict):
        return prev
    return None


def build_record(lines: list[Line], counts: dict[str, int], manifest_path: str, finished_at: dt.datetime) -> dict[str, Any]:
    return {
        "finished_at": finished_at.astimezone(dt.timezone.utc).isoformat(),
        "manifest": manifest_path,
        "counts": counts,
        "items": {ln.item: {"status": ln.status, "value": ln.value} for ln in lines},
    }


def _num(n: float) -> str:
    return f"{n:.0f}" if float(n).is_integer() else f"{n:.2f}"


def _prev_value(entry: Any) -> tuple[str | None, float | None]:
    if not isinstance(entry, dict):
        return None, None
    value = entry.get("value")
    ok = isinstance(value, (int, float)) and not isinstance(value, bool)
    return entry.get("status"), (value if ok else None)


def diff_lines(prev: dict[str, Any] | None, lines: list[Line], state_path: str) -> list[str]:
    # 與前一次的差：第一行 since:，其後每個差一行（CHANGED / DELTA / NEW / GONE）。
    if prev is None:
        return [f"since: 沒有前一次的結果（{state_path}）"]
    out: list[str] = []
    seen: set[str] = set()
    for ln in lines:
        seen.add(ln.item)
        if ln.item not in prev["items"]:
            out.append(f"NEW     {ln.item}  {ln.status}")
            continue
        old_status, old_value = _prev_value(prev["items"][ln.item])
        if old_status != ln.status:
            out.append(f"CHANGED {ln.item}  {old_status}→{ln.status}")
        if old_value is not None and ln.value is not None and old_value != ln.value:
            delta = ln.value - old_value
            out.append(f"DELTA   {ln.item}  {_num(old_value)} → {_num(ln.value)}（{'+' if delta > 0 else '-'}{_num(abs(delta))}）")
    out.extend(f"GONE    {item}" for item in sorted(set(prev["items"]) - seen))
    if not out:
        return [f"since: {prev['finished_at']}，與前一次相同"]
    return [f"since: {prev['finished_at']}", *out]
```

讀結果檔的三個函式都把讀到的內容當成不可信的輸入：檔案不存在是第一次執行，不印說明；JSON 壞掉、編碼不對、讀不到，回傳一條 `note`（由 `main` 印到 stderr）並當成沒有前一次；最外層不是 `format` 等於 `STATE_FORMAT`（1）、帶 `phases` 的物件時，同樣當成沒有前一次。`previous_phase` 與 `_prev_value` 再逐層確認型別，值是布林時不拿來算差。手改過或被別的程式寫壞的結果檔，最多讓差異段印成「沒有前一次的結果」，不會讓腳本中止（單元測試 `test_corrupt_state_does_not_abort`，本篇沒有收錄）。

`diff_lines` 以項目名稱比對前後兩次，所以清單改了名稱的項目印成一筆 `GONE` 加一筆 `NEW`。同一個項目狀態與數字都變了時，`CHANGED` 與 `DELTA` 各印一行；`DELTA` 只在兩次都有數字時印，`value` 是 `null` 的項目只會出現在 `CHANGED`。`GONE` 依名稱排序，同樣的兩份紀錄每次印出的差異段順序相同。`test_new_and_gone_items` 斷言清單加進一個累積項目之後印 `NEW     accumulation/b  PASS`，拿掉之後印 `GONE    accumulation/b`；`test_second_run_prints_changed_and_delta` 斷言一個計數門檻 100 的探針從 42 變成 50 時印 `DELTA   log/edge/status-429  42 → 50（+8）`，變成 500 時同時印 `CHANGED … PASS→WARN` 與 `DELTA … 50 → 500（+450）`，再變成 20 時印 `DELTA … 500 → 20（-480）`。

```python
def _fsync_directory(directory: str) -> None:
    # rename 要等目錄項寫進磁碟才耐斷電；Windows 不能開目錄，略過。
    if not hasattr(os, "O_DIRECTORY"):
        return
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_state(path: str, state: dict[str, Any]) -> str | None:
    # 原子地寫結果檔；失敗回傳 note（不改變 exit code）。
    directory = os.path.dirname(os.path.abspath(path))
    tmp_path = None
    try:
        os.makedirs(directory, mode=0o700, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(prefix=".last-", suffix=".tmp", dir=directory)  # mkstemp 建出來就是 0600
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
        tmp_path = None
        _fsync_directory(directory)
    except OSError as e:
        return f"結果檔 {path} 寫不進去（{e}）；這次的結果沒有存下來，報告與 exit code 不受影響"
    finally:
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass  # 暫存檔已不在（沒建成功或已被取代），沒有東西要清
    return None
```

`write_state` 的寫法依序是：在結果檔的同一個目錄用 `tempfile.mkstemp` 建暫存檔（權限 0600），寫完內容之後 `fsync`（要求作業系統把檔案內容寫到磁碟），再用 `os.replace` 換上正式的檔名，最後 `fsync` 那個目錄。暫存檔要在同一個目錄，因為 `os.replace` 在同一個檔案系統裡才是一次完成的換名；目錄的 `fsync` 讓換名這件事本身也寫進磁碟，斷電之後正式的檔名指著的是舊的或新的完整內容，不會是寫到一半的檔案。`os.replace` 擋的是中斷，擋不住兩次執行同時寫：程式裡沒有檔案鎖（`flock` 這類），兩次同時跑時，各自讀到的是開始時的結果檔，後換名的那一次蓋掉先換名的那一次寫進的紀錄（讀碼）。`test_write_state_fsyncs_file_and_directory` 斷言 `fsync` 至少呼叫兩次（檔案一次、目錄一次）。

`os.makedirs` 的 `mode=0o700` 只套在這次新建的最後一層目錄上（中間各層用預設的權限），已經存在的目錄不改權限；`exist_ok=True` 只讓目錄已經存在時不丟例外。所以由 systemd 的 `StateDirectory=` 建出的目錄，權限照 `StateDirectoryMode=` 設定，腳本不跟 systemd 爭這個值。寫入失敗時，`finally` 刪掉留下的暫存檔，函式回傳一條 `note`，命令列印到 stderr，exit code 照檢查的結果決定（`test_unwritable_state_keeps_exit_code`）；成功時目錄裡只剩結果檔（`test_first_run_writes_only_last_json`）。

## 命令列與 exit code：main

`main` 是命令列的入口：解析參數、載入清單、執行檢查、印報告與差異、寫結果檔，最後依報告決定 exit code。exit code 的讀法，以及接上排程時為什麼 exit code 不是 0 就要告警，在 [主機維護清單寫成 TOML：JSON、YAML、TOML 的取捨、TOML 1.0 與 1.1 的版本差異、清單的欄位設計與只讀檢查腳本](/operations/09-host-lifecycle/host-manifest-in-toml/)〈只讀檢查腳本的白名單、輸出、exit code 與結果檔〉；跨主機執行時每台的 exit code 在 [多台主機維護清單的實作紀錄：在容器上安裝 ansible-core 與 Terraform、由 Terraform 產生 inventory、用 Ansible 的範本部署每台的清單、以 sudo 與 systemd-run 執行檢查腳本，以及清理](/operations/09-host-lifecycle/hands-on/multi-host-manifest-walkthrough/)〈以 -b 與 systemd-run 執行檢查腳本：每台的輸出與 ansible 的 exit code〉。

```python
def main(argv: list[str] | None = None, runner: Runner | None = None, out=None) -> int:
    out = out or sys.stdout
    ap = argparse.ArgumentParser(description="web-demo 主機的只讀維護檢查")
    ap.add_argument("--manifest", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "host.toml"))
    ap.add_argument("--phase", choices=PHASES, default="maintain")
    ap.add_argument("--state-file", default=DEFAULT_STATE_FILE, metavar="PATH", help=f"結果檔路徑（預設 {DEFAULT_STATE_FILE}）")
    ap.add_argument("--no-state", action="store_true", help="不讀也不寫結果檔")
    ap.add_argument("--set", action="append", default=[], metavar="NAME=VALUE", help="覆寫 [vars] 的值")
    args = ap.parse_args(argv)
    overrides = {}
    for s in args.set:
        k, sep, val = s.partition("=")
        if not sep:
            print(f"manifest error: --set 要寫成 NAME=VALUE：{s}", file=sys.stderr)
            return 2
        overrides[k] = val
    try:
        manifest = load_manifest(args.manifest, overrides)
    except ManifestError as e:
        for msg in e.errors:
            print(f"manifest error: {msg}", file=sys.stderr)
        print(f"manifest error: {len(e.errors)} 項，沒有執行任何檢查", file=sys.stderr)
        return 2
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        print("note: 不是 root，journal、audit.log 與 collector 的目錄可能讀不到（會印成 WARN）", file=sys.stderr)
    try:
        lines = Checker(manifest, runner).run(args.phase)
    except RuntimeError as e:
        # validate 已比對過 Checker 會拼的指令，正常路徑不該走到；保險：當格式錯處理。
        print(f"manifest error: {e}", file=sys.stderr)
        return 2
    counts = {"PASS": 0, "WARN": 0, "MANUAL": 0}
    for ln in lines:
        counts[ln.status] += 1
        print(f"{ln.status:<6} {ln.item}  {ln.reason}", file=out)
    state: dict[str, Any] = {}
    if not args.no_state:
        state, note = load_state(args.state_file)
        if note:
            print(f"note: {note}", file=sys.stderr)
        for text in diff_lines(previous_phase(state, args.phase), lines, args.state_file):
            print(text, file=out)
    print(f"summary: {counts['PASS']} PASS, {counts['WARN']} WARN, {counts['MANUAL']} MANUAL（phase {args.phase}，{args.manifest}）", file=out)
    if not args.no_state:
        phases = dict(state.get("phases", {}))
        phases[args.phase] = build_record(lines, counts, args.manifest, now_utc())
        note = write_state(args.state_file, {"format": STATE_FORMAT, "phases": phases})
        if note:
            print(f"note: {note}", file=sys.stderr)
    return 1 if counts["WARN"] else 0


if __name__ == "__main__":
    sys.exit(main())
```

`main` 收 `argv`、`runner` 與 `out` 三個參數，單元測試直接呼叫它，傳入假的執行器並把報告寫進記憶體裡的字串，不必另起一個程序。`--manifest` 的預設是腳本所在目錄的 `host.toml`，腳本與清單放在同一個目錄時不用帶這個參數。exit 2 的出口有四個：`argparse` 遇到不認得的參數或不在 `PHASES` 裡的 `--phase`（`argparse` 自己以 2 結束）、`--set` 沒有寫成 `名稱=值`、清單格式錯、執行時白名單拒絕了一條指令；前三個出口在任何檢查執行之前，執行時的拒絕發生時，在它之前的指令已經執行過。走到執行時的拒絕時，`RuntimeError` 從 `Checker(...).run` 裡丟出來，`run` 沒有回傳，`lines` 沒有被設定，所以已經執行過的那些項目，報告行一行都不會印出，stderr 印一行 `manifest error:` 加上拒絕的理由。清單格式錯時，每一條錯誤印一行 `manifest error:`，最後一行寫出錯誤的條數與「沒有執行任何檢查」。`-h`／`--help` 由 `argparse` 印出用法之後以 exit 0 結束，一項檢查都不執行，也沒有 `summary:` 那一行（實跑）；這支腳本裡，exit 0 而沒有 `summary:` 的只有這一種（讀碼），跟中途中止的 exit 1 分得開。單元測試 `test_cli_format_error_exit_2`（本篇沒有收錄）把腳本當成獨立的程序執行一份 `name = 1` 的清單，斷言 exit code 是 2、stderr 有 `manifest error`。

不是 root 時，`main` 在 stderr 印一行 `note:`，不改變 exit code：哪些項目會讀不到，由那幾項自己印成 `WARN`。報告的順序是每一項一行、差異段、`summary:` 一行；結果檔在檢查跑完之後才讀，結果檔壞掉不影響檢查本身，寫結果檔排在印出 `summary:` 之後，寫入失敗時報告已經完整印出。exit code 只看 `WARN` 的數量，`MANUAL` 不影響它。`if __name__ == "__main__"` 讓這個檔案被當成模組載入時（部署時的 `validate` 只呼叫 `load_manifest`）不執行檢查。

照這支腳本的做法替自己的主機寫檢查腳本時，程式裡有幾處字串是寫給示範清單那台主機的，要換成自己的環境：

- **`web-demo`**：docstring 的第一行與 `argparse` 的 `description`，寫的是示範主機上的服務名。
- **`collector`、`audit.log`**：docstring 的用法說明與只讀保證，以及 `main` 不是 root 時印的那一行 `note:`，寫的是示範主機上讀不到的目錄與檔案。
- **OCI Console、Cloudflare dashboard**：docstring 第二段，寫的是示範主機外的確認位置。
- **`dnf-automatic`**：`check_updates` 找不到設定檔時印的理由；自動更新用的是別的工具時，`REBOOT_REQUIRED_TEXT` 與 `config_files` 的讀法也要一起換。
- **`deploy.sh 不自動重開，排時間 sudo systemctl reboot`**：`check_updates` 判定需要重開機時印的理由，`deploy.sh` 是私有專案部署那台主機的腳本。
- **`/var/lib/host-check/last.json` 與 `host.toml`**：`DEFAULT_STATE_FILE` 是結果檔的預設路徑，`--manifest` 的預設是腳本所在目錄的 `host.toml`；路徑換了時，systemd 沙箱的 `StateDirectory=` 也要跟著換。

## host-check.py（3fc41c0）的已知限制與重現方式

這一版的腳本沒有處理的行為，依腳本的結構分成四組：清單的驗證、指令的執行與 exit code、各項檢查、結果檔。每一條寫出觸發條件與結果，括號裡的「實跑」與「讀碼」照開場的定義讀。

實跑的方式以同一個連接埠在兩個位址接聽那一條為例。在放著 `host-check.py` 的目錄執行下面這段，假的執行器不管收到哪一條指令都回同一份 `ss` 的輸出；第一行印出兩筆 `('WARN', 'listen-audit/111/tcp')`，第二行印出結果檔的 `items` 只剩一個 `listen-audit/111/tcp`：

```bash
python3 - <<'EOF'
import importlib.util

spec = importlib.util.spec_from_file_location("host_check", "host-check.py")
hc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hc)


class FakeRunner(hc.Runner):
    def run(self, command):
        out = "tcp LISTEN 0 128 0.0.0.0:111 0.0.0.0:*\ntcp LISTEN 0 128 [::]:111 [::]:*\n"
        return hc.Result(0, out, "")


manifest = {"listen_audit": {"protocols": ["tcp"], "allow": []}, "entrypoint": []}
checker = hc.Checker(manifest, FakeRunner())
checker.check_entrypoints()
print([(ln.status, ln.item) for ln in checker.lines])
print(list(hc.build_record(checker.lines, {}, "m", hc.now_utc())["items"]))
EOF
```

例子裡直接組出 `Checker` 收的 dict，因為 `listen_audit` 與空的 `entrypoint` 在 `validate` 正規化之後，形狀跟 TOML 的寫法相同。其餘段落正規化之後的形狀不同：`[[accumulation]]` 的 `path` 變成 `paths`（一律是串列），`[[log]]` 多一個 `alerts` 串列，每一個探針換成 `Probe` 物件，`[[entrypoint.verify]]` 在主機上的確認變成帶 `probe` 鍵的 dict。照 TOML 的欄位名組 dict 交給 `check_accumulations`，得到 `KeyError: 'paths'`（實跑）。所以其餘各條的重現，先寫一份 TOML 清單，用 `hc.load_manifest(<清單的路徑>)` 取得正規化之後的 dict，再交給 `hc.Checker`、呼叫對應的方法（`check_logs`、`check_updates`、`check_accumulations`、`check_entrypoints`）；`_Validator.probe`、`load_state`、`measure_paths`、`_is_loopback`、`parse_time` 這些函式可以直接呼叫；〈結果檔：壞掉時的其他階段與兩次同時執行〉的那幾條用 `hc.main([..., "--state-file", <路徑>], runner=<假的執行器>)` 從頭跑。

### 清單的驗證：不認得的鍵、同時寫 expect_exit 與 ok_exit、expect 的大寫鍵

- **`[updates].expect` 的鍵有大寫字母**（實跑）：`ConfigParser` 預設把設定檔裡的鍵轉成小寫，`merged` 的鍵因此全是小寫；清單的 `expect` 寫 `Upgrade_Type = "security"` 時，查 `merged.get("Upgrade_Type")` 得到 `None`，那一項永遠印 `WARN`。實跑時同一份設定檔，`expect` 的鍵寫 `Upgrade_Type` 時印 `WARN`（理由是 `Upgrade_Type = None`），寫 `upgrade_type` 時印 `PASS`。dnf-automatic 的設定檔裡 `[commands]` 的鍵寫成小寫（`upgrade_type`、`apply_updates`），清單照設定檔的寫法寫小寫就不會碰到。
- **探針同時寫 `expect_exit` 與 `ok_exit`**（實跑）：`validate` 不拒絕這種寫法，`run_probe` 只比 `expect_exit`，`ok_exit` 不起作用。實跑時 `expect_exit = 0`、`ok_exit = [0, 1]` 的探針沒有任何格式錯，指令以 exit 1 結束時判成不符（理由 `exit 1（預期 0）`）。
- **`validate` 不認得的鍵與只在 `[[log.alert]]` 生效的 `measure`**（實跑）：`validate` 只讀它認得的鍵，其餘的鍵不報錯、當成沒寫。打錯字的鍵因此安靜地失效：實跑時一個寫了 `expect_exit = 0` 與 `expect_stdot = "x"` 的探針沒有任何格式錯，`expect_stdout` 讀出來是 `None`，輸出不會被比對；`[[accumulation]]` 的 `missing_okk` 照同一個機制被當成沒寫，`missing_ok` 取預設的 `false`（讀碼）。`measure` 與 `warn_above` 也屬於這一類：它們只在 log 的計數門檻（`[[log.alert]]`）讀，入口與暫停、恢復步驟的 `verify` 探針上寫了這兩個欄位、同一個探針又另外寫了別的預期值時，兩個欄位被略過（實跑：`measure` 讀出來是 `None`）；只寫 `measure` 而沒有其他預期值時，判成「探針至少要有一個預期值」的格式錯（實跑）。

### 指令的執行與 exit code：沒有接住的例外

- **`check_logs` 與 `Runner.run` 沒有接住的例外**：兩處的 `try` 只接幾種指定的例外，沒有列出的例外一路往上，Python 印出 traceback、以 exit 1 結束，stdout 沒有 `summary:` 那一行。觸發的情形有三種：
  - `[[log]]` 的 `source` 寫成 `file:<目錄>`：`os.stat` 成功，接著 `open()` 丟出 `IsADirectoryError`（實跑，從命令列跑整支腳本：exit 1，stdout 沒有 `summary:`）。
  - `source` 寫成 `file:/etc/hosts/x`，把一個檔案當成目錄：`os.stat` 丟出 `NotADirectoryError`（實跑，呼叫 `check_logs`）。`check_logs` 只接 `OSError` 底下的 `FileNotFoundError` 與 `PermissionError`，`IsADirectoryError` 與 `NotADirectoryError` 都不是這兩個子類別。
  - `PATH` 上找到的同名檔案沒有執行權限、而 `PATH` 上沒有另一個可執行的同名檔案：`subprocess.run` 丟出 `PermissionError`，`Runner.run` 只接 `FileNotFoundError` 與逾時（實跑：`PATH` 只放一個權限 0644 的 `id`，`Runner().run("id")` 丟出 `PermissionError`）；經由命令列時的 exit 1 是讀碼。

  這個 exit 1 跟「至少一項 `WARN`」的 exit 1 相同，接上排程或告警的程式只看 exit code 時分不出兩者，要再看 stdout 有沒有 `summary:` 那一行（docstring 寫的「沒有印出 summary 代表腳本中途中止」）。替代的做法是在 `main` 外面包一層 `try`／`except`，把沒有接住的例外改回一個獨立的 exit code，這一版沒有實作。

### 各項檢查：ss 失敗、重複的項目名、loopback、特殊檔案、稀疏檔案與時間值

- **`updates/config` 的項目名重複**（實跑）：`config_files` 裡有一個檔案讀不到或格式錯時，`check_updates` 先以 `updates/config` 印一行 `WARN`，讀完其餘的檔案之後比對 `expect`，又以同一個項目名印一行。`build_record` 以項目名當鍵，結果檔只留後一行。實跑時一個沒有段名的設定檔加一個正確的設定檔：報告印 `WARN` 與 `PASS` 兩行 `updates/config`，結果檔裡這一項是 `PASS`，讀不到設定檔的那一筆 `WARN` 不在結果檔裡，下一次的差異段也比不到它。
- **會累積的資料裡的目錄與特殊檔案**（實跑）：`measure_paths` 只把一般檔案算進大小與最舊的修改時間，目錄本身的修改時間不算；socket 與 FIFO 既不算進大小，也不算成讀不到的路徑。實跑時一個只放了一個 FIFO 的目錄，量到的是總大小 0、沒有最舊的時間、讀不到的路徑 0 個；這種目錄設了 `retention_days` 時，理由印「最舊的檔案：沒有資料」（讀碼）。
- **全是空洞的稀疏檔案**（實跑）：`measure_paths` 在 `st_blocks` 是 0 時改用 `st_size`，整個檔案都是空洞的稀疏檔案因此被算成它的長度，跟用 `st_blocks` 量磁碟用量的做法相反。實跑時在 macOS 上用 `truncate` 建一個 10 MiB 的稀疏檔案，`st_blocks` 是 0，`measure_paths` 量到 10485760 位元組；檔案只要有一個資料區塊，`st_blocks` 就不是 0，量到的是佔用的區塊（讀碼）。這個退路的理由原始碼沒有寫，`limit_bytes` 因此可能被一個沒有佔用磁碟的檔案觸發 `WARN`。
- **`ss` 以非零結束**（實跑）：`listening_sockets` 回 `None`，主機上的每個入口印「讀不到監聽中的 socket」的 `WARN`，`listen-audit` 那一行整個不印。實跑時清單有一個主機上的入口，報告只有那個入口的 `WARN`；清單沒有 `where = "host"` 的入口時，報告裡一行跟 `ss` 有關的都沒有。前一次的結果有 `listen-audit` 那一項時，這一次的差異段印 `GONE listen-audit`（讀碼）。
- **同一個連接埠在兩個位址接聽**（實跑）：`audit_listening` 依協定、位址、連接埠各印一行，項目名只帶連接埠與協定；`0.0.0.0:111` 與 `[::]:111` 同時接聽時印兩行 `WARN`，項目名都是 `listen-audit/111/tcp`。`build_record` 以項目名當鍵，結果檔裡只留後一行，實跑時 `items` 裡只有一個 `listen-audit/111/tcp`；下一次的差異比的是留下的那一行。
- **IPv4 對映的 loopback 位址**（實跑）：`_is_loopback` 只認 `127.` 開頭與 `::1`，`[::ffff:127.0.0.1]` 回 `False`。一支程式在 IPv6 的 socket 上綁定 `::ffff:127.0.0.1` 時，`listen-audit` 把它當成 loopback 以外的接聽、印成 `WARN`（讀碼）。
- **時間值寫成 `0` 或 `n/a`**（實跑）：`parse_time` 對單獨的 `0` 與 `n/a` 回 `None`，兩個呼叫端的判法不同。`measure` 先把空的輸出與 `n/a` 判成「沒有時間值」，`0` 不在其中：`measure("age_days", "0")` 與 `measure("age_days", "LastTriggerUSec=0")` 都得到「輸出不是時間值」，那一項的理由指向腳本讀不懂格式。`check_accumulations` 只把空的輸出當成沒有資料：`oldest_command` 印 `n/a` 或 `0` 時，記一條「oldest_command 的輸出不是時間值」、那一項印 `WARN`，只有空的輸出印 `PASS`（「最舊一筆：沒有資料」）。重現時呼叫 `hc.Checker({}, <假的執行器>).measure("age_days", "0")`，或讓假的執行器對 `oldest_command` 回 `n/a`，再呼叫 `check_accumulations`。

### 結果檔：壞掉時的其他階段與兩次同時執行

- **結果檔壞掉時，其他階段的紀錄一起消失**（實跑）：`load_state` 讀到不是合法 JSON 的結果檔時回傳空的內容，`main` 寫回時只帶這一次的階段。實跑時用 `hc.main([..., "--state-file", <路徑>, "--phase", <階段>], runner=<假的執行器>)` 依序跑 `suspend` 與 `maintain`，結果檔的 `phases` 是 `maintain` 與 `suspend`；把結果檔改成一段沒有收尾的 JSON 之後再跑一次 `maintain`，stderr 印「讀不到或壞掉」的 `note:`，寫回之後 `phases` 只剩 `maintain`。
- **兩次執行同時寫結果檔**（讀碼）：`write_state` 沒有檔案鎖，兩次同時跑時各自讀到開始時的結果檔，後換名的那一次蓋掉先換名的那一次；兩次跑的是不同的 `--phase` 時，先寫完的那個階段的紀錄消失。替代的做法是在腳本外面用 `flock` 這類工具讓兩次執行排隊，這一版沒有實作。
