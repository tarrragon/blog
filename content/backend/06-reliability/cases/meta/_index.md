---
title: "Meta / Facebook"
date: 2026-05-01
description: "Meta Reliability Engineering 與超大規模事故學習"
weight: 23
---

Meta（前 Facebook）是超大規模分散式系統的代表、2021-10 BGP 全球失效事故是大規模事故敘事的教學標竿。Engineering blog 公開的 reliability 文章涵蓋 region failover、cell architecture 等深度實踐。

## 規劃重點

- BGP 與 DNS 自我封鎖：2021-10 事故揭露的內部依賴鎖死
- Region Failover：超大規模服務的跨區切換挑戰
- Cell Architecture：Facebook 規模下的 cell 設計
- Storm：Internal incident management 系統公開的設計

## 預計收錄實踐

| 議題                | 教學重點                            |
| ------------------- | ----------------------------------- |
| 2021-10 BGP 事故    | 配置變更鎖死自己、recovery 工具失效 |
| Region Failover     | 超大規模 traffic shift 的設計       |
| Storm IM System     | 內部 IR 工具的揭露                  |
| Reliability Reviews | 服務級可靠性審查制度                |

## 案例定位

Meta 這個案例在講的是超大規模系統如何面對全球級網路與控制面事故。讀者先抓 BGP、自我封鎖、region failover 與 MySQL Raft 這些原語，再把它們當成超大規模恢復能力的組件。

## 判讀重點

當外部路由或內部配置互相牽制時，事故會把恢復工具一起拖進失效狀態。當服務開始做更快的 failover 投資時，真正要看的不是單點工具，而是它是否能縮短恢復時間並降低手動介入成本。

## 可操作判準

- 能否分辨事故是路由、配置還是服務層問題
- 能否說明 region failover 的前置條件
- 能否把 IR 工具與對外說明串成一致時間線
- 能否把資料庫 failover 投資對應到恢復時間縮短

## 與其他案例的關係

Meta 的價值在於把超大規模網路事故和恢復工具放在一起看，這和 AWS S3、GCP、Cloudflare 都是在談「控制面出事時會擴散多遠」。如果先讀 Meta，再回看其他案例，會更容易看出 region failover 和 route propagation 的真正成本。

## 代表樣本

- 2021-10 BGP 事故顯示一個控制面變更可以讓整個公司失去對外可見性。
- MySQL Raft 代表的是把資料庫 failover 工具化，縮短人工介入時間。
- region failover 顯示超大規模 traffic shift 的成本。
- reliability reviews 讓服務級風險在變更前先被看見。
- cell architecture 讓大規模服務把故障切成可管理的單位。
- Storm 代表內部 incident management 工具如何支撐跨團隊協作。
- DNS 自我封鎖讓內外部控制面一起失效。
- traffic shift 讓恢復不只是切流量，而是管理整個依賴網。

## 引用源

- [More details about the October 4 outage](https://engineering.fb.com/2021/10/05/networking-traffic/outage-details/)：Meta 2021-10 outage 的技術回顧。
- [Update about the October 4th outage](https://engineering.fb.com/2021/10/04/networking-traffic/outage/)：事故初始公開說明。
- [Building and deploying MySQL Raft at Meta](https://engineering.fb.com/2023/05/16/data-infrastructure/mysql-raft-meta/)：更快 failover 與可靠性投資。
- [HydraBase – The evolution of HBase@Facebook](https://engineering.fb.com/2014/06/05/core-infra/hydrabase-the-evolution-of-hbase-facebook/)：分散式儲存與 failover 的早期實踐。
