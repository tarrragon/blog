---
title: "多台主機的維護清單：值的分層與合併的位置、用 Ansible 的 inventory 與範本產生每台的清單、由 Terraform 的輸出產生 inventory、跨主機執行的 exit code，以及單台清單的適用範圍"
date: 2026-10-26
description: "把單台的主機維護清單擴充到多台主機：每台相同、依角色不同、每台不同的值怎麼分層，合併放在部署時產生每台一份、由檢查腳本讀多份、依角色過濾還是執行時覆寫，用 Ansible 的 inventory、群組變數與範本產生 TOML 清單時的變數合併、兼任角色、型別、語法撞名、跳脫與產生時的驗證，由 Terraform 的輸出產生 inventory、terraform plan 能取代哪些主控台上的確認，對多台執行檢查腳本時 exit code 的讀法與執行身分的代價，以及單台清單夠用的條件"
weight: 4
tags: ["operations", "maintenance", "ansible", "terraform", "toml"]
---

這篇處理 [主機維護清單寫成 TOML：JSON、YAML、TOML 的取捨、TOML 1.0 與 1.1 的版本差異、清單的欄位設計與只讀檢查腳本](/operations/09-host-lifecycle/host-manifest-in-toml/) 那份單台清單要套用到好幾台主機時的做法：清單裡的值依「每台相同、依角色不同、每台不同」分類，以及每台各複製一份時，漏改的那一份為什麼沒有任何訊號；合併這些值的步驟可以放在部署時產生每台一份完整的清單、由檢查腳本自己讀多份檔案合併、一份清單裡的項目依角色過濾、或共用一份清單再由執行時的參數覆寫，各自的代價與適用的條件；用 [組態管理](/infra/knowledge-cards/configuration-management/) 工具 Ansible 的 inventory、`group_vars` 與 `host_vars`、Jinja2 範本產生每台清單的實測，包括變數合併的優先順序（同層的兩個群組依名稱排序，`ansible_group_priority` 要寫在 inventory 檔、寫在 `group_vars` 裡沒有效果）、兼任兩種角色的主機、YAML 把 `no` 讀成 `false`、用 `to_json` 把值寫進 TOML 時的跳脫與 BMP 以外字元被拒、範本的 `{{ }}` 與清單自己的替換語法同形時的兩種結果，以及在產生的那一步就驗證清單；主機由 Terraform 建立時，由它的輸出產生 inventory、再交給 Ansible 產生清單，以及這個做法對 autoscaling 的主機不成立的原因；清單裡要到雲端主控台確認的防火牆規則，`terraform plan` 比對得到與比對不到的範圍；用 Ansible 對多台主機執行檢查腳本時，`ansible` 指令的 exit code（2、4）與每台的 `rc` 怎麼讀、由 Ansible 執行時換來的安全代價；最後是單台清單夠用的條件與改成分層的時機。

Ansible 與 Terraform 的指令都在容器裡實跑過（ansible-core 2.17.7、Terraform 1.9.8），產生的清單用 Python 3.12 的 `tomllib` 解析過；主機的 IP 用文件保留的位址段（203.0.113.0/24）當佔位值。這篇的範本是簡化過的示範，確認的是清單解析得出預期的值；照檢查腳本實際要求的欄位寫範本、經由 SSH 部署到兩台容器、以 `-b` 與 `systemd-run` 執行 TOML 那一篇的只讀檢查腳本 `host-check.py`，以及跨主機的 exit code，在 [多台主機維護清單的實作紀錄：在容器上安裝 ansible-core 與 Terraform、由 Terraform 產生 inventory、用 Ansible 的範本部署每台的清單、以 sudo 與 systemd-run 執行檢查腳本，以及清理](/operations/09-host-lifecycle/hands-on/multi-host-manifest-walkthrough/) 實際走過一次。用 Ansible 管理主機上的套件與服務設定（playbook 與 role）不在這篇的範圍。

## 主機變成多台時清單裡的值：每台相同、依角色不同、每台不同

單台的清單裡每個值都只描述那一台主機；主機變成多台時，同一份清單的值依它跨主機的變化分成三類：

- **每台相同的值**：檢查項目本身、檢查腳本的白名單、log 的 regex、會累積的資料的檢查方式、暫停與恢復的步驟（TOML 那一篇示範清單的 `[[suspend]]` 與 `[[resume]]` 段）。這些描述的是「怎麼檢查」，跟主機是哪一台無關。白名單是檢查腳本允許執行的工具與每個工具允許的選項，腳本載入清單時逐條比對，有一條不符就把整份清單判成格式錯、一項都不執行；它的規則與比對方式寫在 TOML 那一篇的〈只讀檢查腳本的白名單、輸出、exit code 與結果檔〉。
- **依角色不同的值**：主機的角色決定它上面跑什麼服務，也就決定要檢查哪些入口與 log。跑 nginx 的 web 主機要檢查 443 與 80 的入口、讀 nginx 的 access log；跑 PostgreSQL 的資料庫主機要檢查 5432 只開放給管理者的來源（清單裡寫 `exposure = "admin-only"`）、讀資料庫的 log。TOML 那一篇示範清單的 `[[entrypoint]]`、`[[log]]` 與 `[listen_audit]` 段（loopback 以外允許接聽的連接埠）都是依角色不同的值。
- **每台不同的值**：主機名、公開 IP、網域、資料庫檔案的路徑、依這台的磁碟大小訂的剩餘空間門檻。

同一個值可以跨兩類：先給所有主機一個共用的預設，再由角色或某一台覆寫，〈用 Ansible 的 inventory、群組變數與範本產生每台的清單〉範例裡的剩餘空間門檻就是這樣，`all` 給 80、web 角色改成 85、`web1` 再改成 90。分類看的是一個值最後在各台之間有沒有不同、在哪一層開始不同。

