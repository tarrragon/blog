---
title: "斷網環境的版本控制與 CI/CD"
date: 2026-06-26
description: "在沒有 GitHub、沒有 Docker Hub 的隔離網路裡，怎麼部署版本控制、設定 CI runner、跨邊界傳輸 commit、以及讓 PR review 流程運作"
weight: 6
tags: ["infra", "air-gapped", "git", "ci-cd"]
---

版本控制和 CI/CD 是所有 infra 操作的前提——程式碼要有地方存、變更要能被 review、build 和 deploy 要自動化。正常環境裡這些由 GitHub + GitHub Actions 提供，斷網環境裡這兩個服務都不存在，需要在內網自建替代品。

## GitLab CE vs Gitea：選型判準

兩個主流的自建版本控制方案定位不同：

| 維度               | GitLab CE                                          | Gitea                                   |
| ------------------ | -------------------------------------------------- | --------------------------------------- |
| 定位               | VCS + CI + Container Registry + Issue Tracker 一體 | 純 VCS（輕量 Git 伺服器）               |
| 資源需求           | 4GB+ RAM、推薦 8GB                                 | 512MB RAM 即可運作                      |
| CI 內建            | GitLab CI（`.gitlab-ci.yml`）                      | 無（搭配 Drone / Woodpecker / Jenkins） |
| Container Registry | 內建                                               | 無（搭配 Harbor）                       |
| 安裝複雜度         | 中（Omnibus 包裝簡化了安裝、但設定項多）           | 低（單一二進位檔、啟動即可用）          |
| 維護負擔           | 高（PostgreSQL、Redis、Sidekiq 都在裡面）          | 低（SQLite 或 MySQL、無背景服務）       |

選型判準是團隊規模和需要的功能範圍。5 人以下、只需要 VCS + 輕量 CI 的團隊，Gitea + Drone 的組合維護成本低。10 人以上、需要 MR review + CI pipeline + Container Registry 一站到位的團隊，GitLab CE 的整合度值得它的資源消耗。

接下來以 GitLab CE 為主線說明（功能最完整），Gitea 的差異在各段附註。

## GitLab CE 離線安裝

GitLab Omnibus 包把所有依賴打包成單一安裝檔，不需要在目標機器上 `apt install` 任何前置套件。

### 在外網機器下載安裝包

```bash
# Ubuntu/Debian
wget https://packages.gitlab.com/gitlab/gitlab-ce/packages/ubuntu/jammy/gitlab-ce_17.0.0-ce.0_amd64.deb/download.deb

# RHEL/CentOS
wget https://packages.gitlab.com/gitlab/gitlab-ce/packages/el/9/gitlab-ce-17.0.0-ce.0.el9.x86_64.rpm/download.rpm
```

把下載的 `.deb` 或 `.rpm` 透過[內容搬運機制](/infra/air-gapped/air-gapped-principles/)（USB、光碟、跨邊界傳輸站）帶進斷網環境。

### 在斷網機器安裝

```bash
# Ubuntu/Debian
sudo dpkg -i gitlab-ce_17.0.0-ce.0_amd64.deb

# RHEL/CentOS
sudo yum localinstall gitlab-ce-17.0.0-ce.0.el9.x86_64.rpm
```

### 離線設定

安裝後編輯 `/etc/gitlab/gitlab.rb`，把所有外部連線關掉：

```ruby
# 設定內部域名（不是公網域名）
external_url 'https://gitlab.internal.example.com'

# 關閉 Gravatar（頭像服務、需要外網）
gitlab_rails['gravatar_enabled'] = false

# 關閉 usage ping（回報使用統計到 GitLab Inc）
gitlab_rails['usage_ping_enabled'] = false

# 關閉 version check
gitlab_rails['gitlab_check_on_connect'] = false

# 如果沒有內部 SMTP，用 sendmail 或關閉 email
gitlab_rails['smtp_enable'] = false

# TLS 憑證用內部 CA 簽發
nginx['ssl_certificate'] = "/etc/gitlab/ssl/gitlab.crt"
nginx['ssl_certificate_key'] = "/etc/gitlab/ssl/gitlab.key"
```

```bash
sudo gitlab-ctl reconfigure
```

Gitea 的離線安裝更簡單：下載單一二進位檔 `gitea`、設定 `app.ini`、用 systemd 管理即可。

### 升級策略

