---
title: "Self-managed Kafka → AWS MSK：把 $15K/month operational cost 拆解到 managed"
date: 2026-05-19
description: "Kafka self-managed → MSK 是 Type C operational redesign — protocol 完全相容、operational stack（ZooKeeper / brokers / monitoring / patching）全託管；本文用 cost 拆解開頭、5 個 production 踩雷（client connection pattern / version pinning / metric pipeline / IAM auth / cross-cluster mirror）"
weight: 12
tags: ["backend", "message-queue", "kafka", "msk", "managed", "migration", "type-c"]
---

> 本文是跨 vendor migration playbook、cross-link [Kafka](/backend/03-message-queue/vendors/kafka/) 跟 AWS MSK。跑 [migration-playbook-methodology 6 維 audit](/posts/migration-playbook-methodology/) 後對映 *Operational = High（self-managed → AWS managed）→ Type C operational redesign hybrid*。

## $15K/month operational cost 拆解

跟 [Datadog → Grafana Stack](/backend/04-observability/vendors/datadog/migrate-to-grafana-stack/)（H cost variant）同 framing — 用 cost 拆解開頭、不是「為什麼遷」driver list：

| Self-managed Kafka cost 項                  | 中型 (3 broker + 3 ZK + monitoring) / month |
| ------------------------------------------- | ------------------------------------------- |
| EC2 (3× r6g.xlarge broker)                  | $660                                        |
| EBS (3× 1TB io2)                            | $1,500                                      |
| EC2 (3× t3.medium ZK / KRaft)              | $90                                         |
| Monitoring (Prometheus + Grafana on EC2)    | $200                                        |
| Backup S3 (1TB)                             | $25                                         |
| Cross-AZ traffic                            | $300                                        |
| **Operational FTE (0.5)**                   | **$5,000-8,000**                            |
| Patching window cost                        | $200 (downtime opportunity)                 |
| Total infrastructure                        | $7,975-10,975                               |
| Total with FTE                              | **$13,000-18,975**                          |

**最大成本塊是 operational FTE、不是 infrastructure**。MSK 把 50-80% operational 工作轉嫁 AWS、留 application + cost monitoring 給 SRE。

跑 [6 維 diff dimension audit](/posts/migration-playbook-methodology/)：

| 維度                 | 評估                                              | 等級       |
| -------------------- | ------------------------------------------------- | ---------- |
| Schema / API         | 同 Kafka protocol、client SDK 不改               | Low        |
| Operational model    | Self-managed → AWS managed、HA / patch / backup 全託管 | **High** |
| Paradigm             | 同 Kafka log-based                                | Low        |
| Components           | 同 1 個 Kafka cluster                             | Low        |
| Application change   | Auth config 改（IAM / SASL）、其他不變            | Low-Medium |
| Data topology        | 同 broker + partition 配置                       | Low        |

Operational = High（其他 Low-Medium）→ **Type C operational redesign hybrid**。

## 為什麼遷：FTE / availability / consistency 三條 driver

- **Operational FTE**：Kafka self-managed + ZooKeeper / KRaft + Prometheus 端到端 ops 是 0.5-1 FTE、MSK 把 patch / HA / backup 全託管
- **Availability**：MSK 自動 multi-AZ broker + auto-recovery、self-managed 自管 broker 故障 RTO 30 分鐘-2 小時
- **Consistency with cloud stack**：已 deep on AWS（RDS / S3 / Lambda）、MSK 進 same VPC + IAM auth、降低 cross-vendor 設置成本

反向 driver（MSK → self-managed）：

- Throughput / GB 規模大時 MSK 跨 broker cost 反轉（cost > self-managed）
- 需要 Kafka 客製化（custom plugin / kraft early adopter / 非 AWS region）
- Multi-cloud / hybrid 架構不想 vendor lock

## Operational redesign 對位

跟 [PostgreSQL → Aurora](/backend/01-database/vendors/postgresql/migrate-to-aurora/) / [MongoDB → Atlas](/backend/01-database/vendors/mongodb/migrate-to-atlas/) 同 Type C pattern：

