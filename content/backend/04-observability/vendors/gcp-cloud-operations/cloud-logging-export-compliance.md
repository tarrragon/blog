---
title: "Cloud Logging 查詢、匯出與合規"
date: 2026-06-22
description: "說明 GCP Cloud Logging 的查詢語言、log router / sink 匯出架構、retention 設計、organization-level 聚合、audit log 與 PII / CMEK 合規治理"
weight: 11
tags: ["backend", "observability", "gcp", "cloud-logging", "compliance"]
---

> 本文是 [GCP Cloud Operations](/backend/04-observability/vendors/gcp-cloud-operations/) 的 vendor deep article，深化 overview「Cloud Logging 結構化 logs」跟「BigQuery 匯出長期儲存」段。初次接觸 GCP 觀測的讀者建議先讀 [GCP Cloud Operations 服務頁](/backend/04-observability/vendors/gcp-cloud-operations/)。

## 問題情境

Cloud Logging 對 GCP 服務是預設開啟的 — GKE、Cloud Run、Cloud Functions 的 stdout/stderr 自動進 Cloud Logging，工程師不需要配置就能查。問題出在後續階段：log 量成長後的成本控制（GCP 的 ingestion 計費讓高 volume 服務成本快速累積）、合規需求要求特定 log 保留特定時間（healthcare / fintech 的 7 年留存）、organization-level 的 log 聚合與存取控制（多 project 集中 audit）、以及 PII 在 log 中的遮罩與加密。理解 Cloud Logging 的 router / sink 架構跟 retention bucket 才能從「預設全收」走向「可治理的 log pipeline」。

## 核心概念

### Log Router 與 Sink

Cloud Logging 的資料流是 **log entry → log router → sink → destination**。每一筆 log 進入 Cloud Logging 後，log router 根據 inclusion filter 跟 exclusion filter 決定這筆 log 送到哪些 destination。

**Sink** 是 log router 的輸出端點。每個 GCP project 預設有兩個 sink：`_Required`（admin activity audit log、system event，不可關閉）和 `_Default`（其他所有 log、送到 `_Default` log bucket、可修改 filter）。工程師可以建立自訂 sink，把符合條件的 log 送到 BigQuery、Cloud Storage、Pub/Sub 或 Splunk。

**Exclusion filter** 在 log router 層攔截 — 被排除的 log 不會寫入任何 sink destination，也不計入 ingestion 計費。這是成本控制的第一道防線。

**Inclusion filter** 在 sink 層生效 — 只有符合 filter 的 log 會送到該 sink 的 destination。

路由順序很重要：exclusion filter 先執行（全域攔截），然後 `_Required` sink 攔走必留 log，然後 `_Default` sink 跟自訂 sink 各自的 inclusion filter 平行執行。一筆 log 可以同時送到多個 sink。

### Retention 與 Log Bucket

Cloud Logging 的儲存單位是 **log bucket**。每個 project 預設有兩個 bucket：

- `_Required` bucket：admin activity audit log 跟 system event，保留 400 天，不可刪除或修改 retention
- `_Default` bucket：其他所有 log，預設保留 30 天，可調整為 1-3650 天

自訂 log bucket 可以設定不同 retention 期。常見用法：把 application log 留 30 天、把 audit log 留 7 年（送到自訂 bucket 或 BigQuery）。

Cloud Logging 的 ingestion 計費跟 storage 計費是分開的。前 50 GiB/month per billing account 的 ingestion 免費；超過後按 ingestion volume 計費。`_Required` log 的 ingestion 免費。Storage 在 `_Default` bucket 的前 0.5 GiB 免費，自訂 bucket 按用量計費。

成本治理判讀：高 volume 服務（例如 GKE 的 container stdout）的成本主要來自 ingestion，而非 storage。Exclusion filter 攔掉不需要的 log 是最直接的降成本方式。

### 查詢語言

Cloud Logging 的查詢語言用在 Logs Explorer 跟 gcloud CLI：

