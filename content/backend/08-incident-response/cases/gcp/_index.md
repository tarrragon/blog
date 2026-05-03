---
title: "Google Cloud Platform"
date: 2026-05-01
description: "GCP 重大事故時間線與架構脈絡"
weight: 4
---

GCP 是全球 anycast + 強控制面整合的代表、Load Balancer / IAM 失效是全球控制面事故的教學標竿。Google 公開的 post-mortem 包含詳細時間線與技術細節、適合作為事故敘事範本。

## 規劃重點

- 全球控制面失效：IAM / Load Balancer 失效如何擴散到所有地區
- 配置變更的 blast radius：staged rollout 為何在 L7 LB 變更上難以實施
- Postmortem 結構：Google PIR 的 timeline / impact / root cause / action items 格式
- 跨服務依賴：Cloud SQL / GKE / Cloud Build 之間的隱性耦合

## 預計收錄事故

| 事件                  | 教學重點                          |
| --------------------- | --------------------------------- |
| Incident #20003       | Cloud IAM 造成多個 GCP 服務受影響 |
| Incident #20001       | Cloud IAM 區域性事故與連鎖影響    |
| External ALB incident | 控制面變更 staged rollout 的限制  |
| 下游服務退化案例      | 跨產品的 dependency 暴露          |

## 案例定位

GCP 這個案例在講的是全球控制面如何把單一變更擴成跨產品事故。讀者先看懂 LB、IAM 與 identity 依賴的責任，再把 status event 當成 postmortem 與容災設計的入口。

## 判讀重點

當 Load Balancer 或 IAM 出現問題時，故障不會只停在單一產品，而會沿著共享控制面擴散到 YouTube、Drive 或其他下游。當變更需要 staged rollout 時，重點不只是慢，而是能否在全球邊界上保留足夠的驗證空間。

## 可操作判準

- 能否指出事故是發生在 control plane 還是 data plane
- 能否把一個 LB 變更的影響範圍說清楚
- 能否在 status page 上對應到具體恢復階段
- 能否把 identity 依賴視為跨產品風險

## 與其他案例的關係

GCP 這頁和 Azure AD、AWS S3 是同一組「共享控制面」案例，只是 GCP 更強調全球服務整合。讀者若把這頁和 Cloudflare 一起讀，會更容易看出 staged rollout、identity 依賴與全球路由之間的互相牽制。

## 代表樣本

- Incident #20003 與 #20001 是 Cloud IAM 影響多服務的直接樣本。
- External ALB incident 顯示全球控制面變更為何需要保留驗證空間。
- LB、IAM 與 identity 依賴是同一條控制面鏈上的不同節點。
- 這類樣本適合和 Cloudflare / AWS S3 一起看。
- staged rollout 限制讓 global LB 變更不能只靠局部驗證。
- identity 控制面失效會把下游產品一起拉進事故。
- service health page 的粒度決定客戶能不能快速定位影響範圍。
- global load balancing 讓一個配置錯誤具有跨區同步效應。

## 引用源

- [Google Cloud Status Dashboard: Incident #20003](https://status.cloud.google.com/incident/zall/20003)：Cloud IAM 造成多個 GCP 服務受影響的官方事件摘要。
- [Google Cloud Status Dashboard: Incident #20001](https://status.cloud.google.com/incident/cloud-iam/20001)：Cloud IAM 區域性事故與連鎖影響。
- [Architecting disaster recovery for cloud infrastructure outages](https://cloud.google.com/architecture/disaster-recovery)：Google Cloud 的 LB / IAM / IAP / Identity Platform 容災說明。
- [Google Cloud Service Health: External Application Load Balancer incident](https://status.cloud.google.com/incidents/4jGVd9eWeezcNwH8cFhU)：Cloud Load Balancing 的全球影響案例。
