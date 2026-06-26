---
title: "斷網環境的容器與映像管理"
date: 2026-06-26
description: "Private registry 架設、映像搬運（docker save/load、skopeo）、base image 更新週期、離線漏洞掃描"
weight: 3
tags: ["infra", "air-gapped", "container", "registry"]
---

容器化應用在斷網環境的主要挑戰不是容器本身——Docker 和 containerd 不需要網路就能啟動容器。挑戰在映像的取得和更新：沒有 Docker Hub、沒有 ECR、沒有 ghcr.io，每一個 base image 和應用映像都要經過搬運路徑進入隔離網路。映像的管理在斷網環境裡需要一條完整的 pipeline：外部下載 → 安全掃描 → 搬運 → 推送到內部 registry → 各節點 pull。

## Private Registry

隔離網路裡需要一個容器映像倉庫，讓內部的 Docker host / Kubernetes 節點能 pull image。

### Harbor

Harbor 是 VMware 開源的企業級 registry，功能包含：映像儲存、漏洞掃描（整合 Trivy）、存取控制（RBAC）、映像簽章（Cosign / Notary）、複製策略。適合中大規模的斷網環境。

離線安裝：Harbor 提供 offline installer（`.tgz`，約 600MB），包含所有需要的容器映像。搬進隔離網路後解壓、跑 `install.sh`。

```bash
# 外部：下載 offline installer
wget https://github.com/goharbor/harbor/releases/download/v2.11.0/harbor-offline-installer-v2.11.0.tgz

# 搬運後，在內部解壓安裝
tar xzf harbor-offline-installer-v2.11.0.tgz
cd harbor
cp harbor.yml.tmpl harbor.yml
# 編輯 harbor.yml：設定 hostname、HTTPS 憑證、admin 密碼
./install.sh
```

### Docker Registry（官方輕量版）

如果不需要 Harbor 的進階功能（RBAC、掃描），官方的 Docker Registry 是單一容器、設定最簡單：

```bash
# registry image 也要先搬進來
docker load < registry-2.8.3.tar
docker run -d -p 5000:5000 --restart=always --name registry \
  -v /data/registry:/var/lib/registry \
  registry:2.8.3
```

內部機器的 Docker daemon 要設定信任這個 registry（如果是 HTTP 而非 HTTPS）：

```json
{
  "insecure-registries": ["registry.internal:5000"]
}
```

## 映像搬運

### docker save / load

最直接的搬運方式——把映像匯出成 tar 檔、搬運後匯入：

```bash
# 外部：匯出
docker pull nginx:1.25-alpine
docker save nginx:1.25-alpine -o nginx-1.25-alpine.tar

# 搬運後，內部匯入
docker load < nginx-1.25-alpine.tar
# 重新 tag 指向內部 registry
docker tag nginx:1.25-alpine registry.internal:5000/nginx:1.25-alpine
docker push registry.internal:5000/nginx:1.25-alpine
```

多個映像可以打包成一個 tar：`docker save img1 img2 img3 -o bundle.tar`。

### skopeo copy

skopeo 是不需要 Docker daemon 的映像操作工具，適合 CI 環境或沒有裝 Docker 的工作站：

```bash
# 外部：從 Docker Hub 複製到本地目錄
skopeo copy docker://nginx:1.25-alpine dir:/path/to/export/nginx-1.25

# 搬運後，從本地目錄推送到內部 registry
skopeo copy dir:/path/to/export/nginx-1.25 docker://registry.internal:5000/nginx:1.25-alpine
```

skopeo 的優勢是不需要 pull 整個映像到本地 Docker（省磁碟空間）、支援 OCI layout、且可以在沒有 root 權限的環境執行。

### 搬運清單管理

映像搬運容易變成「需要什麼才搬什麼」的臨時操作。建議維護一份搬運清單（manifest），列出所有需要的 base image 和版本：

```yaml
# image-manifest.yaml
images:
  - name: nginx
    tag: 1.25-alpine
    source: docker.io/library/nginx
  - name: postgres
    tag: "16.3"
    source: docker.io/library/postgres
  - name: node
    tag: 20-alpine
    source: docker.io/library/node
```

搬運腳本讀這份清單自動 pull + save，確保每次搬運的內容一致且可追蹤。

## Base Image 更新週期

斷網環境的 base image 不會自動更新——`nginx:1.25-alpine` 搬進去之後就是那個版本，裡面的 Alpine 套件不會收到安全補丁。需要定期用新版 base image 替換舊的。

### 更新流程

1. **外部**：pull 最新版 base image
2. **外部**：用 Trivy 掃描漏洞（見下一節）
3. **搬運**：走 content ferry 帶進內部
4. **內部**：push 到內部 registry、更新 tag
5. **內部**：重新 build 所有依賴這個 base image 的應用映像
6. **內部**：部署更新後的應用映像

更新頻率：安全敏感環境月更、一般環境季更。每次更新都要記錄哪些 base image 換了、從哪個版本換到哪個版本。

### Helm Chart 離線

如果內部有 Kubernetes 且使用 Helm，chart 也要離線管理：

```bash
# 外部：下載 chart
helm pull bitnami/postgresql --version 15.5.0

# 搬運後，內部用本地檔案安裝
helm install pg ./postgresql-15.5.0.tgz -f values.yaml
```

或架設 ChartMuseum 作為內部 Helm repo：chart 搬進來後 push 到 ChartMuseum，`helm repo add` 指向它。

## 離線漏洞掃描

連網環境的 Trivy 會自動下載漏洞資料庫（CVE DB）。斷網環境要先在外部下載 DB、搬進來。

```bash
# 外部：下載 Trivy 漏洞資料庫
trivy image --download-db-only --cache-dir /path/to/trivy-db/

# 搬運 DB 檔案（~30MB）
# db.tar.gz 在 /path/to/trivy-db/db/ 裡

# 內部：用離線 DB 掃描
trivy image --skip-db-update --cache-dir /path/to/trivy-db/ registry.internal:5000/nginx:1.25-alpine
```

掃描結果的處理方式跟連網環境相同——critical 和 high 的 CVE 要評估是否影響、是否有 base image 更新可修。差別是斷網環境的修復週期更長（要走搬運流程），所以掃描要更頻繁（至少跟 base image 更新同步）。

Harbor 整合 Trivy 後可以在 push 時自動掃描——Trivy DB 的更新同樣需要定期搬運。

時程參考：Private registry 建置（Harbor offline）約需 1 天。映像搬運流程建立約需半天。第一批 base image 搬運 + 掃描約需半天。之後每次更新約 2-4 小時。

## 跨分類引用

- → [斷網環境的通用原則](/infra/air-gapped/air-gapped-principles/)：映像搬運走 content ferry 模式
- → [模組五：核心服務上 IaC — 運算](/infra/05-core-services/compute-ecs-eks/)：連網環境的容器部署
- → [ECS 知識卡](/infra/knowledge-cards/ecs/)：容器編排的基礎概念
