---
title: "Trivy"
date: 2026-05-18
description: "Aqua Security 開源 all-in-one scanner：Container / Filesystem / K8s / IaC + Secret + License + SBOM、Apache 2.0、CI 友善"
weight: 7
tags: ["backend", "security", "vendor", "trivy", "container-scan", "sca", "iac-scan", "open-source"]
---

Trivy 是 Aqua Security 維護的 *open-source all-in-one security scanner*、Apache 2.0、單一 CLI 涵蓋 container image / filesystem / git repo / Kubernetes / IaC 五種 scan target、額外做 secret / license / SBOM scan。設計目標跟 [Snyk](/backend/07-security-data-protection/vendors/snyk/) 不同 — Snyk 是 SaaS-first、用 server-side dashboard 跨 SCM / 跨 repo 聚合；Trivy 是 CLI-first、零 server、CI runner 自己就能完成所有工作、air-gapped 環境也能跑。商業版 Aqua Platform 加 dashboard / RBAC / policy / runtime defense、但 Trivy 本身免費覆蓋大部分團隊需求。

## 服務定位

Trivy 的核心定位是 *把 supply chain scan 收斂成一個 CLI*。同一個 binary 處理 container image、source tree、K8s cluster live state、Terraform / Dockerfile / CloudFormation 配置、secret / license / SBOM — 不需要拼裝多個工具、不需要 SaaS account、不需要 server。跟 [Snyk](/backend/07-security-data-protection/vendors/snyk/) 商業 SaaS 的差異是 *資料治理權* 在自己這邊（scan 結果不上 vendor cloud）、代價是 *跨 repo 集中報表* 需要自己拼（用 Trivy Operator 或 Aqua Platform）。

跟 [Syft + Grype](/backend/07-security-data-protection/vendors/syft-grype/) 的差異是 *工具邊界劃法*。Anchore Syft 專做 SBOM 生成、Grype 專做 vuln scan、兩個工具靠 SBOM 標準（CycloneDX / SPDX）串接；Trivy 一個 CLI 全包、SBOM 也同樣輸出標準格式。多 vendor 並存環境（例：build pipeline 用 Syft 生 SBOM、release gate 用 Grype scan、跟 SBOM repository 互通）Syft+Grype 模組化較適合；單一團隊單一 pipeline 想 *一次裝完* 用 Trivy 更直接。

跟 [GitHub Advanced Security](/backend/07-security-data-protection/vendors/github-advanced-security/) 的差異是 *偵測類型 + 部署面*。GHAS 綁 GitHub、SAST（CodeQL）覆蓋深、但容器掃跟 IaC scan 較弱；Trivy 跨 SCM、容器跟 IaC 掃強、但沒 SAST 深度。跟 Clair（RedHat / Quay 內建）或 Anchore Enterprise 比、Trivy 用戶基數大（CNCF Sandbox）、社群更新快、整合面廣（GitLab CI / GitHub Actions / Jenkins / CircleCI 都有官方 step）。

## 本章目標

讀完本頁、讀者能判斷：

1. Trivy 的五種 scan target（image / fs / repo / k8s / config）各承擔哪段 supply chain 責任、什麼時候用哪個
2. Trivy DB 的更新模型（OCI artifact、6 小時 cadence、air-gapped mirror）跟 CI runner 信任邊界
3. `.trivyignore` 跟 severity gate 在 CI 怎麼接、exception 治理要設哪些 tripwire
4. 何時用 Trivy、何時改走 [Snyk](/backend/07-security-data-protection/vendors/snyk/) / [Syft + Grype](/backend/07-security-data-protection/vendors/syft-grype/) / [GHAS](/backend/07-security-data-protection/vendors/github-advanced-security/) 的取捨

## 最短判讀路徑

判斷 Trivy 配置是否健康、最少看四件事：

