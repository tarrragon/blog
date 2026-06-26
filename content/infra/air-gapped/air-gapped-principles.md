---
title: "斷網環境的通用原則"
date: 2026-06-26
description: "離線套件管理、內容搬運、變更追蹤的共通操作模式 — 所有斷網情境都要先建立的基礎能力"
weight: 1
tags: ["infra", "air-gapped", "offline", "security"]
---

斷網環境的 infra 原則跟連網環境相同——可重建、可追蹤、可審查。差別在於連網環境用網路解決的事情（下載套件、推送 code、拉取映像、發送告警），斷網環境要用替代路徑解決。這些替代路徑有一個共通模式：把內容在有網路的環境準備好，經過安全審查後搬進隔離網路。本篇建立這個共通模式的操作框架，後續的 IaC、容器、監控各篇在這個框架上展開各自的細節。

## 內容搬運模式（Content Ferry）

斷網環境裡的所有外部依賴（套件、映像、工具、更新）都要經過一條可控的搬運路徑進入。這條路徑的設計決定了環境的安全性和維護效率。

### 搬運路徑的三種形態

**離線媒介搬運**：用 USB 隨身碟、外接硬碟或光碟把檔案從有網路的工作站搬進隔離網路。適合高安全環境（軍事、政府機密網路），搬運頻率通常是週或月級。每次搬運的內容要經過掃毒和完整性驗證。

```bash
# 外部工作站：準備搬運包
mkdir -p ferry/$(date +%Y%m%d)
# 把需要的套件、映像、工具複製進去
cp -r packages/ images/ tools/ ferry/$(date +%Y%m%d)/
# 產生 checksum
find ferry/$(date +%Y%m%d) -type f -exec sha256sum {} \; > ferry/$(date +%Y%m%d)/manifest.sha256
```

```bash
# 隔離網路內：驗證搬運包完整性
cd /mnt/usb/ferry/20260626
sha256sum -c manifest.sha256
```

**跨網段閘道搬運**：在隔離網路的邊界放一台 staging gateway（跳板機），它有兩張網卡——一張連外部網路（或 DMZ）、一張連內部隔離網路。外部的內容先傳到閘道、經過掃描和審查後再推進內部。適合金融和工控環境，搬運頻率可以是日級。

閘道的安全約束：只允許特定的檔案類型通過、所有傳入的檔案經過掃毒、傳輸記錄要保留 audit log、閘道本身定期更新安全軟體。

**單向資料二極體（Data Diode）**：硬體層面只允許資料單向流動（外 → 內），物理上無法從內部網路傳資料出去。用在最高安全等級的環境。搬運頻率和內容由二極體的設定決定。

### 搬運的操作紀律

每次搬運都要記錄：日期、搬運者、搬運內容清單（檔名 + 版本 + checksum）、搬運理由。這份紀錄存在內部網路的版本控制裡，讓「這個套件是誰、什麼時候、為什麼帶進來的」事後可追溯。

搬運內容的安全審查至少包含：掃毒（ClamAV 或商業掃毒）、checksum 驗證（確認搬運過程沒有被竄改）、版本確認（確認搬進來的版本跟預期的一致、不是被降級的舊版）。

時程參考：建立搬運流程（含閘道設定、掃描工具安裝、紀錄模板）約需 2-3 天。之後每次搬運操作約 1-2 小時（含準備、掃描、驗證、紀錄）。

## 離線套件管理

連網環境的 `apt install`、`yum install`、`npm install` 背後都在連線到公開的套件倉庫。斷網環境需要在內部建立這些倉庫的離線鏡像。

### 作業系統套件

**Debian/Ubuntu**：用 `apt-mirror` 或 `aptly` 在有網路的環境建立 mirror，把整個 mirror 搬進內部網路，內部機器的 `/etc/apt/sources.list` 指向內部 mirror。

```bash
# 外部：建立 mirror（首次約 50-200GB，後續增量）
apt-mirror /etc/apt/mirror.list

# 內部：設定 sources.list 指向內部 mirror
echo "deb http://internal-mirror.local/ubuntu jammy main restricted" > /etc/apt/sources.list
apt update
```

**RHEL/CentOS**：用 `reposync` 把 yum repo 同步到本地，搬進內部後用 `createrepo` 建立 repo metadata。

```bash
# 外部：同步 repo
reposync --repoid=baseos --download-metadata -p /path/to/mirror/

# 內部：建立 repo 並設定
createrepo /path/to/mirror/baseos
```

### 應用層套件

**Node.js（npm）**：`npm pack` 把每個依賴打包成 .tgz，搬進內部後用 `npm install --offline` 或建立 Verdaccio private registry。

```bash
# 外部：打包所有依賴
npm pack --pack-destination ./offline-packages/
# 或用 npm-offline-mirror
npm install --prefer-offline --cache ./npm-cache
```

**Python（pip）**：`pip download` 把依賴下載成 wheel 或 tarball，搬進內部後 `pip install --no-index --find-links=./packages/`。

**PHP（Composer）**：`composer install` 後整個 `vendor/` 目錄打包搬進去。或建立 Satis 作為 private Packagist mirror。

### 套件鏡像的維護節奏

