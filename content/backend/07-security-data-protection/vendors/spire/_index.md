---
title: "SPIRE"
date: 2026-05-18
description: "SPIFFE Runtime Environment、attested workload identity、short-lived SVID + Trust Bundle、跨組織 federation"
weight: 11
tags: ["backend", "security", "vendor", "spire", "spiffe", "workload-identity", "zero-trust"]
---

SPIRE（SPIFFE Runtime Environment）是 SPIFFE 規範的 reference 實作、CNCF graduated 專案、解決 *workload identity attestation* 的核心問題：在 service mesh / 跨 cluster / 跨組織的環境裡、一個 workload 必須能 *被驗證* 它是誰（是哪個 namespace 的哪個 service account、跑在哪台 attested host 上）、而不是依靠 IP / hostname / 共用 API key 這種可偽造的識別。SPIRE 發出的識別憑證叫 *SVID*（SPIFFE Verifiable Identity Document）、識別格式是 URI 形式的 *SPIFFE ID*（例如 `spiffe://example.org/ns/prod/sa/api-gateway`）、TTL 是分鐘級短期、workload 透過本地 Unix socket（Workload API）持續拉新 SVID、不 mount file 一勞永逸。

## 服務定位

SPIRE 的核心定位是 *attestation-first 的 workload identity 控制面*、解的問題是「這個 workload 在執行時是不是它聲稱的那個」— 識別語意是 *attested SPIFFE ID*、不是 DNS name 也不是 cluster-internal ServiceAccount。跟 [cert-manager](/backend/07-security-data-protection/vendors/cert-manager/) 的 *cert lifecycle*（DNS name 為主）、Kubernetes ServiceAccount 的 *cluster-internal scope*、[Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) AppRole 的 *pull-based secret*（workload 要先持有 secret_id）都解不同問題、不是替代關係。

跟雲端 workload identity（[AWS IAM Roles Anywhere](/backend/07-security-data-protection/vendors/aws-iam/) / GCP Workload Identity Federation / Azure Federated Identity Credential）相比、SPIRE 多了 *跨雲統一抽象* + *跨組織 federation*（兩個 SPIRE deployment 互相信任只需要交換 trust bundle）。代價是 *自管控制面*（SPIRE Server HA + Agent rollout + Registration Entry 維護）。詳細跟其他 vendor 的場景對比見「核心取捨表」與「何時改走其他服務」。

## 本章目標

讀完本頁、讀者能判斷：

1. 何時用 SPIRE（zero-trust mesh、跨 cluster / 跨組織 federation、需要 attestation）、何時用 cert-manager + Service Account / cloud-native workload identity 就夠
2. SPIRE deployment 的最低安全骨架（Server / Agent 拓樸、Node Attestor、Workload Attestor、Registration Entry、SVID TTL）
3. 跟 [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) / Istio / [AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) Roles Anywhere 的整合形狀
4. 失敗模式如何排錯（Attestor 設計太寬、SVID 過期、Trust Bundle 不同步）

## 最短判讀路徑

判斷 SPIRE deployment 是否健康、最少看四件事：

- **Server / Agent 拓樸**：SPIRE Server 是 trust domain 的 root、發 SVID、簽 Trust Bundle；SPIRE Agent 跑在每個 host / node 上、向 Server 註冊、為本機 workload attest 身份。Server HA（多副本 + 共享 DB）跟 Agent rollout coverage 缺一就會出現 *節點上 workload 拿不到 SVID*。
- **Attestor 設計**：Node Attestor 驗 *這台 host 是真的*（K8s SAT / AWS IID / Azure MSI / GCP IIT / TPM 等）、Workload Attestor 驗 *這個 process 是誰*（K8s pod selector、unix UID/GID、systemd unit）。Selector 太寬等於整個 namespace 任何 pod 都拿同一個 SPIFFE ID、blast radius 失控。
- **SVID lifetime**：X.509-SVID 預設 TTL 1 小時、production 建議 5–15 分鐘；workload 必須走 Workload API（Unix socket）持續拉新 SVID、不能 mount 成 file。Workload 不支援 SDK 整合就被擋在 SPIRE 之外。
- **Registration Entry**：定義「哪個 SPIFFE ID 可以被哪個 attestation selector 取得」、是 SPIRE 的 *authorization 設計核心*。一個 entry 寫錯（selector 用了 `k8s:ns:default` 沒鎖 service account）就等於 default namespace 任何 pod 都拿 admin SPIFFE ID。