| Operational concept       | Self-managed Kafka                       | MSK                                              |
| ------------------------- | ---------------------------------------- | ------------------------------------------------ |
| Cluster bootstrap         | 手動配置 broker + ZK + brokers.properties | UI / Terraform 一鍵建                            |
| HA                        | 自管 replica + ISR + broker placement     | 自動 multi-AZ + auto-recovery                    |
| Patching                  | Rolling restart 手動 / 工具               | MSK 自動 monthly maintenance window              |
| Backup                    | 自管 MirrorMaker / cluster snapshot       | MSK 內建 backup（S3、自動）                      |
| Authentication            | SASL/SCRAM / mTLS 自管                    | IAM auth（推薦）/ SASL/SCRAM via Secrets Manager |
| Monitoring                | Prometheus + JMX exporter 自建            | CloudWatch + open monitoring + Prometheus       |
| Sizing                    | 手動 broker instance class                | MSK broker size（kafka.m5.large+）              |
| Configuration             | server.properties 全控                    | Configuration set（限制可調 parameter）          |
| Cluster topology          | 自管 placement / rack awareness           | MSK 自動 multi-AZ + rack-aware                  |
| Tiered storage            | Kafka 3.6+ 自管                           | MSK Tiered Storage（auto-tier 到 S3）            |

每行 operational concept 都需要 migration plan、application code 不變但 *運維知識體系全換*。

## 4-phase migration（Type C 標準流程）

### Phase 0：Pre-migration audit

- **Workload sizing → MSK broker class**：當前 throughput / partition count / topic count
- **Application connection pattern audit**：客戶端 producer / consumer 用 SASL / mTLS / plaintext？哪個 application
- **Topic config audit**：retention / replication factor / cleanup policy
- **Backup pattern audit**：有 MirrorMaker / cross-cluster mirror 嗎

### Phase 1：MSK cluster 建置（2-3 週）

```hcl
resource "aws_msk_cluster" "main" {
  cluster_name           = "production"
  kafka_version          = "3.6.0"
  number_of_broker_nodes = 3

  broker_node_group_info {
    instance_type   = "kafka.m5.large"
    client_subnets  = var.private_subnets
    security_groups = [aws_security_group.msk.id]
    storage_info {
      ebs_storage_info {
        volume_size = 1000
        provisioned_throughput {
          enabled           = true
          volume_throughput = 500
        }
      }
    }
  }

  client_authentication {
    sasl {
      iam = true        # IAM auth (推薦)
      scram = false
    }
  }

  configuration_info {
    arn      = aws_msk_configuration.main.arn
    revision = aws_msk_configuration.main.latest_revision
  }

  encryption_info {
    encryption_in_transit {
      client_broker = "TLS"
    }
  }

  logging_info {
    broker_logs {
      cloudwatch_logs {
        enabled   = true
        log_group = aws_cloudwatch_log_group.msk.name
      }
    }
  }
}
```

### Phase 2：Data migration（MirrorMaker 2.0）

```text
Self-managed Kafka ──(MM2)──→ MSK
                       │
                consumer offset sync
                       │
                topic config sync
```

MM2 跑 1-7 天、依 topic 量 + retention 期間；replica.lag 對齊後進 cutover。

### Phase 3：Cutover

- Application 端切 bootstrap.servers 從 self-managed → MSK
- Producer 漸進切（10% → 50% → 100%）
- Consumer 切換時 offset 從 MM2 sync 過的位置開始
- Self-managed cluster read-only standby 2 週

## Production 故障演練

### Case 1：IAM auth 沒設、application 連不上

**徵兆**：cutover 後 application 報 `SaslAuthenticationException: Access denied`；MSK 端 cloudWatch log 顯示 IAM principal 不認。

**根因**：MSK IAM auth 要求 client 跑 *MSK IAM auth library*（Java 用 `aws-msk-iam-auth`、Python 用 `aws-msk-iam-sasl-signer-python`）；application 端用 standard Kafka client、不知道怎麼 sign IAM signature。

**修法**：

