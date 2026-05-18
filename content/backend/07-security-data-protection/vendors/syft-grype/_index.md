---
title: "Syft + Grype"
date: 2026-05-18
description: "Anchore 開源姐妹工具：Syft 產 SBOM (CycloneDX / SPDX) + Grype scan 漏洞、Unix philosophy、cosign attestation 整合"
weight: 8
tags: ["backend", "security", "vendor", "syft", "grype", "sbom", "supply-chain", "open-source"]
---

Syft 跟 Grype 是 Anchore 開源的 *姐妹工具*（Apache 2.0、免費）、各做一件事、用 pipe 串接成 *SBOM-first* 的 supply chain scan 鏈：**Syft** 掃 container image / 檔案系統 / 目錄、產出標準 SBOM（CycloneDX 1.5+ / SPDX 2.3 / SyftJSON）；**Grype** 吃 SBOM 或直接 scan target、比對 Grype-DB 回報 CVE。設計哲學是 Unix philosophy — `syft image:tag -o cyclonedx-json | grype` 等價於 `grype image:tag`、但中間的 SBOM 是 *正式 artifact*、可以單獨簽章、單獨保存、單獨給下游消費。跟 [Trivy](/backend/07-security-data-protection/vendors/trivy/) 全包式設計不同、跟 [Snyk](/backend/07-security-data-protection/vendors/snyk/) 商業 SaaS 路線也不同。

## 服務定位