```text
resource.type="k8s_container"
resource.labels.cluster_name="prod-us-central1"
severity>=ERROR
jsonPayload.order_id="ord-12345"
timestamp>="2026-06-22T00:00:00Z"
```

語法特點：field path 用 `.` 分隔、支援 comparison operators（`=` / `!=` / `>` / `>=` / `<` / `<=`）、支援 boolean（`AND` / `OR` / `NOT`）、支援 regex（`=~` / `!~`）。

跟 KQL（Elastic）或 LogQL（Loki）相比，Cloud Logging 查詢語言更接近 structured filter 而非 full-text search。Full-text 搜尋要用 `textPayload:` 或 `jsonPayload:` prefix。進階分析（aggregation、time bucketing、join）需要匯出到 BigQuery 後用 SQL 做。

## 配置 step-by-step

### Organization-level log 聚合

多 project 環境下，集中 log 的標準做法是在 organization 或 folder level 建立 aggregated sink：

```text
gcloud logging sinks create org-audit-sink \
  bigquery.googleapis.com/projects/central-audit/datasets/org_audit_logs \
  --organization=123456789 \
  --include-children \
  --log-filter='logName:"cloudaudit.googleapis.com"'
```

`--include-children` 讓 organization 下所有 project、folder 的符合 log 都送到同一個 BigQuery dataset。Sink 的 service account 需要 destination 的寫入權限（BigQuery Data Editor）。

適用場景：SOC 團隊需要跨 project 的 audit log 查詢、compliance team 需要集中的 data access log 存檔、security team 需要異常 IAM 變更的全域偵測。

### Data Access Audit Logs 啟用

GCP 的 audit log 分三類：

- **Admin Activity**：對資源的管理操作（建立 / 刪除 / 修改 IAM）。預設開啟、不可關閉、不計費。
- **Data Access**：對資源的讀取操作（BigQuery query、GCS read、Cloud SQL connect）。預設關閉（除 BigQuery）、需手動啟用、計費。
- **System Event**：GCP 系統自動操作。預設開啟、不可關閉、不計費。

Data Access audit log 的啟用是 per-service、per-project（或 org level）。啟用後 log 量會大幅增加 — 一個高 QPS 的 Cloud SQL 服務可能每秒產生數百筆 data access log。成本跟 volume 判讀要先做。

建議做法：先對 security-sensitive 服務啟用（IAM / KMS / Cloud SQL / GCS），其他服務按需啟用。用 exclusion filter 精細控制 — 例如只保留 `ADMIN_READ` 跟 `DATA_WRITE`、排除 `DATA_READ`（read 量通常遠大於 write）。

### VPC Flow Logs 與 DNS Logs 的觀測用途

VPC Flow Logs 記錄每一筆通過 VPC 的網路流量元資料（src/dst IP、port、protocol、bytes、packets）。啟用方式是 per-subnet 設定、支援 sampling rate（100% / 50% / 10%）。

DNS Logs 記錄 VPC 內的 DNS 查詢（query name、response code、source VM）。啟用方式是 per-VPC 或 per-policy 設定。

觀測用途：

- **異常流量偵測**：VPC Flow Logs 送到 BigQuery 後用 SQL 找出異常流量模式（大量對外連線、非預期 port、跨 region 資料傳輸）
- **網路效能分析**：量測 inter-service latency、跨 AZ 流量比例
- **安全稽核**：DNS Logs 偵測 DNS tunneling 或 C2 callback

成本注意：VPC Flow Logs 在高流量服務上的 ingestion 量非常大。100% sampling + 高 QPS 服務可能每天產生 TB 級 log。建議用 sampling rate 控制、或只對 security-sensitive subnet 啟用 100%。

### 自建 vs managed pipeline 的取捨

[Cloudflare 觀測案例](/backend/04-observability/cases/cloudflare-internal-observability-architecture/)展示了自建觀測 pipeline 的理由 — 全球 300+ edge locations、每秒數十億 request 的規模下，SaaS 觀測平台的帳單不合理，自建 pipeline 的 compute 成本反而更低。