四件事任一缺失、就是 [Workload Identity and Federated Trust](/backend/07-security-data-protection/workload-identity-and-federated-trust/) 邊界的待補項目。

## 日常操作與決策形狀

**Server / Agent 拓樸**：SPIRE Server 是 trust domain 的 root CA + 註冊中心、必須 HA（至少兩副本 + 共享 PostgreSQL / MySQL）、production 通常每個 cluster 一個 Server cluster；SPIRE Agent 以 DaemonSet 跑在每個 K8s node、或以 systemd unit 跑在每台 VM、負責本機的 attestation 與 SVID 派發。Agent 跟 Server 之間用 mutual TLS、Agent 自己也走 Node Attestation 才能向 Server 註冊。

**Node Attestor**：決定「這個 Agent 是不是真的跑在它聲稱的 host 上」。K8s SAT / PSAT（projected service account token）驗 Agent 的 ServiceAccount + Pod；AWS IID 驗 EC2 instance identity document；GCP IIT 驗 GCE metadata；Azure MSI 驗 Managed Identity；TPM attestor 驗硬體 TPM 簽章。選錯 attestor 等於 host 識別被偽造 — 例如 K8s SAT 沒鎖 audience、外部能用任何 K8s SA token 註冊 fake Agent。

**Workload Attestor**：決定「這個 process 是哪個 workload」。Kubernetes attestor 用 pod label / annotation / namespace / service account；Unix attestor 用 UID / GID / parent process / binary hash；Docker attestor 用 container label / image。Workload 連到 Agent 的 Workload API Unix socket、Agent 透過 attestor 收集 selector、比對 Registration Entry、決定能發哪個 SPIFFE ID。Selector 設計是 *least privilege* 的 enforcement point — 寫得越精確、blast radius 越小。

**Registration Entry**：定義 SPIFFE ID 到 selector 的 mapping、例如「`spiffe://example.org/ns/prod/sa/api-gateway` 對應 `k8s:ns:prod`、`k8s:sa:api-gateway`、`k8s:pod-label:app:api-gateway`」。Entry 透過 SPIRE Server API 或 GitOps 維護、變更走 PR review（policy-as-code）、避免單一 admin 偷加 entry 拿 admin SPIFFE ID。

**SVID 生命週期**：X.509-SVID 是 mTLS 用的 cert（含 SPIFFE ID 作 URI SAN）、JWT-SVID 是給 non-mTLS 場景（HTTP header bearer token、跟 OIDC 整合）。workload 透過 Workload API stream 接 SVID、TTL 過半就 Agent 主動 push 新 SVID — workload 不需要自己排程 renew。Trust Bundle（trust domain 的 root cert）也透過 Workload API 同步、自動更新。

**Federation between trust domains**：兩個獨立 SPIRE deployment（不同組織、不同 trust domain）要互信、交換 *trust bundle*（自簽 root cert）、走 SPIFFE Federation API。`example.org` 的 workload 可以驗證 `partner.com` 的 SVID、不需要共用 PKI、不需要在中間放 broker。對應 [Workload Identity and Federated Trust](/backend/07-security-data-protection/workload-identity-and-federated-trust/) 的 federation 章節。

## 核心取捨表

| 取捨維度          | SPIRE                                                  | cert-manager                                | Kubernetes ServiceAccount       | Vault AppRole                    |
| ----------------- | ------------------------------------------------------ | ------------------------------------------- | ------------------------------- | -------------------------------- |
| 識別語意          | Attested SPIFFE ID（who is this workload）             | DNS name（who owns this name）              | Cluster-internal SA name        | Pull-based role + secret_id      |
| 信任邊界          | Trust domain、可跨 cluster / cloud / 組織              | Cluster 內、外部走 ACME / Vault PKI         | 單一 cluster                    | Vault 範圍內                     |
| Attestation       | First-class — Node + Workload Attestor 雙層            | 無 — 僅驗 DNS / cert request                | TokenReview API、cluster-scoped | 無 — secret_id 即是 proof        |
| Cert TTL          | 分鐘級短期、Workload API 自動 rotate                   | 天 / 月級、cert-manager 排程 renew          | Token TTL（projected: 短）      | Token TTL（lease 治理）          |
| Workload 改動     | 需走 SPIFFE Workload API SDK 或 sidecar                | Mount file 即可                             | Mount file 即可                 | 拉 secret_id + 換 token          |
| 跨組織 federation | 強 — 交換 trust bundle 即可                            | 弱 — 需共用 CA 或 ACME                      | 不支援                          | 弱 — 需共用 Vault 或 OIDC bridge |
| 運維成本          | 高 — Server HA + Agent rollout + Entry 治理            | 低 — Operator 模式                          | 內建                            | 中 — Vault 自管                  |
| 適合場景          | Zero-trust mesh、跨 cluster / 跨組織、需要 attestation | K8s app cert lifecycle、ACME / Vault issuer | Cluster-internal 簡單 app       | 不在雲 metadata 內的 workload    |