一台主機屬於哪個角色，寫在主機清冊裡（Ansible 那一節的 inventory），不從主機的現況推。從現況推的做法（偵測到裝了 nginx 就套 web 的檢查）讓新主機不必登記就拿到檢查，代價是檢查項目由被檢查的狀態決定：nginx 被誤刪或沒裝上時，web 的檢查跟著消失，報告全部是 `PASS`，正好是清單要抓的那種故障看不見。

每台各複製一份完整的清單是最直接的做法，代價落在每台相同的值上：要修改一個共用的檢查（例如收緊白名單的一條規則、修正一條 regex），就要改每一份；漏改一份時，那台主機照舊跑舊版的檢查。沒有另外的一致性檢查時（例如在 repo 的 CI 裡用 `tomllib` 讀出各份清單、比對共用段落是否相同），報告裡沒有任何訊號顯示它的檢查比別台舊。所以多台主機的清單要讓三類值各自只寫一次，再在某一個步驟把它們合併成每台主機實際讀到的清單。

## 合併每台相同、依角色不同、每台不同的值的位置：部署時產生、檢查腳本讀多份、依角色過濾、或執行時覆寫

合併放在哪裡，決定了合併的結果有沒有寫成一份檔案、合併由哪個元件負責，以及檢查腳本要不要改：

- **部署時產生每台一份完整的清單**：共用的檢查寫成範本，依角色與主機的值逐台產生一份 `host.toml`，部署到主機上。主機上的檢查腳本照舊只讀一份檔案，不必改；載入時比對白名單的那一道檢查，比對的是最後實際要執行的清單；主機上那份檔案就是那台主機實際被檢查的內容，要知道一台主機檢查了什麼，讀那一份就夠。產生的工具可以是 Ansible（下一節），也可以是部署端的一支小程式：讀共用、角色、主機三份 TOML，合併成一個字典，再用 TOML 的序列化函式庫寫出（Python 的 `tomli_w`，不在標準函式庫裡），這樣寫出來的引號與跳脫由函式庫處理，下一節範本的跳脫問題不會出現（這支程式的寫法是推論，沒有實作）。代價有三項。一是多了一個產生的步驟。二是要決定產生出來的檔案放哪裡：不放進 repo 時，repo 裡只有範本與變數，要讀某一台的完整清單得先跑一次產生；放進 repo 時，每次改範本都要重新產生並一起提交，換到的是 code review 時看得到每台清單的 diff，所以審查的人要逐台確認改動範圍時放進 repo，主機多、每次改動都牽動每一份時不放。三是產生出來的清單一樣會變舊：部署時某一台連不上、用 `--limit` 只部署了一部分、新主機沒跑到部署，那台主機就照舊跑上一版的清單，報告裡仍然看不出它比 repo 舊。要讓這種落後看得見，在產生時把 repo 的 commit hash 寫進清單（例如 `[host]` 的一個欄位），或定期用 `--check --diff` 比對主機上的清單與範本算出來的內容（寫法在下一節）。
- **檢查腳本自己讀多份檔案合併**：主機上放一份共用的清單、一份角色的、一份主機自己的，腳本載入時合併。不必另外的工具，代價移到腳本身上：腳本要定義合併規則，同一個鍵出現在兩份檔案時誰勝出，表格陣列（`[[entrypoint]]` 這類）是接在後面還是整個取代。合併的結果只存在於腳本的記憶體裡，除非腳本另外把合併後的清單印出或寫進結果檔；沒有這一步時，規則寫錯或讀清單的人記錯規則，沒有一份檔案可以拿來對出一台主機實際檢查了什麼。白名單的比對要排在合併之後：比對排在合併之前時，比對的是合併前的片段，合併之後才組出來的指令、或被後一份檔案覆寫的值，沒有經過比對就被執行。
- **一份清單，項目依角色過濾**：所有主機讀同一份清單，每個依角色不同的項目標出它屬於哪些角色（例如 `roles = ["web"]`），腳本只執行符合這台主機角色的項目。只要過濾，不必定義覆寫的語意（誰蓋過誰、陣列接續還是取代），改一個共用檢查只改一份檔案，白名單比對的是整份清單，包括別的角色的項目。代價是腳本要改：TOML 那一篇的 `host-check.py` 沒有這個功能，要決定角色從哪裡來（寫在主機上的一個檔、或執行時傳入），每台的報告也會多出「略過」的項目。這是設計上的選項，示範腳本沒有實作。
- **共用一份清單，執行時覆寫**：主機上的清單每台相同，每台不同的值在執行時用參數覆寫。`host-check.py` 的 `--set 名稱=值` 取代 `[vars]` 段裡已經有的名稱（`[vars]` 沒有那個名稱時，腳本把它判成清單格式錯）；腳本讀清單時，把每一個字串欄位裡的 `{{名稱}}` 換成 `[vars]` 的值，所以 `[host]` 的主機名、網域、路徑這類字串欄位都能寫成 `{{名稱}}`、由 `--set` 給值。數字欄位（連接埠、剩餘空間的門檻）不經過替換，表格陣列裡有幾筆項目、陣列裡有哪些值，也不是一個字串，`--set` 改不到它們，表達不了「多一筆入口」這種結構上的差異。覆寫的值寫在每台主機執行檢查的排程指令上，要讀一台實際檢查了什麼，得同時讀清單與那台的排程設定。

選哪一個位置，看每台不同的值是什麼形狀，以及手上已經有什麼工具：

