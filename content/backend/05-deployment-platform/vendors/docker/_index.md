---
title: "Docker"
date: 2026-05-01
description: "Container runtime / image 標準"
weight: 2
tags: ["backend", "deployment", "vendor"]
---

Docker 是最早 popularize container 的工具、承擔三個責任：container image build（Dockerfile / BuildKit）、local container runtime（docker run / Compose）、image distribution（Docker Hub / private registry）。設計取捨偏向「dev experience + image format standard」、production orchestration 多被 Kubernetes + containerd 取代、但 image build / dev workflow / OCI image 仍是事實標準。

對「Local dev / CI container 工具、image build pipeline、小規模 dev 環境」這條路徑、Docker 是首選。

## 本章目標

讀完本章後、你應該能：

1. 寫 Dockerfile + 跑 docker build / run
2. 用 multi-stage build / BuildKit 優化 image
3. 用 Docker Compose 編排 dev 環境
4. 配置 image registry + scanning + SBOM
5. 評估 Docker Desktop license 對團隊的影響、選替代（Podman / Rancher Desktop）

## 最短路徑：5 分鐘把 Docker 跑起來

```bash
# 1. 安裝 Docker / Podman / Rancher Desktop
# TODO: macOS: Docker Desktop / brew install --cask docker

# 2. 跑 container
# TODO: docker run -d -p 8080:80 nginx
# TODO: docker ps / docker logs / docker exec

# 3. Build image
# TODO: docker build -t myapp:1 .
# TODO: docker push <registry>/myapp:1
```

## 日常操作與決策形狀

### Dockerfile 設計

子議題：

- FROM / RUN / COPY / WORKDIR / EXPOSE / CMD / ENTRYPOINT
- Multi-stage build（build stage + runtime stage 分離）
- Layer cache 設計（COPY 順序影響 cache hit）
- 對應指令：`docker build --no-cache`、`docker history <image>`

### BuildKit / Buildx

子議題：

- BuildKit：新 builder、parallel + cache mount + secret + SSH agent
- Buildx：cross-platform build（amd64 / arm64）
- Cache backend（local / registry / S3 / GHA）
- 對應指令：`docker buildx create --use`、`docker buildx build --platform=linux/amd64,linux/arm64`

### Docker Compose

子議題：

- docker-compose.yml：service / network / volume 配置
- 適合：local dev 多 container（DB + cache + app）
- 不適合：production（用 K8s）
- 對應 [5.2 K8s deployment](/backend/05-deployment-platform/kubernetes-deployment/)

## 進階主題（按需閱讀）

### Image security / scanning / SBOM

子議題：

- Trivy / Grype / Snyk image vulnerability scanning
- SBOM 產生（syft / Docker scout）
- Sign image（cosign / notary v2）
- 對應 [07 security](/backend/07-security-data-protection/) supply chain

### Image registry 選擇

子議題：

- Docker Hub（public + rate limit issue）
- 雲端：ECR / GCR / Artifact Registry / ACR
- Self-host：Harbor / GitLab Container Registry / Nexus
- 對應 image pull credentials 管理

### Docker Desktop license

子議題：

- 2021 改授權：商業企業（> 250 員工 / > $10M）需付費
- 替代：Podman Desktop / Rancher Desktop / Colima / Lima
- 替代品的 daemon / rootless 差異
- 對應企業 IT 採購決策

### Containerd / CRI-O 在 production

子議題：

- K8s 1.24+ 移除 dockershim、改用 containerd / CRI-O
- Docker image 跟 containerd 相容（OCI standard）
- production 不用 Docker、用 containerd

### Image size 優化

子議題：

- Base image 選擇（distroless / alpine / scratch）
- Multi-stage build + layer combine
- Build context（.dockerignore）
- 跟 image scanning 跟 deploy speed 對應

### Rootless / 安全強化

子議題：

- Rootless mode（Docker / Podman 都支援）
- User namespace mapping
- Seccomp / AppArmor / SELinux profile
- 對應 [07 security](/backend/07-security-data-protection/) container security

## 排錯快速判讀

### Image build cache 不命中

操作原則：COPY 順序錯、`.dockerignore` 缺、變動的 layer 在前面。

```bash
# TODO: docker build --progress=plain --no-cache 比對
```

### Image 過大

操作原則：base image 太重 / 沒 multi-stage / build context 過大。判讀：`docker history` 看 layer 大小。

### Container 起不來

操作原則：`docker logs` + `docker inspect` 看 exit code + state。

### Network port 不通

操作原則：`-p` mapping vs `EXPOSE` 差異、host network vs bridge network、firewall。

### Volume 權限問題

操作原則：container UID 跟 host UID 不對齊、rootless mode 特別容易踩。

## 何時改走其他服務

| 需求形狀                    | 改走                                                              |
| --------------------------- | ----------------------------------------------------------------- |
| Production orchestration    | [Kubernetes](/backend/05-deployment-platform/vendors/kubernetes/) |
| Rootless / 安全強化         | Podman                                                            |
| 替代 Docker Desktop（cost） | Rancher Desktop / Colima / Lima                                   |
| 純單機 service              | [systemd](/backend/05-deployment-platform/vendors/systemd/)       |
| 雲端 managed container      | ECS / Cloud Run / Container Apps                                  |
| Build-only（無 daemon）     | Buildah / Kaniko / BuildKit standalone                            |

## 不在本頁內的主題

- Dockerfile 完整 reference
- Docker Compose v2 進階配置
- Container runtime spec（runc / OCI）
- 各 registry 完整 API

## 案例回寫

### 跨 vendor 對照

| 案例                                                                                          | 對 Docker 的對應            |
| --------------------------------------------------------------------------------------------- | --------------------------- |
| [5.C10 規模對照](/backend/05-deployment-platform/cases/contrast-platform-migration-by-scale/) | 小規模直接 Docker / Compose |

**待補 Docker 案例**：Docker Hub rate limit incident、企業 license 遷移到 Podman 案例、image scanning supply chain 案例。

## 下一步路由

- 上游概念：[5.1 container runtime](/backend/05-deployment-platform/container-runtime/)
- 平行 vendor：[Kubernetes](/backend/05-deployment-platform/vendors/kubernetes/)、[systemd](/backend/05-deployment-platform/vendors/systemd/)
- 下游能力：[07 security](/backend/07-security-data-protection/)（image scanning / SBOM）