但多數團隊的結論是反過來的。GCP 環境下，Cloud Logging 的 managed pipeline（log entry → router → sink → BigQuery / Cloud Storage）幾乎不需要維運人力。自建等價的 pipeline（Fluent Bit → Kafka → Elasticsearch / BigQuery）需要維運 Kafka cluster、Elasticsearch cluster、Fluent Bit DaemonSet 的升級與監控。

判斷分水嶺的兩個維度：

| 維度       | 偏向 managed（Cloud Logging） | 偏向自建                                                    |
| ---------- | ----------------------------- | ----------------------------------------------------------- |
| Log volume | < 1 TB/day                    | > 10 TB/day（SaaS ingestion 成本超過自建 compute）          |
| 查詢需求   | Logs Insights + 偶爾 BigQuery | 需要 Elasticsearch 的全文搜尋 + aggregation + visualization |

1-10 TB/day 的灰色地帶取決於查詢模式 — 如果 Logs Insights 能滿足 90% 的查詢、BigQuery 能處理剩下 10% 的分析，不需要自建。如果團隊需要 Kibana dashboard、Elasticsearch alerting、或跨 cloud 的統一 log backend，自建可能更合理。

### Healthcare 分層 retention 在 GCP 的實現

[Healthcare 案例](/backend/04-observability/cases/healthcare-access-traceability-and-retention/)的核心需求是分層 retention — 不同 log 類型有不同的法規留存要求（data access audit log 要 6 年+、application operational log 要 90 天、debug log 要 7 天）。

在 GCP 上用三層架構實現：

**Hot 層（Cloud Logging custom bucket）**：application log 保留 90 天、audit log 保留 1 年。設定 custom log bucket + retention。優點是 Logs Explorer 直接可查、延遲低。

**Warm 層（BigQuery）**：audit log sink 到 BigQuery dataset，BigQuery 的 partition expiration 設 2 年。需要分析跟 correlation 時用 SQL 查。成本低於 Cloud Logging storage。

**Cold 層（Cloud Storage + Object Lifecycle）**：BigQuery 的 scheduled export 或直接 Cloud Logging sink 到 GCS bucket。Object lifecycle rule 把 90 天以上的 object 轉 Nearline / Coldline / Archive class。最終刪除設定在 7 年。

三層各自的 access control 要獨立設定 — cold 層的 GCS bucket 只有 compliance team 有讀取權限，application team 看不到。CMEK 在三層都啟用（Cloud Logging custom bucket 的 CMEK + BigQuery dataset 的 CMEK + GCS bucket 的 CMEK），金鑰由安全團隊集中管理。

### PII 治理與 CMEK

Cloud Logging 中的 PII 治理有三層：

**第一層：不寫入**。Application 端在 log 之前就遮罩 PII（email → `***@***.com`、credit card → last 4 digits）。這是最有效的方式，因為一旦寫入 Cloud Logging，即使後續刪除 log entry，在 deletion 前可能已經被 sink 匯出到 BigQuery / GCS。

**第二層：log 層過濾**。用 exclusion filter 把含 PII 的 log field 排除（例如排除特定 jsonPayload field）。限制是 Cloud Logging 的 exclusion filter 只能排除整筆 log entry，不能 redact 單一 field。需要 field-level redaction 的話，在 OTel Collector 或 Fluentd 層做 processor 處理、再送到 Cloud Logging。

**第三層：加密**。Cloud Logging 預設用 Google-managed encryption。需要自管金鑰的場景（HIPAA / PCI-DSS / 金融監管）用 CMEK（Customer-Managed Encryption Keys）。CMEK 設定在 log bucket 層 — 自訂 log bucket 可以指定 Cloud KMS key。`_Default` bucket 也可以啟用 CMEK（需要把 `_Default` bucket 的 region 從 `global` 改成特定 region）。