- **每台不同的只有字串（主機名、網域、路徑），而且所有主機的角色相同**：執行時覆寫最省事，不需要任何新工具，清單不必分層；代價是覆寫的值散在各台的排程裡。
- **角色不只一種，而每台不同的值只有字串**：依角色過濾加上執行時覆寫就夠，角色決定執行哪些項目，`--set` 給每台的字串；所有主機讀同一份清單，規則最少，前提是檢查腳本可以改（示範腳本沒有過濾的功能）。
- **每台不同的值有數字或結構（某一台的門檻、某一台多一個入口）**：過濾與覆寫都表達不了，剩下部署時產生與檢查腳本讀多份合併。已經有產生設定檔的工具（Ansible、Terraform），或檢查腳本是別人維護的、不能改時，用部署時產生，換到的是腳本不必改、每台的完整清單看得到；沒有任何產生工具時，部署時產生要另外付引進工具（學一個工具、多一個步驟與一份 inventory）或在部署端寫一支合併程式的成本，而讀多份合併把這份成本換成在檢查腳本裡寫並維護合併規則，所以檢查腳本可以改、又不想在部署端多一個步驟時，讀多份合併是剩下的那一個。
- **主機由 Terraform 建立**：它負責的是產生 Ansible 要讀的 inventory，清單仍由 Ansible 依範本產生（做法在〈主機由 Terraform 建立時由它的輸出產生 inventory〉）；Terraform 自己的 `templatefile()` 也能直接寫出每台的清單，放進主機的 user_data 時由 cloud-init 在第一次開機寫到主機上；代價是它只在建立主機時寫一次，之後改清單時，業者不是要重建主機、就是不再套用新的 user_data，主機上的清單就落後了（從 cloud-init 只在第一次開機執行的機制推論，沒有實測），所以會改的值仍要另一個部署步驟。

## 用 Ansible 的 inventory、群組變數與範本產生每台的清單

Ansible 從 inventory（主機清冊：列出受管主機與分組的檔案）讀出受管的主機與分組，變數依層次放在 `group_vars/` 與 `host_vars/` 兩個目錄，範本用 Jinja2 寫（Python 的範本引擎：`{{ }}` 代入變數，`{% %}` 寫迴圈與條件這類控制語法，`|` 把變數交給過濾器（filter）這類轉換函式）；inventory 的分層與合併規則在 [Configuration Management（組態管理）](/infra/knowledge-cards/configuration-management/) 卡。三類值的對應是：每台相同的值寫在範本本身與 `group_vars/all.yml`，依角色不同的寫在 `group_vars/<角色>.yml`，每台不同的寫在 `host_vars/<主機>.yml`。

```yaml
# inventory.yml：兩台 web 主機、一台資料庫主機
all:
  children:
    web:
      hosts:
        web1:
        web2:
    db:
      hosts:
        db1:
```

四個變數檔各自是一份檔案，檔名就是它所屬的群組或主機：

```yaml
# group_vars/all.yml：每台相同的預設值
disk_warn_percent: 80
collector_path: /var/lib/collector/monitor.db
country: no    # 刻意示範：這一行會被讀成布林值 false，見下文
```

```yaml
# group_vars/web.yml：web 角色的值；依角色不同的串列用帶角色名的變數名
disk_warn_percent: 85
web_listen_ports: [22, 80, 443]
web_entrypoints:
  - { name: https, port: 443, exposure: cdn-only }
  - { name: http, port: 80, exposure: cdn-only }
```

```yaml
# group_vars/db.yml：資料庫角色的值
db_listen_ports: [22, 5432]
db_entrypoints:
  - { name: postgres, port: 5432, exposure: admin-only }
```

```yaml
# host_vars/web1.yml：只有 web1 不同的值
disk_warn_percent: 90
```

一台主機最後拿到的值是各層合併的結果，`ansible-inventory -i inventory.yml --host <主機>` 印出合併之後的值。這次的結果：`web1` 的 `disk_warn_percent` 是 90（`host_vars` 蓋過 web 群組的 85），`web2` 是 85（web 群組蓋過 `all` 的 80），`db1` 是 80（db 群組沒有寫，沿用 `all`）。`country` 想寫的是挪威的國碼 `no`（例如給地理封鎖的設定用），三台讀出來卻都是布林值 `false`：`group_vars` 是 YAML，Ansible 照 YAML 1.1 的規則把不加引號的 `no` 讀成 false（YAML 的隱式型別見 [YAML](/infra/knowledge-cards/yaml/) 卡），產生出來的清單拿到 `country = false`。值要當字串用時寫成 `country: "no"`。

連接埠與入口的變數名帶著角色名（`web_listen_ports`、`db_listen_ports`），是為了一台主機同時屬於兩個角色的情形。兩個群組用同一個變數名時（例如都叫 `listen_ports`），把同一台主機同時放進 web 與 db 兩個群組實測，它拿到的是 web 的 `[22, 80, 443]`：同一層的群組依名稱的字母順序合併，排在後面的蓋過前面的，web 排在 db 後面。要指定誰優先，替群組設 `ansible_group_priority`（預設是 1，數字大的較晚合併而勝出）；這個變數寫在 `group_vars/db.yml` 裡沒有改變結果，寫在 inventory 檔裡 db 群組的 `vars` 底下（`db: {vars: {ansible_group_priority: 10}, hosts: …}`）之後，結果變成 db 的 `[22, 5432]`。這台主機兩組連接埠都要允許，而合併規則只會挑其中一組，兩個群組都定義的每一個變數都會這樣。在 `host_vars` 替它寫一份完整的值，等於又做出一份副本：web 角色的連接埠改了，這一份就是漏改而沒有訊號的那一份。所以依角色不同的串列，每個角色用自己的變數名，範本依這台主機所屬的群組（Ansible 的 `group_names`）取聯集：

```jinja
{% set eps = (web_entrypoints if 'web' in group_names else []) + (db_entrypoints if 'db' in group_names else []) %}
{% for ep in eps %}
[[entrypoint]]
name = {{ ep.name | to_json(ensure_ascii=False) }}
port = {{ ep.port }}
exposure = {{ ep.exposure | to_json(ensure_ascii=False) }}

{% endfor %}
```

