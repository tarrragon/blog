---
title: "主機維護清單寫成 TOML：JSON、YAML、TOML 的取捨、TOML 1.0 與 1.1 的版本差異、清單的欄位設計與只讀檢查腳本"
date: 2026-10-26
description: "把一台主機的維護、暫停與恢復上線項目寫成一份資料檔：這份清單對格式的需求、JSON、YAML、TOML 逐項比對（YAML 把 no 讀成 false、010 讀成 8 的實測，以及 TOML 照樣把 1.10 讀成 1.1）、TOML 的表格與表格陣列寫法、1.0 與 1.1 的解析器差異（Python tomllib 的 TOMLDecodeError）、欄位怎麼依檢查腳本與人的需要設計，以及只讀檢查腳本的白名單條件、輸出與 exit code"
weight: 3
tags: ["operations", "maintenance", "toml", "config", "python"]
---

這篇把 [長期上線主機的維護項目：會累積的資料、定期讀的 log、對外入口的盤點、安全更新、會到期的設定與檢查間隔的推算](/operations/09-host-lifecycle/long-running-host-maintenance/) 與 [服務暫停與恢復上線：只停服務、停止主機、終止主機到全部刪除各自保留的資源，暫停期間仍計費與仍被指向的資源，恢復前要查的漂移與恢復的順序](/operations/09-host-lifecycle/suspend-and-resume-service/) 要檢查的項目，寫成一份機器讀得懂、人也讀得懂的資料檔，並用一台實際的主機示範：為什麼要從文件改成資料檔；這份清單對檔案格式有哪些需求，以及 JSON、[YAML](/infra/knowledge-cards/yaml/)、TOML 逐項比對的結果（含 YAML 與 TOML 隱式型別的逐行實測）；清單用到的 TOML 寫法（表格、表格陣列、巢狀的表格陣列、寫在同一行的表格、兩種字串與 regex 的跳脫）；TOML 1.0 與 1.1 的差異，以及解析器版本對不上時的兩種結果；欄位依讀者分成檢查腳本要讀的與人要讀的兩類，各自怎麼設計；最後是讀這份清單的只讀檢查腳本，它的白名單要擋下哪些寫法才能保證不改動受檢查的設定與服務、哪些寫入白名單管不到而要靠系統層限制、輸出與 exit code 怎麼讀、結果檔怎麼跟上一次比對，以及它第一次在真主機上跑出的結果。TOML 的語法速查在 [TOML](/infra/knowledge-cards/toml/) 知識卡。示範用的清單（`host.toml`）與檢查腳本（`host-check.py`）放在作者的私有專案裡，完整內容沒有公開，本篇摘錄其中的段落，網域、IP 與帳號相關的值在摘錄裡用佔位值。同一份清單要套用到好幾台主機時，每台相同、依角色不同、每台不同的值怎麼分層，以及用 Ansible 的範本或 Terraform 的輸出產生每台清單的做法，在 [多台主機的維護清單：值的分層與合併的位置、用 Ansible 的 inventory 與範本產生每台的清單、由 Terraform 的輸出產生 inventory、跨主機執行的 exit code，以及單台清單的適用範圍](/operations/09-host-lifecycle/multi-host-manifest/)。

## 從維護文件改成資料檔

維護的項目寫在文件裡時，執行的人每次讀一遍、挑出這次要做的、照著執行；文件跟實際的檢查之間沒有任何機制保證一致：文件說 SSH 只放行管理者 IP，而沒有任何一條指令在檢查這件事。把項目寫成資料檔，同一份內容有兩個讀者：維護的人照註解讀每一段，檢查腳本照欄位執行主機上量得到的項目，把主機外的項目（雲端主控台上的規則、從另一台機器才量得到的入口）印成待人工確認。主機上量得到的那些項目，清單寫了什麼，腳本就檢查什麼；主機外的項目，腳本只負責每次都把它們列出來，確認仍然靠人。新增一個檢查項目，等於同時更新了文件與檢查。

示範清單涵蓋維護與暫停兩篇的主要項目：對外入口與每一層的防護、定期讀的 log 與它的計數門檻、會累積的資料與上限、檔案系統的剩餘空間、自動更新的設定，以及暫停與恢復上線的每一步；會到期的外部設定（憑證效期、CDN 位址段、管理者 IP）分散在入口與恢復上線的段落裡，syslog 的檔案與暫存檔沒有收進這份清單。項目的種類多、每一種的欄位不同，而且大部分是同一種項目列很多筆：示範清單裡有五個入口、六份 log、六類累積的資料、十六個暫停與恢復的步驟。

## 主機維護清單對檔案格式的需求：JSON、YAML、TOML 的比對

從清單的用途推出它對格式的需求：

- **可以寫註解**：清單的讀者有一個是人，每一段要寫出它是什麼、欄位怎麼讀；註解要跟資料寫在同一份檔案裡，分開放就會分歧。
- **型別由寫法決定**：門檻是數字、regex 與路徑是字串、開關是布林值；一個值被解析器讀成錯的型別時，檢查會照錯的值執行，而且不報錯。
- **同一種項目可以列很多筆**：每一筆有自己的一組欄位。
- **主機上不必另裝套件就能解析**：檢查腳本在主機上執行，主機上已經有的直譯器要讀得懂它。
- **巢狀不深**：清單的結構是「一類項目 → 很多筆 → 每筆幾個欄位 → 少數幾筆子項目」。

拿這幾項比對三種常見的設定檔格式：

| 需求                 | JSON              | YAML                                                 | TOML                                                                                 |
| -------------------- | ----------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------ |
| 註解                 | 不支援            | 支援                                                 | 支援                                                                                 |
| 型別由寫法決定       | 是，規則嚴格      | 不加引號的值由解析器推測，YAML 1.1 與 1.2 的規則不同 | 是；不屬於任何型別的寫法解析失敗，看起來像字串、卻剛好合乎某個型別的寫法照那個型別讀 |
| 同一種項目列很多筆   | 陣列              | 序列                                                 | 表格陣列 `[[名稱]]`                                                                  |
| 主機上的 Python 解析 | 標準函式庫 `json` | 要另裝 PyYAML 這類第三方套件                         | 3.11 起標準函式庫 `tomllib`；3.10 以下要另裝 `tomli`                                 |
| 巢狀很深時           | 括號多但結構清楚  | 縮排表示結構，深的時候最簡潔                         | 表頭要寫完整路徑，深的時候冗長                                                       |

型別由寫法決定這一項，兩種格式的差別要實測才看得清楚。用 PyYAML 6.0.3（實作 YAML 1.1）的 `safe_load` 解析下面這幾行：

```yaml
country: no
mode: 010
port_map: 22:22
version: 1.10
on: true
```

