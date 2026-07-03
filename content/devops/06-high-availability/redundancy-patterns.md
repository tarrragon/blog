---
title: "冗餘設計模式"
date: 2026-07-03
description: "在 active-passive、active-active、multi-region 之間選冗餘模式時，用資料同步方式與 standby 是否服務流量來區分，並知道冗餘不等於備份"
weight: 2
tags: ["devops", "high-availability", "redundancy", "active-active", "multi-region"]
---

單點有了替代路徑之後，那一份備援要怎麼擺——閒著等、還是也一起服務？冗餘設計模式沿兩個維度區分三種主要形態：備援的那一份服不服務流量（active-passive 的備援閒著等、active-active 的備援也在幹活），以及資料怎麼同步（同步副本幾乎不丟資料、非同步副本有延遲窗口）。選哪一種，決定了冗餘的成本、切換的速度、以及切換時可能丟多少資料。

## Active-passive：備援熱備、不服務流量

Active-passive 是最基礎的冗餘形態：有一個備援節點存在、隨時準備接手，但平時不服務任何流量。雲端資料庫的 multi-AZ 就是它的典型形態——用一個布林屬性開啟，背後是在另一個可用區維護一個同步副本，主庫的可用區故障時自動切到這個 standby，秒級到一兩分鐘的窗口後恢復。這個 standby 是熱備、不可讀——它不接受任何查詢流量、也不提供讀取擴展，純粹在那裡等 failover。要分攤讀流量得另開唯讀副本（那是另一個資源、另一個機制）。

Active-passive 的可用性不是零中斷。failover 期間，應用到資料庫的連線會斷、需要重連；應用層若沒有連線中斷後的重試邏輯，這個 failover 就從「透明切換」變成「使用者可見的服務中斷」。冗餘節點準備好了，不代表切換對上層是無感的——上層要配合處理切換瞬間的連線中斷，冗餘才真的透明。這個「切換對上層透明」的前提，是 failover 機制那章的主題。

## Active-active：備援也服務流量

Active-active 讓備援的那一份也承接流量，不是閒著等。它的好處是那份冗餘資源沒有閒置——平時就在分攤負載、故障時少一份也還撐得住。代價是它要求所有份都能同時服務，對有狀態的部分（資料庫）意味著多份要同時可寫或至少可讀，資料一致性的協調比 active-passive 複雜得多。無狀態的應用層做 active-active 很自然（每個實例都對等，這正是 [水平擴展](/devops/02-horizontal-scaling/) 的無狀態設計）；有狀態的資料層做 active-active 要處理多寫衝突或讀寫分離，難度高得多。

## Multi-region：在冗餘之上疊地理層

Multi-region 是在 active-passive 或 active-active 之上再疊一層地理冗餘，解的是「整個 region 不可用」的極端情境。它靠幾個機制組合：跨 region 的唯讀副本、跨 region 的物件儲存複製、以及 DNS 層的 failover 路由（健康檢查加 DNS 切換）。做到極致的可用性很可觀——有客服平台跨 15 個 region 用分散式資料庫達成 99.999% 的可用性，等於一年只停機約 5 分鐘。

Multi-region 跟同 region 冗餘的關鍵差異在資料同步。同 region 的 multi-AZ 是同步副本，failover 幾乎不丟資料；跨 region 的複製是非同步的、有延遲，failover 時會落在「複製延遲窗口」裡的資料就丟了。這個同步方式的差異直接決定了能承受多少資料遺失——同步副本對應接近零的資料落差，非同步跨 region 對應一個延遲窗口的落差。這條差異是 [disaster recovery](/devops/06-high-availability/disaster-recovery/) 裡 RPO 的來源。

## 冗餘不等於備份

冗餘模式有一個常見的誤解要拆穿：冗餘防的是硬體與可用區故障，不防邏輯損壞。multi-AZ 的 standby 是同步副本——一個誤刪的 table、一個算錯的批次 UPDATE、一個有 bug 的 migration，會被同步複製到 standby，兩份一起壞。active-active 也一樣，錯誤的寫入會傳到每一份。冗餘讓「硬體掛了還有另一份」，但那另一份跟壞掉的這份內容一模一樣，對邏輯錯誤毫無保護。

防邏輯損壞的是另一條正交的防線：備份與時間點還原（PITR）。冗餘管的是可用性（硬體或 AZ 掛了服務不中斷），備份管的是可還原性（資料被邏輯性破壞後能倒回某個時間點）。這兩者職責正交，要分別配置、分別驗證——不能把冗餘當成備份，也不能因為有備份就省掉冗餘。

## 冗餘要靠 drill 驗證

冗餘設計「宣稱有效」不等於「實測有效」。一個 multi-AZ 切換窗口寫在文件上說「秒級」，跟它在真實故障下確實秒級切換，是兩回事——中間可能卡在應用沒重連、監控誤報、或 failover 腳本的某個前提在 production 不成立。驗證的手段是 chaos drill：用基礎設施層的故障注入（AZ failure、region failure，雲端的 chaos 工具支援）真的打掉一個可用區，看冗餘有沒有按預期接手、切換窗口是不是真的在承諾內。冗餘設計要從紙面轉成證據，靠的是演練，這條延伸到 [disaster recovery](/devops/06-high-availability/disaster-recovery/) 的演練節奏。

## 下一步路由

- 冗餘準備好了，切換怎麼觸發、怎麼對上層透明 → [Failover 機制](/devops/06-high-availability/failover-mechanism/)
- 同步 vs 非同步副本怎麼對應 RPO、演練怎麼跑 → [Disaster recovery 策略](/devops/06-high-availability/disaster-recovery/)
- 冗餘至少 2x 資源，值不值得 → [高可用的成本](/devops/06-high-availability/ha-cost/)
- multi-AZ 是 infra 層的能力，怎麼在 IaC 開啟 → [infra Stateful 資源保護](/infra/05-core-services/stateful-protection-dependency/)