- **scan target 覆蓋面**：是否 image / fs / config / secret 四類都跑（不是只 scan image）、CI 是否把 dev container / base image / runtime image 全納入 — 漏掉 base image 等於信任 upstream registry
- **Trivy DB 更新 cadence**：CI runner 是否每次都 pull 最新 DB（OCI artifact、預設 6 小時 TTL）、air-gapped 環境是否有內部 mirror（`--db-repository` 指到內部 registry）、`trivy --skip-db-update` 是否被誤用
- **severity gate 是否真的 fail build**：Trivy 預設 scan 完 exit 0、CI 不會 fail；需要 `--exit-code 1 --severity HIGH,CRITICAL` 才會把 PR build 擋下來、否則 scan 結果只在 log、沒人看
- **`.trivyignore` 治理**：ignore 的 CVE 有 reason + expiration 嗎、quarterly review 流程在嗎、`.trivyignore.yaml` 有用嗎 — 沒治理的 ignore list 會無限膨脹、最後等於沒 scan

四件事任一缺失、就是 [supply chain integrity](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/) 邊界的待補項目。

## 日常操作與決策形狀

**CLI 五種 scan target**：`trivy image <ref>` 掃 container image 的 OS package + language dependency；`trivy fs <dir>` 掃 source tree（含 lockfile + Dockerfile + IaC manifest + secret）；`trivy repo <url>` 不 clone 直接掃 git repo；`trivy k8s --report summary cluster` 掃 K8s cluster 內所有 workload（image + manifest 配置）；`trivy config <dir>` 專掃 IaC 配置（Terraform / CloudFormation / K8s YAML / Dockerfile / Helm）。本地 dev 最常用 `trivy fs .`、CI 最常用 `trivy image $IMAGE`、K8s 場景用 Trivy Operator 跑 in-cluster scan。

**Trivy DB（OCI artifact）**：Trivy 自己維護 vulnerability DB、以 OCI artifact 形式存在 `ghcr.io/aquasecurity/trivy-db`、每 6 小時更新一次。CI runner 第一次 scan 自動 pull、後續用 cache。air-gapped 環境（金融 / 政府 / 工控）需要把 DB mirror 到內部 OCI registry、`--db-repository internal.registry/trivy-db` 指過去。DB 內容是 aggregated source — NVD、GHSA、各 Linux distro security advisory、language ecosystem advisory（npm / PyPI / Maven / RubyGems / crates.io / Go / etc.）合在一起、所以單一查詢就能跨多生態。

**`.trivyignore` 跟 `.trivyignore.yaml`**：scan 發現的 CVE 若已評估無風險（無 reachable code path、已有 mitigation、upstream 尚未 patch 但業務不受影響）寫進 `.trivyignore`（純 CVE-ID list）或 `.trivyignore.yaml`（含 `expired_at` + `comment` + `paths`、更適合治理）。後者強制每筆 ignore 有 expiration（建議 quarterly）跟 reason、過期自動失效、避免 ignore list 變成「忘了清的死帳」。CI 應該每季跑 `trivy --ignorefile .trivyignore.yaml` 同時 alert 即將過期的條目。

**Severity gate 是 CI 必設**：Trivy 預設 scan 完 print 結果但 exit 0、CI build 不會 fail。要在 CI 真正擋下高風險 PR、必須 `trivy image --exit-code 1 --severity HIGH,CRITICAL $IMAGE`。Severity 級別（UNKNOWN / LOW / MEDIUM / HIGH / CRITICAL）對應 CVSS score、團隊需要決定 *什麼 severity 算 release blocker*。常見 baseline：CRITICAL fail PR build、HIGH fail nightly build（給 24 小時修補窗口）、MEDIUM 進 backlog ticket。

**SBOM 生成與 scan**：`trivy image --format cyclonedx --output sbom.json $IMAGE` 生 CycloneDX 格式 SBOM、`--format spdx-json` 生 SPDX。也可以反向 — 拿別人生的 SBOM 餵給 Trivy：`trivy sbom sbom.json` 跑 vuln scan、不重新解析 image。這個 workflow 跟 [Syft + Grype](/backend/07-security-data-protection/vendors/syft-grype/) 重疊（Syft 生 SBOM + Grype scan SBOM）、差別是 Trivy 一站完成、Syft+Grype 拆兩階段更模組化。SBOM artifact 進 OCI registry（用 cosign attach）或 SBOM repository（如 Dependency-Track）做長期追蹤。