選 SPIRE 的核心訴求：*需要 attested workload identity*（不只是「有 cert 就信」）+ *跨 cluster 或跨組織*（單 cluster 內 ServiceAccount 已夠）+ *workload 能整合 SPIFFE SDK 或 sidecar*。三個條件缺一就先用 cert-manager + ServiceAccount 組合、別硬上 SPIRE。

## 進階主題

**跟 Istio / Linkerd / Envoy 整合**：Istio 1.14+ 支援 SPIRE 作 identity provider（取代 Citadel）、Envoy SDS（Secret Discovery Service）走 SPIRE Workload API 拉 SVID、service mesh 內 mTLS 用 SPIFFE ID 做 peer 驗證 + authz policy（`source.principal == "spiffe://example.org/ns/prod/sa/api-gateway"`）。Linkerd 也有實驗性整合（policy controller 接受 SPIFFE ID）。

**跟 [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) 整合**：Vault 可以用 SPIRE JWT-SVID 作 auth method、workload 拿 SVID 換 Vault token、不需要 AppRole secret_id — 等於把 Vault auth 的 *bootstrap secret 問題* 交給 SPIRE attestation 處理。workload 同時拿 SPIFFE 身份（mTLS）跟 Vault secret（DB credential、PKI cert）、兩條鏈共用同一個 attestation root。

**跟 [AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) Roles Anywhere 整合**：AWS IAM Roles Anywhere 接受 X.509 cert 換 IAM credential、SPIRE 發的 X.509-SVID 可以當這個 cert — non-AWS workload（on-prem、其他雲、CI runner）用 SPIFFE ID 拿 short-term AWS STS credential、不需要存 long-lived AWS access key。

**Nested SPIRE（多層 trust domain）**：大型組織把 trust domain 切成 *parent + child*（例如 `example.org` 作 parent、每個 BU 各自 `bu1.example.org`、`bu2.example.org`）、child Server 向 parent Server 註冊作 downstream、child trust domain 的 workload 還是被 parent root 信任。適合需要 *部門自治 + 全公司互通* 的場景。

**JWT-SVID 給 non-mTLS workload**：HTTP service 不一定能跑 mTLS（CDN 後面、legacy app）、SPIRE 發 JWT-SVID（標準 JWT、aud / sub claim、SPIFFE ID 在 sub）給這類 workload、走 HTTP `Authorization: Bearer` 傳遞、收方驗 SPIRE trust bundle 簽章。代價是失去 mTLS 的 mutual auth、需要 application-level 驗 JWT-SVID。

## 排錯與失敗快速判讀

- **Workload Attestor selector 太寬**：Entry 只鎖 `k8s:ns:prod` 沒鎖 `k8s:sa:*` — namespace 內任何 pod 都拿同一個 admin SPIFFE ID。修法：selector 必含 namespace + service account + （建議）pod label，policy review 走 GitOps PR。
- **SVID 過期但 workload 沒接 Workload API**：workload 把 SVID dump 成 file 後不再連 Workload API、TTL 過期之後 mTLS 失敗 — workload 必須用 SPIFFE SDK 或 sidecar（envoy / spiffe-helper）持續 stream SVID。
- **Node Attestor audience 未鎖**：K8s SAT attestor 沒設 `audience`、外部能用任何 K8s SA token 註冊 fake Agent — 改用 PSAT（projected SA token）+ 明確 audience 鎖到 SPIRE Server URL。
- **Trust Bundle 不同步**：federation 對端 rotate root cert、本端沒抓到新 bundle、跨 trust domain mTLS 失敗 — federation endpoint 必須走 HTTPS + 定期 refresh、SPIRE Server metric 監控 federation fetch 失敗。
- **Registration Entry 漂移**：手動加的 entry 沒進 GitOps、admin 離職後沒人知道為何某個 SPIFFE ID 存在 — entry 必須走 declarative source（YAML in Git）+ CI apply、禁止直接 `spire-server entry create`。
- **Server DB 單點**：SPIRE Server SQLite mode 跑在 production、節點掛了 = 整個 trust domain 不能發 SVID — production 必走 PostgreSQL / MySQL + HA Server 副本。
- **Audit log gap**：SPIRE Server audit log 沒接 SIEM、SVID 派發紀錄 7 天後輪轉掉、事故時無法回查誰拿過 admin SPIFFE ID — audit log 同步到外部 SIEM 是基本要求、對應 [Audit Log](/backend/knowledge-cards/audit-log/) 卡。