```python
# Python kafka-python + IAM auth
from aws_msk_iam_sasl_signer import MSKAuthTokenProvider
from kafka import KafkaProducer

class AwsMskIamProvider(MSKAuthTokenProvider):
    def token(self):
        return self.generate_auth_token('us-east-1')[0]

producer = KafkaProducer(
    bootstrap_servers='b-1.mycluster.kafka.us-east-1.amazonaws.com:9098',
    security_protocol='SASL_SSL',
    sasl_mechanism='OAUTHBEARER',
    sasl_oauth_token_provider=AwsMskIamProvider(),
)
```

EKS pod 必須有 IAM role（IRSA）對 MSK cluster `kafka-cluster:Connect` action。

### Case 2：Version pinning、3.6.0 跟 self-managed 行為差

**徵兆**：cutover 到 MSK 3.6.0 後、某些 consumer 跑舊 client 失敗；新 broker 改 default `inter.broker.protocol.version` 但 client 不認。

**根因**：MSK 升 Kafka version 後 broker config 變動、舊 client（< 2.8）跟新 broker 協議不對；self-managed 端可能用更舊 broker version 跑、看不出問題。

**修法**：

1. **Pre-migration**：所有 client 升 Kafka client library 2.8+
2. **MSK kafka_version 對齊 self-managed**：先建 MSK 3.0 / 3.5、跟 self-managed 一致、cutover 後再升
3. **Phase rollout**：用 *Tiered Storage* + retention 策略保留舊資料、新 producer / consumer 用新 version

### Case 3：Metric pipeline 失效、SOC dashboard 無數據

**徵兆**：cutover 後 Grafana dashboard 顯示 MSK metric 0；舊 JMX exporter 抓不到 MSK；CloudWatch 有 metric 但 SOC 端不接 CloudWatch。

**根因**：MSK 不暴露 JMX、metric 走 CloudWatch / open monitoring (Prometheus + Grafana)、跟自建 JMX-based pipeline 不對等。

**修法**：

1. **Open monitoring enabled**：MSK config 設 `open_monitoring.prometheus.jmx_exporter.enabled = true`、跑 Prometheus 對 MSK broker 拉 metric
2. **CloudWatch → Prometheus**：用 `cloudwatch-exporter` 拉 CloudWatch metric 進 Prometheus
3. **Dashboard refresh**：Grafana dashboard 對 MSK-specific metric name 重寫（`kafka_server_*` → `aws_kafka_*` 或統一 alias）

### Case 4：Cross-cluster mirror（MM2 → MSK）配置複雜

**徵兆**：MM2 跑了 1 週、self-managed 跟 MSK consumer offset 沒同步；application 切過去後 *重新讀整批舊資料*、duplicate processing。

**根因**：MM2 consumer offset sync 需要 *跨 cluster* mapping、source 端 offset 跟 target 端 offset 不直通；MM2 預設 offset sync 沒打開。

**修法**：

```properties
# MM2 config
source.consumer.bootstrap.servers=self-managed-kafka:9092
target.consumer.bootstrap.servers=msk-cluster:9098
target.security.protocol=SASL_SSL
sync.group.offsets.enabled=true       # 必須打開
emit.checkpoints.enabled=true
checkpoints.topic.replication.factor=3
```

**Architecture**：consumer 切換時讀 *MM2 checkpoint* topic、不直接讀 internal offset；application 端用 *idempotent* + *dedup key*、avoid duplicate processing。

### Case 5：MSK billing 暴漲、Tiered Storage / cross-AZ 沒控

**徵兆**：MSK 第一個月帳單比預估高 50%；breakdown 後發現 cross-AZ traffic（producer/consumer 跨 AZ）+ Tiered Storage 退到 S3 的 hot tier。

**根因**：

- MSK auto multi-AZ deployment 不可避免 cross-AZ traffic、producer 寫 partition leader 可能跨 AZ
- Tiered Storage 對 hot data（retention < 24 小時）會多 storage cost；cold data 才 cost-effective

**修法**：

1. **Application AZ-aware routing**：producer 走 same-AZ broker（用 rack-aware producer config）、降 cross-AZ
2. **Retention 對齊 hot tier**：< 24 小時 retention 用 broker local storage、24 小時+ 才走 Tiered Storage
3. **Reserved instance**：MSK 不直接 reserved、但 EBS / data transfer 可預付、降 10-20%

