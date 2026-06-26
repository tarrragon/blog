---
title: "斷網環境要自建的服務清單"
date: 2026-06-26
description: "正常環境消費的 SaaS（GitHub、Docker Hub、npm、Datadog）在斷網環境全部要自建 — 服務清單、選型、部署順序、統一管理取捨與維護的隱藏成本"
weight: 5
tags: ["infra", "air-gapped", "self-hosted"]
---

連網環境的 infra 團隊消費數十個 SaaS 服務：程式碼放 GitHub、CI 用 GitHub Actions、套件從 npm 和 PyPI 拉、container image 從 Docker Hub pull、憑證用 Let's Encrypt 自動簽、監控用 Datadog。這些服務的共同特性是「有人幫你維護」——infra 團隊只需要設定和使用，不需要部署、升級、備份。

斷網環境裡這些服務全部要自建。每一個 SaaS 變成一個內部服務，infra 團隊承擔它的部署、設定、升級、備份、監控和使用者管理。這篇文章盤點完整的服務清單、推薦的自建工具、部署順序，以及容易被低估的維護成本。

## 服務清單與選型

| 服務類別       | 連網環境的 SaaS          | 自建替代                    | 部署複雜度 | 維護頻率   |
| -------------- | ------------------------ | --------------------------- | ---------- | ---------- |
| 版本控制       | GitHub / GitLab.com      | GitLab CE / Gitea           | 中         | 月級更新   |
| CI/CD          | GitHub Actions           | Jenkins / GitLab CI         | 高         | 週級維護   |
| 套件 registry  | npm / PyPI / Maven / apt | Nexus Repository            | 中         | 月級更新   |
| 容器 registry  | Docker Hub / ECR         | Harbor / Docker Registry    | 中         | 月級更新   |
| 內部 CA        | Let's Encrypt            | step-ca / cfssl             | 低         | 季級輪替   |
| 內部 DNS       | Route 53 / Cloud DNS     | CoreDNS / BIND              | 低         | 變更時維護 |
| 時間同步       | pool.ntp.org             | chrony                      | 低         | 部署後極少 |
| 監控           | Datadog / New Relic      | Prometheus + Grafana + Loki | 高         | 週級維護   |
| 機密管理       | AWS Secrets Manager      | HashiCorp Vault             | 高         | 月級維護   |
| IaC state 後端 | S3 + DynamoDB            | PostgreSQL / Consul         | 低         | 變更時維護 |

「部署複雜度」指首次部署到可用狀態的工程量。「維護頻率」指部署完成後的持續性工作——安全更新、容量擴充、故障排查。

### 各服務的選型判斷

**版本控制**：GitLab CE 功能完整（含 CI/CD、container registry、package registry），但資源消耗大（建議 4 核 / 8GB 以上）。Gitea 輕量（512MB 記憶體可跑），適合小團隊或只需要 Git hosting 的情境。如果選 GitLab CE，版控 + CI/CD + registry 可以用同一個實例，減少部署數量。

**CI/CD**：如果已部署 GitLab CE，內建的 GitLab CI 是最低成本的選擇——Runner 裝在同一網段的機器上即可。Jenkins 的生態更大（plugin 多），但 plugin 的離線安裝和更新需要額外的搬運流程。

**套件 registry**：Nexus Repository 是斷網環境的首選，因為它用一個實例同時支援 apt / yum / npm / Maven / PyPI / Docker / Helm——維護一個服務取代六個獨立的離線 repo mirror。Artifactory 是商業替代品，功能相似但需要授權費。

**容器 registry**：Harbor 提供映像掃描（整合 Trivy）、RBAC、複寫、稽核 log。如果只需要儲存和拉取映像、不需要掃描和稽核，Docker Registry（開源）足夠。

**內部 CA**：step-ca 支援 ACME 協定（跟 Let's Encrypt 相同的自動簽發流程），內部服務可以用跟外部一樣的 certbot 工具自動續期。cfssl 是更輕量的選擇但沒有 ACME 支援、需要手動或腳本續期。

**內部 DNS**：CoreDNS 用設定檔驅動、輕量、適合 Kubernetes 環境。BIND 是傳統選擇、功能完整但設定複雜。多數斷網環境的 DNS 需求簡單（幾十筆 A record），CoreDNS 的 file plugin 足夠。

**時間同步**：chrony 是 NTP 的現代替代——啟動快、適應性強、低資源。內網裡指定一台機器當 NTP server（stratum 1 如果有 GPS 時鐘、stratum 2 如果手動校時），其他機器指向它。時間不同步會讓 log correlation 失效、TLS 憑證驗證失敗、Kerberos 認證拒絕。

**監控**：Prometheus（metric 收集）+ Grafana（視覺化）+ Loki（log 聚合）是最常見的 self-hosted 監控組合。三者都支援離線部署、不需要外部依賴。詳見[斷網環境的監控與可觀測性](/infra/air-gapped/air-gapped-monitoring/)。