離線 mirror 需要定期更新——安全補丁、版本升級都要透過搬運流程進入。更新頻率取決於安全需求：高安全環境至少月更（安全補丁）、一般環境季更可接受。每次更新都是一次搬運操作，要走完整的審查流程。

### 多格式統一：Nexus Repository

上面的做法是每個套件生態各自建 mirror（apt-mirror + Verdaccio + Satis + pip local index）。Nexus Repository 是多格式統一的 artifact proxy，同時支援 apt / yum / npm / Maven / PyPI / Docker / Helm——在企業級斷網環境裡，用一個 Nexus 實例取代多個獨立的離線 repo mirror，維護成本較低。代價是 Nexus 本身的安裝和維運（Java 應用、需要磁碟空間和記憶體），小團隊各自建 mirror 可能反而更簡單。

### 離線 Configuration Management：Ansible

斷網環境的 OS 設定、套件安裝、服務啟動等 configuration management 需求，Ansible 是運作良好的工具——它不需要在目標機器安裝 agent、透過 SSH 推送 playbook 執行，playbook 本身是 YAML 可版本控制。在沒有雲端 IaC（Terraform 管的是雲端資源 API）的地端斷網環境裡，Ansible 負責 configuration management 層。Ansible 自身的安裝只需要 Python，控制端安裝後即可透過 SSH 管理內部所有機器。

## 變更追蹤：沒有 GitHub 怎麼辦

斷網環境不能 push 到 GitHub、不能開 PR、不能用 GitHub Actions。但 git 本身是離線工具——git 的所有操作（commit、branch、merge、log、diff）都不需要網路。

### 內部 Git Server

在隔離網路內架設 git server：Gitea（輕量、單一二進位、適合小團隊）、GitLab CE（功能完整、含 CI/CD runner、適合中大團隊）、或最簡單的 bare repo on NFS。

```bash
# 最簡單的方式：bare repo on 共用檔案系統
git init --bare /shared/repos/infra.git

# 開發者 clone
git clone /shared/repos/infra.git
```

### Git Bundle 跨網段傳遞

如果需要在有網路的環境開發、完成後搬進隔離網路，用 `git bundle` 把 commit 打包成單一檔案：

```bash
# 外部：把 main branch 的所有 commit 打包
git bundle create infra-$(date +%Y%m%d).bundle main

# 搬運後，在內部 clone 或 pull
git clone infra-20260626.bundle infra-repo
# 或增量更新
git pull infra-20260626.bundle main
```

bundle 檔案可以用 `git bundle verify` 驗證完整性。增量 bundle（只包含某個 tag 之後的 commit）可以減少搬運的資料量：

```bash
git bundle create incremental.bundle last-imported-tag..main
```

### Code Review 的替代方案

沒有 GitHub PR，code review 可以用：

- GitLab CE / Gitea 的內建 merge request（如果架了內部 git server）
- `git format-patch` 產出 patch 檔 + email review（傳統做法、不需要 web UI）
- `git diff main..feature | less` 直接在終端機 review（最簡陋但可行）

## Staging Gateway 的設計

staging gateway 是搬運路徑的關鍵節點——它決定了什麼能進、什麼不能進。設計要點：

**最小安裝**：閘道上只裝搬運需要的工具（scp、rsync、掃毒軟體、checksum 工具），不裝開發工具、不跑應用服務。攻擊面越小越好。

**雙網卡隔離**：一張網卡連外部（或 DMZ）、一張連內部。兩張網卡之間沒有自動路由——檔案必須經過人工或腳本從外部目錄搬到內部目錄，中間經過掃描。

**審計紀錄**：閘道上的所有檔案操作（建立、複製、刪除）都要記錄。`auditd` 或等價工具提供核心層級的操作追蹤。

**定期輪替**：閘道本身的 OS 和掃毒軟體需要更新。這是一個遞迴問題（用什麼搬運閘道的更新？）——通常用離線媒介搬運閘道自身的更新，或用另一台更上游的閘道。

時程參考：閘道的初次設定（含 OS 安裝、雙網卡配置、掃描工具、審計設定）約需 1-2 天。搬運流程文件化約需半天。

## 安全審查：什麼能跨越隔離邊界

每一筆跨越隔離邊界的內容都是潛在的攻擊向量。審查的原則是：預設拒絕，逐項允許。

審查清單：

| 項目   | 檢查方式          | 通過條件                    |
| ------ | ----------------- | --------------------------- |
| 掃毒   | ClamAV / 商業掃毒 | 0 偵測                      |
| 完整性 | sha256sum 比對    | checksum 與外部記錄一致     |
| 版本   | 比對預期版本號    | 跟申請單的版本一致          |
| 來源   | 驗證下載來源      | 來自官方 repo 或已知 mirror |
| 必要性 | 申請理由審查      | 有明確的使用場景            |

對決策者的重點：斷網環境的安全不是「隔離就安全」——搬運路徑是唯一的攻擊面，這條路徑的安全審查品質決定了整個隔離環境的安全水位。

## 跨分類引用

- → [斷網環境的 IaC](/infra/air-gapped/air-gapped-iac/)：Terraform provider 和 module 的離線管理
- → [斷網環境的容器管理](/infra/air-gapped/air-gapped-container/)：映像搬運用的是本篇的 content ferry 模式
- → [模組八：治理好習慣](/infra/08-governance-habits/)：斷網環境的搬運紀錄是治理的一部分