得到的是 `{'country': False, 'mode': 8, 'port_map': 1342, 'version': 1.1, True: True}`：`no` 被讀成布林值、`010` 被讀成八進位的 8、`22:22` 被讀成六十進位的 1342、`1.10` 被讀成浮點數 1.1，連鍵名 `on` 都變成了布林值 `True`。每一個值都解析成功，沒有任何錯誤訊息；`no` 被讀成 `false` 這一種，英文資料常稱為 Norway problem（挪威的國家代碼 `NO` 變成布林值）。放回這份清單：`firewall-cmd --query-service=https` 印出的是字串 `yes`，清單用 YAML 寫成 `expect_stdout: yes` 時，PyYAML 把值讀成布林值 `True`，跟輸出的字串比對永遠不相等，這一項每次都報警告；`billed_when_stopped: no` 也一樣被讀成 `False`。

同樣五個值寫成 TOML、不加引號，逐行各自交給 Python 的 `tomllib` 解析，結果是：兩個版本都報錯（`no`、`010`）、只有 TOML 1.1 的解析器接受並讀成另一個型別（`22:22`）、兩個版本都照合法的型別讀（`1.10` 讀成浮點數、`on` 是普通的鍵名）。表格的「同左」代表 3.15 的結果跟 3.12 相同：

| TOML 這一行        | Python 3.12（TOML 1.0）                                                                                                   | Python 3.15（TOML 1.1） |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| `country = no`     | `TOMLDecodeError: Invalid value`                                                                                          | 同左                    |
| `mode = 010`       | `TOMLDecodeError: Expected newline or end of document after a statement`（整數不允許前導零，解析器讀完 `0` 就結束這個值） | 同左                    |
| `port_map = 22:22` | `TOMLDecodeError`                                                                                                         | `datetime.time(22, 22)` |
| `version = 1.10`   | 浮點數 `1.1`                                                                                                              | 同左                    |
| `on = true`        | `{'on': True}`（`on` 是普通的鍵名）                                                                                       | 同左                    |

TOML 擋下的是不屬於任何型別的寫法（`no`、`010`），屬於另一個合法型別的寫法它照樣接受：`1.10` 是合法的浮點數，所以被讀成 1.1；`22:22` 在 TOML 1.1 是合法的時間（1.1 允許省略秒），所以 1.1 的解析器把它讀成時間 22:22。差別在範圍：YAML 1.1 的解析器會替幾乎任何不加引號的值找一個型別，TOML 只在寫法剛好合乎某個型別時才這樣做，其餘的拒絕整份檔案。由實測得出這份清單的寫法：版本號、時間字串、連接埠對應這類「看起來像數字或時間、內容是字串」的值，在兩種格式裡都一律加引號，不依賴解析器拒絕它。

YAML 1.2 把布林值限定成 `true` 與 `false` 及其大小寫變體，部分隱式型別的問題因此消失，但一份 YAML 檔被讀成哪個版本的規則，由讀它的解析器決定，寫檔的人控制不了。

由比對的結果，這份清單選 TOML：它滿足全部需求，付出的代價是巢狀的子項目要寫完整的表頭（`[[entrypoint.verify]]`），以及 Python 的標準函式庫只能讀、不能寫，要由程式產生 TOML 時得另裝套件。這個選擇有兩個前提：主機上的 Python 是 3.11 以上，以及清單巢狀不深、由人手動維護。RHEL 9、Debian 11、Ubuntu 22.04、Amazon Linux 2023 內建的 Python 更舊，在那些主機上 TOML 一樣要另裝 `tomli`：主機上可以裝套件，或可以把 `tomli` 這個純 Python 的套件跟檢查腳本放在一起部署時，仍然選 TOML；兩者都不行時選 JSON，人要讀的說明另外寫成一個欄位（例如每一筆的 `note`），讓說明跟資料仍然放在同一份檔案裡。巢狀很深（例如 Kubernetes 的 manifest）或要由程式大量產生時，YAML 或 JSON 會比較合適。

## 清單用到的 TOML 寫法

示範清單的頂層有這幾段：`[vars]`（主機上的路徑與網域，給其他欄位引用）、`[host]`（這台主機是什麼）、`[listen_audit]`（loopback 以外允許接聽的連接埠）、`[[entrypoint]]`（對外入口與每一層防護）、`[[log]]`（定期讀的 log 與計數門檻）、`[[accumulation]]`（會累積的資料與上限）、`[[filesystem]]`（檔案系統的剩餘空間）、`[updates]`（自動更新的設定）、`[[suspend]]` 與 `[[resume]]`（暫停與恢復上線的步驟）。

清單的每一類項目寫成一個表格陣列（array of tables），每一筆以 `[[類別]]` 開頭；這裡的表格（table）是 TOML 的一組鍵值，等於程式裡的一個物件，定義見 [TOML](/infra/knowledge-cards/toml/) 知識卡。一筆項目底下又有好幾筆子項目時，用巢狀的表格陣列。下面是示範清單對外入口那一段的節錄，原檔這個入口有五層防護，這裡只留兩層，`enforced_by` 也照節錄改成兩層：

```toml
[[entrypoint]]
name = "https"
port = 443
protocol = "tcp"
exposure = "cdn-only"
where = "host"
enforced_by = ["oci-nsg", "firewalld"]

  [[entrypoint.verify]]
  layer = "oci-nsg"
  where = "console"
  console_path = "OCI Console → Networking → Virtual cloud networks → <vcn> → Network security groups → <nsg> → Security rules"
  expect = "TCP 443 的 ingress 規則只有 Cloudflare 的 IPv4 位址段（每段一條），沒有 0.0.0.0/0"

  [[entrypoint.verify]]
  layer = "firewalld"
  where = "host"
  command = "firewall-cmd --query-service=https"
  expect_stdout = "yes"
```

`[[entrypoint]]` 每出現一次，就在 `entrypoint` 陣列裡加一筆；它下面的 `[[entrypoint.verify]]` 屬於最近的那一筆 `entrypoint`，所以每個入口各有自己的一組驗證方式。縮排只是給人讀的，TOML 不用縮排表示結構，縮排寫錯不改變解析的結果。兩層都有 `where`，意思不同：入口那一層的 `where = "host"` 代表接聽程式在這台主機上，腳本會確認有程序在聽這個連接埠；每一筆 `verify` 的 `where` 決定那一層防護由誰檢查。

只有幾個欄位的子項目可以寫成同一行的表格（inline table），例如暫停步驟裡確認資料庫完整的那一項：

```toml
verify = { command = "sqlite3 -init /dev/null -readonly -safe {{collector_db}} 'pragma quick_check'", expect_stdout = "ok" }
```

`{{collector_db}}` 是清單自己的替換語法，檢查腳本在執行前換成 `[vars]` 段寫的路徑；TOML 本身沒有變數，這兩個大括號在 TOML 看來只是字串裡的普通字元。清單改由 Jinja2 的範本（Ansible 的 `template` 模組）產生時，這個寫法跟範本自己的替換語法同形，產生的那一步會先處理它，處理方式見 [多台主機的維護清單：值的分層與合併的位置、用 Ansible 的 inventory 與範本產生每台的清單、由 Terraform 的輸出產生 inventory、跨主機執行的 exit code，以及單台清單的適用範圍](/operations/09-host-lifecycle/multi-host-manifest/)〈範本的 {{ }} 與清單自己的替換語法同形〉。TOML 1.0 的 inline table 要寫在一行內、結尾不能有逗號；1.1 放寬了這兩條，解析器版本不同時會怎樣，寫在〈TOML 1.0 與 1.1 的差異與解析器的版本〉。