## 何時改走其他服務

| 需求形狀                                  | 改走                                                                                                                                          |
| ----------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| 單 cluster 簡單 K8s app + DNS-named cert  | [cert-manager](/backend/07-security-data-protection/vendors/cert-manager/) + Kubernetes ServiceAccount                                        |
| 公開 serving cert（HTTPS endpoint）       | [AWS ACM](/backend/07-security-data-protection/vendors/aws-acm/) / [Let's Encrypt](/backend/07-security-data-protection/vendors/letsencrypt/) |
| Static secret + dynamic credential        | [HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)                                                              |
| AWS-only workload + IAM role              | [AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) IRSA / Roles Anywhere                                                        |
| GCP-only workload                         | GCP Workload Identity Federation                                                                                                              |
| 純 human identity / SSO                   | [Keycloak](/backend/07-security-data-protection/vendors/keycloak/) / [Okta](/backend/07-security-data-protection/vendors/okta/)               |
| 跨組織 OIDC federation（human + machine） | [Workload Identity and Federated Trust](/backend/07-security-data-protection/workload-identity-and-federated-trust/)（章節層）                |

## 不在本頁內的主題

- SPIFFE 規範完整逐條解讀（spec 各 section 細節）
- SPIRE Server / Agent 完整 CLI 與 config reference
- 每個 Attestor plugin 的內部實作細節
- Istio / Linkerd / Envoy 整合的完整步驟（屬 service mesh 章節）
- SPIFFE Helper / spire-agent sidecar 各語言 SDK 用法

## 案例回寫

SPIRE 在 07 案例庫沒有直接 vendor-level 事件、以下為對照引用：

| 案例                                                                                                                                                                  | 跟 SPIRE 的關係（對照）                                                                                                                                                 |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Workload Identity and Federated Trust (section)](/backend/07-security-data-protection/workload-identity-and-federated-trust/)                                        | SPIRE 是 federation 信任邊界的具體實作 — 跨 trust domain 交換 bundle 是 SPIFFE federation 的標準形狀                                                                    |
| [Microsoft Storm-0558 Signing Key Chain (red-team)](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) | 對照啟示 — JWT-SVID 是 *short-lived + attested* 設計、跟 Storm-0558 的 long-lived signing key 是相反 mindset；attestation + 分鐘級 TTL 限制了 key 外洩後的 blast radius |
| [GitHub OAuth 2022 Token Supply Chain (red-team)](/backend/07-security-data-protection/red-team/cases/supply-chain/github-oauth-2022-token-supply-chain/)             | 對照啟示 — 傳統 OAuth token 過寬 + 過長、SPIRE 設計是 short TTL + scope-narrow SPIFFE ID + Registration Entry 走 declarative authz、把 secret-leak 路徑收掉             |

## 下一步路由

- 上游：[Workload Identity and Federated Trust](/backend/07-security-data-protection/workload-identity-and-federated-trust/)、[Identity & Access Boundary](/backend/07-security-data-protection/identity-access-boundary/)
- 平行：[cert-manager](/backend/07-security-data-protection/vendors/cert-manager/)（DNS-named cert lifecycle）、[HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)（用 SPIRE JWT-SVID 作 Vault auth method）、[AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/)（Roles Anywhere 接 SPIRE 發的 X.509-SVID）
- 下游：service mesh（Istio / Linkerd / Envoy）整合層、[Audit Log](/backend/knowledge-cards/audit-log/)
- 官方：[SPIFFE Specification](https://spiffe.io/docs/latest/spiffe-about/spiffe-overview/)、[SPIRE Documentation](https://spiffe.io/docs/latest/spire-about/)
