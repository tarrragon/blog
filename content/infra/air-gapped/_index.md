---
title: "斷網環境的 infra：沒有網路時怎麼做"
date: 2026-06-26
description: "實體隔離或無法連網的環境裡，IaC、套件管理、容器映像、監控、CI/CD 怎麼運作 — 原則不變、工具路徑全部要換"
weight: -4
tags: ["infra", "air-gapped", "offline", "security"]
---

斷網環境（air-gapped）是跟網際網路完全隔離的執行環境——沒有 `apt install`、沒有 `terraform init` 自動下載 provider、沒有 Docker Hub 可以 pull image、沒有 GitHub Actions 可以跑 CI。這個約束不改變 infra 的原則（可重建、可追蹤、可審查），但改變了幾乎所有工具的使用方式。

常見的斷網情境：政府或軍事機密網路（實體隔離）、工控與 OT 環境（工廠、電廠、SCADA）、金融交易系統的高安全隔離區、醫療設備網路、以及地端機房裡刻意不開 internet access 的 private zone。

這個模組是橫切約束——它影響[模組一（IaC 選型）](/infra/01-minimal-iac/)到[模組七（PR 流程）](/infra/07-infra-as-pr/)的每一個操作步驟。每篇文章處理一個被斷網影響的主要面向。

## 章節文章

| 文章                                                                            | 主題                                                            |
| ------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| [斷網環境的通用原則](/infra/air-gapped/air-gapped-principles/)                  | 離線套件管理、內容搬運、變更追蹤的共通操作模式                  |
| [斷網環境的 IaC](/infra/air-gapped/air-gapped-iac/)                             | Terraform provider mirror、離線 state backend、plan/apply 流程  |
| [斷網環境的容器與映像管理](/infra/air-gapped/air-gapped-container/)             | Private registry、映像搬運、離線 base image 更新                |
| [斷網環境的監控與可觀測性](/infra/air-gapped/air-gapped-monitoring/)            | Self-hosted 監控工具、離線告警、log 收集                        |
| [斷網環境要自建的服務清單](/infra/air-gapped/air-gapped-self-hosted-services/)  | 10 類服務的選型、部署順序、統一管理 vs 個別部署、維護成本       |
| [斷網環境的版控與 CI/CD](/infra/air-gapped/air-gapped-vcs-ci/)                  | GitLab CE / Gitea 離線安裝、CI runner、git bundle 跨邊界傳輸    |
| [斷網環境的套件與容器 Registry](/infra/air-gapped/air-gapped-package-registry/) | Nexus 統一 proxy、Harbor 容器 registry、映像搬運 SOP、Helm 離線 |
| [斷網環境的基礎服務](/infra/air-gapped/air-gapped-infrastructure-services/)     | DNS (CoreDNS) + NTP (chrony) + CA (step-ca) + Vault             |
| [斷網環境的資安與權限控管](/infra/air-gapped/air-gapped-security-access/)       | 威脅模型轉變、實體安全、離線認證、稽核日誌、跨邊界安全審查      |

## 跟其他模組的關係

- → [模組一：最小可行 IaC](/infra/01-minimal-iac/)：斷網時 IaC 工具選型和 state backend 的替代做法
- → [模組五：核心服務上 IaC](/infra/05-core-services/)：容器映像和套件依賴的離線管理
- → [模組六：可觀測性](/infra/06-observability-logging/)：斷網環境的監控不能 phone home
- → [模組七：PR 流程](/infra/07-infra-as-pr/)：CI/CD 在內網怎麼跑
- → [接手維運](/infra/takeover/)：接手斷網環境的額外約束