## Capacity / cost

| 維度                | Self-managed Kafka                | MSK                                          |
| ------------------- | --------------------------------- | -------------------------------------------- |
| Cluster cost (3 broker) | $660 EC2 + $1500 EBS = $2,160 | $2,500-3,500（含 storage + multi-AZ）       |
| Operational FTE     | 0.5-1 FTE = $5K-10K               | 0.1-0.3 FTE = $1K-3K                         |
| Patch / maintenance | Manual + downtime opportunity     | Auto + maintenance window scheduled          |
| Backup              | Self-managed MirrorMaker          | Built-in（S3 archive、auto）                |
| Metric / monitoring | Prometheus + Grafana self-deploy   | CloudWatch + open monitoring                 |
| Cross-AZ traffic    | Limited by VPC layout             | Auto multi-AZ、cross-AZ traffic cost 注意    |
| Tiered storage      | Kafka 3.6+ self-managed           | MSK built-in tiered storage                  |
| Total (3 broker, 中型) | $7K-11K / mo (含 FTE)            | $3.5K-6.5K / mo (含 FTE)                     |
| Migration cost      | -                                 | 1-3 FTE × 1-2 個月                          |

**判讀**：< 50 broker organization MSK ROI 通常 6-12 月持平、之後省 FTE；50+ broker 大 organization 自管 cost 可能反而低。

## 整合 / 下一步

### 跟 [Kafka ↔ NATS migration](/backend/03-message-queue/vendors/kafka/migrate-from-to-nats/) 對位

兩條 Kafka 出路：

- MSK：operational simplification、protocol drop-in、cost 中等漲；適合 *繼續用 Kafka paradigm* 的 organization
- NATS：paradigm shift、application 必須改、適合 *單純 messaging 不要 event sourcing* 的 use case

多數 organization 不需要 paradigm shift、MSK 更合理；真正需要 lightweight messaging 才走 NATS。

### 跟 [Confluent Cloud](https://www.confluent.io/confluent-cloud/) 對位

Confluent Cloud 是另一個 managed Kafka、跨 cloud（AWS / GCP / Azure）；MSK 是 AWS-only、但跟 IAM / VPC 整合更深。Multi-cloud organization 走 Confluent、AWS-deep organization 走 MSK。

### 跟 IAM / Secrets Manager 整合

MSK + IAM auth + Secrets Manager（連 [Vault → AWS Secrets Manager migration](/backend/07-security-data-protection/vendors/hashicorp-vault/migrate-to-aws-secrets-manager/)）是 AWS-deep stack 的標準組合；short-lived credential + IRSA 是 production best practice。

### 反向 migration（MSK → self-managed）

少見、通常是 *cost 反轉*（大 scale）或 *multi-cloud strategy*；流程鏡像對稱、注意 MSK Tiered Storage data 不直接 export、需要 *先 disable tiered storage* + recall data。

### 下一步議題

- **MSK Connect**：managed Kafka Connect、降 connector 運維、但 plugin ecosystem 比 self-managed Connect 少
- **MSK Serverless**：burst workload 適合、steady workload 反而貴
- **Cost monitoring playbook**：MSK billing 拆解每月跑一次、catch unexpected egress / tiered storage cost

## 相關連結

- Source vendor：[Kafka](/backend/03-message-queue/vendors/kafka/)
- 平行 migration playbook (Type C)：[PostgreSQL → Aurora](/backend/01-database/vendors/postgresql/migrate-to-aurora/) / [MongoDB → Atlas](/backend/01-database/vendors/mongodb/migrate-to-atlas/)
- 平行 H cost variant：[Datadog → Grafana Stack](/backend/04-observability/vendors/datadog/migrate-to-grafana-stack/)
- 平行 paradigm shift：[Kafka ↔ NATS](/backend/03-message-queue/vendors/kafka/migrate-from-to-nats/)
- Methodology：[Migration playbook methodology](/posts/migration-playbook-methodology/)