字串有兩種寫法，差在跳脫：雙引號的基本字串（basic string）會處理反斜線跳脫，regex 裡的 `\.` 要寫成 `\\.`；單引號的字面字串（literal string）不處理任何跳脫，寫什麼就是什麼。清單裡的 regex 用基本字串寫成 `"(example\\.com|www\\.example\\.com)"`，解析出來是 `(example\.com|www\.example\.com)`。檢查腳本另外提供 `--set 名稱=值` 參數，讓維護的人在執行時覆寫清單 `[vars]` 段裡已有的值（`[vars]` 沒有那個名稱時，腳本把它判成清單格式錯）；這個值不經過 TOML 解析，腳本原樣代入，所以反斜線只寫一個。值經過 shell 傳給腳本時，雙引號裡的反斜線會被 shell 處理一次，經 SSH 在遠端執行時，本機與遠端的 shell 可能各處理一次，送進腳本的值會少掉反斜線；經 SSH 傳時，外層用雙引號、值本身用單引號包住，遠端的 shell 就不再處理裡面的反斜線。另一個要注意的是這個值被代入的位置：示範清單把 `host_re` 嵌進一條更長的 regex 中間（先跳過前面幾個以 tab 分隔的欄位，再比對 `Host` 那一欄），值本身帶了 `^`、`$` 錨點時，錨點出現在 pattern 的中間，一行都比對不到。要覆寫 regex 這類值時，先讀清單裡引用它的那一行，知道它被嵌在哪裡，再決定值要怎麼寫。

數字寫成整數時就是整數：位元組上限寫 `limit_bytes = 1073741824`，解析出來就是 Python 的 `int`，檢查腳本不必再轉型。TOML 1.0 允許用底線分隔位數（`1_073_741_824`），讓人讀得出數量級。

## TOML 1.0 與 1.1 的差異與解析器的版本

TOML 1.0.0 在 2021 年 1 月發佈，1.1.0 在 2025 年 12 月發佈。1.1 新增的語法有：inline table 可以跨行並在結尾加逗號、基本字串的 `\xHH` 與 `\e` 跳脫、時間可以省略秒。這些語法只有支援 1.1 的解析器讀得懂。Python 的 `tomllib` 在 3.11 加入時支援 1.0，3.15 起支援 1.1。

這個版本差異在開發機與主機的直譯器版本不同時出現，結果有兩種：

- **解析失敗**：同一行 `a = {x = 1, y = 2,}`，Python 3.15 解析成 `{'a': {'x': 1, 'y': 2}}`，Python 3.12 丟出 `TOMLDecodeError: Invalid initial character for a key part`。開發機是 3.15、主機是 Oracle Linux 10 內建的 Python 3.12 時，清單在開發機上測試通過，部署到主機之後解析失敗，腳本一項都不執行。
- **同一個值在一個版本報錯、在另一個版本被讀成別的型別**：〈主機維護清單對檔案格式的需求：JSON、YAML、TOML 的比對〉那張逐行解析表裡的 `port_map = 22:22`，Python 3.12 報錯，3.15 讀成時間。開發機是 3.15 時，作者在開發機上測不到任何錯誤，而 3.15 讀到的時間 22:22 本身也不是作者要的值（要的是字串 `"22:22"`）；換成兩邊都是 3.15 的環境，這個錯讀就一直不會被發現。

由此推出兩條寫法：清單照所有讀者裡最舊的那個解析器支援的版本寫（這次是 1.0），並在檔頭的註解寫明；測試時用那個最舊的版本實際解析一次。示範清單的單元測試另外用 `uv run --python 3.12` 解析清單，開發機的直譯器版本較新時，這一項會擋下 1.1 的語法。主機上用的是另外部署的 `tomli` 時，支援 1.0 還是 1.1 由 `tomli` 的版本決定，跟 Python 的版本無關（用 `a = {x = 1, y = 2,}` 實測，`tomli` 2.4.0 接受、2.3.0 拒絕），最舊的解析器就是部署上去的那個 `tomli`，測試時用同一個版本解析。

## 清單欄位的設計：檢查腳本要讀的與人要讀的

清單的每個欄位，讀者是檢查腳本或人。設計時逐個欄位先決定它的讀者，因為兩種讀者對欄位的要求不同：腳本要的是可以照著執行、可以比對的值；人要的是判斷時需要的脈絡。

**`where` 決定一個項目誰能檢查**：`"host"` 是主機上執行得了的只讀指令，腳本會執行它；`"external"` 要在主機外的機器上做（例如從開發機直連源站，確認繞過 CDN 時連不進來）；`"console"` 要在雲端主控台上看（Oracle Cloud 的網路安全群組 Network Security Group，簡稱 NSG，裡的規則、CDN 的 SSL 模式）。`external` 與 `console` 兩種，腳本只印出來，標成待人工確認。分出這個欄位，是因為入口的防護有幾層不在主機上（雲端的 NSG、CDN 的 SSL 模式），只從主機裡面量的話，雲端那一層的設定改了也看不出來。

**`enforced_by` 與 `verify` 互相對得上**：每個入口宣告它由哪幾層擋住，每一層至少要有一筆驗證方式，每一筆驗證的 `layer` 都要在 `enforced_by` 裡。腳本載入清單時比對兩邊，宣告了某一層而沒有寫怎麼驗證的、或寫了驗證而沒有宣告的，都算清單格式錯；同一層寫兩筆驗證是允許的。這條規則讓「這個入口有幾層防護」從一句宣稱變成每一層都可以查的事實。

**探針的欄位**（`command`、`expect_exit`、`ok_exit`、`expect_stdout`、`expect_contains`、`expect_not_contains`）描述一次檢查：執行什麼指令、什麼結果算通過。exit code 怎麼判通過分兩種情形：寫了 `expect_exit` 時，只有等於它的 exit code 算通過，`ok_exit` 不作用；沒有寫 `expect_exit` 時，exit code 落在 `ok_exit` 列的任何一個值都算通過，`ok_exit` 也沒有寫時只有 0 算通過。`ok_exit` 是為了 `grep -c` 這類指令而設的：找不到時它印 0、exit code 是 1，這是正常的結果，不是失敗。

**計數的欄位**（`measure` 與 `warn_above`）讓 log 的檢查變成數字的比對：探針的指令執行之後，`measure` 決定怎麼從輸出取出數字（`lines` 算非空行數、`value` 取印出的數值、`age_days` 算印出的時間距今幾天；輸出是 `鍵=值` 的形式時，`value` 與 `age_days` 取等號後面那一段，`systemctl show -p NRestarts` 印出的 `NRestarts=0` 就是這種），取出的數字大於 `warn_above` 時警告。清單在 log 那一段的註解寫明「門檻是第一次上線時的起點，不是量過的基準」：讀到警告的人要知道，門檻本身可能需要調整。

