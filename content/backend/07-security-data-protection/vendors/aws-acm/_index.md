---
title: "AWS ACM"
date: 2026-05-18
description: "AWS-managed certificate provisioning、DNS validation + auto-renewal、整合 ELB / CloudFront / API Gateway、Private CA 後端"
weight: 9
tags: ["backend", "security", "vendor", "aws-acm", "pki", "tls", "aws"]
---

AWS Certificate Manager (ACM) 是 AWS-managed 的 *certificate provisioning 服務*、解決兩件事：*public TLS cert 全自動化*（Amazon Trust Services 簽發、DNS validation 通過後 60 天前自動 renew）跟 *AWS-managed service 的 cert 整合*（[ELB / CloudFront / API Gateway / App Runner](https://docs.aws.amazon.com/acm/latest/userguide/acm-services.html) 直接 attach、不需要客戶持有私鑰）。內部 mTLS / 自管 endpoint 的 private cert 走另一個產品 ACM Private CA（PCA）— ACM 是 *frontend*、PCA 是 *自管 CA hierarchy backend*。

## 服務定位

ACM 的核心定位是 *AWS 平台內 cert 的全託管 lifecycle*。客戶不持私鑰、不跑 ACME client、不手動 renew — 但代價是 ACM public cert *只能 attach 到 AWS-managed service*（ELB / CloudFront / API Gateway / App Runner / Nitro Enclaves）、不能 export 給自管 Nginx / EC2 應用。Private cert 必須有 ACM Private CA (PCA) 後端、ACM 自己不是 CA。

跟其他 cert 工具的場景重疊度低、不是替代而是分工：[cert-manager](/backend/07-security-data-protection/vendors/cert-manager/) 走 cluster 內 K8s workload cert（Ingress / service mesh）、[Let's Encrypt](/backend/07-security-data-protection/vendors/letsencrypt/) 走跨平台公共 ACME cert（可 export 任何地方使用）、ACM Private CA 走自管 CA hierarchy（root + intermediate、客戶控制 policy）。常見組合：AWS-native endpoint 用 ACM、K8s workload + 自管伺服器走 cert-manager + Let's Encrypt、內部 mTLS root 走 PCA。詳細差異見「核心取捨表」。

## 本章目標

讀完本頁、讀者能判斷：

1. ACM public cert vs private cert vs imported cert 各自的使用邊界（能 attach 哪些 service、能不能 export）
2. DNS validation vs Email validation 的差異、跟 auto-renewal 條件的關聯
3. 跨 region 跟 CloudFront 的 us-east-1 限制如何處理
4. 何時 ACM 不夠用、要改走 cert-manager / Let's Encrypt / ACM Private CA

## 最短判讀路徑

判斷 ACM cert 部署是否健康、最少看四件事：

- **Cert 跟 service 整合**：cert ARN 是否真的 attach 到 ELB / CloudFront / API Gateway listener、`DescribeCertificate` 的 `InUseBy` 有沒有資源、有 cert 但沒 attach 等於 issue 失敗
- **DNS validation 設定**：cert 是 DNS 還是 Email validation、DNS 的 CNAME record 是否還留在 DNS（auto-renewal 需要這條 record 持續存在）、Route53 vs 外部 DNS 的責任分界
- **Renewal status**：`DescribeCertificate` 的 `RenewalSummary.RenewalStatus` 是 `SUCCESS` / `PENDING_AUTO_RENEWAL` / `FAILED`、失敗時 `RenewalStatusReason` 是什麼（多半是 DNS record 被刪、CNAME 不再回應）
- **CloudTrail 證據**：`RequestCertificate` / `ImportCertificate` / `DeleteCertificate` 的 caller identity、是否有非預期的 cert 建立或刪除（防誤刪 / 惡意刪）

四件事任一缺失、就是 [Transport Trust and Certificate Lifecycle](/backend/07-security-data-protection/transport-trust-and-certificate-lifecycle/) 的覆蓋缺口。

## 日常操作與決策形狀

**Request public cert**：對 internet-facing endpoint（網站、API）issue public cert、走 `RequestCertificate` API、選 DNS validation。ACM 給一組 CNAME record、放進 DNS（Route53 可一鍵 create）、ACM 自動驗證 + issue。Cert 生效後 attach 到 ELB / CloudFront / API Gateway listener。Issuer 是 Amazon Trust Services、所有主流瀏覽器 / OS trust store 都認。

**Request private cert（需 PCA 後端）**：內部 service mTLS root、走 `RequestCertificate` 但指定 PCA ARN。ACM 透過 PCA 簽 cert、cert chain 是組織內部 CA hierarchy。Trust store 必須在各 workload 手動建立（不像 public cert 自動 trust）。

**DNS validation vs Email validation**：DNS validation 是預設 + 推薦 — CNAME record 放進 DNS 後、ACM 持續驗證 domain ownership、auto-renewal 全自動。Email validation 是 legacy、ACM 寄信到 domain 的 WHOIS / 預設 admin email、人工點連結驗證；auto-renewal 不會自動完成、cert 到期前必須手動 re-validate。Production 一律用 DNS validation。

**Auto-renewal 條件**：ACM 在 cert lifetime 60 天前嘗試 renew、條件嚴格：(1) cert 是 ACM-issued（不是 imported）(2) DNS validation 走 CNAME record 仍存在且可回應 (3) cert 至少 attach 到一個 AWS service。三個條件任一不滿足、renewal 不自動觸發、cert 會 expire。Imported cert *完全不自動 renew*、必須在 expiry 前手動 re-import。

**跟 ELB / CloudFront / API Gateway 整合**：ELB / API Gateway 用所在 region 的 ACM cert、CloudFront 例外 — *只認 us-east-1 region 的 ACM cert*（CloudFront edge 是 global、cert metadata 統一從 us-east-1 拉）。Multi-region app 要在每個 region 各 request 一份 cert、CloudFront 那份固定放 us-east-1。

**Imported certificate**：自管 cert（外部 CA 簽的、舊系統遷移過來的）可以 import 進 ACM、拿到 ARN 後一樣 attach 到 AWS service。代價是 *ACM 不會 renew*、expiry 前必須手動 re-import 新版。常見事故源：imported cert 過期、AWS service 突然 serve expired cert、Browser 顯示警告。建議 imported cert 都設 CloudWatch alarm 監 `DaysToExpiry`。

**跟 [AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) 整合**：誰能 issue / delete cert 走 IAM policy 控制 — `acm:RequestCertificate` / `acm:DeleteCertificate` / `acm:ImportCertificate`。Tag-based access control 可以限定「只有帶 `team=platform` tag 的 cert 才能被 platform team IAM role 改」、防誤刪 production cert。Cert 是 region-scoped resource、IAM policy 可指定 `Resource` ARN 限定 region / cert ID。

## 核心取捨表

| 取捨維度      | ACM (public)                                     | ACM Private CA (PCA)                   | cert-manager + Let's Encrypt               | 手動 OpenSSL CA   |
| ------------- | ------------------------------------------------ | -------------------------------------- | ------------------------------------------ | ----------------- |
| 部署模型      | AWS managed                                      | AWS managed CA hierarchy               | K8s cluster 內 self-hosted controller      | 手動腳本          |
| 私鑰持有      | AWS 持有、客戶不能 export                        | AWS 持有 CA key、subordinate 可 export | cluster 內 Secret、可 export               | 自己持有          |
| Issuer        | Amazon Trust Services（public trust store）      | 客戶自管 CA（內部 trust）              | Let's Encrypt / 任何 ACME CA               | 自簽              |
| 適用 endpoint | AWS-managed service（ELB / CloudFront / API GW） | 內部 mTLS、AWS service 也可用          | K8s workload、Ingress、任何持有 PEM 的服務 | 實驗 / 內部小規模 |
| Auto-renewal  | DNS validation 全自動                            | 透過 ACM 自動                          | cert-manager 自動                          | 自己寫 cron       |
| 跨雲 / 跨平台 | 弱 — AWS 內                                      | 弱 — AWS 內                            | 強 — K8s 在哪都可                          | 強                |
| 計費          | public cert 免費                                 | per CA + per cert（PCA 較貴）          | 免費（Let's Encrypt）                      | 免費              |
| 適合場景      | AWS-heavy + edge endpoint                        | 內部 mTLS root + AWS 整合              | K8s workload + 跨雲                        | 實驗、極小規模    |
| 退場成本      | 中 — cert 重 issue 但 service 配置要改           | 高 — CA hierarchy 遷移痛苦             | 低 — PEM 在手、換 issuer 容易              | 低                |

選 ACM 的核心訴求：cert 主要 attach 到 AWS-managed service、希望 cert 完全 hands-off、不需要 export 私鑰、能接受 AWS lock-in。需要 export PEM 或跨雲 / 自管 endpoint、改走 cert-manager + Let's Encrypt。需要內部 mTLS root + CA hierarchy 控制、走 ACM Private CA。

## 進階主題

**ACM Private CA hierarchy**：PCA 支援 root CA + 多層 intermediate CA、生產建議 root CA 離線（CA 簽完 intermediate 後 disable）、日常簽發走 subordinate CA。Subordinate CA compromise 時 revoke 該層、root 不受影響。Cert policy（path length、key usage、name constraint）在 CA 建立時設定、之後無法改、設計時要算對。

**Cross-region cert（CloudFront 的 us-east-1 限制）**：CloudFront 是 global service、但 attach 的 ACM cert *必須在 us-east-1*。Multi-region 部署：每個 region 各 issue 一份 cert 給該 region 的 ELB / API Gateway、CloudFront 的那份單獨在 us-east-1 issue。Terraform / CloudFormation 要顯式宣告 provider region。

**Imported cert 跟 auto-renewal 邊界**：imported cert（外部 CA 簽的）ACM 知道存在、可以 attach、但 *不 renew*。常見事故：團隊 import cert 後忘了；幾個月後 cert 到期；CloudFront / ELB serve expired cert；客戶看到 browser 警告。對策：所有 imported cert 設 CloudWatch alarm `DaysToExpiry < 30`、`AlmostExpired` event 推 EventBridge → PagerDuty。長期策略是把 imported cert 都遷移成 ACM-issued cert（如果 domain ownership 可驗證）。

**Tag-based access control**：cert 加 tag（`team=platform`、`env=prod`）後、IAM policy 用 `Condition` 限定：只有同 tag 的 role 才能 update / delete。防誤刪 production cert（dev IAM role 跑 cleanup script 不會誤刪 prod）。配合 [AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) 的 ABAC 模型運作。

**Wildcard cert 跟 SAN cert**：ACM 支援 wildcard（`*.example.com` 涵蓋一層 subdomain）跟 SAN（一張 cert 多個 domain，最多 100 個）。Wildcard 簡化部署但 blast radius 大 — 一張 cert compromise 等於整個 subdomain tree 出事；SAN cert 細粒度但管理成本高。Production 建議按服務邊界拆 — 每個 service 一張 cert、不共用 wildcard，除非確實有大量短 lifecycle subdomain。

## 排錯與失敗快速判讀

- **Cert PENDING_VALIDATION 一直卡住**：DNS validation CNAME record 沒放對、或 DNS provider 緩存太久 — 用 `dig` 直接查 CNAME 是否生效、Route53 + ACM 整合通常幾分鐘、外部 DNS 可能 30 分鐘以上
- **Cert renewal FAILED**：`RenewalStatusReason` 多半是 `DOMAIN_VALIDATION_DENIED`（CNAME record 被刪了）或 cert 沒 attach 到任何 service — 補回 CNAME record、或把 cert attach 到至少一個 resource
- **CloudFront 找不到 cert**：cert 在 us-east-1 以外的 region issue — 在 us-east-1 重 issue、或用 Terraform 顯式跨 provider 設定
- **Imported cert expired**：忘了 manual renewal、AWS service serve expired cert — CloudWatch alarm + EventBridge 推 alert、長期遷成 ACM-issued
- **ACM cert 無法用在 EC2 自管 Nginx**：public cert 私鑰不能 export 是設計限制 — 改用 ACM Private CA 或 Let's Encrypt + cert-manager
- **誤刪 production cert**：沒設 tag-based protection、admin script bug — 開 deletion protection（暫時無內建、用 IAM Condition 限定 delete operation + 24h cooldown via Lambda）+ CloudTrail alert 上 `acm:DeleteCertificate`
- **Cross-account cert 共用**：ACM cert 不支援 RAM 共用 — 跨 account 要在每個 account 各 issue（或用 PCA + RAM 共用 PCA、各 account 從 PCA issue）

## 何時改走其他服務

| 需求形狀                                 | 改走                                                                                                                                     |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| K8s workload mTLS / Ingress TLS          | [cert-manager](/backend/07-security-data-protection/vendors/cert-manager/) + Let's Encrypt / 內部 issuer                                 |
| 自管 Nginx / EC2 / 跨雲 endpoint         | [Let's Encrypt](/backend/07-security-data-protection/vendors/letsencrypt/) + 自管 ACME client                                            |
| 內部 mTLS root + CA hierarchy 控制       | ACM Private CA（PCA）或 [HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) PKI engine                      |
| Workload identity（SPIFFE）跨平台        | [SPIRE](/backend/07-security-data-protection/vendors/spire/)                                                                             |
| Cert renewal 證據鏈（rotation evidence） | [7.5 Credential Rotation Scoped Evidence](/backend/07-security-data-protection/credential-rotation-scoped-evidence/)                     |
| Cert + session invalidation 邊界         | [7.3 入口治理](/backend/07-security-data-protection/entrypoint-and-server-protection/)、cert renew 跟 session token 是兩條獨立 lifecycle |

## 不在本頁內的主題

- ACM Private CA 完整 hierarchy 設計（root CA 離線儲存、HSM-backed CA key、CRL / OCSP responder 部署）
- ACM API 完整 CLI reference 跟 Terraform resource 詳盡欄位
- TLS protocol 本身（TLS 1.2 vs 1.3、cipher suite、handshake 流程）
- Certificate Transparency log 跟 SCT embedding 內部機制
- 各 browser / OS trust store 的更新週期

## 案例回寫

ACM 在 07 案例庫沒有直接 vendor-level 事件、以下採對照引用：

| 案例                                                                                                                                    | 跟 ACM 的關係（對照）                                                                                                                                   |
| --------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Transport Trust and Certificate Lifecycle (section)](/backend/07-security-data-protection/transport-trust-and-certificate-lifecycle/)  | ACM 是 AWS 平台 cert lifecycle 自動化的具體落地 — DNS validation + auto-renewal 是 *自動化覆蓋率* 的指標、imported cert 是覆蓋缺口、要單獨設 alarm 兜底 |
| [Citrix Bleed 2023 Session Hijack](/backend/07-security-data-protection/red-team/cases/edge-exposure/citrix-bleed-2023-session-hijack/) | 對照啟示 — cert 自動 renew 不等於 session 自動 invalidate、舊 session token 在新 cert 下仍可重放、session lifecycle 是另一層責任、不在 ACM 範圍         |
| [Credential Rotation Scoped Evidence (section)](/backend/07-security-data-protection/credential-rotation-scoped-evidence/)              | ACM renewal 自動、但 *Certificate Transparency log 比對* + *fleet-wide trust bundle update* 是另一條 evidence chain、要跟 SBOM / CMDB 對齊              |

## 下一步路由

- 上游：[7.4 傳輸信任與憑證生命週期](/backend/07-security-data-protection/transport-trust-and-certificate-lifecycle/)、[7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/)
- 平行：[cert-manager](/backend/07-security-data-protection/vendors/cert-manager/)、[Let's Encrypt](/backend/07-security-data-protection/vendors/letsencrypt/)、[SPIRE](/backend/07-security-data-protection/vendors/spire/)
- 下游：[AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/)（誰能 issue / delete cert）、[AWS KMS](/backend/07-security-data-protection/vendors/aws-kms/)（PCA CA key 後端）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（cert expiry / mis-issuance 進 IR 流程）
- 官方：[AWS Certificate Manager Documentation](https://docs.aws.amazon.com/acm/)
