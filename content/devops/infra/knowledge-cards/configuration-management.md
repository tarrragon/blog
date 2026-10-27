---
title: "Configuration Management（組態管理）"
date: 2026-10-26
description: "要讓好幾台主機的套件、設定檔與服務維持同一個狀態、讀到 Ansible 的 inventory 與 group_vars、或要判斷主機上的設定該交給 Ansible 這類工具還是 Terraform 這類 IaC 管理時"
weight: 75
tags: ["infra", "knowledge-cards", "ansible", "config"]
aliases: ["/infra/knowledge-cards/configuration-management/"]
---

組態管理（configuration management；其他中文資料也寫作設定管理）在主機維運的語境裡，指用工具把一群主機「內部」的狀態寫成宣告，再由工具把每台主機帶到那個狀態：要裝哪些套件、設定檔的內容、哪些服務要啟用、哪些使用者與權限要存在。Ansible、Puppet、Chef、Salt 是這一類工具。它跟 [Infrastructure as Code (IaC)](/devops/infra/knowledge-cards/iac/) 的分界在管理對象：IaC 管的是雲端業者那一端的資源（主機本身、網路、防火牆規則、DNS 紀錄），組態管理管的是主機開機之後作業系統裡面的套件、設定檔與服務；兩者常一起用，IaC 建出主機，組態管理把主機設定好。

同名而所指不同的兩個詞：軟體工程裡的軟體組態管理（software configuration management，SCM）指原始碼的版本控制、基線與變更控制；中國大陸工業控制業界的「組態」（组态软件）指在 SCADA 或 HMI 軟體裡設定畫面與點位。本卡講的是主機設定的管理工具。

## 概念位置

組態管理工具都有兩個部分：主機清冊，與每台主機要套用的內容。Ansible 把主機清冊叫 inventory（列出受管主機與分組的檔案），跟商業領域的存貨（inventory）同字而無關；要套用的內容寫在 playbook（依序列出要對哪些主機套用哪些模組的 YAML 檔）與 role（把一類主機要用的任務、範本與變數收成一個可重用的目錄）裡，這個 playbook 跟事故處理的 [Playbook](/backend/knowledge-cards/playbook/) 同名而所指不同。inventory 把主機分成群組（`web`、`db`），變數依層次放在 `group_vars/<群組>.yml` 與 `host_vars/<主機>.yml`，一台主機最後拿到的值是各層合併的結果，合併時越具體的層越優先：`host_vars` 蓋過群組的值，子群組蓋過 `all`。一台主機同時屬於兩個同層的群組、而兩個群組給了同一個變數不同的值時，依群組名稱的字母順序，排在後面的蓋過前面的；要指定誰優先，在 inventory 檔本身替群組設 `ansible_group_priority`（預設 1，數字大的較晚合併而勝出），寫在 `group_vars` 檔裡沒有效果；優先順序只會讓其中一組勝出，兼任兩種角色的主機需要兩組值都生效時，要讓兩個角色用不同的變數名、在範本裡取聯集。這幾條用 ansible-core 2.17 實測過，`ansible-inventory --host <主機>` 印得出合併後的值，實測的檔案與輸出見 [多台主機的維護清單：值的分層與合併的位置、用 Ansible 的 inventory 與範本產生每台的清單、由 Terraform 的輸出產生 inventory、跨主機執行的 exit code，以及單台清單的適用範圍](/devops/operations/09-host-lifecycle/multi-host-manifest/)。inventory 與 `group_vars` 是 [YAML](/devops/infra/knowledge-cards/yaml/)，所以 YAML 1.1 的隱式型別照樣作用：`country: no` 讀出來是布林值 `false`。