Syft + Grype 的核心定位是 *SBOM-first 的 OSS supply chain scan tool chain*。SBOM 不是中間產物、是 *正式可簽章 artifact*：Syft 產 SBOM 後通常用 [Sigstore cosign](https://docs.sigstore.dev/) `attest --predicate sbom.cdx.json` 把 SBOM 簽進 image OCI metadata、跟 image 一起發布；下游團隊 / 客戶 / scan pipeline 拿 *trusted SBOM* 跑 Grype、不需要重新 scan image。對 *air-gapped 環境*、*multi-team handoff*、*合規場景*（EO 14028 / FedRAMP 要求交付 CycloneDX 或 SPDX）特別合適。

跟 [Trivy](/backend/07-security-data-protection/vendors/trivy/) 的差異是 *分工 vs 全包*：Trivy 一個 binary 把 SBOM 生成 + vuln scan + IaC + secret + license 都做了；Syft + Grype 拆兩個工具、SBOM 互通流程適合、團隊偏好 Unix philosophy 選這條。功能覆蓋面 Trivy 略廣（含 IaC / secret scan）、Syft 的 SBOM 格式互通性是 OSS reference implementation。跟 [Snyk](/backend/07-security-data-protection/vendors/snyk/) 的差異更直接：Snyk 商業 SaaS、覆蓋廣（SAST / IaC / CSPM / Reachability）、有 dashboard 跟 fix PR；Syft + Grype 純 CLI、OSS 免費、聚焦 SBOM + vuln 兩件事、沒 server / 沒 dashboard、要 dashboard 走商業 Anchore Enterprise 或自接 JSON 到 Elasticsearch / Grafana。

關鍵 first-class concept：**Source**（OCI image / OCI archive / Docker daemon / dir / file / 既有 SBOM）、**Catalog**（Syft 內部 package inventory 結構）、**Package**、**Vulnerability**、**Match**（Grype 的 package ↔ CVE 配對）、**Match Configuration**（`grype.yaml` 設 severity gate / 比對策略）、**Vulnerability DB**（Grype-DB、Anchore 聚合 NVD + GHSA + 各 distro secdb）、**Ignore Rule**（CVE 例外、強制帶 expiration）。

## 本章目標

讀完本頁、讀者能判斷：

1. Syft 跟 Grype 各自的責任邊界、為什麼拆兩個工具比合一個工具好（SBOM 互通、attestation、air-gapped）
2. SBOM 格式（CycloneDX / SPDX / SyftJSON）的選擇、跟合規要求對應
3. Grype Match Configuration 跟 Ignore Rule 怎麼設、CI fail 條件怎麼定
4. 何時改走 [Trivy](/backend/07-security-data-protection/vendors/trivy/) 全包式、何時走 [Snyk](/backend/07-security-data-protection/vendors/snyk/) 商業 SaaS

## 最短判讀路徑

判斷 Syft + Grype 配置是否健康、最少看四件事：

- **SBOM 格式跟保存**：產出格式是否符合合規（多數 EO 14028 / FedRAMP 場景要 CycloneDX 或 SPDX、不是 SyftJSON）、SBOM 是否簽章（cosign attest）、是否集中保存（OCI registry 旁邊 / artifact store）、是否有 *baseline diff*（image 升級前後依賴變化）
- **Grype DB 更新**：DB 是否每日同步、air-gapped 場景是否 mirror 到內部 registry（Grype DB 是 OCI artifact、可 `oras pull` 鏡像）、DB version 是否進 SBOM scan record（重現性）
- **Match Configuration**：`grype.yaml` 的 severity gate（CI fail 條件、通常 high / critical fail）、`only-fixed: true` 是否開（只報有 patch 的 CVE）、`add-cpes-if-none: true` 對 binary-only package 行為
- **Ignore Rule 治理**：例外清單是否帶 *expiration*、`reason` 欄位是否填 ticket / decision 連結、quarterly review 機制、過期自動回到 fail 狀態

四件事任一缺失、就是 [Supply Chain Integrity](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/) 邊界的待補項目。

## 日常操作與決策形狀

**Syft 用法跟 Source 種類**：`syft <source> -o <format>` 是核心 — source 可以是 OCI image（`registry/image:tag`）、OCI archive（`oci-archive:image.tar`）、Docker daemon（`docker:image:tag`）、目錄（`dir:./`）、單一檔案、甚至既有 SBOM（`sbom:./prev.cdx.json`、用來 *轉格式*）。format 包括 `cyclonedx-json` / `cyclonedx-xml` / `spdx-json` / `spdx-tag-value` / `syft-json` / `table`。production 通常產 *cyclonedx-json*（合規要求最常見）+ 保留 *syft-json*（Syft 自家最完整、未來 round-trip 用）。

**Package detector 廣度**：Syft 自動偵測 OS package（apk / dpkg / rpm）+ 語言 dependency（npm / pip / gem / go module / cargo / maven / gradle / nuget / composer / hex / conan / swift / dart 等）+ binary analysis（Go binary 內 embedded module、Rust binary metadata、Java jar / war / ear nested）。對 *static binary* / *FAT image* 的支援是 Syft 的強項、比多數 SBOM tool 廣。但 *runtime-only dependency*（dlopen / dynamic load）SBOM 看不到、要靠 runtime workload protection（Falco / Cilium Tetragon 類工具、見 [7 後續候選 vendor 清單](/backend/07-security-data-protection/vendors/)）補。

**Grype 用法**：`grype <source>` 或 `grype sbom:./image.cdx.json`。輸出 `table` / `json` / `cyclonedx-json`（CycloneDX VEX 格式）/ `sarif`（GitHub code scanning）/ `template`（Go template 自訂）。production CI 通常 `--output sarif` 上傳 GitHub code scanning + `--output json` 進內部 SIEM。`grype sbom:./prev.cdx.json` 模式是 *SBOM-only scan*、不碰 image — 適合 *下游團隊拿 SBOM 持續 monitor*、原始 image 已經 frozen 或不可達。

**Match Configuration（`grype.yaml`）**：核心欄位包括 `fail-on-severity: high`（CI gate）、`only-fixed: true`（只回報有 fix 可用的 CVE、避免 noise）、`ignore` list（個別 CVE 例外）、`match` strategy（如何把 package CPE / PURL 對應到 CVE、預設策略對 90% 場景夠用、特殊 binary 場景才調）。所有設定走版控、`grype.yaml` 跟程式碼一起 review、避免 console 改。

**Ignore Rule 治理**：`grype.yaml` 的 `ignore` entry 結構：`vulnerability` + `reason` + `expiration`（YYYY-MM-DD）+ optional `package.name` / `fix-state`。Anchore 設計 *沒有「永久 ignore」*、必須帶 expiration — 強制 quarterly review、避免「五年前 ignore 的 CVE 早被 fix 了還在清單裡」。reason 欄位填 ticket 編號或 ADR link、給未來的人 context。

**Cosign attest SBOM**：`syft image:tag -o cyclonedx-json > sbom.cdx.json && cosign attest --predicate sbom.cdx.json --type cyclonedx --key cosign.key image:tag` — SBOM 被簽進 image 的 OCI signature manifest、下游 `cosign verify-attestation --type cyclonedx ...` 拿到 *cryptographically signed SBOM*。這把 SBOM 從「可被竄改的 JSON 檔」升級到 *trusted artifact*、是 [SLSA L3+](https://slsa.dev/) provenance 的基礎。

**SLSA / SPDX 流程整合**：Syft SBOM 是 build 階段產物、跟 SLSA provenance（誰 build 的、用什麼 builder、source commit 是什麼）併存、不互斥 — SBOM 答「裡面有什麼」、provenance 答「怎麼 build 的」。完整 supply chain trust 需要兩者 + cosign signature。

## 核心取捨表

| 取捨維度      | Syft + Grype                                           | Trivy                                          | Snyk                                                  |
| ------------- | ------------------------------------------------------ | ---------------------------------------------- | ----------------------------------------------------- |
| 工具拆分      | 兩個（Unix philosophy）                                | 一個（all-in-one binary）                      | SaaS + CLI（多模組）                                  |
| 授權          | OSS Apache 2.0                                         | OSS Apache 2.0                                 | 商業（freemium、付費才解鎖完整）                      |
| 部署模型      | CLI、無 server                                         | CLI、無 server                                 | SaaS dashboard + CLI                                  |
| SBOM 格式     | CycloneDX 1.5+ / SPDX 2.3 / SyftJSON（reference 實作） | CycloneDX / SPDX                               | CycloneDX / SPDX（次要、scan 為主）                   |
| Vuln 資料源   | Grype-DB（NVD + GHSA + 各 distro secdb 聚合）          | Trivy-DB（類似來源 + Aqua 加值）               | Snyk Intel（自家 research、含 reachability）          |
| 額外掃描      | 無（聚焦 SBOM + vuln）                                 | IaC / secret / license / k8s misconfig         | SAST / IaC / container / IaC / Open Source / Code     |
| Dashboard     | 無（Anchore Enterprise 商業才有）                      | 無（Aqua 商業才有）                            | 內建 SaaS dashboard                                   |
| Air-gapped    | 強 — Grype DB 是 OCI artifact、可 mirror               | 強 — Trivy DB OCI artifact                     | 弱 — SaaS-only 為主（自管 server 是 Enterprise）      |
| Reachability  | 無                                                     | 無                                             | 有（Java / JS）                                       |
| Fix PR 自動化 | 無                                                     | 無                                             | 有（auto PR、Renovate-like）                          |
| 適合場景      | OSS 偏好、SBOM 互通流程、air-gapped、Unix tool chain   | OSS 偏好、單一工具想包多事、k8s misconfig 也要 | 商業 SaaS、需 dashboard / fix workflow / reachability |

選 Syft + Grype 的核心訴求：*要正式 SBOM 作為交付 artifact*（合規 / 多 team handoff）+ *偏好 OSS Unix philosophy*（兩個工具各做一件事、容易整合自家 pipeline）+ 不需要 SaaS dashboard（自家 SIEM / Grafana 已經有）。需要 IaC scan 一起做、看一下 Trivy 是不是更省整合成本；需要 fix workflow 跟 reachability、商業預算足、走 Snyk。

## 進階主題

**SBOM attestation 完整鏈**：build pipeline 順序通常是 — build image → `syft image -o cyclonedx-json > sbom.cdx.json` → `cosign sign image` → `cosign attest --predicate sbom.cdx.json --type cyclonedx image` → push。下游 admission controller（Kyverno / Gatekeeper / Sigstore policy-controller）`verify-attestation` 拿 trusted SBOM、再 Grype scan、policy 決定是否允許 deploy。這條鏈把 SBOM 從 *文件* 升級成 *deploy gate*。

**Grype DB air-gapped sync**：Grype DB 是 OCI artifact（`ghcr.io/anchore/grype/listing.json` + `db.tar.gz`）、`oras pull` 或 `grype db update` 取得。air-gapped 場景：DMZ 跑 `grype db update --skip-listing-content-check`、把 `~/.cache/grype/db/` 整個 sync 到內部 mirror registry、內部 grype 透過 `GRYPE_DB_UPDATE_URL` 指到內部 listing。DB 版本進 scan record、確保 *相同 SBOM + 相同 DB = 相同結果*（可重現）。

**Custom matcher / Ignore Rule 細部**：Grype 預設 matcher 對 90% 場景夠、但 *Go binary*、*static-linked binary*、*custom C++ build* 可能需要 `add-cpes-if-none: true` 強制配對 CPE。Ignore Rule 支援 `vex-status` 欄位（accepted / under-investigation / fixed / not-affected）對齊 CycloneDX VEX 標準、輸出 VEX-enriched SBOM 給下游 / 客戶。

**Anchore Enterprise 商業整合**：OSS Syft + Grype 不夠時、Anchore Enterprise 加：policy engine（GraphQL 寫複雜 policy）、dashboard、RBAC、SLA-backed support、跟 Kubernetes admission integration、跟 Jira / ServiceNow ticket 自動建單。OSS 是 90% 場景的起點、Enterprise 解的是 *policy + workflow* 而非 *scan ability*。

**SBOM diff（baseline 比對）**：`syft` 自己沒內建 diff、但 `cyclonedx-cli diff` 或自家 script 可以比對 *image v1 SBOM* vs *image v2 SBOM*、找出新增 / 移除 / 升級的 package。用途：[XZ backdoor](/backend/07-security-data-protection/red-team/cases/supply-chain/xz-backdoor-2024-open-source-supply-chain/) 之類「相同 version 但被植入後門」事件、單靠 SBOM 看不出來、但 *baseline + behavior anomaly* 雙軌可以提早警示。

## 排錯與失敗快速判讀

- **Syft scan 找不到 package**：image 是 `FROM scratch` 或 distroless、Syft 偵測不到 OS package metadata — 改 scan source 為 build 階段的 `dir:./` 或保留 builder image 的 SBOM
- **Grype 報一堆 unfixed CVE**：base image 老、有 CVE 但 upstream 還沒 patch — 設 `only-fixed: true` 過濾 noise、focus 在 actionable item；同時排程 base image 升級
- **CI 突然 fail 變多**：Grype DB 更新後新 CVE 揭露 — 看 DB version diff、評估是 *真新風險* 還是 *舊 package 被重新分類*、必要時用 Ignore Rule + expiration 過渡
- **SBOM 格式下游不認**：合規要求 SPDX、產的是 SyftJSON — 用 `syft convert syft-json:./sbom.json -o spdx-json` 轉格式（Syft 本身就是 SBOM 互轉工具）
- **Air-gapped 環境 Grype 跑不動**：DB 沒同步、scan 直接報 0 vulnerability（假陰性）— `grype db status` 看 DB age、mirror sync 機制檢查、加 staleness alarm
- **Ignore Rule 過期回到 fail**：CI 突然 fail、查 expiration 已過 — 預期行為、強制 quarterly review；補 rotation 機制（cronjob 提前一週 alert owner）
- **Binary 偵測不到 module**：Go binary stripped、`-trimpath` 後 module path 沒了 — build 改加 `-buildvcs=true` 保留 VCS info、或 build 階段 SBOM scan source code、不是 binary
- **cosign verify-attestation 失敗**：image 被 re-tag / re-push 後 attestation manifest 不對 — 用 image digest（`@sha256:...`）而非 tag 做 attest、tag 不可信
- **Grype 不抓某個 ecosystem**：例如新冒出的 package manager — Syft 沒實作 detector、Grype 也看不到；submit issue 或自己寫 catalogger 貢獻

## 何時改走其他服務

| 需求形狀                                   | 改走                                                                                                   |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| 一個工具想包 IaC / secret / k8s misconfig  | [Trivy](/backend/07-security-data-protection/vendors/trivy/)                                           |
| 需要 SAST / Reachability / Fix PR workflow | [Snyk](/backend/07-security-data-protection/vendors/snyk/)                                             |
| 綁 GitHub 的 SAST + Dependabot             | [GitHub Advanced Security](/backend/07-security-data-protection/vendors/github-advanced-security/)     |
| Container runtime detection                | Falco / Cilium Tetragon（見 [7 後續候選 vendor 清單](/backend/07-security-data-protection/vendors/)）  |
| Image signing / attestation                | [Sigstore cosign](https://docs.sigstore.dev/)                                                          |
| Policy at admission                        | Kyverno / OPA Gatekeeper（見 [7 後續候選 vendor 清單](/backend/07-security-data-protection/vendors/)） |
| SBOM dashboard / enterprise policy / RBAC  | Anchore Enterprise（商業）                                                                             |

## 不在本頁內的主題

- CycloneDX / SPDX 完整 schema 規格逐欄位解讀
- Sigstore cosign / Rekor / Fulcio 完整架構（attest 鏈的 OIDC / transparency log）
- SLSA framework 各 level 對應的 builder 要求
- Anchore Enterprise policy DSL 完整語法
- VEX（Vulnerability Exploitability eXchange）跟 CSAF 標準對照細節

## 案例回寫

07 案例庫沒有直接 Syft / Grype-level 事件、但供應鏈案例都是 SBOM-first 思維的對照：

| 案例                                                                                                                                   | 跟 Syft + Grype 的關係                                                                                                              |
| -------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| [Log4Shell CVE-2021-44228](/backend/07-security-data-protection/red-team/cases/supply-chain/log4shell-cve-2021-44228-component-chain/) | 對照啟示 — 預先用 Syft 產 SBOM 集中保存後、Log4Shell 公開時拿歷史 SBOM 跑 Grype 在分鐘級回答「我們哪些服務有用、含 transitive」     |
| [SolarWinds 2020 Sunburst](/backend/07-security-data-protection/red-team/cases/supply-chain/solarwinds-2020-sunburst/)                 | 對照啟示 — Syft 看 package layer、看不到 build-time backdoor 注入；需配 cosign attest + SLSA provenance 才完整                      |
| [XZ Backdoor 2024](/backend/07-security-data-protection/red-team/cases/supply-chain/xz-backdoor-2024-open-source-supply-chain/)        | 對照啟示 — 相同 version 被植入後 SBOM 一樣、純比對 SBOM 看不出來；mitigation 是 SBOM diff 對 baseline + release tarball verify      |
| [Kaseya VSA 2021](/backend/07-security-data-protection/red-team/cases/supply-chain/kaseya-vsa-2021-msp-ransomware-chain/)              | 對照啟示 — 多服務 SBOM 集中 inventory（哪 service 用哪 component）、緊急時可 *affected-services-by-package* 反查、不是逐 image scan |
| [7.12 供應鏈完整性與 Artifact 信任](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)                   | Syft 是 SBOM reference implementation、章節原則對應 SBOM + signing + provenance 的 trust chain                                      |

## 下一步路由

- 上游：[7.12 供應鏈完整性與 Artifact 信任](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)
- 平行：[Trivy](/backend/07-security-data-protection/vendors/trivy/)（一站式替代）、[Snyk](/backend/07-security-data-protection/vendors/snyk/)（商業 SaaS）、[GitHub Advanced Security](/backend/07-security-data-protection/vendors/github-advanced-security/)（GitHub 內建）
- 下游：[Sigstore cosign](https://docs.sigstore.dev/)（SBOM attestation）、admission policy（Kyverno / OPA Gatekeeper、見 [7 後續候選 vendor 清單](/backend/07-security-data-protection/vendors/)）
- 跨類：runtime workload protection（Falco / Cilium Tetragon、見 [7 後續候選 vendor 清單](/backend/07-security-data-protection/vendors/)）、[HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)（cosign signing key 保存）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（新 CVE 揭露時的 SBOM-based fan-out 查詢）
- 官方：[Syft Documentation](https://github.com/anchore/syft) / [Grype Documentation](https://github.com/anchore/grype)