**Misconfig + Secret + License 一起 scan**：`trivy fs .` 預設啟用四類 scanner — vuln（package CVE）、misconfig（IaC 配置錯誤）、secret（hardcoded credential）、license（license compliance）。Misconfig 內建 hundreds of built-in policy（Rego 寫的）涵蓋 K8s / Terraform / Docker / CloudFormation 常見錯誤（privileged container / open S3 bucket / 0.0.0.0/0 ingress）。Secret scanner 用 regex pattern 找 AWS access key / GCP service account / Stripe key 等常見格式、不是萬能、但 dev pre-commit 攔截已洩漏 secret 很實用。

**Trivy Operator（K8s in-cluster scanner）**：K8s 場景的標準配置。Operator 在 cluster 跑、定期 scan 所有 namespace 的 workload、產 CRD reports：`VulnerabilityReport`（image CVE）、`ConfigAuditReport`（manifest 配置）、`SbomReport`、`ClusterComplianceReport`（CIS Kubernetes Benchmark / NSA Kubernetes Hardening Guide）。Operator 可選配 ValidatingAdmissionWebhook、admission 階段拒絕高風險 image（CVE severity 超門檻）。Reports 是 CRD、可以走 `kubectl get vulnerabilityreport` 看、也可以 prometheus exporter 出 metric 進 Grafana。

**Aqua Platform 整合**：Trivy CLI / Operator 結果可以推到 Aqua Platform（商業版）做集中 dashboard、跨 cluster RBAC、policy engine、compliance report、runtime defense（runtime container 監控）。純 CLI 用戶不需要、但企業有多 cluster + 跨團隊 governance 需求時、Aqua Platform 補 server-side aggregation 那塊（對應 Snyk dashboard 的功能）。

## 核心取捨表

| 取捨維度         | Trivy                                              | Snyk                                                   | Syft + Grype                               | GitHub Advanced Security                     |
| ---------------- | -------------------------------------------------- | ------------------------------------------------------ | ------------------------------------------ | -------------------------------------------- |
| 部署模型         | CLI-only、零 server                                | SaaS-first、需要 Snyk account                          | CLI-only、兩個 binary                      | 綁 GitHub、整合在 PR / Code Scanning         |
| 授權             | Apache 2.0、完全免費                               | 商業 SaaS（Free tier + 付費 plan）                     | Apache 2.0、完全免費                       | GitHub Enterprise add-on                     |
| Scan target      | image / fs / repo / k8s / config                   | image / SCA / IaC / Code (SAST) / Container            | image / fs（SBOM-first）                   | SAST (CodeQL) + Dependabot + Secret scanning |
| Vulnerability DB | Trivy DB（OCI artifact、6h cadence、可 mirror）    | Snyk Intel（私有、含 reachability data）               | Grype DB（GitHub-hosted、可 mirror）       | GitHub Advisory DB                           |
| Reachability     | 無                                                 | 有（Snyk Code reachability）                           | 無                                         | 部分（CodeQL data flow）                     |
| SBOM 支援        | 生 + scan（CycloneDX / SPDX）                      | 生（Snyk SBOM）                                        | Syft 生、Grype scan、最完整 SBOM workflow  | 部分（Dependency Graph）                     |
| K8s in-cluster   | Trivy Operator（CRD reports + admission）          | Snyk Kubernetes（agent-based）                         | 無原生、靠外部 wrapper                     | 無                                           |
| 跨 repo 報表     | Trivy 本身無、Aqua Platform 補                     | Snyk dashboard（強項）                                 | 無原生、靠外部                             | GitHub Security tab（綁 GitHub）             |
| Air-gapped 支援  | 強 — DB 可 mirror 到內部 registry                  | 弱 — 需要 Snyk SaaS（Snyk On-Prem 商業版另算）         | 強 — DB 可 mirror                          | 弱 — 綁 GitHub.com                           |
| 學習曲線         | 低 — 一個 CLI + 通用 flag                          | 低 — UI 友善、CLI 也順                                 | 中 — 兩個工具拼、SBOM 概念要懂             | 中 — CodeQL query 寫 / 調有門檻              |
| 適合場景         | CI image scan、K8s scan、air-gapped、OSS-only 預算 | 跨 SCM 跨 repo 集中治理、SaaS 預算 OK、需 reachability | SBOM 為主軸的 supply chain、多 vendor 互通 | GitHub-only + 需要 SAST 深度                 |

