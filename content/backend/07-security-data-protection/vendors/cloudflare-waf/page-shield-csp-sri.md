---
title: "Cloudflare Page Shield：用 CSP + SRI + script monitoring 防 client-side supply chain"
date: 2026-05-18
description: "Page Shield 三層防禦（CSP / SRI / script monitoring）對應 Magecart / formjacking / skimmer / 第三方 SDK 注入的不同 attack pattern、Cloudflare dashboard + API 配置、四個 production 踩雷（inline script 漏 / dynamic loader / CSP report 噪音 / SRI hash mismatch）、跟 dev workflow + WAF 整合"
weight: 10
tags: ["backend", "security", "cloudflare", "page-shield", "client-side", "supply-chain", "deep-article"]
---

> 本文是 [Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/) overview 的 implementation-layer deep article。Overview 已說明 Cloudflare WAF 在入口治理譜系的定位、本文聚焦 *Page Shield* 這個 client-side（browser）supply chain attack 防禦工具 — 跟 WAF 攔 server-side request 是不同層。

## Attack pattern × Defense mechanism 對照

Client-side supply chain attack 不會被 WAF 看到 — 攻擊發生在 browser 渲染 page 時、不在 origin server 跟 client 之間的網路層。Page Shield 是 *browser-side script execution* 的監測 + 防禦層、跟 WAF 處理 *server-side request inspection* 互補不重疊。

| Attack pattern              | 表現                                                         | Page Shield 對應防禦              |
| --------------------------- | ------------------------------------------------------------ | --------------------------------- |
| Magecart 信用卡 skimmer    | 第三方 JS 被注入惡意 form listener、信用卡資訊送外部 endpoint | CSP `connect-src` + script alert |
| 第三方 SDK 被 compromise   | 廠商 CDN 被攻擊、SDK 改版內含 malicious payload              | SRI hash mismatch + script alert |
| Formjacking                | 結帳頁 form action 被改、submit 送外部 server                 | CSP `form-action` directive       |
| Inline script injection    | XSS / DOM-based injection 插入 `<script>` 跑外部 source       | CSP `script-src` + nonce          |
| Storage abuse              | malicious JS 讀 localStorage / cookies 送外部                | CSP `connect-src` + CSP report   |

三層防禦對應不同 attack 階段：

1. **CSP（Content Security Policy）**：browser-enforced policy、preventive、阻止違反 policy 的 script load / network request
2. **SRI（Subresource Integrity）**：load 階段 hash 驗證、detective + preventive、廠商 CDN 上 script 被改就 browser 拒載
3. **Script monitoring**：runtime 觀測、detective only、記錄頁面 load 哪些 third-party script、變動時 alert

三層各有 ceiling — *CSP 擋 inline / unauthorized source 但擋不到 allowed source 被 compromise*；*SRI 擋已知 vendor 改 hash 但擋不到動態 loader*；*monitoring 看得到但攔不到*。Production 三層疊用、不要單一 layer。

## CSP 配置 step-by-step

### 從 Cloudflare dashboard 啟用 + 寫 policy

```text
# Dashboard: Security → Page Shield → CSP
# 模式: Report-only（第一週）→ Enforced（驗證後）

# 範例 policy
default-src 'self';
script-src 'self' 'nonce-{NONCE}' https://cdn.trusted.com https://www.googletagmanager.com;
style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
img-src 'self' data: https:;
connect-src 'self' https://api.myapp.com https://*.sentry.io;
form-action 'self';
frame-ancestors 'none';
report-uri https://csp-report.cloudflare.com/cdn-cgi/script_monitor/report;
report-to default;
```

關鍵直覺：

- **`'nonce-{NONCE}'`**：origin server 每 request 生成 random nonce、注入 `<script nonce="...">` 跟 CSP header；script tag 沒對應 nonce 就被 browser 拒跑、擋 XSS
- **`connect-src` 精準寫**：第三方 API endpoint 全列出；不寫 `*` 或 `https:` 是擋 exfiltration 的關鍵（Magecart 把信用卡送外部 endpoint 就是用 `connect-src` 攔）
- **`form-action`**：擋 form 被改 action attribute 送外部、formjacking 第一道防線
- **`report-uri` + `report-to`**：违反 policy 的 event 送 Cloudflare、Page Shield dashboard 看 violation report

### Report-only mode 第一週

```text
Content-Security-Policy-Report-Only: <policy>
Content-Security-Policy:             default-src 'self';   # 鬆 policy 仍 enforce
```