GitLab CE 的升級包也要從外部下載帶進來。升級前先備份（`gitlab-backup create`），升級路徑要按 GitLab 的[版本跳級規則](https://docs.gitlab.com/ee/update/index.html#upgrade-paths)——不能任意跳版、某些大版本之間需要中繼版本。在斷網環境裡，每次升級要預先規劃中繼版本、一次帶進所有需要的安裝包。

## CI Runner 離線設定

CI pipeline 在斷網環境裡跑的最大差異是 runner 不能即時拉依賴。

### Runner 安裝與註冊

```bash
# 下載 runner 二進位檔（外網下載、帶進來）
# https://docs.gitlab.com/runner/install/linux-manually.html

sudo gitlab-runner register \
  --url https://gitlab.internal.example.com \
  --token $RUNNER_TOKEN \
  --executor docker \
  --docker-image alpine:3.20
```

### Executor 選擇

| Executor   | 隔離性                       | 前置條件                 | 斷網適用度            |
| ---------- | ---------------------------- | ------------------------ | --------------------- |
| shell      | 低（直接跑在 runner 機器上） | 無                       | 高（最簡單）          |
| docker     | 高（每個 job 一個容器）      | 需要 Docker + 預拉 image | 中（image 管理成本）  |
| kubernetes | 高（每個 job 一個 pod）      | 需要 K8s cluster         | 低（斷網 K8s 維護重） |

斷網環境推薦 shell executor（最少依賴）或 docker executor 搭配預拉好的 image。

### Docker executor 的 image 管理

Docker executor 的每個 job 都基於一個 base image。斷網環境裡這些 image 必須預先存在於內網的 [private registry](/infra/air-gapped/air-gapped-container/)：

```bash
# runner 的 /etc/docker/daemon.json 指向內部 registry
{
  "insecure-registries": ["registry.internal:5000"],
  "registry-mirrors": ["https://registry.internal:5000"]
}
```

CI pipeline 裡用到的每個 image（build 用的 golang/node/php、lint 用的 tflint/checkov、deploy 用的 awscli）都要事先搬進內部 registry。

### 依賴快取

沒有 npm registry / PyPI / Maven Central 可以拉，CI job 的依賴安裝必須用本地來源：

```yaml
# .gitlab-ci.yml — 使用內部 Nexus 作為套件來源
variables:
  NPM_CONFIG_REGISTRY: "https://nexus.internal/repository/npm-proxy/"
  PIP_INDEX_URL: "https://nexus.internal/repository/pypi-proxy/simple/"
```

或者把 `node_modules` / `vendor` 打包成 CI artifact 快取，避免每次 job 都重新安裝。

## Git Bundle 跨邊界傳輸

某些斷網環境不允許直接 `git push` 到內網 GitLab（例如開發在外網、部署在內網）。Git bundle 是把 commit 歷史打包成單一檔案的機制：

```bash
# 外網開發機：打包最近的 commit
git bundle create changes.bundle main~5..main

# 帶進斷網環境後
git bundle verify changes.bundle
git fetch changes.bundle main:incoming
git merge incoming
```

bundle 檔案包含完整的 Git 物件（commit、tree、blob），可以通過任何檔案傳輸方式帶過邊界——USB、光碟、審批後的檔案傳輸閘道。

跨邊界傳輸的安全考量：bundle 的內容應該在傳入前被掃描（至少 `git bundle verify`），確認不包含預期外的分支或異常大的物件。某些高安全環境要求所有跨邊界檔案經過人工審批。

## MR Review 流程

斷網環境的 MR（Merge Request）review 流程跟[模組七：infra 走 PR 流程](/infra/07-infra-as-pr/)的原則相同——變更走 MR → CI 跑 plan → reviewer 看 diff + plan 輸出 → 合併 → apply。差別在於所有環節都在內網：

```yaml
# .gitlab-ci.yml — Terraform plan 貼回 MR comment
plan:
  stage: plan
  script:
    - terraform init -plugin-dir=/opt/terraform/plugins
    - terraform plan -no-color -out=plan.tfplan | tee plan.txt
    - |
      curl --request POST \
        --header "PRIVATE-TOKEN: $GITLAB_TOKEN" \
        --data-urlencode "body=$(cat plan.txt)" \
        "https://gitlab.internal/api/v4/projects/$CI_PROJECT_ID/merge_requests/$CI_MERGE_REQUEST_IID/notes"
  only:
    - merge_requests
```

GitLab CI 的 `merge_requests` trigger 跟 GitHub Actions 的 `pull_request` 等價——MR 開啟或更新時自動跑 pipeline。

reviewer 在 GitLab 的 MR 頁面看 code diff + plan 輸出 comment，approve 後合併，合併觸發 apply pipeline。流程跟有網路時完全相同，只是所有元件（GitLab、runner、Terraform、provider plugin）都在內網。

## 時程與維護

| 項目                      | 初始設定 | 持續維護                                     |
| ------------------------- | -------- | -------------------------------------------- |
| GitLab CE 安裝 + 設定     | 1 天     | 每季升級（含帶包 + 備份 + 升級 + 驗證）~半天 |
| CI runner 設定            | 半天     | image 更新隨 registry 同步                   |
| Gitea + Drone（替代方案） | 半天     | 極低（二進位更新即可）                       |
| Git bundle 流程建立       | 2 小時   | 按需（有跨邊界需求時）                       |

GitLab CE 的主要維護成本在升級——斷網環境的升級不能一鍵 `apt upgrade`，要預先下載正確版本的安裝包帶進來。跳版規則讓這個過程比正常環境多一層規劃。

## 跨分類引用

- → [斷網環境的通用原則](/infra/air-gapped/air-gapped-principles/)：內容搬運、離線套件管理的共通模式
- → [斷網環境的容器與映像管理](/infra/air-gapped/air-gapped-container/)：CI runner 的 Docker image 管理
- → [模組七：infra 走 PR 流程](/infra/07-infra-as-pr/)：MR review 流程的原則與護欄