**只印不執行的指令寫在 `manual_command`**：`command` 一律會被執行，而且要通過白名單；只印給人讀、不執行的指令寫在 `manual_command`，清理資料的做法寫在 `purge_command`（只在那一項警告時印在同一行）。`manual_command` 出現在 `[[log]]` 段落本身（人讀那份 log 用的指令）、`[[suspend]]` 與 `[[resume]]` 的步驟（要人執行的動作），以及 `where` 不是 `"host"` 的 `[[entrypoint.verify]]`（在主機外做的確認）。欄位名分開的理由是讀清單的人只看一行就分得出 `command` 與 `manual_command` 會不會被執行：示範清單的第一版裡，會執行的指令與只印的指令都叫 `command`，一行 `command` 會不會被執行由它所在的段落決定；在 `[[entrypoint.verify]]` 這張表裡，同一個欄位名又依那一筆的 `where` 決定：`where = "host"` 的會執行，其他的只印。讀的人要記得這些規則才分得出來。改名之後，腳本在只印的位置讀到舊名 `command` 時判成清單格式錯（exit code 2），沿用第一版清單的人不會讓一行只印的指令被安靜地略過。`manual_command` 與 `purge_command` 寫的是清理資料與停止主機這類要人判斷時機的動作，腳本裡沒有執行這兩個欄位的程式碼。名字不帶 `manual_` 而會被執行的欄位還有兩個：會累積的資料用 `oldest_command` 查最舊一筆資料的時間，`[updates]` 用 `reboot_check` 查要不要重開機，兩者同樣在載入清單時比對白名單。

**允許「不知道」的值**：暫停步驟的 `billed_when_stopped` 欄位，除了 `yes`、`no`、`n/a` 之外，還允許 `unknown`；清單的註解約定，寫 `unknown` 時在 `billing_basis` 寫出要去哪裡查（腳本只檢查這個欄位存在）。只給是與否兩個值時，查不到答案的人只能二選一，寫進清單的就是一個猜測；有 `unknown` 這個值，查不到的項目留下的是一個待查的標記。這個欄位只描述停止主機這一種暫停範圍，終止主機或全部刪除時各項資源的去留與計費，要照 [服務暫停與恢復上線：只停服務、停止主機、終止主機到全部刪除各自保留的資源，暫停期間仍計費與仍被指向的資源，恢復前要查的漂移與恢復的順序](/operations/09-host-lifecycle/suspend-and-resume-service/)〈暫停期間仍在計費的資源〉逐項決定；要讓清單涵蓋其他範圍，欄位就要依範圍分開寫。

**清單沒有存的資料：上一次的結果**。維護時 access log 的計數要跟前一次比，恢復時要跟暫停之前的狀態比，而清單只描述「要檢查什麼、允許的範圍是什麼」，沒有任何欄位存上一次量到的值。這是刻意的：`tomllib` 只能讀不能寫，清單放在 repo 裡、只在有人改它時才改變，量到的值每次執行都不同，不屬於 repo。上一次的結果由檢查腳本寫進它自己的結果檔，預設是主機上的 `/var/lib/host-check/last.json`，不在 repo 裡；結果檔的格式與比對寫在〈只讀檢查腳本的白名單、輸出、exit code 與結果檔〉。結果檔只在同一個階段之間比較（這一次的維護跟上一次的維護比，這一次的恢復跟上一次的恢復比），所以要比暫停前後的入口與計數，暫停之前跑一次維護的檢查、恢復之後再跑一次，恢復後那一次的差異就是跟暫停前的比較。公開 IP、管理者 IP、憑證效期這類不是數字的值不在結果檔裡，要照 [服務暫停與恢復上線：只停服務、停止主機、終止主機到全部刪除各自保留的資源，暫停期間仍計費與仍被指向的資源，恢復前要查的漂移與恢復的順序](/operations/09-host-lifecycle/suspend-and-resume-service/)〈恢復上線前要重新確認的漂移〉另外記下來。

## 只讀檢查腳本的白名單、輸出、exit code 與結果檔

檢查腳本 `host-check.py` 只用 Python 標準函式庫（`tomllib`、`subprocess`、`shlex` 這類），在主機上以 root 執行，讀清單、執行 `where = "host"` 的項目、印出報告，並把這次的結果寫進自己的結果檔。腳本這一層能保證的範圍是不改動受檢查的設定與服務狀態：不改設定檔、不啟停服務、不安裝或移除套件、不刪資料。白名單上的工具自己照常寫的檔案不在這個範圍裡：在 Oracle Linux 10 的容器實測，`dnf -q history list` 與 `dnf needs-restarting -r` 每次都寫 `/var/log/dnf.log`、`dnf.librepo.log`、`dnf.rpm.log`、`hawkey.log` 與 `/var/cache/dnf/expired_repos.json`，加 `-C` 時仍寫那四份 log；`rpm -q` 會更新 rpm 資料庫的 `rpmdb.sqlite-shm`；`sqlite3` 讀一個 WAL 模式的資料庫時，資料庫旁邊的 `-wal` 與 `-shm` 檔不存在的話（服務停掉之後就是這個狀態）會把它們建出來。要讓這些寫入也不發生，得靠下面講的系統層限制，其中 dnf 要寫的整個 `/var/log` 與 `/var/cache/dnf` 是實測之後要刻意放行的兩個目錄。腳本這一層的保證靠的是三件事：

- **不經過 shell**：指令用 `shlex` 切成參數之後直接執行，沒有管線、轉向與命令替換，清單裡的字串在腳本這一層組不出第二條指令。白名單裡的工具自己仍可能有執行 shell 的選項：`rpm` 帶 `--pipe <指令>` 時，會把輸出交給 `/bin/sh` 執行那條指令，所以這一點要靠白名單的選項規則擋下。
- **執行任何一條之前先比對白名單**：清單欄位裡的指令，以及腳本自己用清單的值組出來的指令（用 `systemctl is-enabled <timer>` 與 `systemctl is-active <timer>` 查自動更新的排程、用 `journalctl -u <unit>` 查服務的紀錄、用 `ss` 列接聽的連接埠），都在載入清單時比對一次，執行前再比對一次。載入時有一條不符，整份清單算格式錯，一條指令都不執行：一條不符代表清單裡寫了一條白名單不認得的指令，可能是筆誤，也可能是有人寫進了會改動主機的指令，在分清楚之前，同一份清單的其他項目也不能信。代價是清單裡一個筆誤會讓全部檢查停掉，所以接上排程時要對 exit code 2 告警（見下面 exit code 那一段）。執行前那一次比對是保險，正常情形下載入時已經擋下；萬一它不通過，腳本立刻停下、以 exit code 2 結束，在它之前的指令已經執行過。
- **清理與暫停的動作只印出來**：它們寫在 `manual_command`、`purge_command` 這些給人讀的欄位裡，腳本裡沒有執行這些欄位的程式碼。

