---
title: "Leader Election"
date: 2026-05-27
description: "從一群對等節點中選出單一主節點負責獨佔工作、leader 失效時自動選新 leader"
weight: 32
---

Leader election 的核心責任是「從一群對等節點選出單一主來執行某類獨佔工作（執行排程、接受寫入、coordinate cluster state）」。Leader 失效時、剩餘節點要在有限時間內選出新 leader。底層通常依賴 [consensus protocol](/backend/knowledge-cards/consensus-protocol/)（Raft / ZAB）保證選舉一致、確保任何時刻只有單一 leader（防範 split-brain）。是 [distributed lock](/backend/knowledge-cards/distributed-lock/) 在「服務角色互斥」這個情境的應用。

## 跟其他概念的關係

Leader election 處於分散式協調控制層、是 [consensus protocol](/backend/knowledge-cards/consensus-protocol/) 三大責任（election / state machine replication / cluster membership）中最常被獨立使用的一支。常見實作載體：ZooKeeper ephemeral node、Etcd lease + revision、Consul session、Kubernetes lease object、Redis 加 fencing token 的近似實作。

## 可觀察訊號與例子

每個 cluster 同時間至多一個 leader 持有 election lease；leader 失效後典型 election timeout 在 150ms-500ms 之間（依 consensus 算法跟 cluster 大小）。應用情境包含：分散式排程器（Quartz cluster、Apache Airflow scheduler）、Kafka controller、PostgreSQL primary 選舉（Patroni）、Kubernetes controller manager / scheduler 的 leader-elect 機制。

## 判斷條件與後果

Election timeout 的長短是兩種錯誤之間的取捨：太短時，網路抖動就被判成 leader 失效，觸發多餘的切換；太長時，leader 確實失效之後要等更久才選出新 leader，failover 延遲。舊 leader 因為程序暫停或網路分割，還不知道自己已經被取代時，舊 leader 與新 leader 並存（split-brain），沒有 fencing token 的話，資源側會接受兩者的寫入；單調遞增的 token 讓資源側拒絕帶著舊 token 的寫入。應用層沒有定義 follower 角色要做什麼時，失去 leader 身分的節點可能繼續執行獨佔工作，所以 follower 通常是 stand-by 加上監控 election event，每個獨佔操作之前主動檢查自己當前是否為 leader。