主機清冊可以手寫，也可以由 IaC 產生：Terraform 知道它建的每台主機的 IP 與角色，可以用 `terraform output -json` 輸出給別的工具讀，或用 `local_file` 這類資源直接寫出一份 inventory 檔。那份檔案是 Terraform 管理的一個資源，它的內容記在 Terraform 的 [State（IaC 狀態檔）](/devops/infra/knowledge-cards/state/) 裡，手動改了它，下一次 `terraform plan` 會要求重建、`apply` 會蓋掉手改的內容。由 `local_file` 寫出 inventory、經由 SSH 部署到兩台容器並執行檢查的實際操作，以及 `file_permission` 的預設值扣掉 umask 之後的實際權限，在 [多台主機維護清單的實作紀錄：在容器上安裝 ansible-core 與 Terraform、由 Terraform 產生 inventory、用 Ansible 的範本部署每台的清單、以 sudo 與 systemd-run 執行檢查腳本，以及清理](/devops/operations/09-host-lifecycle/hands-on/multi-host-manifest-walkthrough/)〈由 Terraform 產生 inventory：init、plan、apply 與 local_file 的檔案權限〉。雲端資源的實際狀態跟 IaC 記錄的不一致叫 [Drift（設定漂移）](/devops/infra/knowledge-cards/drift/)；主機裡的套件與設定檔跟組態管理的宣告不一致，有人同樣叫它 configuration drift，比對的兩邊換成了組態管理的宣告與主機內部的狀態；組態管理工具在下一次套用時把主機帶回宣告的狀態，兩次套用之間有人登入手改的部分，在那之前一直存在。

Ansible 由執行指令的那台機器經由 SSH 連到每台主機，把要執行的模組送過去執行，主機上不必裝常駐的代理程式（agent）；Puppet 與 Chef 傳統上在每台主機跑一個代理程式，定期向伺服器拉取該套用的內容（Puppet 與 Chef 的運作方式取自兩者的文件，沒有實測）。Ansible 這種推送的做法由操作的人或排程決定什麼時候套用；代理程式拉取的做法讓主機自己定期回到宣告的狀態。

## 可觀察訊號

- repo 裡有 `inventory.yml`（或 `hosts.ini`）、`group_vars/`、`host_vars/`、`playbook.yml`、`roles/` 這類目錄。
- 維護的人改一台主機的設定時，改的是 repo 裡的變數或範本，再對那一組主機執行一次，不登入主機手改。
- 同一個設定檔在每台主機上的內容只有主機名、IP、角色相關的幾行不同。

## 設計責任

- **每個值放在哪一層**：所有主機都相同的放 `all`，依角色不同的放群組，只有一台不同的放 `host_vars`。同一個值在兩層都寫了時，讀檔的人要知道合併規則才知道哪一個生效；對哪一個值生效有疑問時，用 `ansible-inventory --host` 查合併後的值。
- **套用要能重複執行**：每個步驟執行第二次時不改變結果（[Idempotency](/backend/knowledge-cards/idempotency/)），排程定期套用時才不會每次都重啟服務或重寫檔案。Ansible 的模組多半這樣設計，`command` 與 `shell` 模組例外：它們每次都執行、每次都回報 changed，要用 `creates`、`removes` 或 `changed_when` 寫出什麼情形下不必執行、什麼結果算有改變。
- **範本的語法與產出的格式分開**：Ansible 的範本是 Jinja2，`{{ }}` 是它的替換語法；產出的檔案自己也用 `{{ }}` 時（例如另一支程式的變數替換），那一段要包在 `{% raw %}` 裡，否則 Jinja2 會先替換它。值寫進 TOML、JSON 這類有引號規則的格式時，用 `to_json` 過濾器輸出（含非 ASCII 字元時加 `ensure_ascii=False`），引號與反斜線才會被正確跳脫；直接輸出時，Python 的布林值寫成 `False`，字串不帶引號，含反斜線的字串陣列被寫成兩個反斜線，TOML 解析失敗或讀到被改掉的值。
- **主機清冊的唯一來源**：主機由 IaC 建立時，inventory 由 IaC 的輸出產生，不另外手寫一份；兩份各自維護時，新增或刪除主機只改了其中一份，另一份就指著不存在的主機，或漏掉新的主機。

## 鄰卡

- [Infrastructure as Code (IaC)](/devops/infra/knowledge-cards/iac/)
- [Drift（設定漂移）](/devops/infra/knowledge-cards/drift/)
- [YAML](/devops/infra/knowledge-cards/yaml/)
- [State（IaC 狀態檔）](/devops/infra/knowledge-cards/state/)