Report-only 期間 browser *report 違反但不擋*、production traffic 不受影響；SOC 看 report 找：

- 漏列的 legitimate third-party（marketing / analytics SDK 沒寫進 policy）
- 意外 inline script（dev 留下的 debug snippet）
- 跨 domain 的合法 connect（CRM / chat widget）

第一週後 dashboard 看 violation 數量趨穩 + 主要違規都已 whitelist、切 Enforced。

### Enforced mode 切換 + canary

不要直接全站 enforced — 用 Cloudflare Page Rule 對 10% traffic enforced、90% report-only：

```text
URL pattern: example.com/*
Page Rule: Add CSP header (enforced)
Bypass: 90% by Cookie / IP hash
```

10% traffic 跑 24-48h、確認 zero legitimate violation、再擴大到 50% → 100%。canary 期間 monitor `error-rate` metric、不只是 violation report。

## SRI 配置

Subresource Integrity 用 hash 驗證 CDN-hosted script 沒被改：

```html
<script src="https://cdn.example.com/widget.v1.2.3.js"
        integrity="sha384-oqVuAfXRKap7fdgcCY5uykM6+R9GqQ8K/uxy9rx7HNQlGYl1kPzQho1wx4JwY8wC"
        crossorigin="anonymous"></script>
```

Browser load 時算 hash、跟 `integrity` 不符就拒跑。關鍵：

- **Hash 一定要 version-pinned**：用 `widget.v1.2.3.js`、不能用 `widget.latest.js`；廠商更新 latest 時 hash 變 → SRI 拒載 → 服務中斷
- **多 hash**：寫 `integrity="sha384-... sha512-..."` 至少一個 match 就過、可在 vendor rotate hash 時平滑遷移
- **`crossorigin="anonymous"`** 必加：跨 origin script 預設 browser 不暴露 hash 失敗細節、`anonymous` 才允許 CORS-based hash check

### Page Shield 自動產 SRI 提示

Dashboard → Page Shield → Scripts 列出所有偵測到的 script、含 *建議 SRI hash*；可以 export 整合進 build pipeline、自動把所有 vendor script 加 SRI。

## 故障演練

### Case 1：CSP report flood，SOC noise

**徵兆**：切 Enforced 後、CSP violation report 從每天 ~500 漲到每分鐘 ~50K、Page Shield dashboard 變紅、SOC 收 alert 收到 silent。

**根因**：browser extension（廣告攔截 / spell checker / password manager）注入 inline script 跟 connect、被 CSP block 同時觸發 report；不是真實 attack、是 user 端 extension 行為。

**修法**：

1. CSP `report-sample` directive 限 sampling（只 report 10%）— spec 部分支援、不是所有 browser 都認
2. Page Shield 規則：filter out extension protocol（`chrome-extension://`、`moz-extension://`、`safari-extension://`）後再 alert
3. Report endpoint 自管 + aggregation：不直接接 SIEM、先 batch + dedupe、再送 SIEM
4. 接受 report flood 是 normal、focus 監測 *unique violation pattern* 不是 *total volume*

### Case 2：Inline script 漏，舊頁面突然壞

**徵兆**：切 Enforced 後 X 個舊頁面壞、user feedback 提交 form 失敗、debugger 看到 console `Refused to execute inline script because it violates...`。

**根因**：legacy page 有 inline `<script>` 沒 nonce、CSP enforced 後 browser 拒跑；報表/管理後台/舊 admin page 常見。

**修法**：

1. Audit 所有 inline `<script>`、加 nonce attribute（server-side render 時注入）
2. 短期：對舊頁面用 `unsafe-inline` 寫進 CSP（接受降級）、page-specific CSP override
3. 長期：legacy page 改 build-time bundle、消除 inline script

### Case 3：Dynamic script loader 繞過 SRI

**徵兆**：vendor script load 成功、但 Page Shield monitoring 看到該 vendor script *load 後又動態 load 多個額外 script*；額外 script 沒 SRI 保護、廠商側 compromise 直接過。

**根因**：第三方 SDK 用 `document.createElement('script')` + `script.src = '...'` runtime 動態 load；CSP `script-src` 可能允許這個來源、但 SRI 沒法在 runtime 注入。

**修法**：