同時屬於 web 與 db 的主機，產生出來的清單有三筆 `[[entrypoint]]`（https、http、postgres），只屬於 web 的主機有前兩筆，`tomllib` 讀出來都是表格陣列。每個角色的值仍然只寫在那個角色的變數檔裡一次。連接埠的聯集兩邊都有 22，串接之後要用 `unique` 去掉重複（寫法在下面的範本節錄）。聯集只適用於串列；兩個角色各自給了一個單一值（例如各自的剩餘空間門檻）時，範本要寫出取法（取嚴的那一個，`[web_disk_warn, db_disk_warn] | min`），或把那個值放在 `host_vars`，因為兼任的主機只有一台，它的單一值本來就屬於每台不同的值。入口與 log 這類「一串項目、每項幾個欄位」的值，用 `{% for %}` 逐欄輸出成表格陣列，不直接 `to_json` 整串：`to_json` 輸出的是 JSON 物件，TOML 讀不懂（下面〈值寫進 TOML 的方式〉那幾種結果的最後一項）。

Ansible 的 `template` 模組依範本把這些值寫進每台的清單。下面是範本 `host.toml.j2` 其餘段落的節錄（上面的 `[[entrypoint]]` 迴圈也在同一份範本裡）。段名沿用 TOML 那一篇的示範清單；段裡的鍵分兩類：`[host]` 的 `name`、`[vars]` 的 `collector_db`、`[[suspend]]` 的 `verify`、`command`、`expect_stdout`，以及 `[[entrypoint]]` 的 `name`、`port` 與 `exposure` 是那份清單的欄位（`[[entrypoint]]` 在那份清單裡另有 `protocol`、`where`、`enforced_by` 與各層的 `verify`，這裡省略），其餘的（`allowed_ports`、`[[filesystem]]` 的 `mount` 與 `warn_percent`、`[vars]` 的 `country`、`[[suspend]]` 的 `name`）是為了這裡的示範取的。所以這份範本示範的是值怎麼代入，不能直接配 `host-check.py` 使用，要換成那份清單實際的鍵名；那份清單另有必填的段落與欄位（`[host]` 的 `provider`、`region`、`role`，以及 `[[log]]`、`[[accumulation]]`、`[updates]`、`[[suspend]]`、`[[resume]]`），其中 `role` 是單一字串，兼任兩個角色的主機要把群組名串成一個值。照那份清單的欄位寫成的範本在 [多台主機維護清單的實作紀錄：在容器上安裝 ansible-core 與 Terraform、由 Terraform 產生 inventory、用 Ansible 的範本部署每台的清單、以 sudo 與 systemd-run 執行檢查腳本，以及清理](/operations/09-host-lifecycle/hands-on/multi-host-manifest-walkthrough/)〈變數檔與範本：檢查腳本實際要求的欄位、兼任兩種角色的主機〉：

```jinja
[host]
name = {{ inventory_hostname | to_json(ensure_ascii=False) }}

[listen_audit]
allowed_ports = {{ ((web_listen_ports if 'web' in group_names else []) + (db_listen_ports if 'db' in group_names else [])) | unique | to_json }}

[[filesystem]]
mount = "/"
warn_percent = {{ disk_warn_percent }}

[vars]
collector_db = {{ collector_path | to_json(ensure_ascii=False) }}
country = {{ country | to_json }}

[[suspend]]
name = "verify-db"
verify = { command = "sqlite3 -init /dev/null -readonly -safe {% raw %}{{collector_db}}{% endraw %} 'pragma quick_check'", expect_stdout = "ok" }
```

```bash
# 在執行指令的這台機器上，依 inventory 逐台產生清單（out/ 目錄要先存在）
ansible all -i inventory.yml -c local -m template \
  -a "src=host.toml.j2 dest=out/{{ inventory_hostname }}.toml"
```

`ansible` 指令直接執行單一模組（ad-hoc 指令），不必另外寫 playbook。指令裡要依環境換的位置：`all` 是要產生清單的主機範圍，可以換成一個群組名（`web`）；`src` 是範本的檔名；`-c local` 讓三台的檔案都寫在執行指令的這台機器上，`dest` 裡的 `{{ inventory_hostname }}` 由 Ansible 換成每台的主機名，所以每台各得到一份。要直接部署到各台主機時拿掉 `-c local`，Ansible 改成經由 SSH 連到每台主機；上面手寫的 inventory 只寫了主機名，Ansible 會拿 `web1` 當成連線的位址，所以每台要加上 `ansible_host: <IP 或 DNS 名稱>`，或讓 `~/.ssh/config` 有同名的 `Host`。同時，`dest` 改成檢查腳本在主機上讀清單的固定位置（絕對路徑）；保留相對路徑的話，檔案會寫在遠端的工作目錄底下。`template` 與 `copy` 不會建立 `dest` 的上層目錄，目錄不存在時實際執行以 `Destination directory … does not exist` 失敗，而 `--check` 的預覽報不出這個錯，所以部署時先用 `file` 模組建目錄。部署到兩台容器的完整 playbook 在 [多台主機維護清單的實作紀錄：在容器上安裝 ansible-core 與 Terraform、由 Terraform 產生 inventory、用 Ansible 的範本部署每台的清單、以 sudo 與 systemd-run 執行檢查腳本，以及清理](/operations/09-host-lifecycle/hands-on/multi-host-manifest-walkthrough/)〈部署清單：建目錄、copy 與 template、validate 改用檢查腳本的載入函式、--check 的預覽〉。

### 值寫進 TOML 的方式：直接輸出、to_json 與 ensure_ascii

