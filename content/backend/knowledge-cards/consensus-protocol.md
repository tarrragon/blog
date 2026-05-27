---
title: "Consensus Protocol"
date: 2026-05-27
description: "讓多個獨立節點在訊息可能延遲、丟失、亂序的網路下對單一決策達成一致的演算法"
weight: 28
---

Consensus protocol 的核心責任是「讓多個獨立節點在訊息可能延遲、丟失、亂序的網路環境下、仍能對同一個值或同一個決策達成一致」。常見演算法：Paxos（理論基礎、難實作）、Raft（教學友善、Etcd / Consul / CockroachDB 採用）、ZAB（ZooKeeper 採用）、Multi-Paxos / EPaxos（Paxos 工程變體）。是 [leader election](/backend/knowledge-cards/leader-election/) 跟 [distributed lock](/backend/knowledge-cards/distributed-lock/) 的底層機制、跟 [replication channel](/backend/knowledge-cards/replication-channel/) 互補（consensus 保證一致順序、replication 負責複製狀態）。

## 概念位置

Consensus protocol 處於分散式系統的協調控制底層、上面分別構築 [leader election](/backend/knowledge-cards/leader-election/)、state machine replication、cluster membership 三類能力。每筆 write 通常要跨 majority quorum 節點 round trip — 5 節點 cluster 失去 3 節點以上就停寫保護（防範 split-brain）。對比 gossip protocol（SWIM、Serf）— consensus 給「強一致順序」、gossip 給「最終一致成員管理」、各自適用情境。

## 可觀察訊號與例子

Etcd / Consul / ZooKeeper 都是 consensus 服務、被 Kubernetes、Vault、Patroni 等系統當 coordination backend。實測 commit latency 隨 cluster 大小升高（3 節點同 AZ ~ 1-5ms、5 節點跨 region 可能 50-200ms）。故障恢復期間 election timeout 典型 150-500ms、期間短暫不可寫。CockroachDB / Spanner 在 OLTP write 路徑同樣依賴 consensus、是寫入延遲的下限。

## 設計責任

水平擴展 stateful 服務時、若依賴 distributed lock 或 leader election 來協調工作、要把 consensus latency 算進事故時的 RTO。Quorum 大小設計要考慮「容忍 N 節點失效」需要至少 2N+1 節點。跨 region 部署的 consensus 服務、要明示「region 失效時降級為 read-only」的策略 — region 失效時 quorum 可能跨不過、要事先規劃降級路徑。