1. CSP `script-src` 精準到 *只允許特定 path*、不是整個 domain（例：`https://cdn.vendor.com/sdk/v3/` 而不是 `https://cdn.vendor.com`）
2. 評估 vendor 是否有 *static-only* 替代（多數 marketing / analytics SDK 不需要 dynamic loader、是 legacy 設計）
3. 不能消除 dynamic loader 時、Page Shield monitoring 設 *new script alert*、廠商加 sub-script 即刻通知

### Case 4：SRI hash mismatch，vendor 偷偷更新

**徵兆**：第三方 widget 突然不顯示、Page Shield 顯示 SRI mismatch、廠商 status page 沒事故公告。

**根因**：廠商在 same URL（不是 versioned）下偷偷 push minor patch、hash 變了 → SRI 拒載；不是 attack、是 vendor 不遵守 immutable URL 慣例。

**修法**：

1. 強制要求廠商提供 versioned URL（`widget.v1.2.3.js`）、不收 `widget.latest.js`
2. 廠商不配合時、build pipeline 加 *daily hash check*、廠商偷改 SRI hash 自動更新 + Slack alert
3. 評估換 vendor — 不遵守 immutable URL 的廠商 supply chain integrity 信用低

## 容量 + cost

Page Shield 是 *Enterprise plan + Page Shield add-on*、cost 維度：

| 維度                | 影響                                                                                 |
| ------------------- | ------------------------------------------------------------------------------------ |
| CSP report 量       | Cloudflare 端聚合、不另外計費；report endpoint 自管要 sizing            |
| Script monitoring   | 不影響 page load latency（async detection）                                          |
| Per-zone pricing    | 跨子域 + apex domain 多 zone 各算一份                                                |
| SOC operation       | 第一週 report 量大、需要 1-2 analyst FTE 跑 tuning；穩定後低人力               |

Page load 影響：

- CSP header ~1-2KB（policy 寫越精準越長、不是越短越好）
- SRI 比對 ~5-10ms / script、現代 browser cache decoded hash、不重複算
- Script monitoring beacon ~100 byte / script load、async 不阻塞 page render

實務 default：

- Critical e-commerce / fintech：CSP enforced + SRI 全 vendor + monitoring all、SOC review weekly
- 一般 SaaS：CSP report-only ongoing + SRI critical vendor only + monitoring 主域
- Marketing / blog：CSP `default-src 'self'` minimum + monitoring only

## 整合 / 下一步

### 跟 dev workflow 整合

CSP 寫進 *deploy pipeline*、不是 dashboard 手動配：

1. Repo 內 `csp-policy.yml`、跟 code 同 lifecycle
2. CI 跑 *CSP linter*（如 `csp-evaluator`）、檢查 policy 弱點
3. Deploy 時 push 到 Cloudflare API、自動 versioning + rollback

### 跟 WAF 互補

Page Shield 跟 [Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/) 不重疊但互補：

- WAF 攔 *server-side* request injection（SQL / command / path traversal）
- Page Shield 攔 *client-side* script execution（XSS / supply chain）
- 共同 dashboard + alert routing、不要分開 SOC team 看

### 跟 supply chain SBOM

Page Shield 偵測的 *client-side dependency* 可進 SBOM、跟 [Snyk](/backend/07-security-data-protection/vendors/snyk/) / [Dependabot](/backend/07-security-data-protection/vendors/dependabot/) 的 server-side SBOM 合併、得到完整 dependency graph。

### 下一步議題

- **Trusted Types**：browser-side template injection 的下一代防禦、Chrome 已支援、Firefox / Safari 進度不一
- **CSP Level 3 + strict-dynamic**：減少 maintenance burden、用 nonce 動態信任 nested script
- **Reporting API v1**：standard report endpoint + `Reporting-Endpoints` header 取代 `report-uri`

## 相關連結

- 上游 vendor 頁：[Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/)
- 上游 chapter：[7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/)、[7.12 供應鏈完整性](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)
- 對照案例：British Airways 2018 Magecart / Macy's 2019 skimmer（公開 supply chain 案例）
- 平行 vendor：[AWS WAF](/backend/07-security-data-protection/vendors/aws-waf/) / [Fastly Next-Gen WAF](/backend/07-security-data-protection/vendors/fastly-ngwaf/)
- 平行 deep article：[Vault Dynamic Credential](/backend/07-security-data-protection/vendors/hashicorp-vault/dynamic-credential/) / [Splunk RBA](/backend/07-security-data-protection/vendors/splunk/risk-based-alerting/)
- Methodology：[Vendor 深度技術文章的寫作方法論](/posts/vendor-deep-article-methodology/)
