---
title: "斷網環境的套件與容器映像 Registry"
date: 2026-06-26
description: "斷網環境裡每一個 apt install、npm install、docker pull 都需要內部來源 — 用 Nexus Repository 統一管理套件、用 Harbor 管理容器映像、建立定期搬運與安全掃描的更新週期"
weight: 7
tags: ["infra", "air-gapped", "registry", "nexus", "harbor"]
---

連網環境的套件安裝和映像拉取，背後都有一個公開的 registry 在服務：apt 走 archive.ubuntu.com、npm 走 registry.npmjs.org、Docker 走 Docker Hub。斷網環境裡這些 endpoint 全部不可達，每一條 `apt install`、`npm install`、`pip install`、`docker pull` 都會失敗。替代做法是在內網部署自己的 registry，把需要的套件和映像從外部下載、經過安全審查後搬進來。

本篇涵蓋兩個 registry 的部署與操作：Nexus Repository（多格式套件）和 Harbor（容器映像）。兩者可以獨立運作，也可以搭配使用——Nexus 管套件依賴、Harbor 管容器映像，各自負責不同的 artifact 類型。

## Nexus Repository：統一的離線套件 proxy

Nexus Repository OSS（開源版）支援 apt、yum、npm、PyPI、Maven、NuGet、Go modules 等多種格式，用一個實例取代多個獨立的離線 repo mirror。部署在內網後，所有開發機器和 CI runner 把套件 source 指向 Nexus。

### 部署

Nexus 本身是一個 Java 應用，用 Docker 部署最簡單。映像需要事先從外部搬進來：

```bash
# 外部機器下載映像
docker pull sonatype/nexus3:latest
docker save sonatype/nexus3:latest -o nexus3.tar

# 搬運到內網後載入
docker load -i nexus3.tar
docker run -d -p 8081:8081 --name nexus \
  -v nexus-data:/nexus-data \
  sonatype/nexus3:latest
```

初始管理員密碼在容器內 `/nexus-data/admin.password`，首次登入後強制修改。

### Hosted repo 模式

連網環境的 Nexus 通常用 proxy repo（代理公開 registry、快取下載過的套件）。斷網環境 proxy 模式無法運作，改用 hosted repo——手動上傳套件到 Nexus，Nexus 作為唯一的分發來源。

以 npm 為例，workflow 是在外部機器打包、搬運、上傳：

```bash
# 外部機器：打包專案的所有依賴
npm pack --pack-destination ./npm-packages/
# 或用 npm-offline-packager 批次下載整棵依賴樹
npx npm-offline-packager --package ./package.json --output ./npm-packages/

# 搬運到內網後上傳到 Nexus
for pkg in ./npm-packages/*.tgz; do
  curl -u admin:password \
    --upload-file "$pkg" \
    "http://nexus.internal:8081/repository/npm-hosted/"
done
```

apt 和 yum 的做法類似：外部機器用 `apt-get download` 或 `yumdownloader` 抓 .deb / .rpm 檔案，搬進來後上傳到 Nexus 的 hosted repo。

### 客戶端設定

開發機器和 CI runner 的套件 source 指向 Nexus：

```bash
# npm
npm config set registry http://nexus.internal:8081/repository/npm-hosted/

# pip
pip install --index-url http://nexus.internal:8081/repository/pypi-hosted/simple/ package-name

# apt（在 /etc/apt/sources.list.d/ 加一份）
deb http://nexus.internal:8081/repository/apt-hosted/ focal main
```

## Harbor：容器映像的 private registry

Harbor 是 CNCF 畢業專案的企業級容器 registry，支援映像簽章、漏洞掃描（Trivy）、存取控制、映像複製。在斷網環境裡它是 Docker Hub 和 ECR 的替代品。

### 部署

Harbor 用 Docker Compose 部署。安裝包需要從外部下載後搬進來：

```bash
# 外部機器下載離線安裝包
wget https://github.com/goharbor/harbor/releases/download/v2.11.0/harbor-offline-installer-v2.11.0.tgz

# 搬運到內網後解壓
tar xzf harbor-offline-installer-v2.11.0.tgz
cd harbor

# 複製並編輯設定
cp harbor.yml.tmpl harbor.yml
# 修改 hostname、storage 路徑、HTTPS 憑證（內部 CA 簽發）

# 安裝
./install.sh --with-trivy
```

`--with-trivy` 啟用內建的漏洞掃描。Trivy 的漏洞資料庫需要離線更新——從外部下載 DB 檔案、搬進來放到指定路徑。

### 專案與存取控制

Harbor 用「專案」（project）組織映像。每個專案可以設定獨立的存取控制：

- `library`：公開專案、所有使用者可 pull
- `platform`：平台團隊專用、限定成員可 push
- `vendor`：第三方 base image、由 infra 團隊管理更新

robot account 提供 CI/CD 用的非互動式認證（限定 pull / push 權限、可設定到期時間）。

## 映像搬運 SOP

映像從外部搬進斷網環境是一個需要標準化的操作，涉及格式、大小、多架構支援：

### 搬運工具比較