腳本這一層之外，另一種做法是在系統層限制腳本能碰到的範圍，有兩條路：用 systemd 的 service unit 或 `systemd-run` 執行腳本，由 systemd 在啟動程序之前套上檔案系統、網路與權限的限制；或不以 root 執行，改用專用帳號。兩條路都在一個以 systemd 257 為 init、用 `--privileged --cgroupns=private` 執行的 Oracle Linux 10 容器裡實測過。量之前先確認限制已經套上：`ProtectSystem=strict` 底下 `touch /var/x` 回 `Read-only file system`，`IPAddressDeny=any` 底下 `curl` 逾時（exit 28）。量測環境本身可能讓限制失效而不報錯：OrbStack 的 Linux machine 是 LXC 容器（`systemd-detect-virt` 印 `lxc`），systemd 在裡面沒有套上命名空間，也沒有印出任何錯誤或警告，`ProtectSystem=strict` 底下照樣寫得進 `/var`，在那種環境量到的是沒有限制的結果。

systemd 的限制用 `systemd-run` 套上的寫法如下，各屬性實測的效果列在後面的表裡：

```bash
# 以 root 執行；腳本與清單的路徑換成主機上實際的位置
systemd-run --wait --pipe --collect \
  -p ProtectSystem=strict -p 'ReadWritePaths=/var/log /var/cache/dnf' \
  -p StateDirectory=host-check -p StateDirectoryMode=0700 \
  -p NoNewPrivileges=yes -p PrivateTmp=yes -p IPAddressDeny=any \
  python3 <host-check.py 的路徑>
```