**機密管理**：HashiCorp Vault 提供 secret 儲存、動態 secret 產生、PKI、加密即服務。部署和維護複雜度高——Vault 本身需要 unseal、HA 需要 Raft 或 Consul 後端、稽核 log 需要儲存規劃。如果機密數量少且變更不頻繁，加密的 ansible-vault 或 git-crypt 是輕量替代。

**IaC state 後端**：PostgreSQL 是 Terraform 支援的 state backend 之一（`backend "pg"`），斷網環境裡用既有的 PostgreSQL 實例存 state、用 PostgreSQL 的 advisory lock 防並行。比自建 S3 + DynamoDB 簡單得多。Consul 是另一個選擇（Terraform 原生支援），但引入 Consul 只為了存 state 的 ROI 通常不划算、除非環境裡已經有 Consul 跑 service discovery。

## 部署順序

服務之間有依賴關係，部署順序由依賴方向決定：

```text
第一層（基礎設施服務）
  DNS → 所有服務都需要名稱解析
  NTP → 所有服務都需要時間同步
  CA  → 所有服務都需要 TLS 憑證

第二層（開發平台服務）
  版本控制 → 程式碼要有地方存才能跑 CI
  套件 + 容器 registry → build 需要依賴

第三層（自動化服務）
  CI/CD → 依賴版控 + registry
  IaC state backend → Terraform 需要 state 存放處

第四層（營運服務）
  機密管理 → 其他服務的 secret 集中管理
  監控 → 監控所有上述服務的健康
```

第一層的三個服務可以平行部署——它們彼此不依賴。第四層的監控放最後是因為它要監控的對象都還沒就位時、設定 target 沒有意義。

每一層部署完成後做一次整體驗證（所有服務能互相連通、TLS 正常、時間同步），再進下一層。

## 統一管理 vs 個別部署

GitLab CE 把版控、CI/CD、container registry、package registry 打包在一個實例裡。用 GitLab CE 取代四個獨立服務的優缺點：

| 面向     | 統一（GitLab CE）                     | 個別部署           |
| -------- | ------------------------------------- | ------------------ |
| 部署成本 | 部署 1 個服務                         | 部署 4 個服務      |
| 維護     | 升級 1 個服務                         | 各自升級週期       |
| 資源消耗 | 單機 8GB+ 記憶體                      | 分散在多台         |
| 故障半徑 | GitLab 掛 = 版控 + CI + registry 全停 | 某一個掛不影響其他 |
| 靈活性   | 綁 GitLab 生態                        | 各服務可獨立替換   |

小團隊（5-15 人）的斷網環境，GitLab CE 統一管理的 ROI 通常較高——維護一個服務比維護四個省力，故障半徑的風險靠備份和 HA（GitLab 支援 Geo replication）緩解。

大團隊或高安全環境，個別部署的隔離性較好——CI runner 跟版控分開、registry 跟 CI 分開，每個服務的存取控制和稽核獨立。

同樣的邏輯適用於 Nexus：它用一個實例服務 6 種格式的套件，比為每種格式各建一個離線 mirror 省力。

## 維護的隱藏成本

自建服務的維護成本容易被低估，因為部署完成時感覺「已經做完了」，但持續性維護才剛開始。每個自建服務需要：

| 維護項目   | 頻率   | 漏做的後果                             |
| ---------- | ------ | -------------------------------------- |
| 安全更新   | 月級   | 已知漏洞暴露在內網（斷網不代表零風險） |
| 備份       | 日級   | 服務掛了資料沒了                       |
| 容量監控   | 週級   | 磁碟滿了服務停擺                       |
| 憑證續期   | 季級   | TLS 過期、服務拒絕連線                 |
| 使用者管理 | 變更時 | 離職員工仍有存取權                     |
| 監控的監控 | 持續   | 監控系統本身掛了沒人知道               |

10 個自建服務各自都有這六項維護需求。時程參考：每月的例行維護（安全更新 + 備份驗證 + 容量檢查）約需 2-3 天工程師時間。這筆時間是隱性的——不在任何 sprint 或 ticket 裡，但不做的後果是累積的。

管理層溝通時的關鍵數字：自建 10 個服務的維護成本約等於 0.3-0.5 個全職工程師。這筆人力投入是斷網環境的結構性成本，跟應用開發無關。

## 跨分類引用

- → [斷網環境的通用原則](/infra/air-gapped/air-gapped-principles/)：內容搬運、離線套件管理的共通模式
- → [斷網環境的 IaC](/infra/air-gapped/air-gapped-iac/)：state backend（PostgreSQL）和 CI 的詳細設定
- → [斷網環境的容器與映像管理](/infra/air-gapped/air-gapped-container/)：Harbor 和映像搬運的詳細操作
- → [斷網環境的監控與可觀測性](/infra/air-gapped/air-gapped-monitoring/)：Prometheus + Grafana + Loki 的部署
- → [模組二：身分與憑證地基](/infra/02-identity-credentials/)：Vault 的身分管理與 infra IAM 的關係
- → [模組八：治理好習慣](/infra/08-governance-habits/)：自建服務的 secret 管理與成本歸因