存取控制：Cloud Logging 的 IAM role 分 `roles/logging.viewer`（讀 log）、`roles/logging.privateLogViewer`（讀含 data access 的 log）、`roles/logging.admin`（管理 sink / bucket / filter）。Audit log 的存取用 `roles/logging.privateLogViewer`、不是一般的 `roles/logging.viewer`。對應 [稽核追蹤與責任邊界](/backend/07-security-data-protection/audit-trail-and-accountability-boundary/) 的 GCP 實作。

## 故障演練與邊界

### Exclusion filter 設太寬，重要 log 被丟掉

**觸發條件**：為了降成本建立 exclusion filter，但 filter expression 太寬泛（例如排除整個 severity=INFO），連帶排除了 business-critical 的 info-level log。

**表現**：事故時查不到關鍵 log、audit 證據鏈斷裂。因為 exclusion filter 在 ingestion 前執行，被排除的 log 無法回補。

**預防**：exclusion filter 建立後先用 `gcloud logging read` 驗證哪些 log 會被排除。用 Logs Explorer 的 preview 功能確認 filter 不會命中關鍵 log。對 audit log 和 security log 不設 exclusion filter。

### BigQuery sink 匯出成本失控

**觸發條件**：org-level aggregated sink 把所有 log 送到 BigQuery，沒有 inclusion filter 限制。

**表現**：BigQuery storage 跟 streaming insert 成本暴增。一個中型 GKE cluster 每天可能產生 100+ GB 的 container log，全部送 BigQuery 的月成本可能超過 Cloud Logging 本身。

**修復**：在 sink 加 inclusion filter（只送 audit log 或 error-level log 到 BigQuery）。高 volume 的 application log 送 Cloud Storage（成本更低），需要查詢時用 BigQuery external table 做 federated query。

### Log entry size 超過限制

**觸發條件**：application log 寫入超過 256 KB 的單筆 log entry（Cloud Logging 的 per-entry 上限）。

**表現**：超過限制的 log entry 被截斷或拒絕寫入。

**修復**：application 端控制 log entry size — 大型 payload（request body / response body / stack trace）做 truncation 後再 log。需要完整內容的場景，把 payload 寫到 GCS、log 中只留 GCS URI。

## 容量與成本

| 計費項目                       | 免費額度                         | 超出後計費       |
| ------------------------------ | -------------------------------- | ---------------- |
| Ingestion（非 `_Required`）    | 50 GiB/month per billing account | per GiB ingested |
| Storage（`_Default` bucket）   | 0.5 GiB                          | per GiB-month    |
| Storage（custom bucket）       | 無免費額度                       | per GiB-month    |
| `_Required` log ingestion      | 不計費                           | 不計費           |
| BigQuery sink streaming insert | 依 BigQuery 計費                 | per GB inserted  |

成本最佳化優先序：

1. **Exclusion filter**：攔掉不需要的 log、最直接
2. **降 log level**：application 端把 verbose debug log 關掉
3. **Sampling**：高 QPS 服務的 request log 做 sampling（在 application 端或 OTel Collector 層）
4. **BigQuery sink filter**：只送需要長期分析的 log 到 BigQuery
5. **Cloud Storage sink**：高 volume + 低查詢頻率的 log 送 GCS、按需用 BigQuery external table 查

## 整合與下一步

- [GCP Cloud Operations 服務頁](/backend/04-observability/vendors/gcp-cloud-operations/)：overview 與日常操作
- [Cloud Monitoring Metrics Model 與 MQL](../cloud-monitoring-mql/)：同 vendor 的 metrics 面
- [4.12 Audit Log 邊界與 PII 治理](/backend/04-observability/audit-log-governance/)：跨 vendor 的 audit log 治理策略
- [4.C1 Fintech audit evidence](/backend/04-observability/cases/fintech-audit-evidence-observability/)：審計證據鏈的案例回寫
- [4.C3 Healthcare retention](/backend/04-observability/cases/healthcare-access-traceability-and-retention/)：長期保留的合規設計
- [07 security 模組](/backend/07-security-data-protection/)：data access audit log 的安全面