| 屬性                                                         | 實測的效果                                                                                                                                                                                | 要另外加的設定                                                                                                                                                   |
| ------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ProtectSystem=strict`                                       | 整個檔案系統唯讀。dnf 每次都要寫 log，`dnf needs-restarting -r` 以 exit 1 結束，錯誤是 `Read-only file system: '/var/log/dnf.log'`；`dnf -C check-update` 只用快取時同樣因為寫 log 而失敗 | `ReadWritePaths=` 放行 `/var/log` 與 `/var/cache/dnf` 之後 exit 0；只放行 `/var/log` 時改報 `/var/cache/dnf/metadata_lock.pid` 寫不進去；`/var/lib/dnf` 不必可寫 |
| `StateDirectory=host-check`                                  | 結果檔的目錄 `/var/lib/host-check` 可寫，其餘仍唯讀                                                                                                                                       | 目錄預設建成 0755，而且每次啟動都被改回 0755，腳本建目錄時給的 0700 只在目錄不存在時有效；加 `StateDirectoryMode=0700` 之後目錄 0700、結果檔 0600                |
| `NoNewPrivileges=yes`、`PrivateTmp=yes`、`IPAddressDeny=any` | 腳本不提權、不用 `/tmp`、不連網，對每一項檢查都沒有看得到的影響                                                                                                                           | 無                                                                                                                                                               |
| `PrivateNetwork=yes`                                         | `ss -tlnp` 只印出表頭，看不到主機上任何接聽的程式；四個入口的檢查全部變成 `WARN`，`listen_audit` 卻判成 `PASS`（一個 socket 都看不到，也就沒有多出來的連接埠）                            | 不開這一項；禁止對外連線由 `IPAddressDeny=` 負責                                                                                                                 |

其他工具在唯讀的檔案系統上：`rpm -q` 照常查得到，`rpmdb.sqlite-shm` 原本就在；`sqlite3 -init /dev/null -readonly -safe` 讀一個服務正在寫、`-wal` 與 `-shm` 都在的資料庫，照常讀得到。服務停掉之後那兩個檔被收掉，同一條指令以 `unable to open database file (14)` 失敗，因為它要建那兩個檔而檔案系統是唯讀的；暫停時停掉服務再跑的那一輪檢查就是這個情形，從這個 exit 14 推論那一項會是 `WARN`（實測只跑了單獨的 `sqlite3` 指令，沒有在服務停掉時跑整份清單）。沒有套限制時，同一條指令讀得到，代價是在資料庫旁邊建出 `-shm`（32768 位元組）與 `-wal`（0 位元組）。dnf 那兩個路徑是單獨對 `dnf needs-restarting -r` 量的；整份清單以 root 執行時只在沒有 `ReadWritePaths=` 與 `StateDirectoryMode=` 的設定下跑過（`StateDirectoryMode=` 在專用帳號那一組用過），那一次比沒套限制時多出的 `WARN` 只有 dnf 那一項，結果檔照常寫進 `StateDirectory`，第二次執行的差異段也照常印出。

接上限制之後，這一版的腳本有一個判定要另外讀：dnf 因為寫不了 log 而以 exit 1 結束時，`reboot_check` 把它印成「更新之後需要重開機」，dnf 的錯誤訊息沒有印出來。狀態是對的（`WARN`），理由是錯的，所以看到這一行時先確認 `ReadWritePaths=` 有沒有放行 dnf 的兩個路徑。這個判定與上面 `PrivateNetwork=` 的假 `PASS`，示範腳本的 repo 開了修正的工作項目，還沒修好。

專用帳號實測換回的範圍很小。以 `useradd -r` 建的帳號、加上 `systemd-journal` 與 `adm` 兩個群組執行，root 下 37 項 `PASS` 的那份清單只剩 29 項，其餘變成 `WARN`。讀不到的有：firewalld 的查詢（`firewall-cmd` 以 exit 253 回 `NotAuthorizedException`）、`sshd -T`（`/etc/ssh/sshd_config` 的權限是 0600）、服務的資料庫（所在目錄 0750）、放在 `/home/opc` 底下的建置產物（家目錄 0700）、nginx 的 log 目錄（0711，進得去、列不出檔名）；audit log 在這個容器裡沒有，沒量到，主機上它是 0600 root，從權限推論同樣要 root。資料庫、nginx 的 log 目錄與建置產物這三項讀不到的路徑，這一版的腳本印成「路徑不存在」，在同一個修正的工作項目裡。加了群組換回來的只有讀 journal 的兩項，而且前提是 `/var/log/journal` 的群組與 ACL 由 systemd-tmpfiles 設好：持久 journal 的目錄由 journald 自己建出時是 root:root、檔案 0640，`systemd-journal` 群組的 `journalctl` 回 `No journal files were opened due to insufficient permissions.`，跑過 `systemd-tmpfiles --create --prefix /var/log/journal` 之後才讀得到。限定指令的 sudoers 這一條走不通，是從腳本的結構推的，沒有實測：腳本直接執行白名單裡的指令、不經過 sudo，sudoers 只能授權整支 `python3 host-check.py`，範圍跟用 root 執行相同。

所以實測之後的做法是以 root 執行，外面套上上面那段 `systemd-run` 的屬性。換到的是：白名單解析錯了，指令照樣寫不進受保護的路徑、連不到外面，sqlite 的 `-shm` 這類工具自己的寫入也一起擋下；為了 dnf 刻意放行的是整個 `/var/log` 與 `/var/cache/dnf` 兩個目錄，nginx 這類其他服務的 log 也在 `/var/log` 底下，白名單漏掉的指令寫得進這兩個目錄裡的任何檔案（只放行 dnf 那四份 log 檔的寫法沒有實測）。兩層的分工是：白名單擋下清單裡寫錯或寫壞的指令，系統層限制擋下白名單漏掉的寫入；下面記的兩輪缺口每一個都是白名單漏掉的寫入或執行，所以只靠白名單時，保證的強度就是白名單解析的正確度。

白名單列的是允許的寫法，不在表上的一律拒絕。另一種寫法是列禁止的寫法：只擋已知會改變狀態的選項，其餘放行。列禁止的寫法要把工具現有的每一個會改變狀態的選項都列進去，漏一個就放行一個，工具日後新增的選項也會被放行；列允許的寫法沒有這個問題，代價是清單要用到新的選項時，得先把它加進白名單。白名單分三層比對：

- **執行檔的路徑**：指令的第一個參數只能是裸的工具名，或 `/usr/bin`、`/usr/sbin`、`/bin`、`/sbin` 底下的路徑。只比對檔名的話，`/tmp/evil/grep` 與 `./grep` 都會被當成 `grep` 放行，執行的是別的程式。裸的工具名依執行時的 `PATH` 找檔案，腳本又把呼叫者的環境變數傳給指令，所以腳本要經由 sudo（它的 `secure_path` 會重設 `PATH`）或 systemd 的 unit（環境是乾淨的）執行；從一個 `PATH` 被改過的 root shell 直接執行時，這一層擋不住 `PATH` 前面的同名檔案。
- **工具**：只有白名單上的工具可以執行。其中 `grep`、`wc`、`stat`、`du`、`df`、`test`、`id`、`uname`、`getenforce`、`sestatus`、`getsebool` 沒有寫檔或執行其他程式的選項（在 Oracle Linux 10 上逐支讀過 `--help`；`df --sync` 會先把快取寫回磁碟，不改任何檔案的內容），選項不另外比對；其餘的工具各自有選項的規則。
- **工具的選項**：有選項規則的工具，各自列出允許的子命令與選項，表外的拒絕；長選項的縮寫（`--cursor-fi` 這種只寫前幾個字元的寫法）也拒絕，因為 `journalctl` 這類工具接受沒有歧義的前綴，把 `--cursor-fi` 當成 `--cursor-file` 執行，只比對全名的規則會放行它。

選項要照工具自己的參數規則切分，比對的結果才可靠。`systemctl`、`journalctl`、`ss` 用 `getopt_long` 的語法；`rpm` 用 popt、`dnf` 與 `needs-restarting` 用 Python 的 argparse，這三支各自的解析器在下面這幾點的切法跟 `getopt_long` 相同。腳本對這六支用同一套切分：短選項可以合併（`-qa`）；需要帶值的選項，值可以直接接在選項後面（`-pX`），也可以是下一個參數；長選項寫成 `--名稱` 或 `--名稱=值`；`--` 之後全部是位置參數。示範腳本的第一版把第一個不以 `-` 開頭的參數當成子命令，這套切分規則一條都沒有用上，於是放行了兩種寫法：`systemctl -p show stop nginx` 被第一版判成子命令是 `show`，而 systemctl 自己解析時把 `show` 當成 `-p` 的值，執行的子命令是 `stop`；`dnf -x history -x list install <套件>` 裡，兩個 `-x` 各把 `history`、`list` 當成要排除的套件，第一版看到的是允許的 `history list`，dnf 執行的是 `install`。現在的版本先把每個選項連同它的值切出來，再判斷剩下的參數裡哪一個是子命令。其餘的工具各有自己的語法：`find` 的運算式不是選項語法，腳本逐個參數比對；`sshd`、`openssl`、`sqlite3`、`ausearch` 用單一連字號的長選項或自己的解析器，腳本逐個參數整字比對；`firewall-cmd` 逐個參數比對允許的樣式。各工具允許的寫法：

- **`systemctl`**：子命令只允許 `is-active`、`is-enabled`、`is-failed`、`show`、`status`、`cat`、`list-timers`、`list-units`、`list-unit-files`；需要帶值的選項只允許 `-p`／`--property`、`-P`、`-t`／`--type`、`--state`、`-n`／`--lines`、`-o`／`--output`、`--timestamp`。`-H`／`--host`（經由 `ssh` 在另一台主機上執行）與 `-M`／`--machine`（改在容器裡執行）不在表上，`--root`、`--user` 也不在。
- **`dnf` 與 `needs-restarting`**：`dnf` 只允許 `needs-restarting` 與 `history list`、`history info` 這幾個子命令，子命令之前只接受 `-q`、`-C`，子命令之後的選項只有 `needs-restarting` 的 `-r`、`-s`、`--reboothint`、`--services`；單獨呼叫的 `needs-restarting` 也只允許這四個。`-x`、`--setopt`、`--installroot`、`-y` 不在表上。
- **`rpm`**：第一個參數要是 `-q` 開頭或 `--query`（查詢模式），格式只能用 `--qf`／`--queryformat` 指定；`--pipe`、`--eval`、`-D`／`--define`、`--macros`、`--rcfile`、`--root`、`--dbpath` 不在表上。
- **`journalctl`**：需要帶值的選項只允許 `-u`、`--since`、`--until`、`-o`、`-g`、`-p`、`-t`，`-n` 的值可帶可不帶；`--cursor-file`（把這次讀到的位置標記 cursor 寫進指定的檔案）、`--vacuum-*`、`--rotate`、`--flush`、`-f` 不在表上。
- **`ss`**：只允許列出連線的選項（`-H`、`-l`、`-n`、`-t`、`-u`、`-a`、`-p`、`-4`、`-6` 這些），加上帶值的 `-f`／`--family`、`-A`／`--query`；`-K`（關掉符合條件的連線）、`-D`、`-N`（換到另一個網路命名空間）、`-F`（從檔案讀過濾條件）、`-r`（反查 DNS，會對外連線）不在表上。
- **`find`**：只允許比對條件（`-name`、`-path`、`-type`、`-mtime`、`-size`、`-user`、`-perm`、`-maxdepth` 這些）與 `-print`、`-print0`、`-printf`；`-delete`、`-exec`、`-execdir`、`-ok`、`-okdir`（執行指令或刪檔）與 `-fprint`、`-fls`（把輸出寫進檔案）不在表上。
- **`sshd`**：參數只能是單獨一個 `-T`（印出生效中的設定）；`-T -E <檔案>`（把 log 寫進那個檔案）、`-f`、`-o` 都拒絕。
- **`firewall-cmd`、`openssl`、`ausearch`**：`firewall-cmd` 只允許 `--query-*`、`--list-*`、`--get-*`、`--info-*`、`--state`，以及指定查詢對象的 `--permanent`、`--zone=`；`openssl` 只允許 `x509 -noout` 加上讀取憑證欄位的選項；`ausearch` 只允許篩選紀錄的選項（`-m`、`-k`、`-ts`、`-te`、`-i` 這些），`--checkpoint`（把讀到的位置寫進檔案）與 `-if`（改讀別的檔案）不在表上。
- **`sqlite3`**：一定要同時帶 `-init /dev/null`、`-readonly`、`-safe`，其餘只允許控制輸出格式與執行方式的選項（`-header`、`-csv`、`-json`、`-separator`、`-bail`、`-batch` 這些）；寫在 SQL 參數裡、以 `.` 開頭的 dot-command（`.shell`、`.output`）也拒絕，不只靠 `-safe`。理由寫在下面講 `sqlite3` 的那一段。

上面這份白名單是兩次測試修出來的。對第一版的白名單函式逐條測試、再在 Oracle Linux 10 容器裡實際執行，找到的缺口是：`systemctl -p` 與 `dnf -x` 這兩種沒有照參數規則切分而放行的寫法；`journalctl` 的規則是列禁止的寫法，漏了 `--cursor-file`；`rpm` 與 `sshd` 的規則只檢查第一個參數，`rpm -q <套件> --pipe <指令>` 會以 root 執行 shell 指令，`sshd -T -E <檔案>` 會建立那個檔案；`systemctl -H` 會讓 systemctl 執行 `ssh`，當時只讀了 man page、沒有實跑。修補時在同一種容器裡實測，在 `PATH` 放一個會記錄參數的假 `ssh`，`systemctl -H <使用者>@<主機> status nginx` 讓 systemctl 以 root 執行了 `ssh -xT -- <使用者>@<主機> systemd-stdio-bridge`；第一版只因為把分開寫的 `-H <主機>` 裡的 `<主機>` 當成子命令而拒絕了它，`-H<主機>` 與 `--host=<主機>` 都會放行。修補時另外找到三個缺口：`rpm` 的 `--eval "%(<指令>)"` 與 `-D` 會經由巨集執行 shell 指令，實測建立了檔案；執行檔的路徑沒有檢查，就是上面「執行檔的路徑」那一層；`sqlite3` 啟動時讀的 init 檔會在 `-safe` 生效之前執行，見下面講 `sqlite3` 的那一段。

除了執行檔的路徑那一個，這些缺口有同一個成因：寫規則的人以為工具會怎麼解析這串參數，工具實際照它自己的解析規則解析，而且支援執行其他程式與寫檔的功能。一支工具要列出哪些選項規則，看它有沒有這幾類功能：執行 shell 的選項或中介機制（巨集、管線、清單能指定的設定檔）、寫檔的選項或函式、執行其他程式或連到別台主機的選項，以及哪些選項需要帶值；這次選項層的缺口全部落在這幾類裡，有這類功能的工具照樣可以進白名單，選項規則要把那些功能排除在允許的寫法之外。另外兩類功能選項規則管不到，要靠上面講的系統層限制：工具不帶任何選項也會寫的檔案（dnf 的 log 與快取、資料庫的 `-shm` 檔），以及讀取本身就有副作用的對象（在接了 LDAP 這類目錄服務的主機上，`id <使用者>` 與 `stat` 查使用者名稱時會連到目錄伺服器；讀裝置檔、碰到自動掛載點會觸發動作；這兩種是從機制推的，沒有實跑）。

白名單防的是清單的內容，所以清單能指定的設定檔都要擋：`rpm` 的 `--macros`、`--rcfile`，`sqlite3` 的 `-init <檔案>`。root 自己擁有的預設設定檔不在白名單的防護範圍內：容器實測，在 `/root/.rpmmacros` 寫進一個 `%(touch <檔案>)` 巨集，`rpm -q bash` 就建出了那個檔案，跟 `sqlite3` 的 `~/.sqliterc` 是同一類；`openssl` 讀的 `openssl.cnf`、`dnf` 載入的 plugin 也一樣。能改這些檔案的人已經有 root 權限，用不著經過清單。`sqlite3` 要求 `-init /dev/null` 的主要理由是清單本身寫得出 `-init <檔案>`，順帶蓋過了 `~/.sqliterc`。執行檔的路徑那一個缺口的成因在工具這一層之前：規則只比對了檔名，沒有比對要執行的是哪一個檔案。示範腳本的修補對照每一個缺口寫了單元測試，在 Python 3.12 與 3.15 上各跑一次，兩個版本都全部通過。

`sqlite3` 執行 shell 與寫檔的途徑有三條：dot-command、SQL 函式與啟動時讀的 init 檔。`-readonly` 只讓資料庫檔案唯讀，`sqlite3` 的 dot-command（`.shell`、`.system`）照樣能執行 shell 指令，SQL 函式 `writefile()` 照樣能寫檔案系統；`-safe` 依 sqlite 的 CLI 文件會關掉除了指定資料庫檔案以外、所有可能改動主機的功能（`.shell`、`.system`、`.output` 這類 dot-command，`writefile()`、`readfile()`、`edit()` 這類 SQL 函式，以及 `ATTACH`），實測加上它之後 `.shell` 與 `writefile()` 都被拒絕。`-safe` 管不到的是啟動時讀的 init 檔：`sqlite3` 啟動時先執行 `-init <檔案>` 指定的檔案，沒有指定時執行執行者家目錄的 `~/.sqliterc`，兩者都在 `-safe` 生效之前執行，實測 init 檔裡的 `.shell touch <檔案>` 照樣建出了檔案。`-init /dev/null` 會取代 `~/.sqliterc`，寫在 `-readonly -safe` 之前或之後都擋得住；把 `HOME` 設成不存在的目錄擋不住，因為 `sqlite3` 先從系統的帳號資料庫（`/etc/passwd` 這一類，經由 `getpwuid()`）查執行者的家目錄，不看 `HOME`。白名單因此要求 `sqlite3` 同時帶 `-init /dev/null`、`-readonly` 與 `-safe`，`-init` 的值只接受 `/dev/null`。sqlite 的版本紀錄寫了 `--safe` 在 3.37.0 加入、3.40.1 修正成確實擋下 `writefile()` 這類 SQL 函式、3.41.0 再補強它擋下的危險 SQL 函式，所以較舊的主機認得這個選項，某些函式卻可能照樣執行得了：主機上的 sqlite 要是 3.41.0 以上（Debian 12 的 3.40.1 介於兩次修正之間），或在主機上對一個測試用的資料庫實際跑一次 `sqlite3 -init /dev/null -readonly -safe <資料庫> "select writefile('/tmp/x','a')"`，確認被拒絕（Oracle Linux 10 的 sqlite 3.46.1 符合）。

輸出每項一行 `PASS`、`WARN` 或 `MANUAL`，結尾印計數；exit code 0 代表沒有任何 `WARN`（只有 `PASS` 與 `MANUAL`），1 代表至少一項 `WARN`，2 代表清單格式錯。把格式錯與檢查失敗分成兩個 exit code，是因為兩者的處置不同：格式錯要改清單，檢查失敗要處理主機。把腳本接上排程或告警時，exit code 不是 0 就要告警：只對 1 告警的話，清單格式錯（2）的那段期間一項檢查都沒有跑，也收不到任何通知。`MANUAL` 不影響 exit code，所以主機外的項目永遠不會觸發告警；那些項目要另外排進維護時段。它們是有人隨時可能做的改動（在主控台改 NSG、改 CDN 的 SSL 模式），改變是[步階變化](/backend/knowledge-cards/step-change/)、沒有變化速度可算，檢查的間隔由能接受那個狀態持續多久決定，會造成對外暴露的要另外排定期比對，見 [長期上線主機的維護項目：會累積的資料、定期讀的 log、對外入口的盤點、安全更新、會到期的設定與檢查間隔的推算](/operations/09-host-lifecycle/long-running-host-maintenance/)〈檢查間隔與哪些項目改成自動處理的推算〉裡「改變是步階變化」的那一類；腳本只把它們印成 `MANUAL`，比對要由那個排程或維護的人做。

結果檔讓每一次的報告能跟前一次比。腳本用 `--phase` 指定這次跑的是維護（`maintain`，預設）、暫停（`suspend`）還是恢復（`resume`）的檢查，每次執行結束時，把這一次的結果寫進結果檔裡同一個階段的那一段，其他階段的紀錄不動：

```json
{"format": 1,
 "phases": {"maintain": {"finished_at": "2026-10-26T09:27:01.975703+00:00",
                         "manifest": "/path/to/host.toml",
                         "counts": {"PASS": 41, "WARN": 1, "MANUAL": 7},
                         "items": {"filesystem/root": {"status": "PASS", "value": 72560254976}}}}}