| 工具               | 優點                                                      | 限制                                                 |
| ------------------ | --------------------------------------------------------- | ---------------------------------------------------- |
| `docker save/load` | 最直覺、不需要額外安裝                                    | 只能處理本地已 pull 的映像、不支援跨 registry 直接搬 |
| `skopeo copy`      | 不需要 Docker daemon、支援跨 registry、支援 manifest list | 需要安裝 skopeo                                      |
| `crane`            | 輕量 CLI、支援 manifest 操作                              | 功能比 skopeo 少                                     |

skopeo 的操作流程：

```bash
# 外部機器：從 Docker Hub 複製到本地目錄
skopeo copy docker://nginx:1.25-alpine dir:./images/nginx-1.25-alpine

# 搬運到內網後：從本地目錄推到 Harbor
skopeo copy dir:./images/nginx-1.25-alpine \
  docker://harbor.internal/library/nginx:1.25-alpine \
  --dest-tls-verify=false  # 如果 Harbor 用內部 CA
```

### 多架構映像

如果環境同時有 amd64 和 arm64 的機器，搬運時要帶整個 manifest list：

```bash
# 外部：複製所有架構
skopeo copy --all docker://nginx:1.25-alpine \
  dir:./images/nginx-1.25-alpine-multiarch

# 內網：推送所有架構
skopeo copy --all dir:./images/nginx-1.25-alpine-multiarch \
  docker://harbor.internal/library/nginx:1.25-alpine
```

`--all` flag 確保 manifest list 裡的每個架構都被複製，而非只複製本機架構。

## 套件與映像的更新週期

斷網環境的套件和映像不會自動更新——每一次更新都是一次有意識的搬運操作。更新週期的頻率由安全需求決定：

| 安全等級 | 更新頻率        | 適用場景                       |
| -------- | --------------- | ------------------------------ |
| 一般     | 每月一次        | 開發工具、非直接面對外部的服務 |
| 中等     | 每兩週          | 有外部接口的服務、包含網路元件 |
| 高       | 每週或 CVE 驅動 | 安全敏感環境、合規要求         |

每次更新的標準流程：

1. **外部機器下載**：按清單下載指定版本的套件和映像
2. **安全掃描**：在外部（或 staging gateway）跑 Trivy / Snyk 掃描，確認沒有已知的高風險 CVE
3. **審查核准**：掃描報告給安全團隊或負責人簽核
4. **搬運**：核准的 artifact 寫入唯讀媒體或加密通道搬進內網
5. **上傳到 registry**：推到 Nexus 和 Harbor
6. **通知團隊**：哪些套件/映像有新版本可用

這個流程的產出是一份更新清單（什麼版本、掃描結果、核准人），存進版控作為稽核紀錄。

## Helm chart 離線管理

Kubernetes 環境用 [Helm](/infra/knowledge-cards/helm/) 部署應用。斷網時 Helm chart 需要離線管理：

```bash
# 外部機器：下載 chart
helm repo add bitnami https://charts.bitnami.com/bitnami
helm pull bitnami/postgresql --version 15.5.0

# 搬運到內網後有兩個存放選項
```

**選項一：Harbor 內建 chart 支援**。Harbor 2.0+ 支援 OCI artifact，Helm chart 可以直接推到 Harbor：

```bash
helm push postgresql-15.5.0.tgz oci://harbor.internal/charts
```

**選項二：ChartMuseum**。獨立的 chart repository server：

```bash
# 上傳 chart
curl --data-binary "@postgresql-15.5.0.tgz" \
  http://chartmuseum.internal:8080/api/charts
```

Harbor 的 OCI 方式較簡單（不需要額外維護 ChartMuseum），但需要 Helm 3.8+ 的 OCI 支援。

## 時程與管理層溝通

| 項目               | 初次部署時間                | 持續維護              |
| ------------------ | --------------------------- | --------------------- |
| Nexus Repository   | 1 天（部署 + 初始套件上傳） | 每次更新週期 2-4 小時 |
| Harbor             | 1 天（部署 + 初始映像搬運） | 每次更新週期 2-4 小時 |
| 搬運 SOP 建立      | 半天（腳本化 + 文件）       | 每次執行 1-2 小時     |
| Trivy 離線 DB 更新 | 含在 Harbor 部署內          | 每次更新週期 30 分鐘  |

管理層需要知道的成本：registry 的維護不是一次性投入，每個更新週期都需要工程師時間執行搬運和掃描。這筆成本在連網環境裡由公開 registry 和自動更新吸收，斷網環境裡由團隊承擔。

## 跨分類引用

- → [斷網環境的通用原則](/infra/air-gapped/air-gapped-principles/)：content ferry pattern 和安全審查流程
- → [斷網環境的容器與映像管理](/infra/air-gapped/air-gapped-container/)：映像搬運的更完整討論（本篇聚焦 registry 部署、該篇聚焦映像生命週期）
- → [斷網環境的 IaC](/infra/air-gapped/air-gapped-iac/)：Terraform provider 也需要離線 mirror、可用 Nexus 的 raw hosted repo 存放