Jinja2 把變數寫進檔案時，用的是 Python 的寫法，不是 TOML 的寫法；`to_json` 過濾器改用 JSON 的寫法輸出，而 JSON 的字串、數字、布林值與陣列 TOML 都讀得懂。範本裡的字串、布林值與陣列因此都經過 `to_json`，`warn_percent` 與 `port` 那幾行是整數，Python 與 TOML 的寫法相同，直接輸出也解析得出來。各種輸出方式的實測結果：

- **直接輸出 `{{ 變數 }}`**：布林值寫成 `False`，`tomllib` 在那一行報 `Invalid value`；字串不帶任何引號，一律解析失敗；字串陣列依內容選引號，`['nginx']` 被 TOML 當成字面字串（literal string）而讀得懂，同時含單引號與雙引號的值解析失敗，含反斜線的值（`C:\dir`）被寫成兩個反斜線，而字面字串不處理跳脫，解析出來的值安靜地多了一個反斜線。
- **`to_json`**：引號與反斜線被跳脫成 TOML 也接受的形式，`a"b\c.example` 輸出成 `"a\"b\\c.example"`，`tomllib` 解析回來是原本的字串。非 ASCII 字元被寫成反斜線加 `u` 與四位十六進位碼的跳脫：基本多文種平面（Basic Multilingual Plane，BMP，碼位 U+0000 到 U+FFFF）以內的中文照樣讀得懂；平面以外的字元（emoji、CJK 擴充 B 區的字）在 JSON 的 `\u` 跳脫裡要拆成兩個 16 位元的碼（surrogate pair），而 TOML 的 `\u` 只接受一個完整的 Unicode 碼位，拆開的半個碼位被 `tomllib` 以 `Escaped character is not a Unicode scalar value` 拒絕。
- **`to_json(ensure_ascii=False)`**：非 ASCII 字元原字照寫，上面幾種字串都解析得出來，範本裡的字串因此都用這個寫法。
- **`to_json` 遇到 TOML 沒有的值**：變數沒有設值時的 `null`，與值是字典時的 JSON 物件，`tomllib` 分別報 `Invalid value` 與 `Expected '='`。範本用到的變數都要在變數檔裡設值；字典與字典的串列照上面 `[[entrypoint]]` 的寫法逐欄輸出。

### 範本的 {{ }} 與清單自己的替換語法同形

示範清單用 `{{collector_db}}` 表示「執行前換成 `[vars]` 的 `collector_db`」，這個寫法跟 Jinja2 的替換語法同形，Ansible 產生清單時會先把它當成 Jinja2 的變數處理，實測有兩種結果：

- **產生失敗**：Ansible 沒有叫 `collector_db` 的變數時，那一台的產生停下來，訊息是 `AnsibleUndefinedVariable: 'collector_db' is undefined`。
- **安靜替換**：Ansible 剛好有一個同名的變數（例如在 `host_vars` 寫了 `collector_db: /srv/other.db`）時，產生成功，指令裡的 `{{collector_db}}` 被換成 `/srv/other.db`，清單的 `[vars]` 寫的卻是另一個路徑，報告看不出這兩者不一致。

兩種結果在產生的那一刻給的訊號不同：產生失敗讓產生停下來，安靜替換產生出一份看起來正確、卻檢查了另一個檔案的清單，所以安靜替換比較危險。範本裡把那一段包在 `{% raw %}` 與 `{% endraw %}` 之間，Jinja2 原樣輸出，產生的清單裡留著 `{{collector_db}}`，交給檢查腳本去換；上面的變數檔把 Ansible 這一端的變數取名 `collector_path`，跟清單的 `collector_db` 分開，也是為了避開同名。另一種避開撞名的做法是讓清單的替換語法換一個寫法（例如 `${collector_db}`，Jinja2 預設不處理），代價是改了既有清單與檢查腳本的格式。

### 產生時驗證清單與比對主機上的清單

上面的錯誤裡，布林值與字串直接輸出、`null`、字典、BMP 以外字元的跳脫這幾種會產生出解析不了的清單；另外三種產生出的清單解析得了、值卻是錯的（`country: no` 變成 `false`、字面字串多一個反斜線、`{{collector_db}}` 被安靜替換），`validate` 攔不到它們。解析不了的那幾種沒有攔下來的話，壞掉的清單照樣部署到主機，等下一次排程執行時，檢查腳本才以 exit code 2（清單格式錯）結束，那台主機在修好之前一項檢查都沒有跑。`template` 模組的 `validate` 參數在寫出檔案之前，先對暫存檔執行一條指令，指令失敗就不寫出：

```bash
# validate 的值是一條指令，%s 由 Ansible 換成暫存檔的路徑；參數用 JSON 形式傳，避免 key=value 寫法把指令裡的空白切開
ansible all -i inventory.yml -c local -m template -a '{"src": "host.toml.j2", "dest": "out/{{ inventory_hostname }}.toml", "validate": "python3 -c \"import tomllib,sys; tomllib.load(open(sys.argv[1],'"'"'rb'"'"'))\" %s"}'
```

實測的結果：範本產生出 `flag = True` 這種 TOML 讀不懂的值時，那一台以 `failed to validate` 失敗，訊息帶著 `TOMLDecodeError: Invalid value`，目的地沒有寫出任何檔案；範本正常時照常寫出。用 `tomllib` 當 `validate` 只驗得到 TOML 的語法；清單的欄位與白名單是否符合，要讓檢查腳本自己讀一次才知道。檢查腳本的 `load_manifest()` 只載入與驗證清單、不執行任何檢查，用 Python 的 `runpy` 載入腳本再呼叫它當 `validate` 時，`exposure` 寫了不在允許值裡的值那一台以 `failed to validate` 失敗，主機上的清單維持舊版；`validate` 的完整寫法與載入方式的取捨在 [多台主機維護清單的實作紀錄：在容器上安裝 ansible-core 與 Terraform、由 Terraform 產生 inventory、用 Ansible 的範本部署每台的清單、以 sudo 與 systemd-run 執行檢查腳本，以及清理](/operations/09-host-lifecycle/hands-on/multi-host-manifest-walkthrough/)〈部署清單：建目錄、copy 與 template、validate 改用檢查腳本的載入函式、--check 的預覽〉。

