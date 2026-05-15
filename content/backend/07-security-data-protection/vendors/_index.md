---
title: "資安與資料保護 Vendor 清單"
date: 2026-05-15
description: "規劃身份、秘密、金鑰、入口防護、供應鏈與偵測工具的服務頁撰寫順序與教學大綱"
weight: 90
tags: ["backend", "security", "data-protection", "vendor"]
---

資安與資料保護 Vendor 清單的核心責任是把安全服務名稱放回控制面、信任邊界、證據鏈與交接路由的判斷。每個服務頁先回答它承擔身份、秘密、傳輸、入口、資料保護、供應鏈或偵測哪一段控制責任，再討論導入條件、操作成本、例外治理與事故回寫。

## 讀法

資安服務要從控制問題進入。讀者如果要處理身份與授權，先回到 [7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)；如果要處理秘密與機器憑證，先回到 [7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)；如果要處理入口與伺服器暴露，先回到 [7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/)。

## T1 服務頁大綱

| 服務群             | 候選服務                                                        | 頁面要回答的核心問題                                                     |
| ------------------ | --------------------------------------------------------------- | ------------------------------------------------------------------------ |
| Identity / IdP     | Okta、Auth0、Keycloak、AWS IAM Identity Center                  | 人類身份、SSO、MFA、group、role 與 session 邊界如何治理                  |
| Cloud IAM          | AWS IAM、Google IAM、Azure RBAC                                 | cloud resource 權限、policy、role assumption 與 least privilege 如何落地 |
| Secrets / Vault    | HashiCorp Vault、AWS Secrets Manager、Google Secret Manager     | secret storage、rotation、lease、audit 與 application delivery 如何治理  |
| KMS / HSM          | AWS KMS、Google Cloud KMS、Azure Key Vault、CloudHSM            | key lifecycle、envelope encryption、rotation 與權限分離如何成立          |
| Edge / WAF         | Cloudflare WAF、AWS WAF、Fastly Next-Gen WAF                    | 入口防護、bot、rate limit、managed rule 與 false positive 如何取捨       |
| Certificate / PKI  | cert-manager、ACM、Let's Encrypt、SPIRE                         | TLS、mTLS、workload identity 與憑證生命週期如何自動化                    |
| Supply chain       | GitHub Advanced Security、Snyk、Dependabot、Trivy、Syft / Grype | SCA、container scan、SBOM、artifact trust 與 release gate 如何接軌       |
| SIEM / Detection   | Splunk、Elastic Security、Datadog Security、Chronicle           | 偵測訊號、log pipeline、alert quality 與 incident handoff 如何治理       |
| DLP / Data control | Google DLP、Microsoft Purview、BigQuery / S3 policy tooling     | 資料分類、遮罩、匯出、資料駐留與證據鏈如何落地                           |

## 服務頁標準章節

| 章節                 | 資安服務頁要補的內容                                                                    |
| -------------------- | --------------------------------------------------------------------------------------- |
| 服務定位             | 它是 identity、IAM、secret、KMS、WAF、PKI、supply chain、SIEM 還是 DLP                  |
| 本章目標             | 讀者能判斷控制面責任、信任邊界、證據需求、例外與事故交接                                |
| 最短判讀路徑         | 用「誰能做什麼、憑證在哪裡、入口如何暴露、證據是否可回查」快速定位                      |
| 日常操作與決策形狀   | onboarding、policy、rotation、rule update、exception、audit、handoff                    |
| 核心取捨表           | managed service、self-hosted control、cloud-native、SaaS security tool 的機會成本       |
| 進階主題             | federation、workload identity、mTLS、SBOM、DLP、multi-cloud policy                      |
| 排錯與失敗快速判讀   | over-permission、stale secret、broken rotation、WAF false positive、missing audit trail |
| 何時改走其他服務     | 觀測訊號回 04、release gate 回 06、入口部署回 05、事故處理回 08                         |
| 不在本頁內的主題     | 合規逐條法規解讀、完整 SOC 2 / HIPAA 流程、所有攻擊技術細節                             |
| 案例回寫與下一步路由 | 回到 7.C cases、7.B blue-team materials、8 incident write-back                          |

## 撰寫批次

| 批次 | 服務群                    | 撰寫目的                                                 |
| ---- | ------------------------- | -------------------------------------------------------- |
| S1   | Identity / Cloud IAM      | 建立人類身份、機器身份、role / policy baseline           |
| S2   | Secrets / KMS / PKI       | 建立 secret、key、certificate lifecycle 與 rotation 判準 |
| S3   | Edge / WAF / Supply chain | 建立入口防護、artifact trust 與 release gate 對照        |
| S4   | SIEM / Detection / DLP    | 建立偵測覆蓋、資料保護、證據鏈與事故 handoff             |

## 後續候選

| 類型              | 候選服務                                                       | 寫作重點                                                      |
| ----------------- | -------------------------------------------------------------- | ------------------------------------------------------------- |
| PAM / access      | Teleport、Boundary、Tailscale SSH、Cloudflare Access           | 管理面 access、session audit、just-in-time access             |
| CSPM / CNAPP      | Wiz、Prisma Cloud、Lacework、CrowdStrike Falcon Cloud Security | cloud posture、asset inventory、risk prioritization           |
| Policy as code    | OPA、Conftest、Kyverno、Gatekeeper                             | admission control、policy review、exception workflow          |
| Runtime detection | Falco、Cilium Tetragon                                         | syscall / runtime signal、container threat detection          |
| Secret scanning   | GitGuardian、Gitleaks                                          | leaked secret detection、developer workflow、rotation trigger |
| Data security     | Immuta、Privacera、Microsoft Purview                           | data access policy、masking、lineage、governance              |

主流覆蓋檢查的重點是分開 preventive control、detective control 與 response handoff。IAM / KMS / WAF / policy-as-code 是 preventive control；SIEM / runtime detection / secret scanning 是 detective control；PAM、incident channel 與 evidence write-back 連到 08 的 response handoff。

## 下一步路由

- 上游：[7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)
- 上游：[7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)
- 上游：[7.12 供應鏈完整性與 Artifact 信任](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)
- 案例：[7.C 資安案例正文](/backend/07-security-data-protection/cases/)
- 規劃：[0.17 後端真實服務討論大綱](/backend/00-service-selection/service-entity-discussion-outline/)