選 Trivy 的核心訴求：*零 server / OSS-only 預算 / air-gapped 友善 / 一個 CLI 涵蓋 container + IaC + secret*。需要跨 SCM 集中 dashboard 跟 reachability 走 Snyk；純 SBOM workflow + 多工具互通走 Syft+Grype；GitHub-only + 重 SAST 走 GHAS。

## 進階主題

**Trivy Operator + admission control**：Operator 跑 ValidatingAdmissionWebhook、admission 階段對 Pod spec 的 image 跑 vuln check、超門檻就拒絕創建。對應 [supply chain integrity](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/) 的 *artifact gate at deploy time*。組態要小心 — webhook timeout / Trivy DB 不可用 / Operator 自己 down 都會擋住 deploy、production 通常 fail-open（DB 不可用時放行 + alert）而非 fail-close。

**Custom check（Rego policy）**：Trivy misconfig scanner 用 Rego 寫 policy、可以自己加 custom check（例：禁止特定 namespace 用 hostPath volume、禁止特定 IAM action）。policy 走 `--policy ./custom-policies/` 載入、跟內建 policy 一起跑。比 OPA Gatekeeper 簡單（不需要部署 admission webhook、scan-time 就執行）、但 runtime enforcement 還是要靠 Gatekeeper / Kyverno。

**Air-gapped DB sync**：金融 / 政府 / 工控環境 CI runner 不能連外網。流程是：有對外網的 staging machine 跑 `trivy --download-db-only` 把 OCI artifact 拉下來、用 `skopeo copy` 推到內部 OCI registry、CI runner 用 `--db-repository internal.registry/trivy-db --skip-db-update`（或排程從內部 mirror pull）。DB 更新節奏要排程化（每天 / 每 6 小時）、否則 air-gapped DB 落後幾天會 miss 掉新公布 CVE。

**Cosign + SLSA + Trivy 三件事**：Trivy 看的是 *known CVE*、看不到 *build-time backdoor*。配套需要 Sigstore cosign 做 image signature verify（確認 image 真的是自家 CI 出的）+ SLSA provenance（build pipeline 不可篡改紀錄）+ Trivy scan（known CVE）三件事一起、才是完整 supply chain trust chain。對應 [Cert-manager](/backend/07-security-data-protection/vendors/cert-manager/) 在 TLS 的角色、Trivy 在 supply chain 的角色是 *已知漏洞檢測*、不是 *trust establishment*。

## 排錯與失敗快速判讀

- **CI 顯示 scan 完但 build 沒 fail**：忘了 `--exit-code 1 --severity HIGH,CRITICAL`、scan 結果只在 log、PR 一直 merge 進高風險 image — 補 severity gate flag、設 baseline
- **Trivy DB 拉不下來 / 過期**：CI runner 沒對外網 / GitHub Container Registry 被擋 / DB cache 太舊 — 設內部 OCI mirror、CI runner `--db-repository` 指過去、排程 update
- **`.trivyignore` 無限膨脹**：用純 list 沒 expiration、團隊找不到誰加的 / 為什麼加 — 改 `.trivyignore.yaml` 強制 reason + expiration、quarterly review 排進 sprint
- **false positive 多到 alert fatigue**：base image 自帶大量未修補 OS package、scan 出 50+ HIGH — 換 distroless / Chainguard / Wolfi 等 *minimal base image*、或 multi-stage build 只保留必要 binary、不是調高門檻當沒看到
- **secret scanner 漏報**：hardcoded credential 是非標準格式（內部 token、特殊 vendor key）— 加 custom secret pattern、或配合 dedicated tool（Gitleaks / GitGuardian）做第二道
- **Trivy Operator 報表沒人看**：reports 是 CRD、`kubectl get` 才看到、PR / Slack 沒通知 — 接 prometheus exporter + Grafana alert、或 webhook 推 Slack
- **K8s admission webhook fail 擋住 deploy**：Operator down / DB 不可用、所有 Pod 創建被拒 — webhook 配 `failurePolicy: Ignore`、production 通常 fail-open + alert、不是 fail-close

## 何時改走其他服務