主機上的清單跟範本算出來的內容是否一致，用 `--check --diff` 比對：`ansible <主機> -i inventory.yml -m template -a "src=host.toml.j2 dest=<清單的路徑>" --check --diff` 不寫任何檔案，只印出兩者的差異。實測時先把產生好的檔案手改成別的內容，這條指令印出 `--- before` 與 `+++ after` 兩邊的差異行、把那一台標成 `CHANGED`，檔案維持手改後的內容。定期對所有主機跑一次，標成 `CHANGED` 的那幾台，就是清單落後於 repo、或在主機上被改過的主機。這條指令有主機標成 `CHANGED` 時，`ansible` 的 exit code 仍是 0，所以接上排程時要讀輸出裡的 `CHANGED`，不能只看 exit code（對兩台容器經由 SSH 實測，在其中一台手改清單之後）。

## 主機由 Terraform 建立時由它的輸出產生 inventory

主機由 Terraform 建立、而且每台主機各自是 Terraform 的一個資源時，它的 [State（IaC 狀態檔）](/infra/knowledge-cards/state/) 已經記著每台主機的 IP；inventory 另外手寫一份的話，新增或刪除主機時要改兩個地方，漏改的那一份就指著不存在的主機，或漏掉新的主機。由 Terraform 的輸出產生 inventory，主機清冊就只剩一個來源，Ansible 再讀這份 inventory 產生每台的清單。下面的設定用 `locals`（設定檔內部的具名常數）代替實際的主機資源（實際的設定裡，IP 來自主機資源的屬性，例如 Oracle Cloud 的 `oci_core_instance` 的 `public_ip`），每台主機的角色寫成串列，用 `local_file` 寫出 inventory：

```hcl
locals {
  hosts = {
    web1  = { roles = ["web"], public_ip = "203.0.113.10" }
    db1   = { roles = ["db"], public_ip = "203.0.113.20" }
    both1 = { roles = ["web", "db"], public_ip = "203.0.113.30" }
  }
}

# 依角色分組，寫出 Ansible 讀得懂的 inventory.yml
resource "local_file" "inventory" {
  filename        = "${path.module}/inventory.yml"
  file_permission = "0644" # 預設值是 "0777"，實際權限再扣掉建立檔案那個程序的 umask
  content = yamlencode({
    all = {
      children = {
        for role in distinct(flatten([for h in values(local.hosts) : h.roles])) :
        role => { hosts = { for name, h in local.hosts : name => { ansible_host = h.public_ip } if contains(h.roles, role) } }
      }
    }
  })
}

output "hosts" { value = local.hosts }
```

`yamlencode` 那一段的兩層 `for`：外層把每台主機的角色串列攤平、取出不重複的角色（`web`、`db`），每個角色成為 `children` 底下的一個群組；內層把角色串列裡含有這個角色的主機收進那個群組的 `hosts`，每台帶上自己的 `ansible_host`（Ansible 連線時用的位址）。`terraform apply` 之後，`inventory.yml` 裡 `both1` 同時出現在 db 與 web 兩個群組，上一節的範本就會替它取兩個角色的聯集。角色寫成單一字串時（`role = "web"`），一台主機只會進一個群組，兼任的主機拿不到另一個群組的任何變數，那個角色的入口與 log 整組不在它的清單裡，而且不會報錯。

`ansible-inventory -i inventory.yml --graph` 列出的分組跟 `locals` 一致；`terraform output -json hosts` 印出同一份資料的 JSON，給 Ansible 以外的工具讀。這份 inventory 是 Terraform 管理的一個資源（`local_file`），它的內容記在 State 裡：手動在檔案末端加一行之後，`terraform plan` 回報 `local_file.inventory will be created`，下一次 `apply` 會把檔案重新寫回 Terraform 算出的內容，手加的那一行消失。plan 寫的是 `will be created` 而不是修改：`local_file` 讀取時發現檔案內容跟 State 記的不同，就把這個資源當成不存在，計畫裡改成重新建立（這是從 plan 的訊息推論的機制）。所以每台不同的值裡，Terraform 知道的那幾個（IP、角色）由它產生，其他的（資料庫路徑、門檻）寫在 Ansible 的 `host_vars`，兩邊各管各的，不在產生出來的檔案上手改；仍有變數要靠 `ansible_group_priority` 決定哪個群組勝出時，inventory 改由 Terraform 產生之後，它要寫進 `yamlencode` 裡那個群組的 `vars`；兼任兩種角色的主機照 Ansible 那一節的聯集寫法，不靠優先順序。

這個做法的前提是每台主機都在 State 裡。由 autoscaling 群組或 instance pool 依流量開關的主機，Terraform 只宣告群組本身，個別主機由業者的服務建立與刪除，不在 State 裡，從 State 產生的 inventory 是空的、或一直落後於實際的主機。這一類主機多半是同一個角色、彼此可以互相取代，每台不同的值只剩主機名這類字串，比較貼近〈合併每台相同、依角色不同、每台不同的值的位置〉的執行時覆寫：同一份清單放進主機的映像檔，或在開機時寫入，主機名由執行時的參數給（這是從機制推出的做法，沒有實測）。這類主機生命週期短，結果檔裡常常沒有上一次的紀錄可比，跨主機的比較要交給監控。

