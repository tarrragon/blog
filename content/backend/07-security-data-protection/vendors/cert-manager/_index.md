---
title: "cert-manager"
date: 2026-05-18
description: "K8s 原生 certificate lifecycle automation、支援 Let's Encrypt / Vault PKI / Venafi 等多 issuer、auto-renewal + Challenge solver"
weight: 8
tags: ["backend", "security", "vendor", "cert-manager", "pki", "tls", "kubernetes"]
---

cert-manager 是 K8s 原生的 *certificate lifecycle automation* — 把「拿 cert、放 cert、定期 renew」這條從以前需要 cron + certbot + 手動 reload 的鏈、轉成 *declarative + controller pattern*。使用者在 cluster 內 apply 一個 `Certificate` resource、cert-manager controller 自動跟 issuer 對話、把 cert 存進 Secret、在 lifetime 2/3 點觸發 renew。它把 cert 這件事接進 K8s 控制循環、跟 Pod / Service / Ingress 同等地位的 first-class resource、層級高於 certbot 的 K8s 移植。

## 服務定位

cert-manager 的核心責任是 *K8s cluster 內所有 cert 的生命週期治理*。從 Ingress / Gateway 對外 TLS、internal service mTLS、到 workload-level 短期 cert、都用同一套 declarative model 表達。Issuer 抽象讓底層 cert 來源可換 — 公開 cert 走 [Let's Encrypt](/backend/07-security-data-protection/vendors/letsencrypt/) ACME、內部 cert 走 [Vault PKI engine](/backend/07-security-data-protection/vendors/hashicorp-vault/) 或 self-signed CA、企業環境走 Venafi 或 AWS PCA — 上層 `Certificate` spec 不變。

跟 [AWS ACM](/backend/07-security-data-protection/vendors/aws-acm/) 的差異是 *cert 的部署面*：ACM 是 AWS-managed cert、只能掛在 AWS service（ELB / CloudFront / API Gateway）、私鑰永不離 AWS；cert-manager 是 K8s-native client、cert 放在 cluster 內的 Secret、可以掛任何 ingress controller 或 workload mTLS。跟 Let's Encrypt 的關係是 *client vs issuer* — cert-manager 是 ACME client、Let's Encrypt 是 ACME server、不是替代關係。跟 [SPIRE](/backend/07-security-data-protection/vendors/spire/) 的差異是 *身份模型* — cert-manager 給 *DNS-named cert*（CN / SAN 是 hostname）、SPIRE 給 *SPIFFE ID-based workload identity*（`spiffe://trust-domain/workload`）、兩者互補不衝突。

## 本章目標

讀完本頁、讀者能判斷：

1. cert-manager 用 Issuer / ClusterIssuer 哪個、配什麼 issuer backend（Let's Encrypt / Vault PKI / self-signed / 公司 CA）
2. Challenge solver 選 HTTP01 還是 DNS01、為什麼 wildcard cert 必須用 DNF01
3. Auto-renewal 觸發點、renew 失敗的 alert 時機、跟 Ingress / Gateway API 整合的 annotation
4. 何時用 cert-manager、何時改走 [ACM](/backend/07-security-data-protection/vendors/aws-acm/)（雲端原生 service）或 [SPIRE](/backend/07-security-data-protection/vendors/spire/)（workload identity）

## 最短判讀路徑

判斷 cert-manager 部署是否健康、最少看四件事：

- **Issuer 配置**：是 `ClusterIssuer`（cluster-wide）還是 `Issuer`（namespace-scoped）、backend 是哪一種（acme / vault / ca / venafi）、credential（ACME private key、Vault token、CA cert）放哪、RBAC 限制誰能參考這個 issuer
- **Certificate spec**：`dnsNames` / `ipAddresses` 跟實際 service 一致、`duration` 跟 `renewBefore` 比例合理（renewBefore >= duration / 3）、`secretName` 指向的 Secret 是不是 ingress 真的會讀的那個
- **Renewal 觸發**：controller log 有沒有按時觸發 renew、`kubectl describe certificate` 的 `Renewal Time` 接近沒、Challenge resource 沒有卡在 pending
- **Challenge solver**：HTTP01 的 ingress / Gateway 80 port 真的能被 Let's Encrypt 從 Internet 打到、DNS01 用的 cloud provider credential 還有效、wildcard cert 沒誤用 HTTP01

四件事任一缺失、cert 就會在不知不覺中過期、production 看到 `x509: certificate has expired` 才驚覺、是 [Transport Trust and Certificate Lifecycle](/backend/07-security-data-protection/transport-trust-and-certificate-lifecycle/) 的典型缺口。

## 日常操作與決策形狀

**Issuer vs ClusterIssuer 的選擇**：`Issuer` 是 namespace-scoped、只能 issue 該 namespace 的 cert、適合 *單 team 自管 issuer credential* 的場景；`ClusterIssuer` 是 cluster-wide、所有 namespace 都可以參考、適合 *平台 team 統一管理 issuer*。production 通常用 ClusterIssuer 配特定 issuer backend + RBAC 收 `Certificate` 建立權（讓 application team 只能在自己 namespace 建 Certificate、不能改 ClusterIssuer）。

**Certificate spec 設計**：`dnsNames` 列出該 cert 涵蓋的 hostname（支援 wildcard `*.example.com`）、`ipAddresses` 加 IP SAN（mTLS 跨 service 常用）、`duration` 是 cert 有效期、`renewBefore` 是提前多久 renew（預設 duration 的 1/3）。短期 cert（hours-level、Vault PKI 常用）配 `renewBefore` 短、長期 cert（90 天、Let's Encrypt）配 `renewBefore` 30 天。`secretName` 指向 cert-manager 會寫入的 Secret、Ingress 跟 workload 從這個 Secret 讀。

**Challenge solver 的選擇**：ACME issuer（Let's Encrypt）需要證明 *你控制這個 domain*、有兩個方法：HTTP01（在 `http://yourdomain/.well-known/acme-challenge/<token>` 放檔案、Let's Encrypt 從 Internet 來抓）跟 DNS01（在 DNS zone 加 `_acme-challenge.yourdomain TXT <token>` record、Let's Encrypt 查 DNS）。**wildcard cert（`*.example.com`）必須用 DNS01**、HTTP01 不支援 wildcard 因為 Let's Encrypt 不知道要打哪個 subdomain。HTTP01 要求 ingress controller 80 port 對 Internet 開放、DNS01 要求 cluster 有 cloud DNS API credential。

**Auto-renewal 機制**：cert-manager 在 cert lifetime 達到 `(duration - renewBefore)` 時間時觸發 renew、預設約 lifetime 2/3 點。Let's Encrypt cert 90 天 = 60 天時開始嘗試 renew、留 30 天緩衝給 renew 失敗的重試。renew 失敗會持續重試（exponential backoff、最長 8 小時間隔）、剩下 ~7 天時 controller log 開始 ERROR 級別 alert — 監控要 hook 進這個 log 訊號、否則 cert 真的過期才知道就太晚。

**跟 Ingress 整合**：Ingress resource 加 annotation `cert-manager.io/cluster-issuer: letsencrypt-prod`（或 `cert-manager.io/issuer:`）、cert-manager 看到 Ingress 的 `tls.hosts` 自動建立對應 Certificate、issue 完寫進 `tls.secretName` 指定的 Secret、ingress controller 自動 reload 用新 cert。Gateway API 的整合機制類似、用 `cert-manager.io/issuer` annotation 在 `Gateway` resource。

**CertificateRequest Approval Policy（v1.4+）**：每個 Certificate 建立會產生 CertificateRequest、由 Approver 決定要不要送給 issuer。預設 cert-manager 內建 approver 自動 approve、但可以加 admission policy（Kyverno / OPA / 自寫 webhook）限制「誰能在哪個 namespace 建什麼 SAN 的 cert」— 防 internal compromise 任意 issue cert 對外冒名。production 環境通常會在 platform-level 鎖 wildcard cert、防 application team 誤建涵蓋整個 zone 的 cert。

## 核心取捨表

| 取捨維度      | cert-manager                                        | AWS ACM                               | 手動 certbot / OpenSSL            |
| ------------- | --------------------------------------------------- | ------------------------------------- | --------------------------------- |
| 部署模型      | K8s controller、declarative `Certificate` resource  | AWS managed、Console / API request    | 手動跑 CLI、cron 跑 renew         |
| Cert 部署面   | K8s Secret、任何 ingress controller / workload      | 只能掛 ELB / CloudFront / API Gateway | 任何地方、但 deploy 要自己做      |
| Issuer 彈性   | 多 issuer（ACME / Vault / Venafi / CA / AWS PCA）   | 只能 Amazon CA                        | 任何 ACME provider、但要手寫 hook |
| Auto-renewal  | 內建 controller、預設 2/3 lifetime 點 renew         | AWS 自動 renew（DNS-validated only）  | 自己寫 cron + reload script       |
| Wildcard 支援 | 走 DNS01 challenge                                  | 支援、需 DNS 驗證                     | 走 DNS01 hook                     |
| 私鑰位置      | K8s Secret（cluster 內、需 RBAC + etcd encryption） | AWS 內、不可 export                   | Local filesystem、要自己管        |
| 適合場景      | K8s cluster 內所有 cert、跨 issuer、internal mTLS   | AWS-only serving cert（ELB / CDN）    | 非 K8s 的 server、舊系統          |
| 退場成本      | 中 — 改其他 ACME client 或回手動                    | 高 — 私鑰拿不出來、要重新 issue       | 低 — 完全自管                     |

選 cert-manager 的核心訴求：*cluster 內 cert 跨 issuer 統一管理 + 自動 renew + 跟 Ingress / Gateway declarative 整合*。如果 cert 完全給 AWS service 用、不進 K8s workload、ACM 更簡單（不用裝 controller、AWS 自動處理）。如果是非 K8s 環境（VM、bare-metal Nginx）、certbot + cron 仍是合理選擇、不需要為了 cert 跑 K8s controller。

## 進階主題

**DNS01 challenge 跟 cloud DNS 整合**：cert-manager 支援多家 cloud DNS provider 作為 DNS01 solver — Route53、Cloud DNS（GCP）、Azure DNS、Cloudflare、ACMEDNS（自管 DNS proxy）。每個 provider 需要 *DNS zone 寫入 credential*（IAM role、service account key、API token）— 這份 credential 等於 *任意改該 zone DNS record 的權力*、blast radius 大、要走 [least privilege](/backend/07-security-data-protection/identity-access-boundary/) 限定到 specific zone + 只給 TXT record write、不要全 zone 全 record type。

**跟 Vault PKI engine 整合**：cert-manager 可用 [Vault PKI engine](/backend/07-security-data-protection/vendors/hashicorp-vault/) 作為 issuer backend — 在 cluster 內建 `Issuer` / `ClusterIssuer` type 為 `vault`、指向 Vault address + PKI mount path + auth method（Kubernetes auth / AppRole）。每張 cert 的 issue / revoke 都進 Vault audit log、跟 secret rotation 用同一套 evidence chain（呼應 [Credential Rotation Scoped Evidence](/backend/07-security-data-protection/credential-rotation-scoped-evidence/)）。typical 用法：short-lived workload mTLS cert（hours-level duration、minutes-level renewBefore）、靠 Vault PKI 短期 cert + cert-manager 自動換。

**跟 SPIRE 的互補**：cert-manager 自動更新 cert、但 *cert 是給人讀的 DNS name*；SPIRE 自動建立 workload identity、*identity 是 SPIFFE ID*。兩者解不同問題 — cert-manager 解「Ingress / external API 的 TLS」、SPIRE 解「service A 要怎麼證明自己是 A 給 service B 看」。production 環境常 *並存*：edge cert 跟 user-facing TLS 用 cert-manager + Let's Encrypt、internal service mesh 用 SPIRE + SPIFFE。

**Trust bundle 管理（trust-manager）**：trust-manager 是 cert-manager 姐妹專案、解決 *trust anchor（root CA bundle）跨 namespace 同步* 問題。傳統做法是每個 pod ConfigMap 各自塞 CA bundle、更新時要逐個改；trust-manager 提供 `Bundle` resource 一處定義、自動 distribute 到指定 namespace 的 ConfigMap。對應 *cert rotation* 跟 *CA rotation* 是兩條獨立 chain、後者是 trust-manager 的領域。

## 排錯與失敗快速判讀

- **Challenge 卡在 pending**：HTTP01 卡 = ingress 80 port 沒對 Internet、firewall / NLB 沒開、redirect 80→443 把 challenge 也轉了；DNS01 卡 = DNS provider credential 過期、IAM 沒 zone write 權、`_acme-challenge` record 沒寫進去 — `kubectl describe challenge` 看 reason
- **Wildcard cert 用 HTTP01**：申請失敗 + log 寫 "wildcard not supported with HTTP-01" — 改 DNS01 solver
- **renewBefore 太短**：renew 失敗只剩幾天才 alert、實際過期前來不及處理 — `renewBefore` 至少 duration / 3、production cert 給 30 天
- **Secret 沒被 ingress 讀到**：Certificate 已 Ready 但 ingress 還用舊 cert — ingress `tls.secretName` 拼錯、ingress controller 沒 reload、TLS handshake 用的 SNI 沒匹配
- **ACME rate limit 撞牆**：[Let's Encrypt rate limit](/backend/07-security-data-protection/vendors/letsencrypt/) 每週同 domain 50 cert / 同 account 300 pending — 反覆建錯 Certificate 重 issue 會撞、staging environment 用 `letsencrypt-staging` issuer 測過再上 prod
- **ClusterIssuer 被 application team 誤改**：沒設 RBAC、任何 namespace 都能 patch ClusterIssuer — 用 admission policy 鎖 ClusterIssuer 變更權給 platform team
- **Approval Policy 缺失**：任何 namespace 能建 wildcard cert、internal compromise 拿到 K8s API token 就能 issue 假冒 cert — 上 CertificateRequest Approval Policy + Kyverno / OPA rule

## 何時改走其他服務

| 需求形狀                                    | 改走                                                                                                                 |
| ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| AWS-only serving cert（ELB / CloudFront）   | [AWS ACM](/backend/07-security-data-protection/vendors/aws-acm/)                                                     |
| 非 K8s 環境（VM、bare-metal）的 ACME cert   | certbot / acme.sh / [Let's Encrypt](/backend/07-security-data-protection/vendors/letsencrypt/) 直接用                |
| Workload identity（不是 DNS-named cert）    | [SPIRE](/backend/07-security-data-protection/vendors/spire/)（SPIFFE-based）                                         |
| 大量短期 internal cert + 完整 PKI 治理      | [Vault PKI engine](/backend/07-security-data-protection/vendors/hashicorp-vault/)（可配 cert-manager 為 client）     |
| 公司既有 enterprise CA（Venafi / DigiCert） | cert-manager + Venafi issuer / 商用 issuer plugin                                                                    |
| 全公司 cert rotation 證據鏈                 | [7.5 Credential Rotation Scoped Evidence](/backend/07-security-data-protection/credential-rotation-scoped-evidence/) |

## 不在本頁內的主題

- cert-manager Helm chart 的所有 value 細節跟版本相容性矩陣
- 每個 issuer backend 的完整 schema（acme / vault / venafi / ca / selfSigned）
- Gateway API 跟 Ingress API 的 cert-manager annotation 完整對照
- ACME RFC 8555 protocol 細節（HTTP01 / DNS01 / TLS-ALPN-01 challenge mechanism）
- trust-manager 的 Bundle source 種類（inMemory / secret / configMap / defaultPackage）

## 案例回寫

cert-manager 在 07 案例庫沒有直接 vendor-level 事件、以下案例採對照引用：

| 案例                                                                                                                                    | 跟 cert-manager 的關係（對照）                                                                                                                           |
| --------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Transport Trust and Certificate Lifecycle (section)](/backend/07-security-data-protection/transport-trust-and-certificate-lifecycle/)  | cert-manager 是 cert lifecycle automation 的具體實作 — auto-renewal + Challenge solver + Approval Policy 是 lifecycle 治理三層機制                       |
| [Credential Rotation Scoped Evidence (section)](/backend/07-security-data-protection/credential-rotation-scoped-evidence/)              | cert-manager 的 renewal 自動但 *revocation 流程不自動* — 舊 cert 失效後 fleet 層級 trust bundle update 是另一條 chain、走 trust-manager                  |
| [Citrix Bleed 2023 Session Hijack](/backend/07-security-data-protection/red-team/cases/edge-exposure/citrix-bleed-2023-session-hijack/) | 對照啟示 — cert 更新後 session 仍可能延續、cert-manager 只管 cert lifecycle、session invalidation 是另一層責任、不要把 cert rotation 當 session 失效手段 |

## 下一步路由

- 上游：[7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)、[Transport Trust and Certificate Lifecycle](/backend/07-security-data-protection/transport-trust-and-certificate-lifecycle/)
- 平行：[Let's Encrypt](/backend/07-security-data-protection/vendors/letsencrypt/)（ACME issuer）、[AWS ACM](/backend/07-security-data-protection/vendors/aws-acm/)（AWS-managed cert）、[SPIRE](/backend/07-security-data-protection/vendors/spire/)（workload identity）
- 下游：[HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)（PKI engine 作為 issuer backend）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（cert 過期 / mis-issue 事件如何 routing）
- 官方：[cert-manager Documentation](https://cert-manager.io/docs/)
