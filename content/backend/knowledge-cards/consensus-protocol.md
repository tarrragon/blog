---
title: "Consensus Protocol"
date: 2026-05-27
description: "說明多個節點如何在故障條件下達成一致決策、含 leader election 與常見演算法"
weight: 28
---

Consensus protocol 是讓多個獨立節點在訊息可能延遲、丟失、亂序的網路環境下、仍能對「同一個值 / 同一個決策」達成一致的演算法。常跟分散式鎖（distributed lock）一起出現、是水平擴展 stateful 服務時的協調基底。跟 [replication channel](/backend/knowledge-cards/replication-channel/) 是上下層關係 — consensus 決定一致順序、replication 負責複製狀態。實務上承擔三類責任：

- **Leader election**：從一群對等節點中選出單一主節點負責某類獨佔工作（執行排程、接受寫入、coordinate cluster state）。Leader 失效時、剩餘節點要在有限時間內選出新 leader。
- **State machine replication**：把 leader 接受的每筆變更同步到 followers、保證跨節點 state 一致。
- **Cluster membership**：追蹤哪些節點還活著、誰有資格成為 leader。

常見演算法包含 Paxos（理論基礎、難實作）、Raft（教學友善、Etcd / Consul / CockroachDB 採用）、ZAB（ZooKeeper 採用）、Multi-Paxos / EPaxos（Paxos 的工程變體）。所有 consensus 演算法都需要 majority quorum 才能繼續運作 — 5 節點 cluster 失去 3 節點以上、就會 split-brain 或停寫保護。

Consensus 不是免費操作。每筆 write 通常要跨 N/2+1 個節點 round trip、latency 隨 cluster 大小跟 region 分布升高；故障恢復期間 leader election timeout（典型 150ms-500ms）會造成短暫不可寫。水平擴展應用層時、若依賴 distributed lock 或 leader election 來協調工作、要把 consensus latency 算進事故時的 RTO。

對比參考：在不需要強一致的場景（log 分發、最終一致 cache），可以用 gossip protocol（如 SWIM、Serf）達成「最終一致」的成員管理、避開 consensus 的 latency 代價。

## 概念位置

Consensus protocol 處於分散式系統的協調控制層、是「跨節點達成單一決策」的工程基底。跟分散式鎖（distributed lock）是上下層關係（lock 服務通常底層用 consensus 實作）、跟 [replication channel](/backend/knowledge-cards/replication-channel/) 互補（consensus 保證一致順序、replication 負責複製狀態）。