`local_file` 寫出的 inventory 只存在執行 `apply` 的那台機器上。團隊共用 remote backend 的 State、或在 CI 上跑 `plan` 時，那台機器的工作目錄裡沒有這個檔（或內容不同），每一次 `plan` 都回報 `local_file.inventory will be created`；〈清單裡要到主控台確認的項目與 terraform plan 的比對範圍〉用 `plan` 偵測防火牆規則的漂移時，同一份 State 的 `plan` 因此永遠不是 `No changes`，漂移告警不是一直響、就是被忽略。這種情形下改用直接讀 State 的 inventory plugin（Ansible 的 `cloud.terraform` collection 的 `terraform_state`），inventory 不寫成檔案，每次執行時從 State 讀出主機（依那個 collection 的文件推論，沒有實測）；`local_file` 適合只有一個人、在同一台機器上 `apply` 與執行 Ansible 的情形。

## 清單裡要到主控台確認的項目與 terraform plan 的比對範圍

TOML 那一篇的清單裡，`where = "console"` 的項目（雲端的網路安全群組（Network Security Group，NSG）規則，概念見 [Security Group](/infra/knowledge-cards/security-group/)）只印出來、等人到主控台確認。主機與防火牆規則都由 Terraform 建立時，那些規則的宣告就在 Terraform 的設定裡，[`terraform plan`](/infra/knowledge-cards/terraform-plan-apply/) 會比對 State 裡每個資源的屬性跟雲端的實際值，有人在主控台改了某一條由 Terraform 建立的規則，plan 會列出差異（[Drift（設定漂移）](/infra/knowledge-cards/drift/)）。plan 看不到的是 State 裡沒有的資源：規則在 Terraform 裡寫成各自獨立的資源時（Oracle Cloud 的 `oci_core_network_security_group_security_rule` 是一條規則一個資源），有人在主控台另外新增一條規則，那一條不在 State 裡，plan 照樣回報 `No changes`。所以 plan 能取代的是確認既有的規則沒有被改，確認沒有多出來的規則仍然要列出雲端上的規則跟宣告比對。這是從 plan 的比對機制推出的做法，這次沒有對雲端的防火牆規則實測。

## 用 Ansible 對多台主機執行檢查腳本：整批的 exit code、每台的 rc 與執行身分的代價

清單部署到各台之後，檢查腳本可以照舊由每台自己的排程執行，也可以由 Ansible 對整個 inventory 一次執行。exit code 的讀法用一條會依主機名回不同 exit code 的指令（web1 回 0、web2 回 1、db1 回 2）在容器裡實測：

```bash
# 實測用的指令：-c local 在執行指令的這台機器上跑，-o 讓每台的結果印成一行
ansible all -i inventory.yml -c local -m command \
  -a "sh -c 'case {{ inventory_hostname }} in web2) exit 1;; db1) exit 2;; esac'" -o
```

輸出裡 web1 標成 `CHANGED`，web2 與 db1 標成 `FAILED!`，各自的 `"rc"` 欄位是 1 與 2；`ansible` 指令本身的 exit code 是 2，依 Ansible 的文件，這個值代表至少一台主機的任務失敗，跟失敗的是哪一台、各自回了什麼 `rc` 無關；有主機連不上時這個值是 4（停掉一台容器實測）。所以接上排程時，告警的條件寫成 `ansible` 的 exit code 不是 0，再讀每台的 `rc` 決定處置；連不上的主機標成 `UNREACHABLE!`、沒有 `rc`，處置是查連線與 SSH，跟清單或主機上的檢查無關。換成檢查腳本時，它的 exit code 1（至少一項 `WARN`）與 2（清單格式錯）在 Ansible 的輸出裡同樣標成 `FAILED!`，兩者的處置不同（處理主機或改清單），要讀每台的 `rc` 才分得開；`command` 模組每次執行都回報 `CHANGED`，這個字不代表主機被改動，只代表指令執行了。

換成檢查腳本時，執行的身分與限制要跟單台時相同：TOML 那一篇的腳本以 root 執行，並套上 `systemd-run` 的檔案系統與網路限制。Ansible 經由 SSH 登入的帳號不是 root，要加 `--become`（`-b`）讓 Ansible 在主機上經由 sudo 切成 root：

```bash
# 部署後對每台執行檢查；systemd-run 的屬性照 TOML 那一篇〈只讀檢查腳本的白名單、輸出、exit code 與結果檔〉
ansible all -i inventory.yml -b -m command \
  -a "systemd-run --wait --pipe --collect -p ProtectSystem=strict ... python3 <host-check.py 的路徑> --manifest <清單在主機上的路徑>" -o
```

`...` 是 TOML 那一篇那段 `systemd-run` 的其他屬性，`<host-check.py 的路徑>` 與 `<清單在主機上的路徑>` 換成部署時放檔案的位置。不加 `-b` 時，這條指令裡的 `systemd-run` 以登入帳號執行，以 `Access denied` 失敗、`rc` 是 1，跟檢查腳本至少一項 `WARN` 的 `rc` 相同；兩者要看輸出裡有沒有檢查腳本結尾的 `summary:` 那一行才分得開（[多台主機維護清單的實作紀錄：在容器上安裝 ansible-core 與 Terraform、由 Terraform 產生 inventory、用 Ansible 的範本部署每台的清單、以 sudo 與 systemd-run 執行檢查腳本，以及清理](/operations/09-host-lifecycle/hands-on/multi-host-manifest-walkthrough/)〈以 -b 與 systemd-run 執行檢查腳本：每台的輸出與 ansible 的 exit code〉）。拿掉 `systemd-run`、以登入帳號直接執行腳本時，腳本讀不到 firewalld、sshd 設定與幾個目錄：那一篇用加了 `systemd-journal` 與 `adm` 群組的專用帳號實測，`PASS` 的項目從 37 項掉到 29 項；沒有這兩個群組的登入帳號另外讀不到 journal（實作紀錄的同一節）。sudo 要不要密碼依主機的 sudoers 設定而定，要密碼時的兩種給法（`-K` 在執行時輸入、放進 Ansible Vault 加密的變數）在實作紀錄〈受管主機與控制端的容器：Oracle Linux 10 加 systemd 與 sshd、python:3.12-slim 加 ansible-core 與 Terraform〉。