| 需求形狀                           | 改走                                                                                                         |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| 需 reachability / 跨 SCM dashboard | [Snyk](/backend/07-security-data-protection/vendors/snyk/)                                                   |
| SBOM-first / 多工具互通            | [Syft + Grype](/backend/07-security-data-protection/vendors/syft-grype/)                                     |
| SAST 深度 / GitHub-only            | [GitHub Advanced Security](/backend/07-security-data-protection/vendors/github-advanced-security/)（CodeQL） |
| 純依賴升級自動化                   | [Dependabot](/backend/07-security-data-protection/vendors/dependabot/)                                       |
| Runtime container monitoring       | Falco / Cilium Tetragon / Aqua Runtime（商業版）                                                             |
| TLS / mTLS cert lifecycle          | [cert-manager](/backend/07-security-data-protection/vendors/cert-manager/)                                   |
| Image signing / provenance         | Sigstore cosign + SLSA framework                                                                             |

## 不在本頁內的主題

- Trivy CLI 所有 flag 跟 output format 完整 reference
- Rego policy language 完整語法（OPA / Rego 自有體系）
- Aqua Platform 商業版完整功能矩陣（dashboard / RBAC / runtime defense）
- 各 PCI DSS / SOC 2 / FedRAMP 合規 mapping
- 跟其他 scanner（Clair / Anchore Enterprise / Twistlock）的逐項比較

## 案例回寫

Trivy 在 07 案例庫沒有 *直接 vendor-level 事件*（Trivy 本身 OSS、無 vendor-side 控制面風險）、但 supply chain 案例都對應 Trivy 的能力與邊界：

| 案例                                                                                                                                    | 跟 Trivy 的關係                                                                                                                                               |
| --------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Log4Shell CVE-2021-44228](/backend/07-security-data-protection/red-team/cases/supply-chain/log4shell-cve-2021-44228-component-chain/)  | 對照啟示 — CVE 公開後 Trivy DB 幾小時內更新、scan container image 找受影響 service 是緊急 response 主軸；air-gapped 環境 DB mirror 更新節奏直接決定窗口期長度 |
| [SolarWinds 2020 Sunburst](/backend/07-security-data-protection/red-team/cases/supply-chain/solarwinds-2020-sunburst/)                  | 對照啟示 — Trivy scan known CVE、看不到 build-time backdoor 植入；必須配合 image signing（cosign）+ SLSA provenance 才完整                                    |
| [3CX 2023 Desktop App Supply Chain](/backend/07-security-data-protection/red-team/cases/supply-chain/3cx-2023-desktopapp-supply-chain/) | 對照啟示 — container scan 看 image layer 內 known CVE、看不到 runtime callback / dynamic load；需配合 runtime monitoring（Falco / Tetragon）                  |
| [XZ Backdoor 2024](/backend/07-security-data-protection/red-team/cases/supply-chain/xz-backdoor-2024-open-source-supply-chain/)         | 對照啟示 — Trivy 比對 package name + version 對應 CVE、看不到 maintainer takeover；mitigation 走 SBOM provenance + maintainer trust baseline                  |
| [7.12 供應鏈完整性與 Artifact 信任](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)                    | 章節原則 — Trivy 是 *known CVE 檢測*、SBOM + signing + provenance 三件事一起才形成完整 trust chain                                                            |

## 下一步路由

- 上游：[7.12 供應鏈完整性與 Artifact 信任](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)
- 平行：[Snyk](/backend/07-security-data-protection/vendors/snyk/)、[Syft + Grype](/backend/07-security-data-protection/vendors/syft-grype/)、[GitHub Advanced Security](/backend/07-security-data-protection/vendors/github-advanced-security/)、[Dependabot](/backend/07-security-data-protection/vendors/dependabot/)
- 下游：[7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/)（image 漏洞最終影響的是 origin server 風險面）
- 跨類：[cert-manager](/backend/07-security-data-protection/vendors/cert-manager/)（TLS lifecycle）、[HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)（secret rotation 對應 Trivy secret scan 找到的 hardcoded credential）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（CVE 緊急 response 流程 / 高風險 image rollback）
- 官方：[Trivy Documentation](https://aquasecurity.github.io/trivy/)、[Trivy Operator](https://aquasecurity.github.io/trivy-operator/)
