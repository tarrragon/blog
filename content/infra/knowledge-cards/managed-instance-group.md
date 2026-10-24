---
title: "Managed Instance Group（MIG，代管執行個體群組）"
date: 2026-10-23
description: "VM 被自動重建之後設定不見、要決定一組 VM 的設定該寫在哪裡，或要判斷一台 VM 能不能直接刪掉重建時，查 GCP 的 MIG 與 instance template 怎麼建立、修復與更新 VM"
weight: 59
tags: ["infra", "knowledge-cards", "gcp", "compute"]
---

Managed Instance Group（MIG）是 GCP 依一份 instance template 自動維持一組相同 VM 的機制：它負責建出指定台數的 VM、在健康檢查失敗時重建、依負載增減台數，以及把整組換成新版 template。instance template 是建立 VM 的完整設定（機器類型、映像、磁碟、網路、[Network Tag（網路標籤）](/infra/knowledge-cards/network-tag/)、metadata、服務帳號），建立之後不能修改。AWS 的對應機制是 Auto Scaling group 加 launch template。可先對照 [EC2](/infra/knowledge-cards/ec2/) 與 [IaC](/infra/knowledge-cards/iac/)。

## 概念位置

MIG 把「一台 VM」換成「一份設定產生的一組 VM」：VM 隨時可能依 template 被重建或替換：`recreate-instances` 沿用原本的名稱、換一顆新的開機磁碟（實測一次時執行個體 ID 也沒變，gcloud 說明寫 ID 可能改變）；滾動更新的預設替換方式 `substitute` 建出新名稱、新 ID 的 VM；擴增則新建 VM。不論哪一種，只存在某一台開機磁碟上的修改都會在下一次重建時消失，要持久的設定一律寫進 template，改設定的方式是建一份新 template 再滾動更新。這是[不可變基礎設施](/backend/knowledge-cards/immutable-image/)的做法：它適合 VM 本身沒有不能丟的狀態的工作負載；有狀態時用 stateful 設定保留指定的磁碟與 IP，或改成單獨管理的 VM。GKE 的 node pool 在底下也是 MIG，但那一組由 GKE 管理，設定改在 node pool 上。template 裡的 [Network Tag（網路標籤）](/infra/knowledge-cards/network-tag/) 決定防火牆規則套不套得到新建的 VM。

## 可觀察訊號

- VM 的 metadata 有 `created-by` 鍵，值是建立這台 VM 的 MIG 的資源路徑（VM 被移出 MIG 之後仍然留著，現在的成員以 `gcloud compute instance-groups managed list-instances` 為準）；名稱是 `gke-...-grp` 的 MIG 屬於 GKE 叢集
- 半夜自動修復之後，某台 VM 上手動加的 tag、metadata 或帳號不見了
- `gcloud compute instance-groups managed list-instances <mig-name>` 的 `INSTANCE_TEMPLATE` 欄顯示每台 VM 用的是哪一份 template

## 設計責任

管理通道、監控代理這類要在每台 VM 上都成立的設定寫進 template 或映像，不靠逐台指令。改 template 時先讀出現行 template 的完整設定逐項帶進新的一份，因為新 template 從預設值開始；先讓一台 VM 換新版驗證再整組更新，舊 template 留到新版驗證完。整組由 IaC 管理時，改動寫在程式碼裡，CLI 上的修改會在下一次套用時被改回。

## 鄰卡

- [Network Tag（網路標籤）](/infra/knowledge-cards/network-tag/) — template 裡決定防火牆規則套不套得到新 VM 的欄位
- [Serial Console（序列主控台）](/infra/knowledge-cards/serial-console/) — 單台 VM 的救援入口；MIG 裡多了依 template 重建這條路
- [IaC](/infra/knowledge-cards/iac/) — MIG 與 template 多半由 IaC 管理
- 實作見 [GCP 上由 MIG 與 GKE 管理的 VM 的管理存取](/infra/cloud-providers/gcp/gke-mig-management-access/)