由 Ansible 加 `-b` 執行的代價是安全上的：執行 Ansible 的那台機器（控制端）要握有能 SSH 登入每台主機、再經由 sudo 切成 root 的憑證。單台時，檢查是主機自己的 timer 以 root 在本機執行，沒有任何一個地方拿得到所有主機的 root；改由 Ansible 集中執行之後，控制端被入侵就等於每台主機都被入侵，檢查腳本「不改動主機」的保證管不到這一條路。縮小這個範圍的做法有三種，都沒有實測：

- **每台照舊用自己的 timer 執行，集中的只有結果**：結果檔的目錄是 `StateDirectoryMode=0700`、擁有者是 root，不帶 `-b` 的帳號讀不到；要讓控制端用一般帳號讀，得把那個目錄改成 0750 並給一個讀取用的群組，或由監控在主機上收集結果再送出去。
- **sudoers 只允許那一條檢查指令**：Ansible 的 become 會把指令包成 `/bin/sh -c '…'` 再交給 sudo，限定指令的 sudoers 對不上，所以執行檢查時不加 `-b`，在 `command` 模組裡自己寫 `sudo -n systemd-run …`；部署用另一個帳號與另一把金鑰，只在部署時使用。排程用的那把金鑰被偷時，拿到的只是以 root 執行檢查（從 become 的機制推論）。
- **ansible-pull**：每台定時從 repo 拉 playbook，在本機產生自己的清單並執行檢查，沒有任何一個地方握有所有主機的 root；代價是每台主機要裝 Ansible、要有讀 repo 的憑證，而且主機要知道自己屬於哪些角色。

每台主機的結果檔照舊留在那台主機上（`/var/lib/host-check/last.json`），每台跟自己的上一次比較；腳本不比較同一個角色的不同主機（web1 的 access log 計數遠高於 web2 這類），這種跨主機的比較要把每台的數字收集到一個地方，那是監控的範圍，各主機的指標怎麼收集見 [多台主機的指標收集：讀取架構、主機標籤、目標清單、監控主機的位置與主機消失的偵測](/backend/04-observability/vendors/prometheus/multi-host-scraping/)。

## 單台清單夠用的條件與改成分層的時機

判斷要不要分層，數的是 repo 裡內容不同的清單有幾份，不是主機有幾台：二十台主機都是同一個角色、每台不同的只有主機名時，一份清單部署到每台、主機名用執行時覆寫，repo 裡只有一份，不需要分層；二十台裡只要有一台的門檻不同，內容不同的清單就變成兩份以上，回到下面的判斷。

內容不同的清單有好幾份時，漏改的代價由兩件事決定，兩件事要分開看：

- **漏改的次數**：一年裡累計要改的份數（一次修改要改的份數乘上一年改幾次），每一份都是一次可能漏改的機會。兩份清單、每週改一次，一年要改一百多份；十份清單、一年改一次，一年改十份。
- **漏改之後持續多久**：漏改的那一份不會讓任何檢查失敗，只會讓那台主機繼續跑舊的檢查，直到有人下一次修改它、或一致性檢查比對到它為止。十份清單、一年改一次時，次數少，可是漏改一份就有一台主機安靜地跑舊檢查到下一年。

改成分層的查得到的時機是下面兩者之一：一次修改要改的份數，多到改的人沒辦法在同一次提交裡逐份確認每一份都改了（要另外記「哪幾台已經改了」）；或 repo 已經需要一致性檢查（CI 裡比對各份清單共用段落的那一道）才知道有沒有漏改。兩份清單、每週改一次，每次只改兩份、同一次提交裡看得完，次數多而每一次都確認得了，不分層也行，代價是每週改兩次；十份清單、一年改一次，次數少而每次要確認十份、漏改會持續一年，到了需要一致性檢查的程度，改成分層的成本比加一道檢查低或相近。

主機由 Terraform 這類工具建立、而且每台主機都在 State 裡時，主機清冊的來源已經是 Terraform，inventory 由它產生；這時每台的清單也一起交給產生的步驟。repo 裡只有一份共用清單、每台只差主機名時，交給產生步驟的是每台的覆寫值，不是整份清單，上面「不需要分層」的判斷照樣成立。手寫的清單不會隨 Terraform 新增或刪除主機而增減，新開的主機沒有清單、已刪除的主機還留著一份，而清單與主機的對應只能靠人記得，所以 Terraform 每增刪一次主機，手寫的清單就有一次對不上的機會。

## 延伸閱讀：單台清單的格式與檢查腳本、維護項目、組態管理與 IaC 的卡

- [主機維護清單寫成 TOML：JSON、YAML、TOML 的取捨、TOML 1.0 與 1.1 的版本差異、清單的欄位設計與只讀檢查腳本](/operations/09-host-lifecycle/host-manifest-in-toml/)：本篇沿用的段名、`{{名稱}}` 的替換語法與 `--set`、檢查腳本的白名單、exit code、結果檔與 `systemd-run` 的限制
- [長期上線主機的維護項目：會累積的資料、定期讀的 log、對外入口的盤點、安全更新、會到期的設定與檢查間隔的推算](/operations/09-host-lifecycle/long-running-host-maintenance/)：清單裡每一類檢查項目的來源，定期讀的 log 與對外入口的盤點方法；那一篇以單台主機為對象，依角色分組在本篇
- [Configuration Management（組態管理）](/infra/knowledge-cards/configuration-management/)：inventory 的分層與合併規則、組態管理工具跟 IaC 的分界
- [Infrastructure as Code (IaC)](/infra/knowledge-cards/iac/)：由 Terraform 建立主機、產生 inventory 的前提