```

這段 JSON 是節錄：`items` 只留了一項，`manifest` 的路徑是佔位的值，`counts` 借用本節最後那台雲端主機修正之後再跑一次的結果，`filesystem/root` 的值取自下一段本機容器連跑兩次的第一次；實際的結果檔依鍵名排序、每層縮排兩格，這裡壓成幾行。`format` 是結果檔格式的版本號，腳本讀到不是 1 的版本時，把它當成壞掉的結果檔處理。`items` 每一項記下狀態與量到的數字，數字來自有 `measure` 的探針、會累積的資料的總位元組與檔案系統的可用位元組，其他項目是 `null`。

報告在每項的結果之後、計數之前，印出跟上一次的差異。第一行寫上一次的時間（`since: <上一次的 finished_at>`），之後每個不同的項目一行：狀態變了的印 `CHANGED <項目> WARN→PASS`，數字變了的印 `DELTA <項目> 舊值 → 新值（差）`，這次新增的與上一次有而這次沒有的項目各印 `NEW`、`GONE`。在本機的 Oracle Linux 10 容器裡連跑兩次，根檔案系統的可用空間印成 `DELTA filesystem/root 72560254976 → 72541392896（-18862080）`，也就是兩次之間少了 18862080 位元組（約 18 MiB）。結果檔裡沒有這個階段的上一次紀錄時（第一次執行、第一次跑這個 `--phase`、結果檔壞掉），這一段只印 `since: 沒有前一次的結果（<路徑>）`；兩次完全相同時印 `since: <時間>，與前一次相同`；帶 `--no-state` 時不印這一段。

結果檔預設在 `/var/lib/host-check/last.json`，`--state-file <路徑>` 換位置、`--no-state` 不讀也不寫。放在 `/var/lib` 而不放 `/run`，是因為 `/run` 在記憶體裡、重開機就清空，而停止主機再啟動等於重開機，放 `/run` 就比不到暫停前的紀錄；終止主機而不保留開機磁碟時 `/var/lib` 也一起消失，終止之前要把 `last.json` 拷出主機。腳本先把內容寫進同一個目錄裡的暫存檔並寫到磁碟，再用 `os.replace` 換上正式的檔名：同一個檔案系統裡的換名是一次完成的動作，所以程序在寫到一半時被中斷，正式的檔名仍然指著上一次的完整內容（中斷時可能留下一個暫存檔）。目錄以 0700、檔案以 0600 的權限建立，因為結果檔記著主機的連接埠、log 計數與磁碟用量，只給 root 讀。結果檔不是合法的 JSON、格式版本不認得、讀不到或寫不進去時（例如不是以 root 執行），腳本在 stderr 印以 `note:` 開頭的說明（讀與寫各一行），壞掉的檔案照常覆寫，exit code 照檢查的結果決定：結果檔是比對用的輔助資料，它出錯不代表主機有問題。

這支腳本先在開發機上的 Oracle Linux 10 容器裡測過，第一次在一台 Oracle Linux 10.2 的雲端主機上執行時，結果是 36 項 `PASS`、12 項 `WARN`、7 項 `MANUAL`。12 項 `WARN` 依成因分成四種：

- **主機的實際狀態跟清單不符**（8 項）：映像檔預設啟用的 `rpcbind`（111，TCP 與 UDP）與效能監測套件 PCP 的 `pmcd`（44321）、`pmlogger`（4330），在 IPv4 與 IPv6 的所有介面上接聽，它們不在清單預期的入口裡。從開發機對公開 IP 實測，TCP 的三個連接埠都連不上，UDP 111 用 `rpcinfo -u` 查詢得到逾時，雲端規則與主機防火牆都擋住了它們；開發機上測試用的容器映像檔沒有裝這幾個套件，所以在容器裡沒有出現。
- **紀錄的保存方式跟預期不同**（1 項）：腳本在 journal 裡找不到自動更新的執行紀錄，因為這台主機的 journal 只存在記憶體裡，在那次執行之前的重開機就清空了；成因與兩種狀態的差別見 [長期上線主機的維護項目：會累積的資料、定期讀的 log、對外入口的盤點、安全更新、會到期的設定與檢查間隔的推算](/operations/09-host-lifecycle/long-running-host-maintenance/)〈會累積的資料：寫入者、清理機制與磁碟寫滿的後果〉。
- **門檻把預期中的紀錄算進去**（2 項）：error log 裡那一行是 413 防護攔下過大的 body 時記下的正常紀錄，要改的是清單的計數條件。access log 的 `Host` 那一項有兩個成因疊在一起：部署腳本自己的 [冒煙測試](/testing/knowledge-cards/smoke-test/) 送出 `Host: 127.0.0.1`，讓計數本來就不是零，冒煙測試這個成因要改清單的計數條件（排除主機自己送的請求）；那一次執行又用 `--set` 傳了一個帶 `^`、`$` 錨點的網域 regex，這一項計數的是 `Host` 不是自己網域的行數，而錨點被嵌進 pattern 的中間之後，沒有一行比對得到自己的網域，於是 log 裡全部 130 行都被算成不是自己網域的請求。錨點造成的那一部分是執行時傳入的值寫錯了，改用清單裡的值就消失。
- **腳本自己的解析錯誤**（1 項）：systemd 回傳的時間格式（`Mon 2026-10-26 07:07:43 GMT`）腳本讀不懂。

主機的實際狀態與紀錄的保存方式，都是讀文件推不出、要在那台主機上量才知道的事；門檻的計數條件與腳本的解析錯誤，是清單與腳本第一次碰到真實資料時要修正的地方。四種成因的處置都不一樣，讀警告時，成因決定要改的是主機、清單還是腳本。這一次的處置是：部署腳本停用並遮蔽 `rpcbind` 與 PCP、把 journal 改存到磁碟，清單的兩個計數條件排除主機自己的請求與防護的正常紀錄，腳本補上 systemd 時間格式的解析。修正部署之後在同一台主機上再跑一次，結果是 41 項 `PASS`、1 項 `WARN`、7 項 `MANUAL`；剩下的那一項是自動更新的執行紀錄：自動更新上一次執行時，這台主機的 journal 還只存在記憶體裡，那一次的紀錄在之後的重開機被清掉，要等下一次排程執行才會在磁碟上的 journal 留下紀錄。
